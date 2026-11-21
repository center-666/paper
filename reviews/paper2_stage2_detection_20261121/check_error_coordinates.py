"""Deterministic algebra fixtures; never generates performance random samples."""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = (
    {"name": "S1", "A": 0.82, "delta": 0.011628232298833967},
    {"name": "U1", "A": 1.04, "delta": 0.022259755314928388},
)


def quant(x: float, delta: float, phase: float) -> float:
    return phase + 2 * delta * math.floor((x - phase + delta) / (2 * delta))


def wrap(x: float, delta: float) -> float:
    return x - 2 * delta * math.floor((x + delta) / (2 * delta))


def direct_update(m: float, P: float, c: float, y: float, sent: bool, action: float):
    effective_R = 0.2 if sent else 0.7
    K = P / (P + effective_R)
    post = m + K * ((y + action - m) if sent else (c - m))
    return post, P * (1 - K), K


def fixture(model: dict) -> dict:
    A, delta = model["A"], model["delta"]
    x = 0.63
    mh = ma = 0.0
    eh = ea = x
    Ph = Pa = 0.8
    max_error = max_covariance_error = max_residual_error = 0.0
    min_event_margin = math.inf
    sends = [0, 0]
    for t in range(220):
        # Fixed analytic sequences, not random generators or statistical data.
        v = 0.27 * math.sin(0.71 * t + 0.3)
        w = 0.11 * math.cos(0.23 * t + 0.2)
        u = ((t + 1) * (math.sqrt(5) - 1) / 2) % 1
        phase_local = 0.0 if t == 0 else delta * (2 * (((t + 1) * math.sqrt(2)) % 1) - 1)
        phase_absolute = wrap(phase_local + mh, delta)
        ch = quant(mh, delta, phase_absolute)
        ca = quant(ma, delta, phase_absolute)
        rh = quant(0.0, delta, phase_local)
        difference = eh - ea
        ra = quant(difference, delta, phase_local) - difference
        max_residual_error = max(max_residual_error, abs(rh - (ch - mh)), abs(ra - (ca - ma)))
        y = x + v
        ph = math.exp(-(y - ch) ** 2)
        pa = math.exp(-(y - ca) ** 2)
        ph_local = math.exp(-(eh + v - rh) ** 2)
        pa_local = math.exp(-(ea + v - ra) ** 2)
        sh, sa = u > ph, u > pa
        if (sh, sa) != (u > ph_local, u > pa_local):
            raise AssertionError("Coordinate update changed event fixture")
        sends[0] += sh
        sends[1] += sa
        min_event_margin = min(min_event_margin, abs(u - ph), abs(u - pa))
        attack = 0.25 if t >= 50 and sa else 0.0
        mh_post, Ph_post, Kh = direct_update(mh, Ph, ch, y, sh, 0.0)
        ma_post, Pa_post, Ka = direct_update(ma, Pa, ca, y, sa, attack)
        eh_post = (1 - Kh) * eh - Kh * v if sh else eh - Kh * rh
        ea_post = (1 - Ka) * ea - Ka * v - Ka * attack if sa else ea - Ka * ra
        max_error = max(max_error, abs(eh_post - (x - mh_post)), abs(ea_post - (x - ma_post)))
        local_Ph_post = Ph * (1 - Ph / (Ph + (0.2 if sh else 0.7)))
        local_Pa_post = Pa * (1 - Pa / (Pa + (0.2 if sa else 0.7)))
        max_covariance_error = max(max_covariance_error, abs(Ph_post - local_Ph_post), abs(Pa_post - local_Pa_post))
        x = A * x + w
        mh, ma = A * mh_post, A * ma_post
        eh, ea = A * eh_post + w, A * ea_post + w
        Ph, Pa = A * A * Ph_post + 0.05, A * A * Pa_post + 0.05
    if max_error > 1e-8 or max_covariance_error > 1e-14 or max_residual_error > 1e-8:
        raise AssertionError("Absolute/local deterministic equivalence fixture failed")
    if not all(0 < count < 220 for count in sends):
        raise AssertionError("Fixture must exercise both event branches")
    return {"model": model["name"], "steps": 220, "max_posterior_error_difference": max_error,
            "max_quantization_residual_difference": max_residual_error,
            "max_covariance_difference": max_covariance_error, "minimum_event_margin": min_event_margin,
            "send_counts": sends, "pass": True}


def main() -> None:
    fixtures = [fixture(model) for model in MODELS]
    translation_error = 0.0
    for model in MODELS:
        delta = model["delta"]
        for h in (-13.7, -0.12, 0.0, 0.13, 9.1):
            for x in (-2.31, -0.08, 0.019, 1.81):
                for s in (-0.83 * delta, 0.11 * delta, 0.79 * delta):
                    lhs = quant(x, delta, s) - h
                    rhs = quant(x - h, delta, s - h)
                    translation_error = max(translation_error, abs(lhs - rhs))
    if translation_error > 1e-13:
        raise AssertionError("Quantizer translation identity failed")
    precision = []
    for t in (512, 1024, 2048, 2248, 4096):
        A = 1.04
        variance = A ** (2 * t) * 0.8 + 0.05 * (A ** (2 * t) - 1) / (A * A - 1)
        rms = math.sqrt(variance)
        precision.append({"time": t, "unconditional_state_rms": rms, "double_ulp_at_rms": math.ulp(rms),
                          "quantizer_delta": MODELS[1]["delta"],
                          "adding_delta_changes_rms": rms + MODELS[1]["delta"] != rms})
    output = {"status": "PASS", "performance_random_samples_generated": False,
              "fixtures": fixtures, "quantizer_translation_max_error": translation_error,
              "U1_absolute_coordinate_precision": precision,
              "scope": "Algebraic simulator equivalence and floating-point scale only; no detector performance claim."}
    (HERE / "error_coordinate_checks.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"status": "PASS", "performance_random_samples_generated": False,
                      "max_fixture_error": max(r["max_posterior_error_difference"] for r in fixtures)}))


if __name__ == "__main__":
    main()
