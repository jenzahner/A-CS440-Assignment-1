"""The replanning agent's plumbing.  DO NOT EDIT.

Sensing, movement and the bookkeeping the grader reads live here so that the
file you edit contains only the loop and the planning.  Your agents subclass
:class:`ReplanningAgent`.
"""
from __future__ import annotations

from gridworld.core import Belief, SearchProblem, make_problem
from gridworld.hlib import h_manhattan


class IllegalMove(Exception):
    """Raised when an agent tries to walk somewhere it has no right to walk."""


class ReplanningAgent:
    """An agent in a gridworld it cannot see.

    Subclasses implement :meth:`plan` and :meth:`run`.  Everything here is
    provided, and two methods are the *only* sanctioned ways to act:
    :meth:`make_search`, which is how a search gets counted, and
    :meth:`move_to`, which is how a move gets recorded.
    """

    label = "agent"

    def __init__(self, world, h=h_manhattan, *, tie_break="large_g", weight=1.0):
        self.world = world
        self.h = h
        self.tie_break = tie_break
        self.weight = weight
        self.belief = Belief(world.w, world.h)
        #: handed to every search this agent runs, so precomputation survives
        self.cache: dict = {}
        self.pos = world.start
        self.goal = world.goal
        #: every cell the agent actually stood in, in order.  The grader
        #: re-walks this against the true map, so it cannot flatter you.
        self.trajectory = [world.start]
        #: one entry per A* search, in order.  The grader reads the counters
        #: off these; this is the only record of what your searches cost.
        self.searches: list[SearchProblem] = []
        #: set by `run`: True if the target was reached, False if the agent
        #: correctly determined that it cannot be
        self.solved: bool | None = None

    # ------------------------------------------------------------ provided

    def sense(self) -> int:
        """Look around from the current cell.  Returns newly found blockages.

        A return of zero means nothing the agent did not already assume:
        learning that an unknown cell is free never invalidates a plan, because
        the freespace assumption already believed it.
        """
        reading = self.world.sensor.sense(*self.pos)
        return self.belief.absorb(self.pos[0], self.pos[1], reading)

    def make_search(self, start, goal) -> SearchProblem:
        """Build one instrumented search problem and register it.

        The only sanctioned way to get a problem: the grader reads its numbers
        off ``self.searches``, so a search built some other way is a search
        that did not happen as far as your report is concerned.
        """
        p = make_problem(self.belief, start, goal, self.cache)
        self.searches.append(p)
        return p

    def move_to(self, cell) -> None:
        """Step to an adjacent cell that is known to be free.

        Refuses any move that is not to a 4-adjacent cell the agent has
        actually observed to be free, so an agent that walks its plan blindly
        into unknown territory raises here instead of quietly producing an
        impossible trajectory.  Since the agent observes all four neighbours
        before it moves, a correct agent never trips this.
        """
        x, y = self.pos
        if abs(cell[0] - x) + abs(cell[1] - y) != 1:
            raise IllegalMove(f"{self.pos} -> {cell} is not a single step")
        if not self.belief.is_known_free(*cell):
            raise IllegalMove(f"stepped into {cell}, which is not known to be free")
        self.pos = cell
        self.trajectory.append(cell)
        self.sense()

    # ------------------------------------------------------------ yours

    def plan(self):
        raise NotImplementedError("your agent must implement plan()")

    def run(self, max_steps: int = 200_000) -> bool:
        raise NotImplementedError("your agent must implement run()")
