#!/usr/bin/env python3
"""CS 440 Assignment 1 autograder. DO NOT EDIT.

    python3 autograder.py
    python3 autograder.py --part 2
    python3 autograder.py --seeds 12
    python3 autograder.py --macros

Gradescope runs these same checks with the default six seeds. The autograder
awards up to 55 points; the other 45 are assessed through written work and
code review. Staff can test the reference with --impl solutions.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
import traceback
from pathlib import Path

from gridworld import bench, core, integrity, report_spec, stats
from gridworld.report_spec import MACROS, macro_value, parse_members, parse_report

#: the machine-scored share of each part; the rest is written work
POINTS = {0: 5, 2: 10, 3: 8, 4: 8, 5: 8, 6: 8, 7: 8}
#: what a human awards: Part 1 in full, plus the written half of Parts 2-7
MANUAL = 45
AUTO = sum(POINTS.values())

PART_TITLE = {
    0: "Submission is well-formed",
    2: "Binary heap, A*, and Repeated Forward A*",
    3: "Tie-breaking",
    4: "Repeated Backward A*",
    5: "Adaptive A*",
    6: "The differential heuristic",
    7: "Weighted A* and bounded suboptimality",
}


class Grader:
    def __init__(self, impl_name, seeds, answers):
        self.impl = bench.Impl(impl_name)
        self.impl_name = self.impl.name
        self.seeds = seeds
        self.answers = answers
        self.scores: dict = {}
        self.notes: dict = {}

    # ---------------------------------------------------------------- utils
    def say(self, part, msg):
        self.notes.setdefault(part, []).append(msg)
        print(f"    {msg}")

    def worlds(self, family, size, n=None, solvable=True):
        n = n or self.seeds
        return [core.generate(size, s, family=family, solvable=solvable)
                for s in range(n)]

    # ---------------------------------------------------------------- part 0
    def part0(self):
        got = 0.0
        problems = integrity.guard()
        if problems:
            for x in problems[:4]:
                self.say(0, f"FAIL import guard: {x}")
        else:
            got += 2
            self.say(0, "import guard clean")

        modified, have = integrity.verify_protected()
        submitted_checks = getattr(self, "submission_checks", None)
        if submitted_checks:
            modified.extend(json.loads(Path(submitted_checks).read_text()))
        if modified:
            for x in modified[:4]:
                self.say(0, f"FAIL {x}")
        else:
            got += 1
            self.say(0, "protected files intact" if have else
                     "no manifest shipped (staff build); skipping file check")

        try:
            parsed = parse_report(Path(self.answers).read_text())
        except OSError:
            self.say(0, f"FAIL {self.answers} is missing")
            return got
        bad = report_spec.check_report(parsed, None)
        if bad:
            for x in bad[:6]:
                self.say(0, f"FAIL report: {x}")
        else:
            got += 2
            self.say(0, "report.txt is complete and cites only measurable values")
        return got

    # ---------------------------------------------------------------- part 2
    def part2(self):
        got = 0.0
        got += self._heap()
        got += self._astar_optimal()
        got += self._forward_agent()
        return got

    def _heap(self):
        """A heap is a heap: the invariant holds, and it does not scan."""
        if hasattr(self.impl, "check_heap"):
            return self.impl.check_heap(self.say)
        Heap = self.impl.heap.BinaryHeap
        rng = random.Random(7)
        try:
            h = Heap()
            ref: dict = {}
            nxt = 0
            for _ in range(4000):
                if ref and rng.random() < 0.45:
                    # ties are a heap's business, not ours: any item holding the
                    # smallest priority is a correct pop
                    lowest = min(ref.values())
                    item = h.pop()
                    if item not in ref:
                        self.say(2, f"FAIL heap popped {item!r}, which is not in it")
                        return 0.0
                    if ref[item] != lowest:
                        self.say(2, f"FAIL heap popped priority {ref[item]}, but "
                                    f"{lowest} was still in the heap")
                        return 0.0
                    del ref[item]
                else:
                    pri = (rng.randrange(500), rng.randrange(500))
                    ref[nxt] = pri
                    h.push(pri, nxt)
                    nxt += 1
                if len(h) != len(ref):
                    self.say(2, f"FAIL heap length {len(h)} != {len(ref)}")
                    return 0.0
                d = h.data
                for i in range(1, len(d)):
                    if d[(i - 1) // 2][0] > d[i][0]:
                        self.say(2, "FAIL heap invariant violated: a parent is "
                                    "larger than its child")
                        return 0.0
            try:
                h2 = Heap()
                h2.pop()
                self.say(2, "FAIL popping an empty heap must raise IndexError")
                return 1.5
            except IndexError:
                pass
        except NotImplementedError:
            self.say(2, "heap not implemented")
            return 0.0
        except Exception as e:                              # noqa: BLE001
            self.say(2, f"FAIL heap raised {type(e).__name__}: {e}")
            return 0.0

        n = 60000
        counter = _Counting.reset()
        h = Heap()
        for i in range(n):
            h.push(_Counting(rng.randrange(1 << 30)), i)
        for _ in range(n):
            h.pop()
        import math
        budget = 6 * n * math.log2(n)
        if _Counting.count > budget:
            self.say(2, f"heap works, but used {_Counting.count:,} comparisons for "
                        f"{n:,} operations -- a binary heap needs about "
                        f"{budget:,.0f}; you are scanning somewhere")
            return 2.0
        self.say(2, f"heap correct over 4,000 random operations, "
                    f"{_Counting.count/n:.1f} comparisons per operation")
        return 3.0

    def _astar_optimal(self):
        ok = tot = re = 0
        shown = 0
        for family, _ in report_spec.FAMILIES:
            for w in self.worlds(family, 51):
                tot += 1
                probe = core._true_grid_passable(w)
                opt = core._optimal_cost(probe, w.w, w.h, w.start, w.goal)
                rec = bench.run_known(self.impl, w, "manhattan")
                if rec["error"]:
                    if shown < 3:
                        shown += 1
                        self.say(2, f"FAIL {family} seed {w.seed}: {rec['error']}")
                    continue
                re += rec["reexpansions"]
                if rec["cost"] != opt:
                    if shown < 3:
                        shown += 1
                        self.say(2, f"FAIL {family} seed {w.seed}: returned cost "
                                    f"{rec['cost']}, optimal is {opt}")
                    continue
                ok += 1
        if not tot:
            return 0.0
        self.say(2, f"A* returned an optimal path on {ok}/{tot} known maps")
        score = 4.0 * ok / tot
        if re:
            self.say(2, f"FAIL {re} re-expansion(s): a consistent heuristic means a "
                        f"state's g-value is final when it is first popped")
            score *= 0.5
        return score

    def _forward_agent(self):
        ok = tot = 0
        for family, size in report_spec.FAMILIES:
            for w in self.worlds(family, size):
                tot += 1
                rec = bench.run_loop(self.impl, "forward", w, "manhattan")
                if rec["error"]:
                    self.say(2, f"FAIL {family} seed {w.seed}: {rec['error']}")
                elif rec["tampered"]:
                    self.say(2, "FAIL the search problem's instrumentation was "
                                "replaced; this scores zero")
                    return 0.0
                else:
                    ok += 1
        for w in self.worlds("scatter", 101, max(2, self.seeds // 3), solvable=False):
            tot += 1
            rec = bench.run_loop(self.impl, "forward", w, "manhattan")
            if rec["error"]:
                self.say(2, f"FAIL unreachable seed {w.seed}: {rec['error']}")
            elif rec["solved"]:
                self.say(2, f"FAIL unreachable seed {w.seed}: claimed success")
            else:
                ok += 1
        self.say(2, f"Repeated Forward A* behaved correctly on {ok}/{tot} worlds "
                    f"(including ones where the target is walled off)")
        return 3.0 * ok / tot if tot else 0.0

    # ---------------------------------------------------------------- part 3
    def part3(self):
        results = {}
        for rule in ("small_g", "large_g"):
            recs = []
            for w in self.worlds("scatter", 101):
                recs.append(bench.run_loop(self.impl, "forward", w, "manhattan",
                                           tie_break=rule))
            bad = [r for r in recs if r["error"]]
            if bad:
                self.say(3, f"FAIL {rule}: {bad[0]['error']}")
                return 0.0
            results[rule] = recs
        got = 4.0
        self.say(3, "both tie-breaking rules run and solve every world")

        sm = stats.mean([r["expansions"] for r in results["small_g"]])
        lg = stats.mean([r["expansions"] for r in results["large_g"]])
        if lg <= 0:
            return got
        if sm > lg * 1.2:
            got += 4.0
            self.say(3, f"larger-g expanded {sm/lg:.1f}x fewer cells "
                        f"({lg:,.0f} vs {sm:,.0f}) -- the expected direction")
        elif sm > lg:
            got += 2.0
            self.say(3, f"larger-g is ahead but only by {sm/lg:.2f}x; check that "
                        f"your priority really orders equal-f states by g")
        else:
            self.say(3, f"FAIL larger-g expanded MORE ({lg:,.0f} vs {sm:,.0f}); "
                        f"the two rules are probably swapped")
        return got

    # ---------------------------------------------------------------- part 4
    def part4(self):
        ok = tot = 0
        backwards = 0
        for family, size in report_spec.FAMILIES:
            for w in self.worlds(family, size):
                tot += 1
                rec = bench.run_loop(self.impl, "backward", w, "manhattan")
                if rec["error"]:
                    self.say(4, f"FAIL {family} seed {w.seed}: {rec['error']}")
                    continue
                agent = rec["_agent"]
                if agent.searches and all(p.start == w.goal for p in agent.searches):
                    backwards += 1
                ok += 1
        if not tot:
            return 0.0
        got = 5.0 * ok / tot
        self.say(4, f"Repeated Backward A* reached the target on {ok}/{tot} worlds")
        if backwards == ok and ok:
            got += 3.0
            self.say(4, "every search started at the target, as a backward search must")
        else:
            self.say(4, f"FAIL only {backwards}/{ok} runs started every search at the target; "
                        f"a backward search searches FROM the target TO the agent")
        return got

    # ---------------------------------------------------------------- part 5
    def part5(self):
        fwd, ada = [], []
        agents = []
        for w in self.worlds("maze", 51):
            a = bench.run_loop(self.impl, "adaptive", w, "manhattan")
            f = bench.run_loop(self.impl, "forward", w, "manhattan")
            if a["error"] or f["error"]:
                self.say(5, f"FAIL maze seed {w.seed}: {a['error'] or f['error']}")
                return 0.0
            ada.append(a["expansions"])
            fwd.append(f["expansions"])
            agents.append((w, a["_agent"]))
        got = 3.0
        self.say(5, f"Adaptive A* solved all {len(ada)} worlds")

        # An empty learned_h is by far the most common failure here, and it is
        # invisible in the expansion counts -- the agent simply behaves like
        # Repeated Forward A*.  Name it directly rather than let them read it
        # off a ratio.
        if not any(getattr(a, "learned_h", None) for _, a in agents):
            self.say(5, "FAIL learned_h is still empty after every search, so this "
                        "agent is just Repeated Forward A*. Check that `astar` "
                        "leaves its g-values where `learn` looks for them, and "
                        "that `plan` calls `learn`.")
            return got

        bad = 0
        for w, agent in agents[:3]:
            true_d = core._true_distances(agent.belief.is_passable, w.w, w.h, w.goal)
            for s, h in getattr(agent, "learned_h", {}).items():
                d = true_d.get(s)
                if d is not None and h > d + 1e-9:
                    bad += 1
        if bad:
            self.say(5, f"FAIL {bad} learned h-value(s) exceed the true goal "
                        f"distance -- they are not admissible")
        else:
            got += 3.0
            self.say(5, "every learned h-value is admissible against exact distances")

        if fwd and sum(fwd):
            r = stats.median([a / f for a, f in zip(ada, fwd) if f])
            if r < 0.98:
                got += 2.0
                self.say(5, f"Adaptive A* expanded a median {r:.2f}x of Repeated "
                            f"Forward A* on the maze family")
            else:
                self.say(5, f"Adaptive A* is not ahead on maze (median {r:.2f}x); "
                            f"check that learned values are reused AND updated")
        return got

    # ---------------------------------------------------------------- part 6
    def part6(self):
        got = 0.0
        adm = con = checked = 0
        for family, _ in report_spec.FAMILIES:
            for w in self.worlds(family, 41, max(2, self.seeds // 2)):
                probe = core._true_grid_passable(w)
                true_d = core._true_distances(probe, w.w, w.h, w.goal)
                for name in ("differential", "custom"):
                    checked += 1
                    p = core._make_known_problem(w, {})
                    h = self.impl.h(name)
                    try:
                        bad_a = bad_c = 0
                        for s, d in true_d.items():
                            hv = h(s, p)
                            if not math.isfinite(hv) or hv < 0 or hv > d + 1e-9:
                                bad_a += 1
                            for dx, dy in core.DIRS:
                                nb = (s[0] + dx, s[1] + dy)
                                if nb in true_d and hv > 1 + h(nb, p) + 1e-9:
                                    bad_c += 1
                        adm += (bad_a == 0)
                        con += (bad_c == 0)
                        if bad_a and checked <= 4:
                            self.say(6, f"FAIL h_{name} overestimates on "
                                        f"{bad_a} cell(s) of {family} seed {w.seed}")
                        elif bad_c and checked <= 4:
                            self.say(6, f"FAIL h_{name} is inadmissible-free but "
                                        f"breaks consistency on {bad_c} edge(s)")
                    except NotImplementedError:
                        self.say(6, f"h_{name} not implemented")
                        return got
        if checked:
            got += 3.0 * adm / checked + 2.0 * con / checked
            self.say(6, f"admissible on {adm}/{checked} and consistent on "
                        f"{con}/{checked} exhaustive checks")
            if adm != checked or con != checked:
                self.say(6, "heuristic credit requires admissibility and consistency")
                return 0.0

        man = cus = 0
        for family, _ in report_spec.FAMILIES:
            for w in self.worlds(family, 101, max(2, self.seeds // 2)):
                baseline = bench.run_known(self.impl, w, "manhattan")
                custom = bench.run_known(self.impl, w, "custom")
                if baseline["error"] or custom["error"]:
                    self.say(6, f"FAIL search: {baseline['error'] or custom['error']}")
                    return got
                if custom["cost"] != custom["optimal"]:
                    self.say(6, "FAIL custom heuristic search returned a suboptimal path")
                    return got
                man += baseline["expansions"]
                cus += custom["expansions"]
        if man and cus:
            if cus < man * 0.85:
                got += 3.0
                self.say(6, f"your heuristic expanded {man/cus:.2f}x fewer cells "
                            f"than Manhattan on one known-map search")
            elif cus < man:
                got += 1.5
                self.say(6, f"your heuristic is ahead of Manhattan by only "
                            f"{man/cus:.2f}x; more or better-placed landmarks help")
            else:
                self.say(6, "your heuristic does not beat Manhattan on a known map")
        return got

    # ---------------------------------------------------------------- part 7
    def part7(self):
        ws = self.worlds("scatter", 101, max(3, self.seeds // 2))
        rows = {}
        for wt in report_spec.WEIGHTS:
            recs = [bench.run_known(self.impl, w, "manhattan", weight=wt) for w in ws]
            if any(r["error"] for r in recs):
                bad = next(r for r in recs if r["error"])
                self.say(7, f"FAIL w={wt}: {bad['error']}")
                return 0.0
            rows[wt] = recs
        got = 3.0
        self.say(7, f"weighted search ran at every w in {list(report_spec.WEIGHTS)}")

        viol = 0
        for wt, recs in rows.items():
            for r in recs:
                if r["cost"] and r["optimal"] and r["cost"] > wt * r["optimal"] + 1e-9:
                    viol += 1
        if viol:
            self.say(7, f"FAIL {viol} path(s) cost more than w times optimal -- the "
                        f"bound Part 7(a) asks you to prove is being broken")
        else:
            got += 3.0
            self.say(7, "every returned path respects the w-times-optimal bound")

        e1 = stats.mean([r["expansions"] for r in rows[1.0]])
        e15 = stats.mean([r["expansions"] for r in rows[1.5]])
        if e1 and e15 < e1 * 0.9:
            got += 2.0
            self.say(7, f"raising w to 1.5 cut expansions {e1/e15:.1f}x "
                        f"({e1:,.0f} -> {e15:,.0f})")
        else:
            self.say(7, f"weighting barely changed the search ({e1:,.0f} -> "
                        f"{e15:,.0f}); check that w multiplies h and not g")
        return got

    # ---------------------------------------------------------------- driver
    def run(self, parts):
        if self.impl.broken:
            print("\n!! your code could not be imported:")
            for name, err in self.impl.errors.items():
                print(f"     {name}.py -- {err}")
            print("   Part 0 still runs (it is a static check); everything that "
                  "needs\n   to import your code scores zero until this is fixed.")
        for n in parts:
            print(f"\n=== Part {n}  {PART_TITLE[n]}  ({POINTS[n]} auto pts) ===")
            t0 = time.perf_counter()
            if n != 0 and self.impl.broken:
                self.say(n, f"your code did not import: {self.impl.why()}")
                self.scores[n] = 0.0
                print(f"    -> 0.0 / {POINTS[n]}")
                continue
            try:
                self.scores[n] = max(0.0, min(POINTS[n], getattr(self, f"part{n}")()))
            except NotImplementedError as e:
                self.say(n, f"not implemented ({e})")
                self.scores[n] = 0.0
            except Exception:                               # noqa: BLE001
                traceback.print_exc(limit=3)
                self.scores[n] = 0.0
            print(f"    -> {self.scores[n]:.1f} / {POINTS[n]}"
                  f"   [{time.perf_counter() - t0:.0f}s]")
        return self.scores


class _Counting:
    """A priority whose comparisons are counted, to catch linear scanning."""

    __slots__ = ("v",)
    count = 0

    def __init__(self, v):
        self.v = v

    def __lt__(self, other):
        type(self).count += 1
        return self.v < other.v

    def __le__(self, other):
        type(self).count += 1
        return self.v <= other.v

    def __gt__(self, other):
        type(self).count += 1
        return self.v > other.v

    @classmethod
    def reset(cls):
        cls.count = 0
        return cls


# ---------------------------------------------------------------- reporting


def print_macros(impl_name, answers):
    """Every name report.txt may cite, with what it currently measures."""
    try:
        members = parse_members(parse_report(Path(answers).read_text())
                                .get("MEMBERS", ""))
        ruids = [r for _, r in members if r] or ["000000000"]
    except OSError:
        ruids = ["000000000"]
    print("measuring (quick) so the values below are real ...\n")
    data = bench.collect(bench.Impl(impl_name), ruids, quick=True)
    width = max(len(k) for k in MACROS)
    for name in sorted(MACROS):
        v = macro_value(name, data)
        print(f"  {{{{{name}}}}}{' ' * (width - len(name))}   "
              f"{report_spec.format_value(v)}")
    print(f"\n{len(MACROS)} names. Anything else in an answer is rejected.")


def write_gradescope(grader, path="/autograder/results/results.json"):
    """Gradescope's results.json.  One visible test per part."""
    tests = []
    for n, pts in POINTS.items():
        tests.append({
            "name": f"Part {n} - {PART_TITLE[n]}",
            "score": round(grader.scores.get(n, 0.0), 2),
            "max_score": pts,
            "output": "\n".join(grader.notes.get(n, [])) or "not attempted",
            "visibility": "visible",
        })
    tests.append({
        "name": "Written answers and code review",
        "score": 0.0,
        "max_score": MANUAL,
        "output": ("Graded by hand: Part 1 in full, the written half of Parts 2-7, "
                   "and the code review. The autograder never awards these."),
        "visibility": "visible",
    })
    out = {
        "score": round(sum(grader.scores.values()), 2),
        "output": (f"Autograded {AUTO} of 100 points. The remaining {MANUAL} are "
                   f"your written answers and the code review.\n"
                   f"Implementation graded: '{grader.impl_name}'."),
        "output_format": "text",
        "visibility": "visible",
        "stdout_visibility": "visible",
        "tests": tests,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", default="gridworld")
    ap.add_argument("--part", type=int, action="append", dest="parts")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--answers", default="report.txt")
    ap.add_argument("--submission-checks", help=argparse.SUPPRESS)
    ap.add_argument("--macros", action="store_true",
                    help="list the values report.txt may cite, and exit")
    ap.add_argument("--gradescope", nargs="?", const=True, default=False,
                    help="also write results.json for Gradescope")
    a = ap.parse_args()

    if a.macros:
        print_macros(a.impl, a.answers)
        return 0

    parts = sorted(a.parts) if a.parts else sorted(POINTS)
    print(f"grading '{a.impl}' on {a.seeds} worlds per check")
    t0 = time.perf_counter()
    try:
        g = Grader(a.impl, a.seeds, a.answers)
        g.submission_checks = a.submission_checks
        g.run(parts)
    except Exception:                                       # noqa: BLE001
        # A crash here must still produce a score report; a student staring at
        # a traceback on Gradescope learns nothing about where they stand.
        traceback.print_exc(limit=4)
        g = Grader.__new__(Grader)
        g.impl_name, g.scores, g.notes = a.impl, {}, {}
        for n in parts:
            g.scores[n] = 0.0
            g.notes[n] = ["the autograder itself crashed; see the trace above"]

    total = sum(g.scores.values())
    possible = sum(POINTS[k] for k in g.scores)
    print("\n" + "=" * 58)
    for k in sorted(g.scores):
        print(f"  Part {k}  {PART_TITLE[k][:34]:34s} {g.scores[k]:5.1f} / {POINTS[k]}")
    print(f"  {'AUTOGRADED TOTAL':44s} {total:5.1f} / {possible}")
    print("=" * 58)
    if parts == sorted(POINTS):
        print(f"  Plus {MANUAL} points for your written answers and the code review,")
        print(f"  which no autograder awards. Full marks here is {AUTO}/100.")
    print(f"  finished in {time.perf_counter() - t0:.0f}s")

    integrity.append_log("autograder", {
        "scores": {str(k): round(v, 2) for k, v in g.scores.items()},
        "total": round(total, 2), "parts": parts, "seeds": a.seeds,
    })
    if a.gradescope:
        p = write_gradescope(g, a.gradescope if isinstance(a.gradescope, str)
                             else "/autograder/results/results.json")
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
