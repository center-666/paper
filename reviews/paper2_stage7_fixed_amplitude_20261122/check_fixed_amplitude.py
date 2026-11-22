"""Deterministic exhaustive checks for fixed-amplitude parameter retention."""
from __future__ import annotations

from fractions import Fraction as F
from itertools import product
from pathlib import Path
import hashlib, json, sys

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"
sys.path.insert(0, str(STAGE6))
from exact_linear import matrix
from projection import inner
from fixed_amplitude import (FixedAmplitudeEnvelope, IntervalFixedAmplitudeEnvelope,
                             interval_fraction, transport_halfspace)


def main():
    model = json.loads((STAGE6 / "model.json").read_text(encoding="utf8"))
    checks = []

    def check(name, condition, detail=None):
        checks.append({"name": name, "pass": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError((name, detail))

    event_words = list(product((False, True), repeat=6))
    checked_truths = 0
    positive_certificates = 0
    excluded_wrong_sign_onsets = 0
    negative_components = []
    for word in event_words:
        for onset in range(6):
            env = FixedAmplitudeEnvelope(model)
            ienv = IntervalFixedAmplitudeEnvelope(model)
            for sent in word:
                env.advance(sent)
                ienv.advance(sent)
            for k, H in enumerate(env.responses):
                for j, exact in enumerate(H):
                    interval = ienv.responses[k][j]
                    check("outward_interval_encloses_exact_response",
                          F(str(interval.lo)) <= exact <= F(str(interval.hi)))
            H = env.responses[onset]
            if any(x < 0 for x in H):
                negative_components.append((word, onset, H))
            b = F(1, 10)
            directions = ((F(1), F(0)), (F(-1), F(0)),
                          (F(0), F(1)), (F(0), F(-1)))
            candidates = [(inner(d, H, env.W), d) for d in directions]
            q, direction = max(candidates, key=lambda item: item[0])
            if q <= 0:
                continue
            z = q * b / 2
            incompatible = {k for k, h in enumerate(env.responses)
                            if inner(direction, h, env.W) <= 0}
            env.add_certificate(direction, z)
            ienv.add_certificate(direction, z)
            positive_certificates += 1
            checked_truths += 1
            check("true_fixed_parameter_retained_at_certificate",
                  env.contains_truth(onset, b), {"word": word, "onset": onset})
            check("all_retained_segments_obey_certificate",
                  env.support(direction) >= z)
            excluded_wrong_sign_onsets += len(incompatible - set(env.bounds))
            check("nonpositive_onset_support_is_excluded",
                  incompatible.isdisjoint(env.bounds))
            check("interval_amplitude_outer_bound_keeps_true_value",
                  ienv.contains_truth_amplitude(onset, b) and
                  ienv.bounds[onset][0] <= env.bounds[onset][0])
            check("interval_support_is_conservative",
                  ienv.support(direction) <= env.support(direction))
            projection = env.projected_action()
            check("projection_gain_dominates_directional_certificate",
                  projection["guaranteed_gain"] >= z * z / inner(direction, direction, env.W))

            # Follow a fixed future event history and compare to the legacy
            # independent-input half-space using its own transported direction.
            old = (direction, z)
            future = (False, True, True, False)
            for j, sent in enumerate(future):
                Fmat, K = env.advance(sent)
                old = transport_halfspace(old, Fmat, K, sent, env.bmax)
                exact_theta = tuple(b * x for x in env.responses[onset])
                check("true_parameter_retained_after_future_events",
                      env.contains_truth(onset, b), {"future_index": j})
                check("true_response_satisfies_current_old_halfspace",
                      old is None or inner(old[0], exact_theta, env.W) >= old[1])
                check("fixed_parameter_set_never_weakens_old_direction_support",
                      old is None or env.support(old[0]) >= old[1],
                      {"future_index": j})

    check("enumerated_positive_certificate_cases", positive_certificates > 100,
          positive_certificates)
    check("negative_state_component_seen", bool(negative_components),
          str(negative_components[0]) if negative_components else None)
    check("wrong_sign_onsets_excluded", excluded_wrong_sign_onsets > 0,
          excluded_wrong_sign_onsets)

    # A second certificate must intersect retained intervals and never revive
    # an onset excluded by the first one.
    env = FixedAmplitudeEnvelope(model)
    for sent in (True, False, True, True, False, True, True):
        env.advance(sent)
    d1 = (F(1), F(0))
    q1 = max((inner(d1, h, env.W) for h in env.responses), default=F(0))
    if q1 <= 0:
        raise AssertionError("fixture lacks positive first-coordinate response")
    z1 = q1 * F(1, 100)
    env.add_certificate(d1, z1)
    retained1 = set(env.bounds)
    d2 = (F(0), F(1))
    positive_q2 = [inner(d2, env.responses[k], env.W) for k in retained1]
    q2 = max(positive_q2, default=F(0))
    if q2 > 0:
        env.add_certificate(d2, q2 * F(1, 1000))
        check("second_certificate_does_not_revive_excluded_onsets",
              set(env.bounds).issubset(retained1))
        check("second_certificate_intersects_existing_bounds",
              all(lo >= F(0) and hi == env.bmax for lo, hi in env.bounds.values()))

    rejected_zero = False
    try:
        env.add_certificate((F(1), F(0)), F(0))
    except ValueError:
        rejected_zero = True
    check("zero_support_is_not_propagated", rejected_zero)

    # Exact support on a line segment agrees with endpoint enumeration,
    # including negative projected state components.
    test_points = env.vertices()
    for d in ((F(1), F(0)), (F(0), F(1)), (F(1), F(-2))):
        exact = env.support(d)
        brute = min((inner(d, p, env.W) for p in test_points), default=None)
        check("segment_support_matches_all_endpoints", exact == brute)

    out = {"status": "PASS", "check_count": len(checks), "checks": checks,
           "enumerated_event_words": len(event_words),
           "enumerated_onset_cases": len(event_words) * 6,
           "positive_certificate_cases": positive_certificates,
           "wrong_sign_onsets_excluded": excluded_wrong_sign_onsets,
           "truth_cases_certified": checked_truths,
           "negative_component_example": str(negative_components[0]),
           "performance_random_samples_generated": False,
           "source_sha256": hashlib.sha256((HERE / "fixed_amplitude.py").read_bytes()).hexdigest()}
    (HERE / "deterministic_checks.json").write_text(json.dumps(out, indent=2) + "\n",
                                                    encoding="utf8", newline="\n")
    print(json.dumps({"status": out["status"], "check_count": len(checks),
                      "event_words": len(event_words),
                      "positive_certificates": positive_certificates}))


if __name__ == "__main__":
    main()
