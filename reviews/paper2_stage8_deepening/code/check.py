"""WP1 exact checks for controls, signed persistent bias, dimensions, and mirrors."""
from __future__ import annotations

import json
from fractions import Fraction as F
from pathlib import Path

from models import (add_vectors, filter_step, load_plants, matvec, matrix,
                    kalman_gain)
from propagation import response_step, update_signed_intervals


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLANTS = load_plants(ROOT / "config" / "plants.json")


def vector_scale(value, vector):
    return [value * x for x in vector]


def run_trace(plant, amplitude, mirror=False):
    covariance = plant.P0
    monitor = [F("0.13") * (i + 1) for i in range(plant.n)]
    if mirror:
        monitor = [-x for x in monitor]
    candidate = list(monitor)
    control = [F("0.07") * (j + 1) for j in range(plant.input_dimension)]
    response = [F(0)] * plant.n
    errors = []
    for t in range(12):
        sent = t % 3 != 1
        active = sent and t >= 3
        clean = [F("0.11") * (1 if (t + i) % 2 else -1) for i in range(plant.measurement_dimension)]
        observation = list(clean)
        if active:
            # The mirror run negates the complete positive-bias record while
            # retaining the signed candidate amplitude used by the filter.
            observation[plant.attack_channel] += abs(amplitude)
        center = [F("0.03") * (i + 1) for i in range(plant.measurement_dimension)]
        if mirror:
            observation = [-x for x in observation]
            center = [-x for x in center]
            control_used = [-x for x in control]
        else:
            control_used = control
        next_covariance, monitor_next, gain, transition = filter_step(
            plant, covariance, monitor, observation, center, not sent, control_used)
        clean_observation = list(observation)
        if active:
            clean_observation[plant.attack_channel] -= amplitude
        _, candidate_next, _, _ = filter_step(
            plant, covariance, candidate, clean_observation, center, not sent, control_used)
        response = response_step(plant, transition, gain, response, sent, plant.attack_channel, active)
        difference = [x - y for x, y in zip(monitor_next, candidate_next)]
        expected = vector_scale(amplitude, response)
        errors.append(max(abs(x - y) for x, y in zip(difference, expected)))
        monitor, candidate, covariance = monitor_next, candidate_next, next_covariance
    return max(errors), monitor, candidate, response


def check_signed_intervals(plant):
    bmax = F("0.25")
    weight = plant.W
    responses = {0: [F("0.4")] + [F(0)] * (plant.n - 1)}
    intervals = {0: (-bmax, bmax)}
    positive = update_signed_intervals(intervals, responses, [F(1)] + [F(0)] * (plant.n - 1), weight, F("0.05"))
    negative = update_signed_intervals(intervals, responses, [F(-1)] + [F(0)] * (plant.n - 1), weight, F("0.05"))
    assert positive[0][0] == F("0.125")
    assert negative[0][1] == F("-0.125")
    return {"positive_interval": [str(x) for x in positive[0]],
            "negative_interval": [str(x) for x in negative[0]]}


def main():
    records = []
    for name, plant in PLANTS.items():
        for amplitude in (F("0.25"), F("-0.25")):
            error, _, _, _ = run_trace(plant, amplitude)
            assert error == 0
            records.append({"plant": name, "dimension": plant.n,
                            "amplitude": str(amplitude), "control": True,
                            "max_exact_difference_error": str(error)})
        positive = run_trace(plant, F("0.25"), mirror=False)
        negative = run_trace(plant, F("-0.25"), mirror=True)
        mirror_error = max(abs(x + y) for x, y in zip(positive[1], negative[1]))
        assert mirror_error == 0
        records.append({"plant": name, "dimension": plant.n,
                        "mirror_max_state_error": str(mirror_error),
                        "signed_interval": check_signed_intervals(plant)})
    result = {"status": "PASS", "plants": records,
              "claim": "exact rational direct-filter difference equals b H with identical B u",
              "source": "config/plants.json"}
    (ROOT / "results" / "wp1_checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
