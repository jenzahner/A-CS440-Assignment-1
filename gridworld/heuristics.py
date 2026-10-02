"""Part 6: implement landmark and custom heuristics. YOU EDIT THIS FILE.

Both heuristics must be admissible and consistent on the map being searched.
Use the provided bfs_from(problem, landmark) to build distance tables.

Available fields: problem.goal, problem.w, problem.h, problem.cache, and
problem.version. problem.passable(x, y) checks the believed map. The cache
persists across replans; the version increases when blockages are discovered.
Precomputation probes and runtime are measured for you.
"""
from __future__ import annotations

from gridworld.hlib import bfs_from, corners, h_manhattan, h_zero


def h_differential(state, problem) -> float:
    """A landmark (differential) heuristic.

    TODO (Part 6a).

    Pick a few landmarks. For each landmark ``l``, one call to ``bfs_from``
    gives ``d(l, v)`` for every cell ``v``. Then

        ``h(s) = max over landmarks l of  | d(l, s) - d(l, goal) |``

    Requirements:

      * Cache the tables in ``problem.cache`` -- the same dict reaches every
        replan of one agent. Do **not** bake the goal into a table; the goal
        moves between replans. Key on the landmarks and the version the tables
        were built at.
      * Tables built at an older belief version stay admissible, so rebuilding
        is a performance decision, not a correctness one. Rebuild when
        ``problem.version - built_at > REBUILD_EVERY``.
      * Skip any landmark whose distance to ``s`` or to ``goal`` is unknown.

    Choose and justify the number and placement of landmarks. ``corners``
    returns candidate locations, which may be blocked.
    """
    raise NotImplementedError("Part 6a: implement h_differential")


def h_custom(state, problem) -> float:
    """Your best admissible heuristic.

    TODO (Part 6d). Combine heuristics while preserving admissibility and
    consistency. Evaluate both search savings and precomputation cost.
    """
    raise NotImplementedError("Part 6d: implement h_custom")


#: How many belief versions a landmark table may be stale before you rebuild
#: it. Part 6(c) sweeps this; the report plots the sweep.
REBUILD_EVERY = 16

#: Registry the autograder and the report iterate over.
HEURISTICS = {
    "zero": h_zero,
    "manhattan": h_manhattan,
    "differential": h_differential,
    "custom": h_custom,
}
