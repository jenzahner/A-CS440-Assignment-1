"""Vector charts drawn straight into the report PDF.  DO NOT EDIT.

No plotting library: these are lines and text placed on the page, which keeps
the whole template dependency-free and keeps the charts crisp at any zoom
instead of being a bitmap of a chart.

Conventions, and the reasons for them:

* **Log y-axis on the scaling chart.**  Expansion counts across grid sizes span
  more than two orders of magnitude.  On a linear axis the three small sizes
  collapse onto the baseline and the chart shows one visible point per series,
  which is exactly the failure the maze-visualisation paper's memory panel has.
* **Series colours are assigned in a fixed order and never cycled**, so
  "Repeated Forward A*" is the same blue on every chart on the page.
* **Identity never rests on colour alone.**  Every multi-series chart carries a
  legend, and the weight sweep labels its points directly, so the page still
  reads correctly printed in greyscale or by a colour-blind reader.
* **The grid is recessive.**  Hairlines in a pale grey, no box, no ticks
  pointing inwards, no numbers on every point.
"""
from __future__ import annotations

import math

from gridworld.pdfwriter import fit, text_width

# categorical slots, in fixed order -- blue, orange, aqua
SERIES = ((0.165, 0.471, 0.839), (0.922, 0.408, 0.204), (0.106, 0.686, 0.478))
INK = (0.043, 0.043, 0.043)
MUTED = (0.322, 0.318, 0.306)
FAINT = (0.60, 0.61, 0.62)
GRID = (0.886, 0.894, 0.906)


def _nice_log_ticks(lo, hi):
    out = []
    e = int(math.floor(math.log10(max(lo, 1e-9))))
    while 10 ** e <= hi * 1.001:
        for m in (1, 3):
            v = m * 10 ** e
            if lo * 0.999 <= v <= hi * 1.001:
                out.append(v)
        e += 1
    return out or [lo, hi]


def _nice_lin_ticks(lo, hi, n=4):
    if hi <= lo:
        return [lo]
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=10) * mag
    start = math.ceil(lo / step) * step
    out, v = [], start
    while v <= hi * 1.0001:
        out.append(round(v, 10))
        v += step
    return out or [lo, hi]


def _fmt(v):
    if v >= 1000:
        return f"{v/1000:g}k"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:g}"


class Axes:
    """A plotting rectangle with its own data-to-page mapping."""

    def __init__(self, pdf, x, y, w, h, xlim, ylim, *, logy=False,
                 xlabel="", title="", subtitle=""):
        """``(x, y)`` is the top-left of the PLOT area; captions go above it."""
        self.p, self.x, self.y, self.w, self.h = pdf, x, y, w, h
        self.x0, self.x1 = xlim
        self.logy = logy
        self.y0, self.y1 = (math.log10(max(ylim[0], 1e-9)),
                            math.log10(max(ylim[1], 1e-9))) if logy else ylim
        if self.x1 == self.x0:
            self.x1 = self.x0 + 1
        if self.y1 == self.y0:
            self.y1 = self.y0 + 1

        if title:
            pdf.text(x - 24, y - TITLE_DY, title, 7.8, bold=True, color=INK)
        if subtitle:
            pdf.text(x - 24, y - SUB_DY, subtitle, 5.9, color=FAINT)

        ticks = (_nice_log_ticks(ylim[0], ylim[1]) if logy
                 else _nice_lin_ticks(ylim[0], ylim[1]))
        for t in ticks:
            py = self.py(t)
            pdf.line(x, py, x + w, py, GRID, 0.35)
            pdf.text_right(x - 3, py - 2.6, _fmt(t), 5.6, color=FAINT)
        pdf.line(x, y + h, x + w, y + h, (0.75, 0.77, 0.79), 0.5)
        if xlabel:
            pdf.text_right(x + w, y + h + 11.5, xlabel, 5.8, color=MUTED)

    def px(self, v):
        return self.x + (v - self.x0) / (self.x1 - self.x0) * self.w

    def py(self, v):
        v = math.log10(max(v, 1e-9)) if self.logy else v
        return self.y + self.h - (v - self.y0) / (self.y1 - self.y0) * self.h

    def xticks(self, values, labels=None):
        labels = labels or [_fmt(v) for v in values]
        for v, lab in zip(values, labels):
            self.p.text(self.px(v) - text_width(lab, 5.6) / 2,
                        self.y + self.h + 3, lab, 5.6, color=FAINT)

    def series(self, xs, ys, color, label="", *, marker=True):
        pts = [(self.px(a), self.py(b)) for a, b in zip(xs, ys)]
        self.p.polyline(pts, color, 1.4)
        if marker:
            for cx, cy in pts:
                self.p.dot(cx, cy, 1.5, color)

    def point_label(self, xv, yv, label, dy=-7.0):
        """A selective direct label, flipped inward when it would overrun."""
        cx, cy = self.px(xv), self.py(yv)
        w = text_width(label, 5.4)
        right = self.x + self.w
        self.p.text(cx + 3.5 if cx + 3.5 + w <= right else cx - w - 3.5,
                    cy + dy, label, 5.4, color=MUTED)


