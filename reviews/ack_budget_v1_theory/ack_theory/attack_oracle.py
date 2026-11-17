"""Independent brute-force checks; deliberately does not call model predicates."""
from __future__ import annotations
from itertools import combinations
from functools import lru_cache


def brute_window_count(points, length, end):
    return sum(1 for point in points if end - length + 1 <= point <= end)


def brute_can_block_all(history, opportunities, length, budget, start, deadline):
    # Enumerate every causally possible block/allow vector; the objective is
    # to find a legal vector blocking all opportunities, independent of T1.
    slots = sorted(opportunities)
    for mask in range(1 << len(slots)):
        blocked = set(history)
        for i, tick in enumerate(slots):
            if mask & (1 << i):
                blocked.add(tick)
        if any(brute_window_count(blocked, length, t) > budget
               for t in range(start, deadline + 1)):
            continue
        if all(t in blocked for t in slots):
            return True
    return False


def brute_guarantees(history, opportunities, length, budget, start, deadline):
    return not brute_can_block_all(history, opportunities, length, budget, start, deadline)


def brute_min_safe_cardinality(history, length, budget, start, deadline):
    horizon = tuple(range(start, deadline + 1))
    for size in range(len(horizon) + 1):
        for choice in combinations(horizon, size):
            if brute_guarantees(history, choice, length, budget, start, deadline):
                return size, choice
    return None, None


def brute_frontier(history, length, budget, start, deadline):
    result = []
    for wait in range(deadline - start + 1):
        first = start + wait
        answer = None
        for attempts in range(1, deadline - first + 2):
            choice = tuple(range(first, first + attempts))
            if brute_guarantees(history, choice, length, budget, start, deadline):
                answer = attempts
                break
        result.append(answer)
    return result


def brute_causal_minimax(history, length, budget, start, deadline):
    """Bellman game with independently enumerated causal wait/send choices.

    Each send offers an immediate success or a legal block, adversary chooses
    the worse branch. Infinity means that a success guarantee is impossible.
    """
    infinity = float("inf")

    @lru_cache(None)
    def value(tick, past):
        if tick > deadline:
            return infinity
        wait_cost = value(tick + 1, past)
        success_cost = 1
        possible_blocks = tuple(sorted((*past, tick)))
        block_legal = all(brute_window_count(possible_blocks, length, e) <= budget
                          for e in range(start, tick + 1))
        if block_legal:
            blocked_future = value(tick + 1, possible_blocks)
            send_cost = max(success_cost, 1 + blocked_future)
        else:
            send_cost = success_cost
        return min(wait_cost, send_cost)

    answer = value(start, tuple(sorted(history)))
    return None if answer == infinity else int(answer)
