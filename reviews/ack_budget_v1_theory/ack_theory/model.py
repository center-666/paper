"""Pure integer model for one persistent communication task."""
from __future__ import annotations


def window_count(times: set[int] | tuple[int, ...], length: int, end: int) -> int:
    return sum(end - length + 1 <= t <= end for t in times)


def history_is_legal(history: set[int] | tuple[int, ...], length: int, budget: int,
                     first: int = 1, last: int | None = None) -> bool:
    if length < 1 or not 0 <= budget < length or any(t < first for t in history):
        return False
    if last is None:
        last = max(history, default=first)
    return all(window_count(history, length, end) <= budget
               for end in range(first, last + length + 1))


def safety_margin(history: set[int] | tuple[int, ...], opportunities: set[int] | tuple[int, ...],
                  length: int, budget: int, start: int, deadline: int) -> int:
    """Maximum combined historical-plus-future attempts in any relevant window."""
    points = set(history) | set(opportunities)
    return max((window_count(points, length, end) for end in range(start, deadline + 1)), default=0)


def guarantees_success(history, opportunities, length, budget, start, deadline) -> bool:
    return safety_margin(history, opportunities, length, budget, start, deadline) > budget


def t_star(history, length, budget, start, deadline) -> int | None:
    for end in range(start, deadline + 1):
        if window_count(history, length, end) + (end - start + 1) > budget:
            return end
    return None


def m_star(history, length, budget, start, deadline) -> int | None:
    end = t_star(history, length, budget, start, deadline)
    return None if end is None else end - start + 1


def continuous_safe(history, length, budget, start, deadline, wait, attempts):
    first = start + wait
    last = first + attempts - 1
    if attempts < 1 or last > deadline:
        return False
    return guarantees_success(history, set(range(first, last + 1)), length, budget, start, deadline)


def m_min(history, length, budget, start, deadline, wait) -> int | None:
    first = start + wait
    for attempts in range(1, deadline - first + 2):
        if continuous_safe(history, length, budget, start, deadline, wait, attempts):
            return attempts
    return None


def frontier(history, length, budget, start, deadline):
    return [m_min(history, length, budget, start, deadline, wait)
            for wait in range(deadline - start + 1)]


def safe_wait_boundary(history, length, budget, start, deadline) -> int:
    """Largest feasible initial wait, clipped to the available task horizon."""
    candidate = deadline - start - budget + window_count(history, length, deadline)
    return min(deadline - start, candidate)


def cost_neutral_boundary(history, length, budget, start, deadline) -> int | None:
    base = m_star(history, length, budget, start, deadline)
    if base is None:
        return None
    start_end = t_star(history, length, budget, start, deadline)
    eligible = [end for end in range(start_end, deadline + 1)
                if window_count(history, length, end) + base > budget]
    return None if not eligible else max(eligible) - start_end
