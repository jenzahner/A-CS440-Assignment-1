"""Heuristic building blocks you are given.  DO NOT EDIT.

These live outside `heuristics.py` so that the file you edit contains only the
heuristics you write.  Import from here; the graders use their own copy.
"""
from __future__ import annotations

from collections import deque

from gridworld.core import DIRS


def h_zero(state, problem) -> float:
    """Uniform-cost search in disguise.  The baseline every other h beats."""
    return 0.0


def h_manhattan(state, problem) -> float:
    """|dx| + |dy|.  The heuristic the handout specifies for Parts 2 to 5.

    Admissible and consistent because each move changes exactly one coordinate
    by exactly one, so no single move can reduce this sum by more than one --
    which is what Part 1(b) asks you to write down properly.
    """
    return abs(state[0] - problem.goal[0]) + abs(state[1] - problem.goal[1])


def bfs_from(problem, source) -> dict:
    """Exact distances from ``source`` to every cell reachable in the belief.

    One breadth-first sweep; uniform costs make it exact, so there is no
    heuristic inside the heuristic.  It goes through ``problem.passable``, so
    the cost of calling it is measured and reported -- which is the honest
    accounting Part 6 is about.
    """
    if not problem.passable(*source):
        return {}
    dist = {source: 0}
    q = deque([source])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for dx, dy in DIRS:
            nxt = (x + dx, y + dy)
            if nxt not in dist and problem.passable(*nxt):
                dist[nxt] = d
                q.append(nxt)
    return dist


def corners(problem) -> list:
    """The four corner cells: a starting point for landmark selection.

    Corners are not necessarily passable.  :func:`bfs_from` from a blocked cell
    returns an empty table, which your heuristic should ignore.  Doing better than corners is part of Part 6(a).
    """
    return [(0, 0), (problem.w - 1, 0), (0, problem.h - 1),
            (problem.w - 1, problem.h - 1)]
