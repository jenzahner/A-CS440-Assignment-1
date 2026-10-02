"""World generation, belief maps, and search measurements. DO NOT EDIT.

Students use the API summary in README.md and the docstrings in the four
editable files. Reading this implementation is optional.

A state is an (x, y) tuple. Cardinal moves cost one. Agents observe terrain
through their base class's sense() and move_to() methods. SearchProblem.expand
counts expansions; passable counts heuristic probes. astar returns (path, g).
Private map access is reserved for the benchmark and visualizations.
"""
from __future__ import annotations

import random
import time
from collections import deque

# ---------------------------------------------------------------- cells

#: never observed; the freespace assumption treats these as traversable
UNKNOWN = 0
#: observed and traversable
FREE = 1
#: observed and blocked
BLOCKED = 2

#: east, south, west, north -- the four compass directions, in that order
DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))


# ---------------------------------------------------------------- the world


class Sensor:
    """The agent's field of view.  The only window onto the true terrain.

    ``sense(x, y)`` returns a 5-tuple ``(here, east, south, west, north)`` of
    :data:`FREE` / :data:`BLOCKED`, with :data:`BLOCKED` reported for anything
    outside the grid. Agents must sense only at their current position;
    use the base class's sense() and move_to() methods.
    """

    __slots__ = ("_probe", "_w", "_h", "count")

    def __init__(self, probe, w, h):
        self._probe = probe
        self._w, self._h = w, h
        #: how many times the agent looked around; the grader reports this
        self.count = 0

    def sense(self, x: int, y: int) -> tuple[int, int, int, int, int]:
        self.count += 1
        out = [BLOCKED if self._probe(x, y) else FREE]
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self._w and 0 <= ny < self._h:
                out.append(BLOCKED if self._probe(nx, ny) else FREE)
            else:
                out.append(BLOCKED)
        return tuple(out)


class GridWorld:
    """One generated instance: a sealed map, a start cell and a target cell.

    Public attributes are ``w``, ``h``, ``start``, ``goal``, ``seed`` and
    ``sensor``.  There is no attribute holding the terrain.
    """

    __slots__ = ("w", "h", "start", "goal", "seed", "sensor", "_probe")

    def __init__(self, w, h, blocked: bytearray, start, goal, seed):
        self.w, self.h = w, h
        self.start, self.goal, self.seed = start, goal, seed

        def probe(x, y):                       # closure: the only reference
            if not (0 <= x < w and 0 <= y < h):
                return True
            return bool(blocked[y * w + x])

        self._probe = probe
        self.sensor = Sensor(probe, w, h)

    def __repr__(self):
        return (f"<GridWorld {self.w}x{self.h} seed={self.seed} "
                f"{self.start}->{self.goal}>")


# ---------------------------------------------------------------- generation


#: the two terrain families every experiment is run on.  They exist because
#: almost every interesting result in this assignment is different in the two,
#: and an experiment run on only one of them will teach you the wrong lesson.
FAMILIES = ("scatter", "maze")


