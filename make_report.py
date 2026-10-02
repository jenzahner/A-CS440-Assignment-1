#!/usr/bin/env python3
"""Generate the one-page report from your code and report.txt. DO NOT EDIT.

    python3 make_report.py          # full run for submission
    python3 make_report.py --quick  # fewer worlds for drafting

Tables, figures, and measurement macros come from the selected implementation.
Inspect the generated report.pdf and resolve any reported problems.
"""
from __future__ import annotations

import argparse
import hashlib
import random
import time
from pathlib import Path

from gridworld import bench, charts, core, integrity, report_spec, viz
from gridworld.charts import FAINT, INK, LABEL, MUTED, SERIES
from gridworld.pdfwriter import PDF, fit, text_width, wrap
from gridworld.report_spec import (
    ANSWER_KEYS, FAMILIES, MAX_CHARS, QUESTION_TITLES, check_report,
    parse_members, parse_report, substitute,
)

RULE = (0.80, 0.84, 0.89)
BAND = (0.937, 0.953, 0.973)
HEAD = (0.96, 0.97, 0.98)
GOOD = (0.06, 0.48, 0.27)
BAD = (0.72, 0.24, 0.16)
W, H, M = 612.0, 792.0, 34.0


# ---------------------------------------------------------------- tables


class Table:
    """A left-aligned first column and right-aligned numeric columns."""

    def __init__(self, pdf, x, y, widths, title, note):
        self.p, self.x, self.w = pdf, x, widths
        pdf.text(x, y, title, 8.0, bold=True, color=INK)
        if note:
            pdf.text(x, y + 9, note, 5.9, color=FAINT)
        self.y = y + (19 if note else 11)

    def header(self, labels):
        p, x = self.p, self.x
        p.rect(x, self.y - 2, sum(self.w), 12, fill=HEAD)
        p.text(x + 3, self.y + 1, labels[0], 6.2, bold=True, color=MUTED)
        for i, lab in enumerate(labels[1:]):
            p.text_right(x + sum(self.w[:i + 2]) - 4, self.y + 1, lab, 6.2,
                         bold=True, color=MUTED)
        self.y += 12

    def row(self, cells, colors=None, bold=None, rule=True):
        p, x = self.p, self.x
        if rule:
            p.line(x, self.y, x + sum(self.w), self.y, RULE, 0.35)
        colors = colors or [INK] * len(cells)
        bold = bold or [False] * len(cells)
        p.text(x + 3, self.y + 2.5, fit(str(cells[0]), 7.0, self.w[0] - 6), 7.0,
               bold=bold[0], color=colors[0])
        for i, c in enumerate(cells[1:]):
            p.text_right(x + sum(self.w[:i + 2]) - 4, self.y + 2.5, str(c), 7.0,
                         bold=bold[i + 1], color=colors[i + 1])
        self.y += 10.5

    def close(self, gap=10):
        self.p.line(self.x, self.y, self.x + sum(self.w), self.y, RULE, 0.6)
        self.y += gap
        return self.y


def num(v, nd=0):
    if v is None:
        return "--"
    return f"{v:,.{nd}f}"


# ---------------------------------------------------------------- the page