#: where a chart's title and subtitle sit above its plot area
TITLE_DY = 30.0
SUB_DY = 21.0
#: where the caller should put the legend row
LEGEND_DY = 11.0


def legend(pdf, x, y, entries, gap=8.0):
    """A one-row legend.  Swatch plus name, in the series order."""
    cx = x
    for name, color in entries:
        pdf.rect(cx, y + 1.2, 5.0, 3.2, fill=color)
        pdf.text(cx + 7, y, name, 5.8, color=MUTED)
        cx += 7 + text_width(name, 5.8) + gap
    return cx


def scaling_chart(pdf, x, y, w, h, trend, algos, title, subtitle):
    """Expansions against grid size, one line per algorithm, log y."""
    sizes = [r["size"] for r in trend]
    allv = [r[a]["expansions_mean"] for r in trend for a in algos
            if r.get(a) and r[a]["expansions_mean"] > 0]
    if not allv:
        pdf.text(x, y + h / 2, "no data", 6.5, color=FAINT)
        return
    ax = Axes(pdf, x, y, w, h, (min(sizes), max(sizes)),
              (min(allv) * 0.8, max(allv) * 1.25), logy=True,
              xlabel="grid size", title=title, subtitle=subtitle)
    ax.xticks(sizes)
    for i, a in enumerate(algos):
        xs = [r["size"] for r in trend if r.get(a)]
        ys = [r[a]["expansions_mean"] for r in trend if r.get(a)]
        if xs:
            ax.series(xs, ys, SERIES[i % len(SERIES)])
    legend(pdf, x - 24, y - LEGEND_DY,
           [(LABEL.get(a, a), SERIES[i % len(SERIES)]) for i, a in enumerate(algos)],
           gap=6.0)


def tradeoff_chart(pdf, x, y, w, h, rows, title, subtitle):
    """Bounded suboptimality: what each weight buys and what it costs."""
    rows = [r for r in rows if r.get("expansions_mean")]
    if not rows:
        pdf.text(x, y + h / 2, "no data", 6.5, color=FAINT)
        return
    xs = [r["expansions_mean"] for r in rows]
    ys = [r["cost_ratio"] for r in rows]
    ax = Axes(pdf, x, y, w, h, (min(xs) * 0.82, max(xs) * 1.06),
              (min(min(ys), 1.0), max(max(ys), 1.02)),
              xlabel="expansions (fewer is better)",
              title=title, subtitle=subtitle)
    ax.xticks(_nice_lin_ticks(min(xs), max(xs), 3))
    ax.series(xs, ys, SERIES[0])
    # label the two endpoints first -- they anchor the reading -- then fill in
    # whichever interior weights still have room.  A label on every point is noise.
    order = [0, len(rows) - 1] + [i for i in range(1, len(rows) - 1)]
    drawn = []
    for i in order:
        px, py = ax.px(xs[i]), ax.py(ys[i])
        if any(abs(px - qx) < 28 and abs(py - qy) < 8 for qx, qy in drawn):
            continue
        ax.point_label(xs[i], ys[i], f"w={rows[i]['w']:g}")
        drawn.append((px, py))


LABEL = {"forward": "Repeated Forward A*", "backward": "Repeated Backward A*",
         "adaptive": "Adaptive A*"}
