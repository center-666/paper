from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

import numpy as np

from .config_loader import canonical_sha256

_PUBLIC_MODEL_DIGESTS: dict[int, tuple[object, str]] = {}


@dataclass(frozen=True)
class OnlineInput:
    """Only receiver innovation and frozen public estimator inputs cross online."""
    z: tuple[float, ...]
    frozen_public_model: Mapping[str, Any]
    threshold: float
    method: str


@dataclass(frozen=True)
class ProposalRecord:
    """Immutable, serializable output saved before any offline labels are joined."""
    method: str
    z: tuple[float, ...]
    threshold: float
    raw_status: str
    proposal_status: str
    gate_status: str
    score: float
    proposal_vector: tuple[float, ...]
    final_action: tuple[float, ...]
    action_norm_before_gate: float
    action_norm_after_gate: float
    certificate_zero_or_unresolved: bool
    certificate_json: str
    solver_stage: str
    solver_gap: float | None
    solver_reject_reason: str
    execution_success: bool
    validation_status: str
    public_model_sha256: str
    record_sha256: str


def build_online_input(z, public_model, threshold: float, method: str) -> OnlineInput:
    value = np.asarray(z, dtype=np.float64)
    if value.shape != (12,) or not np.all(np.isfinite(value)):
        raise ValueError("online input must contain exactly twelve finite innovations")
    if not np.isfinite(float(threshold)):
        raise ValueError("online threshold must be finite")
    return OnlineInput(tuple(map(float, value)), public_model, float(threshold), str(method))


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "items"):
        return {str(k): _jsonable(v) for k, v in value.items()}
    raise TypeError(f"unsupported proposal certificate value {type(value)!r}")


def _public_model_digest(public_model) -> str:
    key = id(public_model)
    cached = _PUBLIC_MODEL_DIGESTS.get(key)
    if cached is not None and cached[0] is public_model:
        return cached[1]

    def pack(value):
        if isinstance(value, np.ndarray):
            return {"dtype": str(value.dtype), "shape": list(value.shape), "values": value.tolist()}
        if hasattr(value, "items"):
            return {str(k): pack(v) for k, v in sorted(value.items())}
        if isinstance(value, (list, tuple)):
            return [pack(v) for v in value]
        return value
    digest = canonical_sha256(pack(public_model))
    _PUBLIC_MODEL_DIGESTS[key] = (public_model, digest)
    return digest


def propose(online_input: OnlineInput) -> ProposalRecord:
    if type(online_input) is not OnlineInput:
        raise TypeError("online proposal accepts only OnlineInput")
    allowed = {"z", "frozen_public_model", "threshold", "method"}
    if set(vars(online_input)) != allowed:
        raise ValueError("OnlineInput contains fields outside the permission contract")

    from .config_loader import BASE
    import sys
    code_path = str(BASE / "code")
    if code_path not in sys.path:
        sys.path.insert(0, code_path)
    import e2_status_adapter

    # The legacy convenience entry catches every Exception. Call the same
    # frozen estimator and the same raw-object adapter without that catch:
    # returned algorithm rejections survive, unexpected exceptions propagate.
    import v2_estimators
    z = np.asarray(online_input.z, dtype=np.float64)
    if z.shape != (12,) or not np.all(np.isfinite(z)):
        raise ValueError("generated innovation is nonfinite or not 12-dimensional")
    if e2_status_adapter.validate_input(z, online_input.frozen_public_model) != "VALID":
        raise ValueError("frozen public model is invalid")
    raw = v2_estimators.propose(z, online_input.frozen_public_model, online_input.method)
    if not isinstance(raw, v2_estimators.Proposal):
        raise TypeError("estimator did not return a Proposal")
    allowed_statuses = {"VALID", "INPUT_INVALID", "MODEL_INVALID", "EMPTY_UNION",
                        "ZERO_OR_UNRESOLVED", "SOLVER_REJECT", "ZERO_PROPOSAL", "GATE_REJECT"}
    if raw.status not in allowed_statuses:
        raise ValueError("estimator returned an undocumented status: " + str(raw.status))
    if (np.asarray(raw.action).shape != (2,) or not np.all(np.isfinite(raw.action))
            or not np.isfinite(raw.score)):
        raise ValueError("estimator returned nonfinite or malformed proposal")
    status = e2_status_adapter.adapt(raw, z, online_input.frozen_public_model,
                                    online_input.threshold)
    if not np.all(np.isfinite(status.final_action)):
        raise ValueError("gate returned a nonfinite action")
    raw = status.raw
    certificate = _jsonable((raw.certificate or {}) if raw is not None else {})
    raw_status = "NO_RAW_PROPOSAL" if raw is None else str(raw.status)
    proposal_vector = tuple(map(float, raw.action)) if raw is not None else (0.0, 0.0)
    gate_status = str(status.gate_status)
    proposal_status = str(status.proposal_status)
    record_base = {
        "method": online_input.method,
        "z": online_input.z,
        "threshold": float(online_input.threshold),
        "raw_status": raw_status,
        "proposal_status": proposal_status,
        "gate_status": gate_status,
        "score": float(status.score_before_gate),
        "proposal_vector": proposal_vector,
        "final_action": tuple(map(float, status.final_action)),
        "action_norm_before_gate": float(status.action_norm_before_gate),
        "action_norm_after_gate": float(status.action_norm_after_gate),
        "certificate_zero_or_unresolved": bool(status.certificate_zero_or_unresolved),
        "certificate_json": json.dumps(certificate, sort_keys=True, separators=(",", ":"),
                                        allow_nan=False),
        "solver_stage": str(certificate.get("stage", "")),
        "solver_gap": (None if certificate.get("gap_squared") is None
                       else float(certificate["gap_squared"])),
        "solver_reject_reason": str(certificate.get("reason", "")),
        "execution_success": bool(status.gate_status == "EXECUTED"
                                   and status.proposal_status == "VALID"
                                   and status.action_norm_after_gate > 1e-12),
        "validation_status": str(status.validation_status),
        "public_model_sha256": _public_model_digest(online_input.frozen_public_model),
    }
    digest = canonical_sha256(record_base)
    return ProposalRecord(**record_base, record_sha256=digest)


def failed_proposal_record(method: str, threshold: float, reason: str,
                           z=()) -> ProposalRecord:
    """Legacy synthetic-test helper only; never used for execution failures."""
    base = {
        "method": str(method), "z": tuple(map(float, z)), "threshold": float(threshold),
        "raw_status": "NO_RAW_PROPOSAL", "proposal_status": "MODEL_INVALID",
        "gate_status": "NOT_CALLED", "score": 0.0,
        "proposal_vector": (0.0, 0.0), "final_action": (0.0, 0.0),
        "action_norm_before_gate": 0.0, "action_norm_after_gate": 0.0,
        "certificate_zero_or_unresolved": False, "certificate_json": "{}",
        "solver_stage": "", "solver_gap": None,
        "solver_reject_reason": str(reason), "execution_success": False,
        "validation_status": "MODEL_INVALID", "public_model_sha256": "",
    }
    return ProposalRecord(**base, record_sha256=canonical_sha256(base))


def record_dict(record: ProposalRecord) -> dict[str, Any]:
    return {name: getattr(record, name) for name in record.__dataclass_fields__}
