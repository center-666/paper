"""Capture a short diagnostic prefix of the actual stage-nine simulator."""
import hashlib
import inspect
import json
from pathlib import Path
import sys
from fractions import Fraction

HERE = Path(__file__).resolve().parent
STAGE9 = HERE.parent / "paper2_stage9_cumulative_evidence_20261123"
sys.path.insert(0, str(STAGE9))
import paired_recovery
from numerical_record import MonitorEnclosure, binary64_value, exact_matvec
from exact_linear import matrix, update


class StopTrace(Exception):
    pass


def main():
    source, start = inspect.getsourcelines(paired_recovery.run_episode)
    prior_line = start + next(i for i, text in enumerate(source) if text.strip() == "residual = y+injection if sent else r")
    posterior_line = start + next(i for i, text in enumerate(source) if text.strip() == 'times["gain_and_monitor_update"] += time.perf_counter()-tick')
    rows = []
    pending = {}

    def trace(frame, event, arg):
        if frame.f_code is not paired_recovery.run_episode.__code__ or event != "line":
            return trace
        local = frame.f_locals
        if frame.f_lineno == prior_line:
            pending.update({"time": int(local["t"]),
                            "prior_hex": [float(x).hex() for x in local["monitor"]],
                            "gain_hex": [float(x).hex() for x in local["K"]],
                            "offset_hex": float(local["r"]).hex(),
                            "sent": bool(local["sent"])})
        elif frame.f_lineno == posterior_line:
            pending["residual_hex"] = float(local["residual"]).hex()
            pending["posterior_hex"] = [float(x).hex() for x in local["monitor"]]
            rows.append(dict(pending))
            if len(rows) == 32:
                raise StopTrace
        return trace

    sys.settrace(trace)
    try:
        paired_recovery.run_episode("fresh", 0, 0, "diagnostic-prefix")
    except StopTrace:
        pass
    finally:
        sys.settrace(None)
    assert len(rows) == 32
    model = json.loads((HERE.parent / "paper2_stage6_vector_correction_20261122" / "model.json").read_text(encoding="utf8"))
    A, C = matrix(model["A"]), matrix(model["C"])
    audit = MonitorEnclosure(model)
    nominal = (Fraction(0), Fraction(0))
    maximum_error = Fraction(0)
    for row in rows:
        prior = tuple(float.fromhex(x) for x in row["prior_hex"])
        posterior = tuple(float.fromhex(x) for x in row["posterior_hex"])
        measured = exact_matvec(C, tuple(binary64_value(x) for x in prior))[0]
        center = measured + binary64_value(float.fromhex(row["offset_hex"]))
        residual = binary64_value(float.fromhex(row["residual_hex"]))
        payload = measured + residual if row["sent"] else None
        nominal_prior = nominal if row["time"] == 0 else exact_matvec(A, nominal)
        _, gain_matrix, transition = update(audit.P, C, Fraction(model["R"]) +
                                            (0 if row["sent"] else 1/Fraction(model["Z"])))
        observation = payload if row["sent"] else center
        nominal = tuple(x + k[0]*observation for x, k in zip(exact_matvec(transition, nominal_prior), gain_matrix))
        frame = audit.append(row["sent"], payload, center, prior=prior, posterior=posterior)
        for j in range(2):
            error = binary64_value(posterior[j]) - nominal[j]
            assert Fraction(frame.posterior_error[j].lo) <= error <= Fraction(frame.posterior_error[j].hi)
            maximum_error = max(maximum_error, abs(error))
    path = Path(inspect.getsourcefile(paired_recovery.run_episode))
    output = {"scope": "32-step deterministic seeded simulator diagnostic, no certificate query",
              "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "case": 0, "index": 0, "rows": rows,
              "max_abs_posterior_error": float(maximum_error),
              "semantics": "offset r is generated directly; an absolute phase and center are not constructed; audit uses a derived exact center"}
    (HERE / "stage9_monitor_trace.json").write_text(json.dumps(output, indent=2)+"\n", encoding="utf8")
    print("PASS: captured 32 production-simulator update steps")


if __name__ == "__main__":
    main()
