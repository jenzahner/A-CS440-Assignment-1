#!/usr/bin/env python3
"""Look at what your code is doing.  DO NOT EDIT.

    python3 demo.py --tour                  start here: a guided five minutes
    python3 demo.py --check                 Part 0: is everything installed?
    python3 demo.py --example               a tiny world, worked end to end
    python3 demo.py --world maze --seed 3   draw one world as text and as a PNG
    python3 demo.py --search --family maze  one A* search, drawn
    python3 demo.py --run --family scatter  the replanning agent, drawn

Add --gif to either of the last two and you get an animation instead of a
still: the search expanding cell by cell, or the agent walking and the walls
appearing as it discovers them.  A still tells you where the search went; the
animation tells you the order, which is the part that tells the algorithms
apart.  Try it on both tie-breaking rules and watch the difference.

Debugging a search by staring at expansion counts is miserable.  Debugging it
by looking at which cells it expanded takes about a minute.  Every drawing
command writes a PNG into `figures/` that any image viewer will open.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gridworld import bench, core, integrity, viz

OUT = Path(__file__).resolve().parent / "figures"


def _say(p, n):
    where = p.relative_to(Path.cwd()) if p.is_relative_to(Path.cwd()) else p
    print(f"  wrote {where}  ({n / 1024:.0f} KB)")


def save(bmp, name):
    OUT.mkdir(exist_ok=True)
    p = OUT / name
    _say(p, viz.write_png(p, bmp))
    return p


def save_gif(gif, name):
    OUT.mkdir(exist_ok=True)
    p = OUT / name
    _say(p, gif.save(p))
    return p


def check():
    print(f"python {sys.version.split()[0]}  (3.10 or newer is required)")
    bad = integrity.guard()
    print("import guard:", "clean" if not bad else f"{len(bad)} problem(s)")
    for b in bad:
        print("   ", b)
    modified, have = integrity.verify_protected()
    print("protected files:", "intact" if have and not modified else
          ("no manifest (staff build)" if not have else f"{len(modified)} modified"))
    for family, size in (("scatter", 101), ("maze", 51)):
        w = core.generate(size, 0, family=family)
        probe = core._true_grid_passable(w)
        free = sum(1 for y in range(w.h) for x in range(w.w) if probe(x, y))
        opt = core._optimal_cost(probe, w.w, w.h, w.start, w.goal)
        print(f"{family:8s} {size}x{size}: {100*free/(size*size):.0f}% open, "
              f"agent {w.start} -> target {w.goal}, shortest path {opt}")
        save(viz.render_world(w, probe), f"world_{family}.png")
    print("\nIf all of that printed, your environment is fine. Start with "
          "`python3 demo.py --example`.")


def tour():
    """A guided five minutes that needs no code from you at all.

    Everything here runs on the provided code, so it works the moment you
    unzip the starter -- which is the point. You should know what a search
    looks like before you write one.
    """
    OUT.mkdir(exist_ok=True)
    step = [0]

    def heading(text):
        step[0] += 1
        print(f"\n{'=' * 68}\n  {step[0]}. {text}\n{'=' * 68}")

    heading("Two terrain families, and why there are two")
    for family, size in (("scatter", 101), ("maze", 51)):
        w = core.generate(size, 0, family=family)
        probe = core._true_grid_passable(w)
        free = sum(1 for y in range(w.h) for x in range(w.w) if probe(x, y))
        opt = core._optimal_cost(probe, w.w, w.h, w.start, w.goal)
        man = abs(w.start[0] - w.goal[0]) + abs(w.start[1] - w.goal[1])
        print(f"  {family:8s} {size}x{size}  {100*free/(size*size):.0f}% open   "
              f"agent {w.start} -> target {w.goal}")
        print(f"           shortest path {opt}, Manhattan distance {man} "
              f"-> h/h* = {man/opt:.2f}")
        save(viz.render_world(w, probe), f"tour_1_{family}.png")
    print("\n  Open both PNGs. Same depth-first idea, completely different shape.")
    print("  Compare the Manhattan estimate with the shortest-path cost.")
    print("  Consider how the difference may affect A* on each family.")

    heading("What a search without a heuristic looks like")
    w = core.generate(31, 0, family="maze")
    probe = core._true_grid_passable(w)
    order, path = viz.bfs_order(probe, w.start, w.goal)
    print(f"  Breadth-first search on maze 31x31: {len(order)} cells expanded "
          f"for a path of {len(path) - 1}.")
    save(viz.render_search(w, probe, set(order), path), "tour_2_bfs.png")
    g = viz.animate_search(w, probe, order, path)
    save_gif(g, "tour_2_bfs.gif")
    print(f"  {len(g)} frames. Dark blue is expanded, pale blue is the frontier,")
    print("  purple is the cell being expanded right now, yellow is the path.")
    print("\n  Watch the GIF. BFS has no idea where the target is, so it grows")
    print("  outward in every direction at once. Your Part 2 A* solves the same")
    print("  problem; the difference between these two pictures is the heuristic.")

    heading("The agent cannot see any of this")
    print("  The visualizations use the true map. Your agent uses observations")
    print("  from its current cell. sense() reads the current cell and its")
    print("  four neighbors; move_to() senses automatically after a move.\n")
    w2 = core.generate(31, 0, family="maze")
    here = w2.start
    print(f"      >>> world.sensor.sense{here}")
    print(f"      {w2.sensor.sense(*here)}")
    print("       (here, east, south, west, north;  1 = free, 2 = blocked)")
    print("\n  That is the entire interface to the world. Planning as if the")
    print("  unseen cells were open is the freespace assumption, and replanning")
    print("  when that turns out to be wrong is what the assignment is about.")

    heading("Where to go next")
    print("  1.  Write BinaryHeap.            python3 autograder.py --part 2")
    print("  2.  Write astar.                 python3 demo.py --example")
    print("  3.  Then look at your own work:")
    print("        python3 demo.py --search --gif --tie-break large_g")
    print("        python3 demo.py --search --gif --tie-break small_g")
    print("      Compare their expansion order for Part 3.")
    print("\n  The handout has the reasoning. README.md has the order of work.")
    print("  The README API summary covers the support code you need.\n")


def example(impl_name):
    """A world small enough to check by hand, run end to end."""
    impl = bench.Impl(impl_name)
    w = core.generate(15, 1, family="maze")
    probe = core._true_grid_passable(w)
    opt = core._optimal_cost(probe, w.w, w.h, w.start, w.goal)
    print(viz.ascii_view(w, probe))
    print(f"\nA = agent {w.start}, T = target {w.goal}, "
          f"shortest path costs {opt}\n")

    rec = bench.run_known(impl, w, "manhattan")
    if rec["error"]:
        print(f"  astar: {rec['error']}")
        return
    p = rec["_problem"]
    path = rec["_path"]
    print(f"  one A* search on the KNOWN map")
    print(f"    path cost      {rec['cost']}   (must equal {opt})")
    print(f"    expansions     {rec['expansions']}")
    print(f"    re-expansions  {rec['reexpansions']}   (must be 0)")
    print(f"    probes         {rec['probes']}")
    ok = rec["cost"] == opt and rec["reexpansions"] == 0
    print(f"    => {'looks right' if ok else 'SOMETHING IS WRONG'}")
    print()
    print(viz.ascii_view(w, probe, path=path))

    rec2 = bench.run_loop(impl, "forward", w, "manhattan")
    if rec2["error"]:
        print(f"\n  RepeatedForwardAStar: {rec2['error']}")
        return
    a = rec2["_agent"]
    print(f"\n  Repeated Forward A* on the UNKNOWN map")
    print(f"    reached the target   {rec2['solved']}")
    print(f"    moves                {rec2['traj']}   (at least {opt}; more is "
          f"normal, it could not see ahead)")
    print(f"    searches             {rec2['searches']}")
    print(f"    expansions           {rec2['expansions']}")
    print(f"    cells ever observed  {a.belief.observed()} of {w.w * w.h}")


def draw_world(family, size, seed):
    w = core.generate(size, seed, family=family)
    probe = core._true_grid_passable(w)
    print(viz.ascii_view(w, probe))
    save(viz.render_world(w, probe), f"world_{family}_{seed}.png")


def draw_search(impl_name, family, size, seed, h, tie_break, gif):
    impl = bench.Impl(impl_name)
    w = core.generate(size, seed, family=family)
    probe = core._true_grid_passable(w)
    problem = core._make_known_problem(w, {}, trace=gif)
    try:
        path, _g = bench.unpack(
            impl.search.astar(problem, impl.h(h), tie_break=tie_break))
    except NotImplementedError as e:
        print(f"  {e}")
        return
    except TypeError as e:
        print(f"  {e}")
        return
    problem.stop_clock()
    opt = core._optimal_cost(probe, w.w, w.h, w.start, w.goal)
    print(f"  h={h}, ties={tie_break}: {problem.expansions} expansions, "
          f"cost {len(path) - 1 if path else None} (optimal {opt}), "
          f"{problem.probes} probes")
    if gif:
        g = viz.animate_search(w, probe, problem.order, path)
        n = save_gif(g, f"search_{family}_{seed}_{h}_{tie_break}.gif")
        print(f"  {len(g)} frames. dark blue = expanded, pale blue = frontier, "
              f"purple = the cell being expanded, yellow = the path")
    else:
        save(viz.render_search(w, probe, problem.closed, path),
             f"search_{family}_{seed}_{h}.png")
        print("  dark blue = expanded, pale blue = frontier it never needed, "
              "yellow = the path")


def draw_run(impl_name, family, size, seed, agent_key, h, gif):
    impl = bench.Impl(impl_name)
    w = core.generate(size, seed, family=family)
    cls = impl.agent(agent_key)
    ag = cls(w, impl.h(h))

    # Record how much the agent knew after each move, so the animation can
    # reveal each wall on the step the agent actually bumped into it.
    marks = [0]
    inner = ag.move_to

    def watched(cell):
        inner(cell)
        marks.append(len(ag.belief.known_blocked))
    ag.move_to = watched

    try:
        ok = ag.run()
    except NotImplementedError as e:
        print(f"  {e}")
        return
    exp = sum(p.expansions for p in ag.searches)
    print(f"  {agent_key}: solved={ok}, {len(ag.trajectory) - 1} moves, "
          f"{len(ag.searches)} searches, {exp} expansions, "
          f"{ag.belief.observed()} of {w.w * w.h} cells ever observed")
    if gif:
        g = viz.animate_run(w, ag.trajectory, ag.belief.known_blocked, marks)
        n = save_gif(g, f"run_{family}_{seed}_{agent_key}.gif")
        print(f"  {len(g)} frames. orange = walked, purple = where it is now, "
              f"dark = walls it has found, grey = never observed")
    else:
        save(viz.render_trajectory(w, ag.belief, ag.trajectory),
             f"run_{family}_{seed}_{agent_key}.png")
        print("  orange = walked, dark = discovered blockages, "
              "grey = never observed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", default="gridworld")
    ap.add_argument("--family", default="maze", choices=list(core.FAMILIES))
    ap.add_argument("--size", type=int, default=51)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--heuristic", default="manhattan")
    ap.add_argument("--agent", default="forward",
                    choices=["forward", "backward", "adaptive"])
    ap.add_argument("--tour", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--example", action="store_true")
    ap.add_argument("--world", nargs="?", const=True)
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--gif", action="store_true",
                    help="animate instead of drawing a still")
    ap.add_argument("--tie-break", default="large_g",
                    choices=["large_g", "small_g"])
    a = ap.parse_args()

    if a.tour:
        tour()
    elif a.check:
        check()
    elif a.example:
        example(a.impl)
    elif a.world:
        fam = a.world if isinstance(a.world, str) else a.family
        draw_world(fam, a.size, a.seed)
    elif a.search:
        draw_search(a.impl, a.family, a.size, a.seed, a.heuristic,
                    a.tie_break, a.gif)
    elif a.run:
        draw_run(a.impl, a.family, a.size, a.seed, a.agent, a.heuristic, a.gif)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
