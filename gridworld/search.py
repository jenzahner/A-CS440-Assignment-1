"""Parts 2, 3, 5, and 7: implement A*. YOU EDIT THIS FILE.

Start with Part 2. Add tie-breaking, learned heuristics, and weighting as you
reach those parts. The API summary in README.md is sufficient to use the
provided search problem; you do not need to read core.py.
"""
from __future__ import annotations

from gridworld.core import SearchProblem
from gridworld.heap import BinaryHeap


def astar(problem: SearchProblem, h, *, tie_break: str = "large_g",
          weight: float = 1.0, learned_h: dict | None = None):
    """A* graph search over the believed map.  Returns ``(path, g)``.

        ``path``   list of cells ``[start, ..., goal]``, or ``None`` if the
                   goal cannot be reached
        ``g``      your g-value dict, ``{cell: cost from start}``

    The framework measures expansions and runtime. Return the g-values so
    Adaptive A* can use them in Part 5. If start equals goal, return
    ``([problem.start], {problem.start: 0})``.

    **What you are given.** Exactly three things:

        ``problem.start``            the cell to search from
        ``problem.is_goal(state)``   have you arrived?
        ``problem.expand(state)``    ``((neighbour, cost), ...)``

    and the heuristic, called as ``h(state, problem)``.

    ---- Part 2: write this much first ----

    TODO. Plain A*, ignoring all three keyword arguments.

      * With a consistent ``h`` and weight 1, return an optimal path.
        Admissibility alone does not suffice for graph search without reopening.
      * Test for the goal when it is selected from OPEN, before expanding it.
      * Call ``problem.expand(state)`` once for each state you commit to
        expanding, and **never twice for the same state**. Re-expansions are
        counted and reported.
      * Return ``(None, g)`` when no path exists.

    `heapq` is blocked; use your `BinaryHeap`. Whether you handle an improved
    g-value by decrease-key or by pushing a duplicate and skipping stale pops
    is your choice. Be ready to explain its time and memory costs.

    ==================================================================
    Everything below is Parts 3, 5 and 7. Come back when you get there.
    ==================================================================

    ---- Part 3: ``tie_break`` ----

    Select among states with equal f-values using the requested rule.

        ``"large_g"``   among equal f, expand the LARGER g first
        ``"small_g"``   among equal f, expand the SMALLER g first

    Push ``(f, -g, counter)`` or ``(f, g, counter)`` respectively. The counter
    is a strictly increasing integer, so runs are reproducible.

    ---- Part 5: ``learned_h`` ----

    Adaptive A* passes h-values learned by earlier searches. Use

        ``max(h(state, problem), learned_h.get(state, 0))``

    -- never the learned value alone, never the sum.

    ---- Part 7: ``weight`` ----

    ``f(s) = g(s) + weight * h(s)``. Weight the heuristic only: not ``g``, and
    not the goal test. Use a consistent base heuristic. Do not reopen closed
    states in this assignment; Part 7's proof must cover this version.
    """
    #part 2

    if problem.is_goal(problem.start): 
        return ([problem.star], {problem.start: 0})

    g = {problem.start:0} #cost from the start to each other state 
    parent = {problem.start: None} #using to remember how we got there 
    closed = set() #states that have already been explored
    open_heap = BinaryHeap() # states we need to explore

    #A* uses f = g+h 
    startf = h(problem.start,problem)
    open_heap.push(startf, problem.start)

    #keep taking the lowest priority state from open
    while open_heap.data:
        present = open_heap.pop()

        #check whether its already been explored 
        if present in closed: 
            continue 
        closed.add(present)

        #now check for the goal 
        if problem.is_goal(present): 
            return( reconstruct(parent,present),g)

        #get neighbors 
        for neighbor, cost in problem.expand(present): 
            #always calculate new cost 
            newg = g[present] + cost 
            #have we seen this one before, or found a better way to get to it
            if neighbor not in g or newg < g[neighbor]:
                #if yes swap 
                g[neighbor] = newg
                parent[neighbor] = present 
                #and calculate A* priority 
                f = newg + h(neighbor,problem)
                #then add to open
                open_heap.push(f,neighbor)

    return(None,g)


def reconstruct(parent: dict, goal):
    """Walk parent pointers back from ``goal``, returning the path forwards.

    Provided. ``parent`` maps each state to the state it was reached from, and
    the start to ``None``.
    """
    path = [goal]
    while parent.get(path[-1]) is not None:
        path.append(parent[path[-1]])
    path.reverse()
    return path
