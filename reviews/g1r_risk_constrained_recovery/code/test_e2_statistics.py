"""Deterministic validation of E2 confidence intervals and gate arithmetic."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_statistics as e2


def test_beta_and_binomial_tail_formulas_agree():
    for k, n in [(0, 200), (1, 200), (99, 200), (100, 200),
                 (189, 200), (190, 200), (199, 200), (200, 200)]:
        lo = e2.cp_lower(k, n)
        lo2 = e2.cp_lower_binomial_tail(k, n)
        hi = e2.cp_upper(k, n)
        hi2 = e2.cp_upper_binomial_tail(k, n)
        assert abs(lo-lo2) < 2e-10, (k, lo, lo2)
        assert abs(hi-hi2) < 2e-10, (k, hi, hi2)


def test_frozen_e2_count_boundaries():
    assert abs(e2.cp_lower(190, 200) - 0.916664848933628) < 1e-12
    assert e2.cp_lower(190, 200) >= .90
    assert e2.cp_lower(189, 200) >= .90
    assert abs(e2.cp_lower(100, 200) - 0.43964102528276117) < 1e-12
    assert e2.cp_lower(100, 200) >= .40
    assert e2.cp_lower(99, 200) >= .40
    assert e2.cp_upper(12, 200) <= .10
    assert e2.cp_upper(13, 200) > .10


def synthetic_rows():
    attack, normal = [], []
    for i in range(200):
        attack.append({"seed": 141430000+i, "main_case": True,
                       "coverage_confirmed": i < 190,
                       "set_action_norm": 0.1 if i < 100 else 0.0})
        normal.append({"seed": 141420000+i, "main_case": True,
                       "set_action_norm": 0.1 if i < 12 else 0.0})
    return attack, normal


def test_gate_uses_full_denominator_and_frozen_counts():
    attack, normal = synthetic_rows()
    gate = e2.evaluate_e2_counts(attack, normal)
    assert gate.n == gate.normal_n == 200
    assert gate.coverage_count == 190 and gate.coverage_pass
    assert gate.nonzero_count == 100 and gate.attack_nonzero_pass
    assert gate.normal_nonzero_count == 12 and gate.normal_nonzero_pass
    # A numerical rejection remains in the denominator and counts as failure.
    attack[0]["coverage_confirmed"] = False
    attack[1]["set_action_norm"] = 0.0
    gate2 = e2.evaluate_e2_counts(attack, normal)
    assert gate2.coverage_count == 189
    assert gate2.nonzero_count == 99
    assert not gate2.coverage_pass and not gate2.attack_nonzero_pass


def test_seed_or_row_deletion_is_rejected():
    attack, normal = synthetic_rows()
    try:
        e2.evaluate_e2_counts(attack[:-1], normal)
    except ValueError:
        pass
    else:
        raise AssertionError("missing seed row was not rejected")


def main():
    tests = [test_beta_and_binomial_tail_formulas_agree,
             test_frozen_e2_count_boundaries,
             test_gate_uses_full_denominator_and_frozen_counts,
             test_seed_or_row_deletion_is_rejected]
    for test in tests:
        test()
        print(test.__name__, "PASS")
    print("E2 test helpers only: no E2 data loaded or generated")


if __name__ == "__main__":
    main()