def build(parsed, data, impl_name, ruids, quick):
    p = PDF()
    members = parse_members(parsed.get("MEMBERS", ""))

    # ---- header
    p.rect(0, 0, W, 50, fill=BAND)
    p.line(0, 50, W, 50, RULE, 0.8)
    p.text(M, 12, "CS 440  Assignment 1", 14.5, bold=True, color=INK)
    p.text(M, 31, "Fast Trajectory Replanning in unknown gridworlds", 8.5,
           color=MUTED)
    y = 10
    for name, ruid in members[:4]:
        p.text_right(W - M, y, f"{fit(name, 8, 150)}   {ruid}", 8, color=INK)
        y += 10
    if not members:
        p.text_right(W - M, 11, "NO TEAM MEMBERS LISTED", 8, bold=True, color=BAD)

    top = 66
    LW = 300.0                       # left column: tables
    RX = M + LW + 16                 # right column: charts and the drawing
    RW = W - M - RX

    # ---- A. head to head --------------------------------------------
    t = Table(p, M, top, [86, 62, 50, 52, 50],
              "A.  Replanning, head to head",
              f"expansions, trajectory and replans per world, h = "
              f"{report_spec.LOOP_HEURISTIC}, larger-g ties")
    t.header(["", "expansions", "moves", "replans", "solved"])
    for family, size in FAMILIES:
        fam = data["loop"].get(family, {})
        base = (fam.get("forward") or {}).get("expansions_mean") or 0
        t.row([f"{family} {size}x{size}", "", "", "", ""],
              colors=[MUTED] * 5, bold=[True] + [False] * 4)
        for key in bench.AGENT_ORDER:
            s = fam.get(key)
            if not s:
                continue
            ratio = (s["expansions_mean"] / base) if base else 0
            col = GOOD if ratio < 0.97 else (BAD if ratio > 1.03 else INK)
            solved = f"{s.get('solved', 0)}/{s['n']}"
            t.row(["   " + LABEL[key], num(s["expansions_mean"]),
                   num(s.get("traj_mean", 0)), num(s.get("searches_mean", 0)),
                   solved],
                  colors=[INK, col if key != "forward" else INK, INK, INK,
                          INK if s.get("solved") == s["n"] else BAD],
                  bold=[False, key != "forward", False, False, False],
                  rule=(key != "forward"))
    t.close()

    # ---- B. ties -----------------------------------------------------
    t = Table(p, M, t.y, [86, 72, 72, 70], "B.  Tie-breaking (Part 3)",
              "Repeated Forward A*, equal-f ties broken toward smaller or larger g")
    t.header(["", "smaller g", "larger g", "small / large"])
    for family, _ in FAMILIES:
        tf = data["tie"].get(family, {})
        sm = (tf.get("small_g") or {}).get("expansions_mean") or 0
        lg = (tf.get("large_g") or {}).get("expansions_mean") or 0
        r = (sm / lg) if lg else 0
        t.row([family, num(sm), num(lg), f"{r:.1f}x"],
              colors=[INK, INK, INK, GOOD if r > 1.2 else INK],
              bold=[False, False, False, True])
    t.close()

    # ---- C. one search on a known map --------------------------------
    t = Table(p, M, t.y, [86, 72, 72, 70], "C.  Heuristics, one search, known map",
              "expansions for a single A* search from the agent to the target")
    t.header(["", "manhattan", "differential", "yours"])
    for family, _ in FAMILIES:
        kf = data["known"].get(family, {})
        vals = [(kf.get(k) or {}).get("expansions_mean") for k in
                ("manhattan", "differential", "custom")]
        best = min([v for v in vals if v], default=None)
        t.row([family] + [num(v) for v in vals],
              colors=[INK] + [GOOD if v == best else INK for v in vals],
              bold=[False] + [v == best for v in vals])
    t.close()

    # ---- D. rebuild policy -------------------------------------------
    t = Table(p, M, t.y, [86, 72, 72, 70],
              "D.  Landmark staleness (Part 6c)",
              "how far the tables may drift before rebuilding, in the maze loop")
    t.header(["rebuild after", "expansions", "seconds", "probes"])
    for s in data.get("rebuild", []):
        lab = "never rebuild" if s["every"] is None else (
            "age > 1" if s["every"] == 1 else f"age > {s['every']}")
        t.row([lab, num(s["expansions_mean"]), f"{s['seconds_mean']:.2f}",
               num(s.get("probes_mean", 0))])
    t.close(gap=10)
    left_bottom = t.y

    # ---- charts -------------------------------------------------------
    CH = 68.0
    ex, ey = RX + 26, top + charts.TITLE_DY
    charts.scaling_chart(p, ex, ey, RW - 30, CH, data.get("trend", []),
                         bench.AGENT_ORDER, "E.  Cost against grid size",
                         "mean A* expansions per world, maze family, log scale")

    fy0 = ey + CH + 16 + charts.TITLE_DY
    wrows = sorted(data.get("weighted", {}).get("scatter", {}).values(),
                   key=lambda r: r["w"])
    charts.tradeoff_chart(p, ex, fy0, RW - 34, CH, wrows,
                          "F.  What weighting buys (Part 7)",
                          "path cost over optimal, one search on a known map, scatter")

    # ---- the drawing --------------------------------------------------
    cy = fy0 + CH + 22
    fig = data.get("_figure")
    p.text(RX, cy, "G.  A trajectory, drawn", 8.0, bold=True, color=INK)
    cap = data.get("_figure_caption", "")
    if fig is not None:
        side = min(RW, 116.0)
        p.image("Traj", fig, RX, cy + 10, side, side)
        ty = cy + 12 + side
        lines = wrap(cap, 5.8, RW)[:3]
        for i, line in enumerate(lines):
            p.text(RX, ty + i * 7.0, line, 5.8, color=MUTED)
        cy = ty + 7.0 * len(lines)
    else:
        p.text(RX, cy + 11, "figure unavailable", 6.5, color=BAD)
        cy += 22

    # ---- answers -------------------------------------------------------
    ay = max(left_bottom, cy) + 6
    p.line(M, ay, W - M, ay, RULE, 0.8)
    ay += 9
    colw = (W - 2 * M - 16) / 2
    rowh = (H - 36 - ay) / 4
    for i, k in enumerate(ANSWER_KEYS):
        cx = M + (i % 2) * (colw + 16)
        cyy = ay + (i // 2) * rowh
        p.text(cx, cyy, fit(QUESTION_TITLES[k], 7.2, colw), 7.2, bold=True,
               color=SERIES[0])
        body = " ".join((parsed.get(k) or "").split())
        rendered, _, _ = substitute(body, data)
        over = len(rendered) > MAX_CHARS
        rendered = rendered[:MAX_CHARS]
        if not rendered:
            p.text(cx, cyy + 11, "(not answered)", 7.0, color=BAD)
            continue
        lines = wrap(rendered, 6.8, colw)
        cap_n = max(1, int((rowh - 12) // 7.9))
        for j, line in enumerate(lines[:cap_n]):
            p.text(cx, cyy + 10 + j * 7.9, line, 6.8, color=INK)
        if over or len(lines) > cap_n:
            p.text_right(cx + colw, cyy, "truncated", 6.0, color=BAD)

    # ---- footer --------------------------------------------------------
    fy = H - 22
    p.line(M, fy - 7, W - M, fy - 7, RULE, 0.5)
    modified, have_manifest = integrity.verify_protected()
    log = integrity.log_summary()
    fp = integrity.fingerprint(data, ruids)
    mode = "QUICK RUN, NOT A SUBMISSION" if quick else "FULL RUN"
    stamp = f"fingerprint {fp}  ·  {mode}  ·  impl '{impl_name}'"
    p.text(M, fy, fit(stamp, 6.2, W - 2 * M - 110), 6.2,
           color=BAD if quick else FAINT)
    if modified:
        p.text_right(W - M, fy, f"INTEGRITY: {len(modified)} protected file(s) "
                     f"modified", 6.2, bold=True, color=BAD)
    elif not have_manifest:
        p.text_right(W - M, fy, "INTEGRITY: no manifest", 6.2, color=FAINT)
    else:
        p.text_right(W - M, fy, "INTEGRITY: ok", 6.2, color=GOOD)
    p.text(M, fy + 8, f"{time.strftime('%Y-%m-%d %H:%M')}  ·  "
           f"{log['runs']} logged runs over {log['days']} day(s), "
           f"{log['versions']} code version(s)", 5.5, color=FAINT)
    return p, fp


# ---------------------------------------------------------------- figure


def make_figure(impl, ruids, quick):
    """Draw one trajectory on a world picked pseudo-randomly from the team's set.

    Which world is drawn is chosen by hashing the team's RUIDs, so it is
    arbitrary but reproducible -- the graders get the same picture from the same
    submission, which is the only way a picture can be evidence of anything.
    """
    family, size = FAMILIES[1]
    seeds = report_spec.team_seeds(ruids, 20, "figure")
    pick = random.Random(hashlib.sha256("".join(sorted(ruids)).encode()).digest())
    seed = pick.choice(seeds)
    world = core.generate(size, seed, family=family)
    rec = bench.run_loop(impl, "adaptive", world, "manhattan")
    agent = rec.get("_agent")
    if agent is None or rec["error"]:
        return None, f"figure unavailable: {rec['error']}"
    bmp = viz.render_trajectory(world, agent.belief, agent.trajectory)
    cap = (f"Adaptive A* on {family} seed {seed}. Orange is the route actually "
           f"walked, dark cells are blockages it discovered, flat grey is terrain "
           f"it never observed.")
    return bmp, cap


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", default="gridworld")
    ap.add_argument("--answers", default="report.txt")
    ap.add_argument("--out", default="report.pdf")
    ap.add_argument("--quick", action="store_true",
                    help="a third of the worlds; for drafting, not for submitting")
    a = ap.parse_args()

    text = Path(a.answers).read_text()
    parsed = parse_report(text)
    members = parse_members(parsed.get("MEMBERS", ""))
    ruids = [r for _, r in members if r] or ["000000000"]
    print(f"reading {a.answers} ... {len(members)} member(s)")

    impl = bench.Impl(a.impl)
    print(f"running '{impl.name}' on this team's worlds"
          f"{' (quick)' if a.quick else ''} ...")
    t0 = time.perf_counter()
    data = bench.collect(impl, ruids, quick=a.quick,
                         progress=lambda m: print(m, flush=True))
    fig, cap = make_figure(impl, ruids, a.quick)
    data["_figure"], data["_figure_caption"] = fig, cap
    print(f"  measured in {time.perf_counter() - t0:.0f}s")

    problems = check_report(parsed, data)
    if problems:
        print("  report problems (these cost points):")
        for x in problems:
            print(f"    - {x}")

    pdf, fp = build(parsed, data, impl.name, ruids, a.quick)
    n = pdf.save(a.out)
    integrity.append_log("report", {"fingerprint": fp, "quick": a.quick,
                                    "problems": len(problems)})
    print(f"wrote {a.out}  ({n/1024:.0f} KB, 1 page, fingerprint {fp})")


if __name__ == "__main__":
    main()
