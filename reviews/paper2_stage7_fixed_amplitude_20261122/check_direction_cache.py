"""Verify incremental adjoint projections against direct interval products."""
from __future__ import annotations
from fractions import Fraction as F
from itertools import product
import json, hashlib
from pathlib import Path

from fixed_amplitude import FixedAmplitudeEnvelope, IntervalFixedAmplitudeEnvelope
from direction_cache import CachedIntervalEnvelope
from projection import inner

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"


def main():
    model = json.loads((STAGE6 / "model.json").read_text(encoding="utf8"))
    checked = 0
    certs = 0
    for word in product((False, True), repeat=7):
        env = CachedIntervalEnvelope(model)
        direct = IntervalFixedAmplitudeEnvelope(model)
        exact = FixedAmplitudeEnvelope(model)
        for t, sent in enumerate(word):
            env.advance(sent)
            direct.advance(sent)
            exact.advance(sent)
            if t == 3:
                # A fixed, deterministic direction certificate derived from
                # the onset-3 response; skip words without positive support.
                H = direct.responses[3]
                q = direct._q_interval((F(1), F(0)), H)
                if q.lo > 0:
                    z = inner((F(1), F(0)), exact.responses[3], exact.W) / 20
                    env.add_certificate((F(1), F(0)), z)
                    direct.add_certificate((F(1), F(0)), z)
                    certs += 1
            if env.constraints:
                for state in env.direction_cache.values():
                    d = state["d"]
                    for k, q in state["q"].items():
                        qexact = inner(d, exact.responses[k], exact.W)
                        if not (F(str(q.lo)) <= qexact <= F(str(q.hi))):
                            raise AssertionError(("cached projection does not enclose exact", t, k, q, qexact))
                    cached = env._support_from_state(state)
                    exact_support = min((inner(d, exact.responses[k], exact.W) *
                                         (lo if inner(d, exact.responses[k], exact.W) >= 0 else hi)
                                         for k, (lo, hi) in env.bounds.items()), default=None)
                    if cached is not None and exact_support is not None and cached > exact_support:
                        raise AssertionError(("cached support is not conservative", t, cached, exact_support))
                    cached_action = env.directional_action(d)
                    exact_gain = max(F(0), exact_support or F(0))**2 / inner(d, d, exact.W)
                    if cached_action["guaranteed_gain"] > exact_gain:
                        raise AssertionError(("cached action overstates exact gain", t))
                    checked += 1
    out = {"status": "PASS", "word_count": 128, "certificate_cases": certs,
           "cached_direction_checks": checked,
           "source_sha256": hashlib.sha256((HERE / "direction_cache.py").read_bytes()).hexdigest()}
    (HERE / "direction_cache_checks.json").write_text(json.dumps(out, indent=2)+"\n",
                                                       encoding="utf8", newline="\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
