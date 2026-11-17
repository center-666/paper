"""Fixed semantic cases for the communication-only task (no simulation)."""
import unittest

from attack_oracle import brute_causal_minimax, brute_guarantees
from model import (cost_neutral_boundary, frontier, guarantees_success,
                   history_is_legal, m_star, safe_wait_boundary)


class BoundaryChecks(unittest.TestCase):
    def test_sparse_attempts_may_all_fail(self):
        self.assertFalse(guarantees_success(set(), {1, 3}, 2, 1, 1, 3))
        self.assertFalse(brute_guarantees(set(), {1, 3}, 2, 1, 1, 3))

    def test_empty_opportunities_fail(self):
        self.assertFalse(guarantees_success(set(), set(), 5, 0, 1, 3))

    def test_zero_budget_counts_successful_attempt(self):
        self.assertEqual(m_star(set(), 5, 0, 1, 3), 1)
        self.assertEqual(brute_causal_minimax(set(), 5, 0, 1, 3), 1)
        self.assertFalse(history_is_legal({1}, 5, 0))

    def test_last_slot_budget_exhaustion_forces_success(self):
        self.assertTrue(guarantees_success({1, 2}, {3}, 5, 2, 3, 3))
        self.assertEqual(brute_causal_minimax({1, 2}, 5, 2, 3, 3), 1)

    def test_last_slot_without_history_may_fail(self):
        self.assertIsNone(m_star(set(), 5, 2, 4, 4))
        self.assertIsNone(brute_causal_minimax(set(), 5, 2, 4, 4))

    def test_equal_history_size_can_change_frontier(self):
        self.assertEqual(frontier({1}, 5, 2, 4, 10), [2, 3, 3, 3, 3, None, None])
        self.assertEqual(frontier({3}, 5, 2, 4, 10), [2, 2, 2, 3, 3, None, None])
        self.assertEqual(cost_neutral_boundary({1}, 5, 2, 4, 10), 0)
        self.assertEqual(cost_neutral_boundary({3}, 5, 2, 4, 10), 2)

    def test_long_horizon_exceeds_window(self):
        self.assertEqual(frontier(set(), 2, 1, 1, 6), [2, 2, 2, 2, 2, None])
        self.assertEqual(safe_wait_boundary(set(), 2, 1, 1, 6), 4)
        self.assertEqual(brute_causal_minimax(set(), 2, 1, 1, 6), 2)


if __name__ == "__main__":
    unittest.main()
