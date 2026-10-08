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

    e1 = problem.cache.get("diff")
    #No tables 
    if e1 is None:

        grids1 = []
        spots = []
        totalc = corners(problem)

        # Iterate over each corner to find landmarks.
        for corner in totalc:
            if problem.passable(*corner):
                spot1 = corner
            else:
                x = corner[0]
                y = corner[1]
                if x == 0:
                    sidesx = 1
                else:
                    sidesx = -1
                if y == 0:
                    sidesy = 1
                else:
                    sidesy = -1
                # Determine the maximum w and h.
                if problem.w > problem.h:
                    size = problem.w
                else:
                    size = problem.h

                spot1 = None
                for k in range(size):
                    finalx = x + (sidesx * k)
                    finaly = y + (sidesy * k)

                    if finalx >= 0 and finalx < problem.w:
                        if finaly >= 0 and finaly < problem.h:

                        
                            if problem.passable(finalx, finaly):
                                spot1 = (finalx, finaly)
                                break

            #If no landmark 
            if spot1 is None:
                continue
            #No repeat landmarks 
            if spot1 in spots:
                continue
            spots.append(spot1)

            #BFS
            grid = bfs_from(problem, spot1)

            grids1.append(grid)

        e1 = {
            "built_at": problem.version,
            "tables": grids1
        }

        problem.cache["diff"] = e1

    else:
        m = problem.version - e1["built_at"]

        if m > REBUILD_EVERY:
            grids1 = []
            spots = []

            all_corners = corners(problem)

            for corner in all_corners:

                if problem.passable(*corner):
                    spot1 = corner

                else:
                    x = corner[0]
                    y = corner[1]

                    if x == 0:
                        sidesx = 1
                    else:
                        sidesx = -1

                    if y == 0:
                        sidesy = 1
                    else:
                        sidesy = -1

                    if problem.w > problem.h:
                        size = problem.w
                    else:
                        size = problem.h

                    spot1 = None

                    for k in range(size):

                        finalx = x + (sidesx * k)
                        finaly = y + (sidesy * k)

                        if finalx >= 0 and finalx < problem.w:
                            if finaly >= 0 and finaly < problem.h:

                                if problem.passable(finalx, finaly):
                                    spot1 = (finalx, finaly)
                                    break

                if spot1 is None:
                    continue

                if spot1 in spots:
                    continue

                spots.append(spot1)

                grid = bfs_from(problem, spot1)

                grids1.append(grid)

            e1 = {
                "built_at": problem.version,
                "tables": grids1
            }

            problem.cache["diff"] = e1

    goal = problem.goal
    f = 0

    #every table
    for grid in e1["tables"]:

        dist = grid.get(state)
        distfinal = grid.get(goal)
        if dist is None:
            continue

        if distfinal is None:
            continue
        sub = dist - distfinal

        if sub < 0:
            sub = -sub
        if sub > f:
            f = sub

    return f


def h_custom(state, problem) -> float:
    """Your best admissible heuristic.

    TODO (Part 6d). Combine heuristics while preserving admissibility and
    consistency. Evaluate both search savings and precomputation cost.
    """
    manhattan = h_manhattan(state, problem)
    diff2 = h_differential(state, problem)
    if manhattan > diff2:
        return manhattan
    else:
        return diff2


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
