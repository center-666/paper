"""E2 record-contract adapter around the immutable v2 Proposal/gate path."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

import numpy as np

import v2_estimators

METHODS = (
    "hard_gls_capped",
    "correct_joint_soft_impact_capped",
    "set_constrained_chebyshev",
)
ZERO_TOL = 1e-12
LOG_FIELDS = (
    "seed", "scenario", "main_case", "event", "age", "method",
    "raw_status", "proposal_status", "gate_status", "score", "threshold",
    "set_proposal_norm", "set_action_norm", "coverage_confirmed",
    "compatible_event_count", "zero_or_unresolved", "solver_stage",
    "solver_gap", "solver_reject_reason", "execution_success",
)


@dataclass(frozen=True)
class StatusRecord:
    """Original proposal object plus derived contract and executed-gate output."""
    raw: v2_estimators.Proposal | None
    proposal_status: str
    gate_status: str
    gated: v2_estimators.Proposal | None
    final_action: np.ndarray
    certificate_zero_or_unresolved: bool
    score_before_gate: float
    action_norm_before_gate: float
    action_norm_after_gate: float
    validation_status: str


def validate_input(z: Any, public_model: Mapping[str, Any]) -> str:
    """Validate only deployed inputs; never reads event labels or simulator data."""
    try:
        value = np.asarray(z, dtype=np.float64)
    except (TypeError, ValueError, OverflowError):
        return "INPUT_INVALID"
    if value.ndim != 1 or value.shape != (12,) or not np.all(np.isfinite(value)):
        return "INPUT_INVALID"
    try:
        sigma = np.asarray(public_model["Sigma_eta"], dtype=np.float64)
        if sigma.shape != (12, 12) or not np.all(np.isfinite(sigma)):
            return "MODEL_INVALID"
        if not np.allclose(sigma, sigma.T, rtol=1e-12, atol=1e-14):
            return "MODEL_INVALID"
        np.linalg.cholesky(sigma)
        u = float(public_model["U"])
        tq, tr = float(public_model["t_Q"]), float(public_model["t_r"])
        events = public_model["events"]
        if not (math.isfinite(u) and u > 0 and math.isfinite(tq) and tq > 0
                and math.isfinite(tr) and tr > 0 and len(events) == 8):
            return "MODEL_INVALID"
        keys = []
        for event in events:
            keys.append((int(event["edge"]), int(event["r"])))
            O = np.asarray(event["O"], dtype=np.float64)
            G = np.asarray(event["G"], dtype=np.float64)
            Szz = np.asarray(event["Sigma_zz"], dtype=np.float64)
            Sthz = np.asarray(event["Sigma_theta_z"], dtype=np.float64)
            if O.shape != (12, 2) or G.shape != (2, 2):
                return "MODEL_INVALID"
            if Szz.shape != (12, 12) or Sthz.shape != (2, 12):
                return "MODEL_INVALID"
            if not all(np.all(np.isfinite(m)) for m in (O, G, Szz, Sthz)):
                return "MODEL_INVALID"
            if not np.allclose(Szz, Szz.T, rtol=1e-12, atol=1e-14):
                return "MODEL_INVALID"
            np.linalg.cholesky(Szz)
        prior = public_model["prior"]
        p0 = float(prior["normal"])
        each = prior["each_event"]
        probabilities = ([float(each)] * 8 if np.isscalar(each)
                         else [float(p) for p in each])
        if (len(set(keys)) != 8 or len(probabilities) != 8
                or not math.isfinite(p0) or p0 <= 0
                or not all(math.isfinite(p) and p > 0 for p in probabilities)
                or abs(p0 + sum(probabilities) - 1.0) > 1e-12):
            return "MODEL_INVALID"
    except (KeyError, TypeError, ValueError, OverflowError, np.linalg.LinAlgError):
        return "MODEL_INVALID"
    return "VALID"


def raw_contract_status(raw: v2_estimators.Proposal) -> tuple[str, bool]:
    zero = bool((raw.certificate or {}).get("zero_or_unresolved", False))
    if raw.status == "VALID" and zero:
        return "ZERO_OR_UNRESOLVED", True
    if raw.status == "VALID" and float(np.linalg.norm(raw.action)) <= ZERO_TOL:
        return "ZERO_PROPOSAL", False
    return raw.status, zero


def adapt(raw: v2_estimators.Proposal | None, z: Any,
          public_model: Mapping[str, Any], threshold: float) -> StatusRecord:
    """Preserve raw object and apply the frozen gate to that exact object."""
    validation = validate_input(z, public_model)
    if not math.isfinite(float(threshold)):
        validation = "MODEL_INVALID"
    if raw is None:
        return StatusRecord(None, validation if validation != "VALID" else "MODEL_INVALID",
                            "NOT_CALLED", None, np.zeros(2), False, 0.0, 0.0,
                            0.0, validation)
    derived, zero = raw_contract_status(raw)
    gated = v2_estimators.apply_gate(raw, float(threshold))
    final = np.asarray(gated.action, dtype=np.float64).copy()
    if validation != "VALID":
        derived = validation
        final = np.zeros_like(np.asarray(raw.action, dtype=np.float64))
    return StatusRecord(
        raw=raw,
        proposal_status=derived,
        gate_status=gated.status,
        gated=gated,
        final_action=final,
        certificate_zero_or_unresolved=zero,
        score_before_gate=float(raw.score),
        action_norm_before_gate=float(np.linalg.norm(raw.action)),
        action_norm_after_gate=float(np.linalg.norm(final)),
        validation_status=validation,
    )


def propose_adapted(z: Any, public_model: Mapping[str, Any],
                    threshold: float, method: str) -> StatusRecord:
    """Run frozen estimator, then adapt records; never feeds derived labels back."""
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}")
    validation_first = validate_input(z, public_model)
    try:
        raw = v2_estimators.propose(z, public_model, method)
    except Exception:
        raw = None
    result = adapt(raw, z, public_model, threshold)
    if validation_first != "VALID" and result.proposal_status == "VALID":
        return StatusRecord(result.raw, validation_first, result.gate_status,
                            result.gated, np.zeros(2),
                            result.certificate_zero_or_unresolved,
                            result.score_before_gate, result.action_norm_before_gate,
                            0.0, validation_first)
    return result


def make_log_record(seed: int, scenario: str, main_case: bool, method: str,
                    status: StatusRecord, threshold: float,
                    offline_eval: Mapping[str, Any]) -> dict[str, Any]:
    """Join online status with offline-only event/age/coverage annotations."""
    if scenario not in {"normal", "replay"}:
        raise ValueError("scenario must be normal or replay")
    raw = status.raw
    cert = (raw.certificate or {}) if raw is not None else {}
    event = None if scenario == "normal" else offline_eval.get("event")
    age = None if scenario == "normal" else offline_eval.get("age")
    execution_success = (
        status.gate_status == "EXECUTED"
        and status.proposal_status == "VALID"
        and status.action_norm_after_gate > ZERO_TOL
    )
    row = {
        "seed": int(seed), "scenario": scenario, "main_case": bool(main_case),
        "event": None if event is None else list(event),
        "age": None if age is None else int(age), "method": method,
        "raw_status": "NO_RAW_PROPOSAL" if raw is None else raw.status,
        "proposal_status": status.proposal_status, "gate_status": status.gate_status,
        "score": status.score_before_gate, "threshold": float(threshold),
        "set_proposal_norm": status.action_norm_before_gate,
        "set_action_norm": status.action_norm_after_gate,
        "coverage_confirmed": (None if scenario == "normal" else
                                bool(offline_eval.get("coverage_confirmed", False))),
        "compatible_event_count": (int(cert["coverage_candidates"])
                                   if "coverage_candidates" in cert else None),
        "zero_or_unresolved": status.certificate_zero_or_unresolved,
        "solver_stage": cert.get("stage", ""),
        "solver_gap": cert.get("gap_squared", ""),
        "solver_reject_reason": cert.get("reason", ""),
        "execution_success": bool(execution_success),
    }
    assert tuple(row) == LOG_FIELDS
    return row
