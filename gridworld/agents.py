"""Parts 2, 4, and 5: implement the replanning agents. YOU EDIT THIS FILE.

Use the freespace assumption: unobserved cells are presumed traversable.
The base class provides sensing, movement, and measurement:

    self.sense()                  update belief at the current position
    self.make_search(start, goal) create and register a search problem
    self.move_to(cell)            move one step AND sense automatically

It also provides self.pos, self.goal, self.belief, self.h, self.tie_break,
self.weight, and self.solved. See README.md for the complete API summary.
"""
from __future__ import annotations

from gridworld.agentbase import IllegalMove, ReplanningAgent
from gridworld.hlib import h_manhattan
from gridworld.search import astar


class RepeatedForwardAStar(ReplanningAgent):
    """Part 2: plan optimistically, walk, replan on surprise.

    The loop:

        1. Look around; fold what you saw into the belief.
        2. Plan a shortest presumed-unblocked path.
        3. No path? Report the target unreachable and stop.
        4. Walk it one cell at a time, looking around after every step.
        5. The moment the next cell turns out to be blocked, replan.
    """

    label = "Repeated Forward A*"

    def plan(self):
        """One A* search, from the agent to the target. Returns ``(path, g)``.

        TODO (Part 2c).

        Build the problem with ``self.make_search(self.pos, self.goal)``, run
        ``astar`` on it with ``self.h``, ``self.tie_break`` and ``self.weight``,
        call ``problem.stop_clock()`` the moment it returns, and hand back both
        the path and the g-values.
        """
        raise NotImplementedError("Part 2c: implement plan")

    def run(self, max_steps: int = 200_000) -> bool:
        """Drive the agent to the target. Returns True if it arrived.

        TODO (Part 2d).

        Two details decide whether this works:

          * Look around *before* the first plan. The agent starts knowing
            nothing at all.
          * Follow the plan only while the next cell ``is_known_free``.
            ``move_to`` senses automatically; do not call ``sense`` again.
          * Stop after at most ``max_steps`` moves and return False if the
            target has not been reached. Handle start == goal without a search.

        Return ``False`` -- do not raise, do not loop forever -- when a plan
        comes back ``None``. Set ``self.solved`` either way.
        """
        raise NotImplementedError("Part 2d: implement run")


class RepeatedBackwardAStar(RepeatedForwardAStar):
    """Part 4: the same loop, searching from the target instead.

    Two things to be careful about, and they are the point of the part: the
    search now runs from ``self.goal`` to ``self.pos``, so the heuristic
    measures distance to the *agent*; and A* hands the path back in the
    direction it searched, while the agent walks the other way.
    """

    label = "Repeated Backward A*"

    def plan(self):
        """TODO (Part 4a). Search target-to-agent, then reverse the path."""
        raise NotImplementedError("Part 4a: implement plan")


class AdaptiveAStar(RepeatedForwardAStar):
    """Part 5: make each replan cheaper by keeping what the last one proved.

    Use weight 1 for Adaptive A*. For every state ``s`` a successful
    unweighted search expanded,
    ``h_new(s) = g(goal) - g(s)`` is a legal h-value, never smaller than the
    one you started with, and costs a subtraction.
    """

    label = "Adaptive A*"

    def __init__(self, world, h=h_manhattan, *, tie_break="large_g",
                 weight=1.0):
        super().__init__(world, h, tie_break=tie_break, weight=weight)
        #: state -> the best h-value any past search has proved for it
        self.learned_h: dict = {}

    def plan(self):
        """TODO (Part 5a).

        As Part 2c, but pass ``learned_h=self.learned_h`` to ``astar`` and
        afterwards call ``self.learn(problem, path, g)``.
        """
        raise NotImplementedError("Part 5a: implement plan")

    def learn(self, problem, path, g) -> None:
        """Record ``h_new(s) = g(goal) - g(s)`` for every expanded state.

        TODO (Part 5b).

        Only learn from a search that actually reached the target.
        ``problem.closed`` is the set of states it expanded. Keep the largest
        value you have ever learned for a state, never a smaller one.
        """
        raise NotImplementedError("Part 5b: implement learn")


#: Registry the autograder and the report iterate over.
AGENTS = {
    "forward": RepeatedForwardAStar,
    "backward": RepeatedBackwardAStar,
    "adaptive": AdaptiveAStar,
}
