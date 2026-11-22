"""Exhaustive short-word check of the one-sided adjoint cache."""
from __future__ import annotations
from fractions import Fraction as F
from itertools import product
import hashlib, json
from pathlib import Path

from fixed_amplitude import FixedAmplitudeEnvelope
from direction_cache_fast import FastCachedEnvelope
from projection import inner

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"


def main():
    model = json.loads((STAGE6 / "model.json").read_text(encoding="utf8"))
    checks = 0
    certified = 0
    for word in product((False, True), repeat=7):
        env = FastCachedEnvelope(model)
        exact = FixedAmplitudeEnvelope(model)
        for t, sent in enumerate(word):
            env.advance(sent)
            exact.advance(sent)
            if t == 3:
                H = exact.responses[3]
                q = inner((F(1), F(0)), H, exact.W)
                if q > 0:
                    z = q / 20
                    env.add_certificate((F(1), F(0)), z)
                    exact.add_certificate((F(1), F(0)), z)
                    certified += 1
            for state in env.direction_cache.values():
                d = state["d"]
                for k, lower in state["q_lower"].items():
                    qexact = inner(d, exact.responses[k], exact.W)
                    if F(str(lower)) > qexact:
                        raise AssertionError(("projection lower bound exceeded exact q", t, k))
                    checks += 1
                cache_support = env._support_from_state(state)
                exact_support = min((inner(d, exact.responses[k], exact.W) *
                                     (lo if inner(d, exact.responses[k], exact.W) >= 0 else hi)
                                     for k, (lo, hi) in env.bounds.items()), default=None)
                if cache_support is not None and exact_support is not None and cache_support > exact_support:
                    raise AssertionError(("cached support exceeds exact", t))
                cache_action = env.directional_action(d)
                denom = inner(d, d, exact.W)
                exact_gain = max(F(0), exact_support or F(0))**2 / denom
                if cache_action["guaranteed_gain"] > exact_gain:
                    raise AssertionError(("cached action exceeds exact bound", t))
                checks += 1
    out = {"status": "PASS", "event_words": 128,
           "positive_certificate_cases": certified, "one_sided_checks": checks,
           "source_sha256": hashlib.sha256((HERE / "direction_cache_fast.py").read_bytes()).hexdigest()}
    (HERE / "direction_cache_fast_checks.json").write_text(json.dumps(out, indent=2)+"\n",
                                                            encoding="utf8", newline="\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
