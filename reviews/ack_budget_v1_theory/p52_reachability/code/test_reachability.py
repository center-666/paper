"""Independent integer oracles for P5.2. No random or estimator imports."""
import json
from collections import deque
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import unittest

from reachability_audit import (
    absolute_replay, bounds, general_witness, graph, transitions, witness,
    worst_attempts,
)


def direct_graph(B, L):
    """Literal old gate, bit history, postcommunication age; no bounds calls."""
    # bit zero represents a block at the preceding tick.
    seen = {(0, 0)}
    todo = deque(seen)
    while todo:
        age, mask = todo.popleft()
        remaining = B - age + 1
        occupied_D = sum((mask >> j) & 1 for j in range(L - 1)
                         if j + 1 + remaining - 1 < L)
        send = remaining <= B - occupied_D + 1
        aged = (mask << 1) & ((1 << (L - 1)) - 1)
        nxt = [(0, aged)]  # low anchor; also success if sending
        if not send:
            nxt.append((age + 1, aged))
        elif mask.bit_count() < B:
            nxt.append((age + 1, aged | 1))
        for dest in nxt:
            assert dest[0] <= B
            if dest not in seen:
                seen.add(dest)
                todo.append(dest)
    return {(a + 1, tuple(i + 1 for i in range(L - 1) if (m >> i) & 1))
            for a, m in seen}


def direct_minimax(state, B, L, first_wait=0):
    """Absolute-time Bellman game: both wait/send; budget tested directly."""
    age, ages = state
    k = L
    D = k + B + 1 - age
    H = tuple(sorted(k - h for h in ages))
    inf = float("inf")

    @lru_cache(None)
    def value(t, past):
        if t > D:
            return inf
        waiting = value(t + 1, past)
        can_block = sum(t - L + 1 <= h < t for h in past) < B
        sending = max(1, 1 + value(t + 1, past + (t,))) if can_block else 1
        return min(waiting, sending)

    return value(k + first_wait, H)


class ReachabilityTests(unittest.TestCase):
    def test_supplied_reachable_trace_and_continuations(self):
        events = ["high_block", "low_anchor", "high_wait", "high_block", "high_success"]
        rows, state = absolute_replay(events, 2, 6, "original")
        self.assertEqual([r["attempt"] for r in rows], [True, False, False, True, True])
        self.assertEqual(state, (1, (2, 5)))
        self.assertEqual(bounds(state, 2, 6)["frontier"], [1, 2, None])
        self.assertEqual(worst_attempts(state, 2, 6, "original"), 2)
        self.assertEqual(worst_attempts(state, 2, 6, "cost_neutral"), 1)
        # This prefix also follows the new policy, not an arbitrary transplanted state.
        _, newstate = absolute_replay(events + ["high_success"], 2, 6, "cost_neutral")
        self.assertEqual(newstate[0], 1)

    def test_legal_but_unreachable_history(self):
        # k=5, tau=4, H={1,3}: legal B=2,L=5 but cannot arise under old gate.
        s = (1, (2, 4))
        self.assertGreater(bounds(s, 2, 5)["s_safe"], bounds(s, 2, 5)["s_cost"])
        self.assertNotIn(s, graph(2, 5, "original")[0])
        parents, _ = graph(2, 5, "original")
        self.assertEqual(len(parents), 12)
        self.assertTrue(all(bounds(x, 2, 5)["s_safe"] == bounds(x, 2, 5)["s_cost"]
                            for x in parents))

    def test_independent_reachable_graphs(self):
        for L in range(1, 10):
            for B in range(L):
                with self.subTest(B=B, L=L):
                    self.assertEqual(set(graph(B, L, "original")[0]), direct_graph(B, L))

    def test_independent_bellman_and_all_waits(self):
        for L in range(1, 9):
            for B in range(L):
                for policy in ("original", "cost_neutral"):
                    for state in graph(B, L, policy)[0]:
                        p = bounds(state, B, L)
                        self.assertEqual(p["m_star"], direct_minimax(state, B, L))
                        for s, val in enumerate(p["frontier"]):
                            self.assertEqual(float("inf") if val is None else val,
                                             direct_minimax(state, B, L, s))

    def test_general_family_outside_graph_range(self):
        for B in range(2, 21):
            for extra in (4, 5, 9, 21):
                L = B + extra
                _, state = absolute_replay(general_witness(B, L), B, L, "original")
                p = bounds(state, B, L)
                self.assertEqual((p["m_star"], p["s_cost"], p["s_safe"]),
                                 (1, 0, min(B - 1, L - B - 2)))

    def test_minimal_boundary_no_101(self):
        for B in range(1, 9):
            L = B + 3
            for state in graph(B, L, "original")[0]:
                H = set(state[1])
                self.assertFalse(any(x in H and x+1 not in H and x+2 in H
                                     for x in range(1, L-2)))
                p = bounds(state, B, L)
                self.assertEqual(p["s_safe"], p["s_cost"])

    def test_all_shortest_witnesses_absolute_replay(self):
        for L in range(1, 9):
            for B in range(L):
                for policy in ("original", "cost_neutral"):
                    parents, _ = graph(B, L, policy)
                    for state in parents:
                        _, end = absolute_replay(witness(parents, state), B, L, policy)
                        self.assertEqual(end, state)

    def test_expiry_criterion_not_only_reachable_states(self):
        # Independent enumerate legal short-task histories; filter infeasibility
        # with Bellman rather than the production formula.
        count = 0
        for L in range(1, 8):
            for B in range(L):
                for size in range(B+1):
                    for H in combinations(range(1, L), size):
                        for a in range(1, B+2):
                            if a in H:
                                continue
                            state = (a, H)
                            if direct_minimax(state, B, L) == float("inf"):
                                continue
                            p = bounds(state, B, L)
                            t = p["m_star"] - 1
                            change = sum(x+t<L for x in H) - sum(x+t+p["s_safe"]<L for x in H)
                            self.assertEqual(p["s_safe"] > p["s_cost"], change > 0)
                            count += 1
        self.assertEqual(count, 559)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReachabilityTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = dict(tests=result.testsRun, failures=len(result.failures),
                  errors=len(result.errors), skipped=len(result.skipped),
                  successful=result.wasSuccessful(),
                  independent_graph_L=[1, 9], independent_bellman_L=[1, 8],
                  absolute_witness_replay_L=[1, 8],
                  feasible_state_expiry_cases=559,
                  general_constructive_family_cases=76,
                  generated_random_trajectories=0)
    out = Path(__file__).resolve().parents[1] / "data" / "regression_results.json"
    out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
