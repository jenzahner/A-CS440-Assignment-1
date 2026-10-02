# CS 440 Assignment 1: Fast Trajectory Replanning

Implement the search algorithms and explain their behavior. The world generator,
sensing, measurements, plots, and PDF writer are provided. You do not need to
read their implementations to complete the assignment.

## Start

Use Python 3.10 or newer; no packages need to be installed. Run these commands
from the folder containing this README:

```bash
python3 demo.py --tour       # works before you implement anything
python3 autograder.py        # untouched starter: 3.0 / 55
```

Open the images in `figures/`. Read the handout for the algorithms and questions,
then work through the four Python files below. Also fill in `report.txt`.

## What to implement

| Order | File | Work | Check |
|---|---|---|---|
| 1 | `gridworld/heap.py` | Binary min-heap | `python3 autograder.py --part 2` |
| 2 | `gridworld/search.py` | A* with Manhattan distance | `python3 demo.py --example` |
| 3 | `gridworld/agents.py` | Repeated Forward A* | `python3 autograder.py --part 2` |
| 4 | `gridworld/search.py` | Both tie-breaking rules | `python3 autograder.py --part 3` |
| 5 | `gridworld/agents.py` | Repeated Backward A* | `python3 autograder.py --part 4` |
| 6 | `gridworld/agents.py`, `gridworld/search.py` | Adaptive A* | `python3 autograder.py --part 5` |
| 7 | `gridworld/heuristics.py` | Landmark and custom heuristics | `python3 autograder.py --part 6` |
| 8 | `gridworld/search.py` | Weighted A* | `python3 autograder.py --part 7` |

Each file marks the required work with `TODO`. Read the section for your current
part. Leave the other files unchanged; Gradescope uses staff copies of the
support code. Ready-made priority queues such as `heapq` are not allowed.

## API reference

A cell is an `(x, y)` tuple. Moves are east, south, west, or north and cost one.

**Search (Part 2).** `astar(problem, h)` returns `(path, g)`: a list of cells
including both endpoints, and a dictionary of g-values. Return `(None, g)` if
the goal is unreachable. For `start == goal`, return `([start], {start: 0})`.

| Use | Meaning |
|---|---|
| `problem.start`, `problem.goal` | Search endpoints |
| `problem.is_goal(s)` | Whether `s` is the goal |
| `problem.expand(s)` | Returns `(neighbor, cost)` pairs and counts one expansion |
| `h(s, problem)` | Heuristic estimate from `s` to this search's goal |
| `reconstruct(parent, goal)` | Provided helper that returns a path |

Check for the goal when it is selected from OPEN, before calling `expand`.
Use your heap and maintain a closed set. The unweighted search uses consistent
heuristics and should not expand a state twice in one search.

**Agents (Parts 2, 4, 5).** The base class supplies these operations:

| Use | Meaning |
|---|---|
| `self.pos`, `self.goal` | Current position and fixed target |
| `self.sense()` | Updates the belief from the current cell and its four neighbors |
| `self.make_search(start, goal)` | Creates and registers a search over the current belief |
| `self.belief.is_known_free(x, y)` | Whether a cell has been observed to be free |
| `self.move_to(cell)` | Moves one step, records it, **and senses automatically** |
| `problem.stop_clock()` | Ends timing after a search returns |
| `problem.closed` | States expanded by that search, for Adaptive A* |

Call `sense()` before the first plan. Read the belief through these methods;
do not access the true map. Set `self.solved` and return a Boolean from `run()`.
Pass the agent's `self.h`, `self.tie_break`, and `self.weight` to its searches.

**Heuristics (Part 6).** `bfs_from(problem, landmark)` is provided and returns
a distance dictionary over the believed map. Missing cells are unreachable.
Use `problem.cache` to keep tables between replans. `problem.version` increases
when new blocked cells are found. `problem.passable(x, y)` tests the belief;
`problem.w` and `problem.h` give the grid dimensions.

## Inspect a run

```bash
python3 demo.py --search --gif --tie-break large_g
python3 demo.py --search --gif --tie-break small_g
python3 demo.py --run --gif --agent adaptive
```

These write animations into `figures/`. Omit `--gif` for still images.
Compare the expansion order and the route the agent walks.

## Write and submit

Enter team members, the pledge, and answers Q1–Q7 in `report.txt`. Each rendered
answer may contain at most 520 characters, including substituted measurements.
Give the main argument; be prepared to explain its details at the code review.

Cite measured results with macros, for example:

```text
The smaller-g rule used {{scatter.tie.ratio}} times as many expansions.
```

`python3 autograder.py --macros` lists the available names and draft values.
Single digits in prose are allowed; typed results such as `15`, `0.42`, `3x`,
or `60%` are rejected. Generate the report with:

```bash
python3 make_report.py --quick    # draft using fewer worlds
python3 make_report.py            # full experiment set for submission
python3 submit.py                 # creates submission.zip, including hidden files
```

Resolve any reported problems and inspect `report.pdf`. Regenerate it after
editing your code, answers, or team list. Run `python3 submit.py` and upload
`submission.zip` to Gradescope. It includes the algorithm and support files,
`language.txt`, `report.txt`, `report.pdf`, and the hidden `.a1log`. Submit exactly
one language variant; Gradescope detects it automatically. Add every team member to the Gradescope submission.

The autograder awards up to 55 points. Written answers and the code review
account for the remaining 45; see the handout for the grading rules.
