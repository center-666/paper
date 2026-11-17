"""Independent exhaustive validation of T1--T3 for small integer instances."""
from __future__ import annotations
import itertools
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model import (cost_neutral_boundary, frontier, guarantees_success,
                   history_is_legal, m_min, m_star, safe_wait_boundary, t_star)
from attack_oracle import (brute_causal_minimax, brute_frontier,
                           brute_min_safe_cardinality, brute_guarantees)


def histories(before_start):
    values = tuple(range(1, before_start))
    for mask in range(1 << len(values)):
        yield {value for i, value in enumerate(values) if mask & (1 << i)}


def run(max_length=10, max_start=4, max_horizon_extra=4):
    t1_cases = t2_cases = t3_cases = 0
    frontiers = []
    for length in range(2, max_length + 1):
        for budget in range(length):
            for start in range(1, max_start + 1):
                for deadline in range(start, start + max_horizon_extra + 1):
                    for history in histories(start):
                        if not history_is_legal(history, length, budget, 1, deadline):
                            continue
                        horizon = tuple(range(start, deadline + 1))
                        for mask in range(1 << len(horizon)):
                            opportunities = {value for i, value in enumerate(horizon)
                                             if mask & (1 << i)}
                            expected = max(
                                (sum(end - length + 1 <= point <= end
                                     for point in history | opportunities)
                                 for end in range(start, deadline + 1)),
                                default=0) > budget
                            actual = brute_guarantees(history, opportunities, length,
                                                     budget, start, deadline)
                            implemented = guarantees_success(history, opportunities, length,
                                                              budget, start, deadline)
                            if expected != actual or expected != implemented:
                                raise AssertionError(("T1", length, budget, start,
                                                      deadline, history, opportunities))
                            t1_cases += 1
                        expected_m = m_star(history, length, budget, start, deadline)
                        actual_m, actual_choice = brute_min_safe_cardinality(
                            history, length, budget, start, deadline)
                        game_value = brute_causal_minimax(history, length, budget, start, deadline)
                        if expected_m != actual_m or expected_m != game_value:
                            raise AssertionError(("T2", length, budget, start,
                                                  deadline, history, expected_m,
                                                  actual_m, actual_choice, game_value))
                        t2_cases += 1
                        expected_frontier = frontier(history, length, budget, start, deadline)
                        actual_frontier = brute_frontier(history, length, budget, start, deadline)
                        if expected_frontier != actual_frontier:
                            raise AssertionError(("T3-frontier", length, budget, start,
                                                  deadline, history, expected_frontier,
                                                  actual_frontier))
                        if any((a is None and b is not None) or
                               (a is not None and b is not None and b < a)
                               for a, b in zip(expected_frontier, expected_frontier[1:])):
                            raise AssertionError(("T3-monotonicity", length, budget,
                                                  start, deadline, history, expected_frontier))
                        finite = [wait for wait, value in enumerate(expected_frontier)
                                  if value is not None]
                        boundary = safe_wait_boundary(history, length, budget,
                                                     start, deadline)
                        if finite and max(finite) != boundary:
                            raise AssertionError(("T3-safe-boundary", length, budget,
                                                  start, deadline, history, expected_frontier,
                                                  boundary))
                        if finite:
                            base = expected_m
                            neutral = cost_neutral_boundary(history, length, budget,
                                                            start, deadline)
                            actual_neutral = max(
                                [wait for wait, value in enumerate(expected_frontier)
                                 if value == base], default=None)
                            if neutral != actual_neutral:
                                raise AssertionError(("T3-cost-neutral", length, budget,
                                                      start, deadline, history, neutral,
                                                      actual_neutral))
                        t3_cases += 1
                        if len(frontiers) < 12 and expected_frontier:
                            frontiers.append({"L": length, "B": budget, "k": start,
                                              "D": deadline, "history": sorted(history),
                                              "frontier": expected_frontier})
    return {"status": "PASS", "T1_cases": t1_cases, "T2_cases": t2_cases,
            "T3_cases": t3_cases, "frontier_examples": frontiers,
            "scope": "exhaustive finite integer validation; not a proof by enumeration"}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
