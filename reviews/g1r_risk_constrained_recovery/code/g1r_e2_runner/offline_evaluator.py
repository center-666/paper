from __future__ import annotations

import json
from typing import Any

import numpy as np

from .config_loader import BASE
from .online_proposal import ProposalRecord
from .scenario_builder import OfflineTruth

import sys
if str(BASE / "code") not in sys.path:
    sys.path.insert(0, str(BASE / "code"))
import v2_estimators


def _point_in_ellipse(point: np.ndarray, ellipse, tolerance: float = 1e-9) -> bool:
    center = np.asarray(ellipse.center, dtype=np.float64)
    shape = np.asarray(ellipse.shape, dtype=np.float64)
    delta = np.asarray(point, dtype=np.float64) - center
    left, singular, _ = np.linalg.svd(shape, full_matrices=True)
    scale = max(1.0, float(singular[0]) if len(singular) else 1.0)
    active = singular > 1e-12 * scale
    coordinates = left.T @ delta
    if np.any(~active) and np.linalg.norm(coordinates[~active]) > tolerance * scale:
        return False
    radius_squared = float(np.sum((coordinates[active] / singular[active]) ** 2)) if np.any(active) else 0.0
    return radius_squared <= 1.0 + tolerance


def set_union_covers(z, public_model, true_impact) -> tuple[bool, int]:
    """Offline-only membership check; it does not depend on center-solver success."""
    value = np.asarray(z, dtype=np.float64)
    if value.shape != (12,) or not np.all(np.isfinite(value)):
        return False, 0
    point = np.asarray(true_impact, dtype=np.float64)
    if point.shape != (2,) or not np.all(np.isfinite(point)):
        return False, 0
    try:
        sigma = np.asarray(public_model["Sigma_eta"], dtype=np.float64)
        chol = np.linalg.cholesky(sigma)
        ellipses, _, _ = v2_estimators._build_set_ellipses(value, chol, public_model)
    except Exception:
        return False, 0
    return any(_point_in_ellipse(point, ellipse) for ellipse in ellipses), len(ellipses)


def evaluate(proposal: ProposalRecord, truth: OfflineTruth,
             public_model, coverage_cache: dict | None = None) -> dict[str, Any]:
    """Join a persisted online record with OfflineTruth only after proposal."""
    certificate = json.loads(proposal.certificate_json)
    coverage, compatible_count = (False, 0)
    if truth.scenario == "replay" and truth.true_impact is not None:
        key = (truth.seed, truth.event, truth.age, proposal.z, truth.true_impact)
        if coverage_cache is not None and key in coverage_cache:
            coverage, compatible_count = coverage_cache[key]
        else:
            coverage, compatible_count = set_union_covers(
                proposal.z, public_model, truth.true_impact)
            if coverage_cache is not None:
                coverage_cache[key] = (coverage, compatible_count)
    event = None if truth.event is None else list(truth.event)
    action_norm = float(np.linalg.norm(proposal.final_action))
    return {
        "seed": int(truth.seed), "scenario": truth.scenario,
        "main_case": bool(truth.main_case), "event": event,
        "age": None if truth.age is None else int(truth.age),
        "method": proposal.method, "raw_status": proposal.raw_status,
        "proposal_status": proposal.proposal_status,
        "gate_status": proposal.gate_status, "score": float(proposal.score),
        "threshold": float(proposal.threshold),
        "proposal_vector_json": json.dumps(list(proposal.proposal_vector), separators=(",", ":")),
        "final_action_json": json.dumps(list(proposal.final_action), separators=(",", ":")),
        "set_proposal_norm": float(proposal.action_norm_before_gate),
        "set_action_norm": action_norm,
        "coverage_confirmed": None if truth.scenario == "normal" else bool(coverage),
        "compatible_event_count": (certificate.get("coverage_candidates")
                                   if proposal.method == "set_constrained_chebyshev" else None),
        "zero_or_unresolved": bool(proposal.certificate_zero_or_unresolved),
        "solver_stage": proposal.solver_stage,
        "solver_gap": proposal.solver_gap,
        "solver_reject_reason": proposal.solver_reject_reason,
        "execution_success": bool(proposal.execution_success),
        "sample_id": _sample_id(truth, proposal.method),
        "replay_source_time": truth.replay_source_time,
        "actual_replay_age": truth.actual_replay_age,
        "cache_replacement_time": truth.cache_replacement_time,
        "first_pollution_state": truth.first_pollution_state,
        "first_receiver_pollution_state": truth.first_receiver_pollution_state,
        "true_impact_x": None if truth.true_impact is None else float(truth.true_impact[0]),
        "true_impact_y": None if truth.true_impact is None else float(truth.true_impact[1]),
        "simulation_status": truth.simulation_status,
        "statistical_cluster": truth.statistical_cluster,
        "online_record_sha256": proposal.record_sha256,
    }


def _sample_id(truth: OfflineTruth, method: str) -> str:
    if truth.scenario == "normal":
        return f"normal:{truth.seed}:{method}"
    return f"replay:{truth.seed}:{truth.event[0]}:{truth.event[1]}:{truth.age}:{method}"
