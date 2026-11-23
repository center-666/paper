"""Reproducible deterministic monitor-horizon diagnostic, not a certificate."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import time

import numpy as np

from numerical_record import MonitorEnclosure, binary64_value, exact_matvec
from exact_linear import asfloat, matrix, update


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--pattern", choices=("silence", "send", "alternating"), default="alternating")
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("steps must be positive")
    stage6 = Path(__file__).resolve().parent.parent / "paper2_stage6_vector_correction_20261122"
    model = json.loads((stage6 / "model.json").read_text(encoding="utf8"))
    A, C = matrix(model["A"]), matrix(model["C"])
    Afloat = np.asarray(asfloat(A))
    monitor = MonitorEnclosure(model)
    nominal = (F(0), F(0))
    actual = np.zeros(2)
    max_error = F(0)
    max_width = F(0)
    started = time.perf_counter()
    for t in range(args.steps):
        sent = args.pattern == "send" or (args.pattern == "alternating" and t % 2 == 0)
        prior = actual if t == 0 else Afloat @ actual
        nominal_prior = nominal if t == 0 else exact_matvec(A, nominal)
        actual_measured = exact_matvec(C, tuple(binary64_value(x) for x in prior))[0]
        center = actual_measured + F(".002")
        payload = actual_measured + F(".17") if sent else None
        _, gain_matrix, transition = update(monitor.P, C, F(model["R"]) + (0 if sent else 1/F(model["Z"])))
        gain = tuple(row[0] for row in gain_matrix)
        observation = payload if sent else center
        actual = prior + np.asarray(asfloat(gain_matrix)).ravel() * float(observation-actual_measured)
        nominal = tuple(x + k*observation for x, k in zip(exact_matvec(transition, nominal_prior), gain))
        frame = monitor.append(sent, payload, center, prior=prior, posterior=actual)
        for index in range(2):
            for estimate, reference, enclosure in ((frame.actual_prior[index], nominal_prior[index], frame.prior_error[index]),
                                                    (frame.actual_posterior[index], nominal[index], frame.posterior_error[index])):
                error = estimate-reference
                if not F(enclosure.lo) <= error <= F(enclosure.hi):
                    raise AssertionError((t, index, "error outside enclosure"))
                max_error = max(max_error, abs(error))
                max_width = max(max_width, F(enclosure.hi)-F(enclosure.lo))
    print(json.dumps({"steps":args.steps,"pattern":args.pattern,"contains_reference":True,
                      "maximum_absolute_error":float(max_error),"maximum_interval_width":float(max_width),
                      "elapsed_seconds":time.perf_counter()-started}, indent=2))


if __name__ == "__main__":
    main()
