"""Deterministic validation of the frozen recovery trial before any sampling."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from numpy.polynomial.legendre import leggauss

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TRIAL = HERE / "run_trial.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf8"))
    frozen = json.loads((HERE / "freeze.json").read_text(encoding="utf8"))
    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, detail: object = None) -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        if not ok:
            raise AssertionError(f"{name}: {detail}")

    head = subprocess.check_output(
        ["git", "-c", f"safe.directory={REPO.as_posix()}", "rev-parse", "HEAD"],
        cwd=REPO, text=True,
    ).strip()
    check("frozen_code_hash", sha(TRIAL) == frozen["recovery_trial_code_sha256"])
    check("frozen_protocol_hash", sha(HERE / "protocol.json") == frozen["protocol_sha256"])
    check("frozen_preflight_hash", sha(HERE / "preflight.json") == frozen["preflight_sha256"])
    check("frozen_base_commit", head == frozen["base_commit"], {"head": head, "frozen": frozen["base_commit"]})
    check("no_sampling_yet", frozen["random_samples_generated"] is False)
    check("no_existing_output", not (HERE / "results" / "run_v1").exists())

    spec = importlib.util.spec_from_file_location("frozen_trial", TRIAL)
    assert spec is not None and spec.loader is not None
    trial = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = trial
    spec.loader.exec_module(trial)

    model = protocol["models"][0]
    A, Q, R, Z = (model[k] for k in ("A", "Q", "R", "Z"))
    delta = model["delta"]
    nodes, weights = leggauss(256)

    # Integrate the phase residual directly and compare it with the formula
    # used by the trial. The residual is uniform on [-delta, delta).
    for P, D in ((0.08, 0.0), (0.16, 0.07), (0.31, -0.2)):
        V = 1 / Z + A * A * P + Q + R
        prefactor = 1 / math.sqrt(1 + Z * (A * A * P + Q + R))
        residual = delta * nodes
        direct = prefactor * float(np.dot(weights / 2, np.exp(-((A * D - residual) ** 2) / (2 * V))))
        formula = float(trial._mean_silence(P, D, model, delta))
        check("phase_average_matches_quadrature", abs(direct - formula) < 2e-14,
              {"P": P, "D": D, "direct": direct, "formula": formula})

    # Verify the posterior-bias recursion against two explicit scalar updates
    # that share the same event and feedback center.
    P = 0.17
    R0 = R + 1 / Z
    K1 = P / (P + R)
    K0 = P / (P + R0)
    Dprior, center, y, attack = -0.13, 0.09, -0.21, 0.12
    true_prior = 0.4
    monitor_prior = true_prior - Dprior
    true_post_send = true_prior + K1 * (y - true_prior)
    monitor_post_send = monitor_prior + K1 * (y + attack - monitor_prior)
    direct_send = true_post_send - monitor_post_send
    formula_send = (1 - K1) * Dprior - K1 * attack
    check("sent_bias_recursion_matches_direct_update", abs(direct_send - formula_send) < 1e-14,
          {"direct": direct_send, "formula": formula_send})
    true_post_silence = true_prior + K0 * (center - true_prior)
    monitor_post_silence = monitor_prior + K0 * (center - monitor_prior)
    direct_silence = true_post_silence - monitor_post_silence
    formula_silence = (1 - K0) * Dprior
    check("silent_bias_recursion_matches_shared_center", abs(direct_silence - formula_silence) < 1e-14,
          {"direct": direct_silence, "formula": formula_silence})

    # The fixed-horizon audit uses N event scores and N+1 reported estimates:
    # the first time is attack onset and the endpoint remains one-step exposed.
    t0, N = protocol["attack_start"], protocol["audit_horizon"]
    T = t0 + N + 1
    check("audit_event_count_is_N", T - 1 - t0 == N, T - 1 - t0)
    check("mse_estimate_count_is_N_plus_one", T - t0 == N + 1, T - t0)
    h = math.sqrt(N / 2 * math.log(1 / protocol["target_false_alarm"]))
    check("threshold_reproduces_target_bound",
          math.exp(-2 * h * h / N) <= protocol["target_false_alarm"] * (1 + 1e-12), h)

    # The checkpoint is the episode-start estimate; it is never replaced at
    # attack onset. Confirm the frozen source has only the declared assignment.
    source = TRIAL.read_text(encoding="utf8")
    check("episode_start_checkpoint_assignment_present", "anchor=m_h.copy()" in source)
    check("rollback_propagates_episode_start_anchor", "safe=m_ck" in source and "anchor*(A**max(t,0))" in source)
    check("production_alarm_gates_current_payload", "out_hard=np.where(alarm_a,safe,mpost_a)" in source)

    output = {
        "status": "PASS",
        "random_samples_generated": False,
        "frozen_code_sha256": sha(TRIAL),
        "frozen_protocol_sha256": sha(HERE / "protocol.json"),
        "checks": checks,
    }
    (HERE / "pre_sampling_validation.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8", newline="\n",
    )
    print(json.dumps({"status": output["status"], "checks": len(checks), "random_samples_generated": False}))


if __name__ == "__main__":
    main()
