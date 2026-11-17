"""P4.5: independent long-horizon enumeration and interface regressions.

Uses an independent interval legality test and a fresh recursive causal game;
the existing attack_oracle module is deliberately not imported.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import unittest
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model


def legal(blocked, length, budget):
    """All physical windows up to the last blocked tick, inclusive."""
    return all(sum(max(1, t-length+1) <= b <= t for b in blocked) <= budget
               for t in range(1, max(blocked, default=0)+1))


def can_force_failure(H, S, length, budget):
    """Enumerate *all* future attack decisions, independently of T1."""
    for decisions in itertools.product((0, 1), repeat=len(S)):
        proposed = {t for t, choice in zip(S, decisions) if choice}
        if legal(set(H) | proposed, length, budget) and len(proposed) == len(S):
            return True
    return False


def game(H, length, budget, k, D):
    @lru_cache(None)
    def solve(t, blocked):
        if t > D:
            return float("inf")
        waiting = solve(t+1, blocked)
        if legal(set(blocked) | {t}, length, budget):
            sending = max(1, 1 + solve(t+1, tuple(sorted((*blocked, t)))))
        else:
            sending = 1
        return min(waiting, sending)
    v = solve(k, tuple(sorted(H)))
    return None if v == float("inf") else int(v)


def long_audit():
    cases = profiles = 0
    per_l = {}
    for L in range(2, 5):
        counts = 0
        for B in range(L):
            k = L + 1
            # Full 2^L histories, including a window close to capacity.
            for mask in range(1 << L):
                H = tuple(i+1 for i in range(L) if mask & (1 << i))
                if not legal(H, L, B):
                    continue
                # Both exactly > 2L and a longer subrange; all S for each.
                for n in (2*L+1, 2*L+2):
                    D = k + n - 1
                    best = None
                    safe_by_size = {}
                    for mask_s in range(1 << n):
                        S = tuple(k+i for i in range(n) if mask_s & (1 << i))
                        failure = can_force_failure(H, S, L, B)
                        criterion = model.guarantees_success(H, S, L, B, k, D)
                        if criterion == failure:
                            raise AssertionError(("T1", L, B, k, D, H, S))
                        safe_by_size.setdefault(len(S), False)
                        safe_by_size[len(S)] |= not failure
                        if not failure and (best is None or len(S) < best):
                            best = len(S)
                        cases += 1
                        counts += 1
                    theory = model.m_star(H, L, B, k, D)
                    bellman = game(H, L, B, k, D)
                    if best != theory or best != bellman:
                        raise AssertionError(("T2", L, B, k, D, H, best, theory, bellman))
                    independent = []
                    for wait in range(n):
                        first = k + wait
                        val = None
                        for m in range(1, D-first+2):
                            S = tuple(range(first, first+m))
                            if not can_force_failure(H, S, L, B):
                                val = m
                                break
                        independent.append(val)
                    calculated = model.frontier(H, L, B, k, D)
                    if independent != calculated:
                        raise AssertionError(("T3", L, B, k, D, H))
                    finite = [i for i,x in enumerate(independent) if x is not None]
                    boundary = model.safe_wait_boundary(H, L, B, k, D)
                    if boundary != (max(finite) if finite else None):
                        raise AssertionError(("boundary", L, B, k, D, H))
                    neutral = max((i for i,x in enumerate(independent) if x == theory), default=None)
                    if model.cost_neutral_boundary(H,L,B,k,D) != neutral:
                        raise AssertionError(("neutral", L, B, k, D, H))
                    for a,b in zip(independent,independent[1:]):
                        if (a is None and b is not None) or (a is not None and b is not None and a>b):
                            raise AssertionError(("monotonic", L,B,k,D,H))
                    profiles += 1
        per_l[str(L)] = counts
    return {"status":"PASS", "L": [2,3,4], "budgets":"0..L-1",
            "k":"L+1", "task_lengths":"2L+1 and 2L+2",
            "histories":"all legal subsets of {1,...,L}",
            "opportunities":"all subsets per profile", "opportunity_sets":cases,
            "history_horizon_profiles":profiles, "cases_per_L":per_l,
            "oracle":"full attack decision vectors; independent recursive minimax game",
            "scope":"finite exhaustive verification; not a proof or all parameter values"}


def targeted_large():
    """Representative >2L tasks; retain only recent window state in the game."""
    def recent_game(H, L, B, k, D):
        @lru_cache(None)
        def f(t, recent):
            if t>D:
                return float("inf")
            recent=tuple(x for x in recent if x>=t-L+1)
            wait=f(t+1,recent)
            if len(recent)<B:
                send=max(1,1+f(t+1,tuple(sorted((*recent,t)))))
            else:
                send=1
            return min(wait,send)
        val=f(k,tuple(H))
        return None if val==float("inf") else int(val)

    profiles=cases=0
    for L in range(5,11):
        for B in (0,L-1):
            k=L+1
            D=k+2*L+1
            histories={(),tuple(range(k-B,k)),tuple(range(1,B+1))}
            for H in histories:
                assert legal(H,L,B)
                policy_options={(),tuple(range(k,D+1)),tuple(range(k,D+1,2)),
                                (k,D),tuple(range(k,k+B+1)),tuple(range(D-B,D+1))}
                for S in policy_options:
                    # In the no-success branch every opportunity must be blocked.
                    oracle_failure=legal(set(H)|set(S),L,B)
                    assert model.guarantees_success(H,S,L,B,k,D) != oracle_failure
                    cases+=1
                m=model.m_star(H,L,B,k,D)
                assert m==recent_game(H,L,B,k,D)
                curve=model.frontier(H,L,B,k,D)
                for s,value in enumerate(curve):
                    q=k+s
                    oracle=next((j for j in range(1,D-q+2)
                                 if not legal(set(H)|set(range(q,q+j)),L,B)),None)
                    assert value==oracle
                feasible=[i for i,v in enumerate(curve) if v is not None]
                assert model.safe_wait_boundary(H,L,B,k,D)==(max(feasible) if feasible else None)
                profiles+=1
    return {"status":"PASS","L":[5,6,7,8,9,10],"B":"0 and L-1",
            "task_length":"2L+2","histories":"empty, recent or old saturation (deduplicated)",
            "opportunities":"representative empty, full, sparse, endpoint and B+1 prefixes/suffixes",
            "profiles":profiles,"opportunity_sets":cases,
            "oracle":"independent full-block window scan and recent-window dynamic game",
            "scope":"targeted checks, not full enumeration"}


class Regression(unittest.TestCase):
    def test_infeasible_returns_none(self):
        self.assertIsNone(model.safe_wait_boundary(set(), 2, 1, 1, 1))
        self.assertIsNone(model.m_star(set(), 2, 1, 1, 1))

    def test_feasible_boundary_zero(self):
        self.assertEqual(model.safe_wait_boundary({1}, 2, 1, 2, 2), 0)

    def test_invalid_parameters_and_illegal_history(self):
        for args in [({1,2}, 3, 1, 3, 4), ({2},2,1,2,3),
                     (set(),2,2,1,3), (set(),2,1,2,1)]:
            with self.assertRaises(ValueError):
                model.safe_wait_boundary(*args)

    def test_sparse_counterexample_for_total_count(self):
        self.assertTrue(can_force_failure((), (1,3), 2, 1))
        self.assertFalse(model.guarantees_success((), (1,3), 2, 1, 1, 3))

    def test_single_long_budget_extremes(self):
        for B in (0,3):
            H=tuple(range(1,B+1))
            L=4; k=5; D=15
            self.assertEqual(game(H,L,B,k,D), model.m_star(H,L,B,k,D))
            self.assertEqual(model.safe_wait_boundary(H,L,B,k,D),
                             max(i for i,v in enumerate(model.frontier(H,L,B,k,D)) if v is not None))


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--long", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Regression)
    result=unittest.TextTestRunner(verbosity=2, stream=sys.stderr).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.long or args.write_summary:
        summary=long_audit()
        summary["targeted_larger"]=targeted_large()
        rendered=json.dumps(summary,ensure_ascii=False,indent=2)+"\n"
        if args.write_summary:
            output=Path(__file__).resolve().parents[1]/"data/p45_long_horizon_independent.json"
            output.write_bytes(rendered.encode("utf-8"))
        print(rendered)
