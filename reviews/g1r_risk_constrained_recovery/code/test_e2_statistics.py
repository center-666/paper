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


def test_gate_uses_full_denominator_and_frozen_counts():
    gate = e2.evaluate_e2_count_gate(190, 100, 12)
    assert gate.n == gate.normal_n == 200
    assert gate.coverage_count == 190 and gate.coverage_pass
    assert gate.nonzero_count == 100 and gate.attack_nonzero_pass
    assert gate.normal_nonzero_count == 12 and gate.normal_nonzero_pass
    # A numerical rejection remains in the denominator and counts as failure.
    gate2 = e2.evaluate_e2_count_gate(189, 99, 12)
    assert gate2.coverage_count == 189
    assert gate2.nonzero_count == 99
    assert not gate2.coverage_pass and not gate2.attack_nonzero_pass


def test_failed_rows_stay_in_count_denominators():
    attack = [{"coverage_confirmed": i < 190,
               "set_action_norm": 0.1 if i < 100 else 0.0}
              for i in range(200)]
    normal = [{"set_action_norm": 0.1 if i < 12 else 0.0}
              for i in range(200)]
    assert e2.count_e2_outcomes(attack, normal) == (190, 100, 12)


def test_seed_or_row_deletion_is_rejected():
    rows = [{"seed": 900000+i} for i in range(5)]
    try:
        e2.validate_seed_rows(rows[:-1], range(900000, 900005))
    except ValueError:
        pass
    else:
        raise AssertionError("missing seed row was not rejected")


def test_frozen_seed_contract_is_not_injectable():
    assert e2.FROZEN_ATTACK_SEEDS == frozenset(range(141430000, 141430200))
    assert e2.FROZEN_NORMAL_SEEDS == frozenset(range(141420000, 141420200))
    assert "expected_attack_seed_set" not in e2.evaluate_e2_counts.__code__.co_varnames
    fixture = [{"seed": 900000, "main_case": True}]
    try:
        e2.evaluate_e2_counts(fixture, fixture)
    except ValueError:
        pass
    else:
        raise AssertionError("formal evaluator accepted non-frozen synthetic rows")


def main():
    tests = [test_beta_and_binomial_tail_formulas_agree,
             test_frozen_e2_count_boundaries,
             test_gate_uses_full_denominator_and_frozen_counts,
             test_failed_rows_stay_in_count_denominators,
             test_seed_or_row_deletion_is_rejected,
             test_frozen_seed_contract_is_not_injectable]
    for test in tests:
        test()
        print(test.__name__, "PASS")
    print("E2 test helpers only: no E2 data loaded or generated")


if __name__ == "__main__":
    main()
