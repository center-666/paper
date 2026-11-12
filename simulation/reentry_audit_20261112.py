"""Read-only numerical audit of prior claims; no trajectories or tuning."""
from pathlib import Path
from hashlib import sha256
import csv
import json
import shutil
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "simulation/validation_runs/2026-11-11_partial_observability_probe_v4"
OUT = ROOT / "simulation/checks/2026-11-12_reentry_audit"


def main():
    OUT.mkdir(exist_ok=False, parents=True)
    cfg = json.loads((RUN / "gap8/config.json").read_text(encoding="utf-8"))
    A = np.asarray(cfg["A"])
    geom = []
    for i, H in enumerate(np.asarray(cfg["H_matrices"])):
        O = np.vstack([H @ np.linalg.matrix_power(A, k) for k in range(cfg["n"])])
        geom.append({"node": i, "measurement_rank": int(np.linalg.matrix_rank(H)),
                     "dynamic_observability_rank": int(np.linalg.matrix_rank(O)),
                     "observable": bool(np.linalg.matrix_rank(O) == cfg["n"])})
    rates = []
    for schedule_name in ("gap8", "irregular"):
        folder = RUN / schedule_name
        config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        edges = np.asarray(config["edges_sender_receiver"])
        with np.load(folder / "test_inputs.npz") as inp:
            schedule = inp["schedule"]
        for method in ("mean", "carry_energy_cusum", "carry_signed_cusum"):
            with np.load(folder / "primary" / (method + "__clean.npz")) as data:
                weights = data["weights"]
                assert np.array_equal(data["sends"], schedule)
            num = np.zeros(3, int)
            den = np.zeros(3, int)
            for trial in range(len(schedule)):
                for e, (sender, _) in enumerate(edges):
                    ts = np.flatnonzero(schedule[trial, :, sender])
                    for start, stop in zip(ts[:-1], ts[1:]):
                        p = 0 if start == 0 else 1 if start < config["warmup"] else 2
                        den[p] += 1
                        num[p] += bool(np.any(weights[trial, start:stop, e] == 0))
            for p, phase in enumerate(("initial", "transient", "steady")):
                rates.append({"schedule": schedule_name, "method": method, "phase": phase,
                              "complete_episode_count": int(den[p]), "false_isolations": int(num[p]),
                              "test_false_isolation_rate": float(num[p]/den[p]),
                              "source": "test saved clean weights; complete episodes; primary edge-label run only"})
    with (OUT / "test_phase_rates.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rates[0])); w.writeheader(); w.writerows(rates)
    summary = {"new_simulations": False, "geometry": geom,
               "steady_test_rates": [r for r in rates if r["phase"] == "steady"],
               "corrections": ["rank(H)=1 does not imply dynamic unobservability",
                               "v4 REPORT previously labeled independent normal-audit rates as test rates",
                               "v3 completed all saved test trajectories before summary export failed"],
               "source_config_sha256": sha256((RUN / "gap8/config.json").read_bytes()).hexdigest()}
    (OUT / "audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(__file__, OUT / Path(__file__).name)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
