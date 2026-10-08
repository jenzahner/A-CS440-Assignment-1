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
    """
    A* graph search over the believed map.  Returns ``(path, g)``.

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
        return ([problem.start], {problem.start: 0})

    g = {problem.start:0} #cost from the start to each other state 
    parent = {problem.start: None} #using to remember how we got there 
    closed = set() #states that have already been explored
    open_heap = BinaryHeap() # states we need to explore

    # Part 3: Tie-breaking when states have an equal f or g

    counter = 0 # When f and g tie, the counter is compared

    def key (f, gval):
        nonlocal counter # Updating the counter that was initialized outside of this function
        counter +=1
        if (tie_break == "large_g"):
            tb = -gval #The larger g becomes higher priority when we flip the sign
        else:
            tb = gval
        return (f, tb, counter) # if f and g tie, the earlier push is expanded

    # Part 5: Use the larger of the base h and the learned h 
    start_h = h(problem.start, problem)
    if learned_h is not None:
        start_h = max(start_h, learned_h.get(problem.start, 0))

    # f = g + (weight * h). g = 0 in the beginning
    open_heap.push(key(weight * start_h, 0), problem.start) 

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

                 # Part 5: use the larger of the base h and the learned h
                neighbor_h = h(neighbor, problem)
                if learned_h is not None:
                    neighbor_h = max(neighbor_h, learned_h.get(neighbor, 0))

                # f = g + (weight * h). Only h is scaled
                f = newg + (weight * neighbor_h)

                open_heap.push(key(f, newg), neighbor)

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