def generate(size: int = 101, seed: int = 0, family: str = "scatter",
             block_prob: float = 0.30, braid: float = 0.20,
             solvable: bool = True) -> GridWorld:
    """Build one gridworld.  ``seed`` and ``family`` determine it completely.

    **family="scatter"** is the depth-first carving from the handout.  Every
    cell starts unvisited; from a random unvisited cell, mark it visited and
    unblocked, then repeatedly pick a random unvisited neighbour, blocking it
    with probability ``block_prob`` and otherwise carving into it.  Dead ends
    backtrack along the stack, and when the stack empties with cells still
    unvisited, carving restarts from one of them.  At 30% the result is about
    70% open: obstacles are scattered rather than structural, there are many
    routes between any two cells, and -- this is the part that matters --
    Manhattan distance is nearly exact.

    **family="maze"** carves corridors instead.  Cells at odd coordinates are
    rooms, walls between them are knocked out by the same depth-first process,
    and then a ``braid`` fraction of dead ends is reopened so that loops (and
    therefore alternative shortest paths) exist.  The result is about 50% open,
    but the shape is completely different: corridors are one cell wide, the
    detours are long, and Manhattan distance is badly wrong almost everywhere.

    You will be asked to run everything on both, and to explain why the two
    disagree.  They disagree because nearly every question in this assignment
    is really a question about *heuristic error*, and the two families sit at
    opposite ends of that scale.

    In both cases the agent and the target are placed in the largest connected
    component, with the target drawn from the quartile of cells furthest from
    the agent.  Two uniformly random cells would often land a few steps apart,
    and a benchmark made mostly of trivial instances measures mostly noise.

    With ``solvable=False`` the target is placed in a different component
    instead, so the agent must discover that it cannot be reached.  The
    autograder uses those to check that you report failure rather than loop.
    """
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; expected one of {FAMILIES}")
    rng = random.Random((seed * 1_000_003) ^ (0x5EED if family == "scatter" else 0xBEE5))
    if family == "scatter":
        blocked = _carve_scatter(size, rng, block_prob)
    else:
        blocked = _carve_maze(size, rng, braid)

    def passable(x, y):
        return 0 <= x < size and 0 <= y < size and not blocked[y * size + x]

    components = _components(passable, size, size)
    components.sort(key=len, reverse=True)
    main = components[0]

    start = rng.choice(sorted(main))
    if solvable:
        dist = _true_distances(passable, size, size, start)
        ranked = sorted(dist, key=lambda c: (-dist[c], c))
        goal = rng.choice(ranked[:max(1, len(ranked) // 4)])
    else:
        others = [c for comp in components[1:] for c in comp]
        goal = rng.choice(sorted(others)) if others else start
    return GridWorld(size, size, blocked, start, goal, seed)


def _carve_scatter(size, rng, block_prob) -> bytearray:
    """The handout's generator: depth-first visiting, blocking as it goes."""
    n = size * size
    blocked = bytearray(n)
    visited = bytearray(n)
    roots = list(range(n))
    rng.shuffle(roots)

    for root in roots:
        if visited[root]:
            continue
        visited[root] = 1
        stack = [root]
        while stack:
            cur = stack[-1]
            cx, cy = cur % size, cur // size
            choices = []
            for dx, dy in DIRS:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < size and 0 <= ny < size:
                    idx = ny * size + nx
                    if not visited[idx]:
                        choices.append(idx)
            if not choices:
                stack.pop()
                continue
            nxt = rng.choice(choices)
            visited[nxt] = 1
            if rng.random() < block_prob:
                blocked[nxt] = 1
            else:
                stack.append(nxt)
    return blocked


def _carve_maze(size, rng, braid) -> bytearray:
    """Recursive-backtracker corridors, then braided to reopen dead ends.

    Braiding is what keeps this from being a "perfect" maze.  A perfect maze
    has exactly one simple path between any two cells, which would make every
    solver return the identical path and every tie-breaking rule irrelevant --
    a benchmark that cannot distinguish the things this assignment is about.
    """
    blocked = bytearray([1]) * (size * size)
    lo, hi = 1, size - 2

    def idx(x, y):
        return y * size + x

    stack = [(1, 1)]
    blocked[idx(1, 1)] = 0
    seen = {(1, 1)}
    while stack:
        x, y = stack[-1]
        choices = [(x + 2 * dx, y + 2 * dy, dx, dy) for dx, dy in DIRS
                   if lo <= x + 2 * dx <= hi and lo <= y + 2 * dy <= hi
                   and (x + 2 * dx, y + 2 * dy) not in seen]
        if not choices:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(choices)
        blocked[idx(x + dx, y + dy)] = 0
        blocked[idx(nx, ny)] = 0
        seen.add((nx, ny))
        stack.append((nx, ny))

    for y in range(lo, hi + 1):
        for x in range(lo, hi + 1):
            if blocked[idx(x, y)]:
                continue
            open_nb = sum(1 for dx, dy in DIRS if not blocked[idx(x + dx, y + dy)])
            if open_nb != 1 or rng.random() >= braid:
                continue
            walls = [(x + dx, y + dy) for dx, dy in DIRS
                     if blocked[idx(x + dx, y + dy)]
                     and lo <= x + dx <= hi and lo <= y + dy <= hi]
            if walls:
                blocked[idx(*rng.choice(walls))] = 0
    return blocked


def _components(passable, w, h) -> list[list[tuple[int, int]]]:
    """Every connected component of traversable cells."""
    seen = set()
    out = []
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or not passable(x, y):
                continue
            comp = []
            q = deque([(x, y)])
            seen.add((x, y))
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for dx, dy in DIRS:
                    nb = (cx + dx, cy + dy)
                    if nb not in seen and passable(*nb):
                        seen.add(nb)
                        q.append(nb)
            out.append(comp)
    return out


# ---------------------------------------------------------------- belief


class Belief:
    """What the agent knows.  Unobserved cells are assumed traversable.

    The freespace assumption lives in :meth:`is_passable`: a cell is passable
    unless it is *known* to be blocked.  :meth:`is_known_free` is the strict
    version, which is what execution (as opposed to planning) must use.
    """

    __slots__ = ("w", "h", "_k", "known_blocked", "version")

    def __init__(self, w, h):
        self.w, self.h = w, h
        self._k = bytearray(w * h)
        #: cells discovered to be blocked, in discovery order (for drawing)
        self.known_blocked: list[tuple[int, int]] = []
        #: bumped every time a blockage is discovered.  Anything you precompute
        #: from the believed map is valid for every LATER version too (the map
        #: only ever loses edges), so this is the number to compare against
        #: when deciding whether a cached table is still worth keeping.
        self.version = 0

    def status(self, x, y) -> int:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return BLOCKED
        return self._k[y * self.w + x]

    def is_passable(self, x, y) -> bool:
        """Freespace assumption: anything not known to be blocked is fair game."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        return self._k[y * self.w + x] != BLOCKED

    def is_known_free(self, x, y) -> bool:
        """Strictly observed to be traversable."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        return self._k[y * self.w + x] == FREE

    def absorb(self, x, y, reading) -> int:
        """Fold one :meth:`Sensor.sense` reading taken at ``(x, y)`` into the map.

        Returns the number of cells whose status changed *in a way that matters*
        -- that is, newly discovered blockages.  Learning that an unknown cell is
        free changes no plan, because the freespace assumption already believed
        it, so it is not counted.
        """
        surprises = 0
        cells = [(x, y)] + [(x + dx, y + dy) for dx, dy in DIRS]
        for (cx, cy), val in zip(cells, reading):
            if not (0 <= cx < self.w and 0 <= cy < self.h):
                continue
            i = cy * self.w + cx
            if self._k[i] != UNKNOWN:
                continue
            self._k[i] = val
            if val == BLOCKED:
                self.known_blocked.append((cx, cy))
                surprises += 1
        if surprises:
            self.version += 1
        return surprises

    def observed(self) -> int:
        return sum(1 for v in self._k if v != UNKNOWN)


# ---------------------------------------------------------------- the problem


class SearchProblem:
    """What :func:`astar` is handed.  Owns every counter.

    ``start``    the cell the search starts from
    ``goal``     the cell the search is trying to reach
    ``cache``    a dict you may use to memoize precomputation across replans;
                 the same dict is handed to every replan by one agent
    ``version``  the belief version (see :attr:`Belief.version`) this problem
                 was built from

    Use :meth:`expand` to get successors and :meth:`passable` to ask about a
    cell.  Both are instrumented.  There is no third way to see the map: the
    belief is reachable only through these two.

    The counters are not attributes.  They are local variables captured by the
    two closures below, so there is nothing on this object to assign to, and
    nothing for a search to accidentally -- or deliberately -- get wrong.  The
    grader reads them through :meth:`snapshot` from its own reference to this
    object after your search returns, and :meth:`intact` tells it whether the
    two closures are still the ones this constructor installed.
    """

    __slots__ = ("start", "goal", "cache", "version", "w", "h",
                 "expand", "passable", "_snapshot", "_orig", "_stop")

    def __init__(self, passable, w, h, start, goal, cache=None, version=0,
                 trace=False):
        self.start, self.goal = start, goal
        #: belief version this problem was built from; see `Belief.version`
        self.version = version
        self.cache = cache if cache is not None else {}
        self.w, self.h = w, h

        n_exp = n_re = n_probe = 0
        expanded = set()
        #: expansions in order, recorded only when `trace` is on.  The
        #: animation needs the order; the benchmarks do not, and an append per
        #: expansion in the hot loop is not something to pay for by default.
        order: list = []
        t0 = time.perf_counter()
        elapsed = [None]

        def expand(state):
            """Return ``((neighbour, cost), ...)`` for the four compass moves.

            Calling this *is* what "expanding a state" means here, and it is how
            expansions are counted.  Call it once per state you pop and commit
            to; calling it twice for the same state in one search is recorded as
            a re-expansion, which A* with a consistent heuristic never needs.
            """
            nonlocal n_exp, n_re
            n_exp += 1
            if state in expanded:
                n_re += 1
            else:
                expanded.add(state)
                if trace:
                    order.append(state)
            x, y = state
            out = []
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if passable(nx, ny):
                    out.append(((nx, ny), 1))
            return tuple(out)

        def probe(x, y):
            """Is this cell traversable under the current belief?

            For heuristics and precomputation.  Counted separately from
            expansions: a heuristic that sweeps the whole grid is doing real
            work, and the report shows what it cost.
            """
            nonlocal n_probe
            n_probe += 1
            return passable(x, y)

        def snapshot():
            return {"expansions": n_exp, "distinct": len(expanded),
                    "reexpansions": n_re, "probes": n_probe,
                    "closed": expanded, "order": order,
                    "elapsed": elapsed[0] if elapsed[0] is not None
                    else time.perf_counter() - t0}

        def stop():
            if elapsed[0] is None:
                elapsed[0] = time.perf_counter() - t0

        self.expand = expand
        self.passable = probe
        self._snapshot = snapshot
        self._stop = stop
        self._orig = (expand, probe)

    def is_goal(self, state) -> bool:
        return state == self.goal

    def stop_clock(self) -> None:
        """Freeze the runtime.  Call this the moment your search returns."""
        self._stop()

    # -- read-only instrumentation -------------------------------------
    def snapshot(self) -> dict:
        return self._snapshot()

    def intact(self) -> bool:
        """False if anything replaced the instrumented closures."""
        return self.expand is self._orig[0] and self.passable is self._orig[1]

    @property
    def expansions(self) -> int:
        return self._snapshot()["expansions"]

    @property
    def reexpansions(self) -> int:
        return self._snapshot()["reexpansions"]

    @property
    def probes(self) -> int:
        return self._snapshot()["probes"]

    @property
    def order(self) -> list:
        """The states you expanded, in the order you expanded them.

        Empty unless the problem was built with ``trace=True``.  This is what
        `demo.py --gif` replays.
        """
        return list(self._snapshot()["order"])

    @property
    def closed(self) -> frozenset:
        """The states you expanded.  Drawn on the report, and used by Adaptive A*."""
        return frozenset(self._snapshot()["closed"])

    @property
    def elapsed(self) -> float:
        return self._snapshot()["elapsed"]


def make_problem(belief: Belief, start, goal, cache=None) -> SearchProblem:
    """The normal way to build a problem: plan over the believed map."""
    return SearchProblem(belief.is_passable, belief.w, belief.h, start, goal,
                         cache, belief.version)


# ---------------------------------------------------------------- references
#
# Ground truth used to grade you.  These are not importable from your own
# modules -- `integrity.guard()` blocks them -- because every one of them would
# let a search cheat rather than compute.


def _true_distances(passable, w, h, source) -> dict:
    """Exact cost-to-go from every reachable cell to ``source``, by BFS.

    Uniform costs make BFS exact, so this needs no heuristic and cannot be
    wrong in the way a student A* can be wrong.  It is the yardstick for both
    optimality and admissibility.
    """
    dist = {source: 0}
    q = deque([source])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in dist and passable(nx, ny):
                dist[(nx, ny)] = d
                q.append((nx, ny))
    return dist


def _optimal_cost(passable, w, h, start, goal):
    """Length of a shortest path, or None when the goal is unreachable."""
    if not passable(*start):
        return None
    return _true_distances(passable, w, h, goal).get(start)


def _true_grid_passable(world: GridWorld):
    """The omniscient passability test.  Graders only."""
    return lambda x, y: not world._probe(x, y)


def _check_path(passable, path, start, goal) -> str | None:
    """Validate a returned path.  Returns a complaint, or None if it is sound."""
    if not path:
        return "empty path"
    if path[0] != start:
        return f"path starts at {path[0]}, not {start}"
    if path[-1] != goal:
        return f"path ends at {path[-1]}, not {goal}"
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return f"{a} and {b} are not adjacent"
        if not passable(*b):
            return f"path enters blocked cell {b}"
    return None


def _effective_branching_factor(nodes: int, depth: int) -> float:
    """Russell & Norvig's b*: the branching factor a uniform tree would need.

    Solve ``N + 1 = 1 + b* + b*^2 + ... + b*^d`` for b* by bisection.  It is the
    standard scale-free way to compare heuristics, because it divides out how
    far away the goal happened to be.
    """
    if depth <= 0 or nodes <= 0:
        return 0.0

    def total(b):
        if abs(b - 1.0) < 1e-9:
            return depth + 1.0
        return (b ** (depth + 1) - 1.0) / (b - 1.0)

    lo, hi = 1.0, 10.0
    target = nodes + 1.0
    if total(hi) < target:
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        if total(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _make_known_problem(world: GridWorld, cache=None,
                        trace=False) -> SearchProblem:
    """A single search over the FULLY KNOWN map.  Graders only.

    Several questions are about one A* search rather than about a sequence of
    them -- how good a heuristic is, what weighting buys -- and those are only
    legible when the map is not also changing underneath the search.  The
    autograder and the report build these; agents never see one, which is why
    this is private.
    """
    return SearchProblem(_true_grid_passable(world), world.w, world.h,
                         world.start, world.goal, cache, 0, trace)
