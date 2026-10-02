"""Drawing gridworlds, searches and trajectories.  DO NOT EDIT.

No imaging library, no numpy -- a :class:`Bitmap` is a ``bytearray`` of RGB
triples and :func:`write_png` encodes it with nothing but ``zlib``.  That keeps
the whole assignment installable with no dependencies at all, which matters
when you have ten minutes to get it running on a machine that is not yours.

The palette follows the convention used in the maze-visualisation literature
(black walls, white corridors, green start, red target, yellow solution), with
one addition: the closed list and the open list are drawn in *different* blues.
Published maze visualisers usually colour "visited" as a single mass, which
hides the thing worth seeing -- the open list is the frontier A* paid for and
did not use, and the gap between the two is the heuristic's whole contribution.
"""
from __future__ import annotations

import struct
import zlib

from gridworld.core import BLOCKED, DIRS, FREE, UNKNOWN

# ---- palette (r, g, b) ------------------------------------------------
WALL = (24, 26, 33)
FREE_C = (247, 248, 250)
UNSEEN = (203, 208, 216)
CLOSED = (86, 132, 226)
OPEN_C = (170, 199, 245)
PATH = (250, 196, 62)
TRAIL = (247, 147, 30)
START = (32, 158, 92)
GOAL = (206, 62, 48)
DISCOVERED = (92, 68, 72)


class Bitmap:
    """A tiny RGB canvas with the origin at the top left."""

    __slots__ = ("w", "h", "px")

    def __init__(self, w, h, fill=(255, 255, 255)):
        self.w, self.h = w, h
        self.px = bytearray(bytes(fill) * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def fill_rect(self, x0, y0, w, h, c):
        row = bytes(c) * w
        for y in range(y0, min(y0 + h, self.h)):
            if y < 0:
                continue
            i = (y * self.w + max(0, x0)) * 3
            self.px[i:i + len(row)] = row

    def to_png(self) -> bytes:
        raw = b"".join(b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3])
                       for y in range(self.h))

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))


def write_png(path, bmp: Bitmap) -> int:
    data = bmp.to_png()
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)


# ---------------------------------------------------------------- renderers


def _scale(size, target=460):
    return max(1, target // size)


def render_world(world, passable, target=460) -> Bitmap:
    """The true terrain, with the agent and the target marked."""
    s = _scale(world.w, target)
    bmp = Bitmap(world.w * s, world.h * s)
    for y in range(world.h):
        for x in range(world.w):
            bmp.fill_rect(x * s, y * s, s, s, FREE_C if passable(x, y) else WALL)
    bmp.fill_rect(world.start[0] * s, world.start[1] * s, s, s, START)
    bmp.fill_rect(world.goal[0] * s, world.goal[1] * s, s, s, GOAL)
    return bmp


def frontier_of(closed, passable) -> set:
    """The open list at termination, reconstructed from the closed list.

    A* generates exactly the successors of the states it expands, so whatever
    was generated and never expanded is precisely the passable neighbourhood of
    the closed list minus the closed list itself.  Recovering it this way costs
    nothing at search time -- no counter, no bookkeeping in the hot loop, and
    nothing for a student implementation to get wrong or to have to report.
    """
    out = set()
    for (x, y) in closed:
        for dx, dy in DIRS:
            nb = (x + dx, y + dy)
            if nb not in closed and passable(*nb):
                out.add(nb)
    return out


def render_search(world, passable, closed, path, target=460,
                  show_frontier=True) -> Bitmap:
    """One finished search: what it expanded, what it merely looked at, and
    what it returned.

    The frontier is drawn in a paler blue than the closed list on purpose.  The
    closed cells are the work A* actually did; the frontier is the work it
    queued and then proved it never needed.  The gap between the two regions is
    the heuristic's entire contribution, and it is invisible if you colour both
    the same -- which is what most maze visualisers do.
    """
    bmp = render_world(world, passable, target)
    s = _scale(world.w, target)
    if show_frontier:
        for (x, y) in frontier_of(closed, passable):
            bmp.fill_rect(x * s, y * s, s, s, OPEN_C)
    for (x, y) in closed:
        bmp.fill_rect(x * s, y * s, s, s, CLOSED)
    for (x, y) in path or ():
        bmp.fill_rect(x * s, y * s, s, s, PATH)
    bmp.fill_rect(world.start[0] * s, world.start[1] * s, s, s, START)
    bmp.fill_rect(world.goal[0] * s, world.goal[1] * s, s, s, GOAL)
    return bmp


def render_trajectory(world, belief, trajectory, target=460) -> Bitmap:
    """The route the agent actually walked, over the map it actually learned.

    Cells the agent never observed are drawn flat grey rather than as terrain:
    the picture is the agent's experience, not the answer key, and drawing the
    parts it never saw would misrepresent what the algorithm had to work with.
    """
    s = _scale(world.w, target)
    bmp = Bitmap(world.w * s, world.h * s)
    for y in range(world.h):
        for x in range(world.w):
            st = belief.status(x, y)
            c = UNSEEN if st == UNKNOWN else (DISCOVERED if st == BLOCKED else FREE_C)
            bmp.fill_rect(x * s, y * s, s, s, c)
    for (x, y) in trajectory:
        bmp.fill_rect(x * s, y * s, s, s, TRAIL)
    bmp.fill_rect(world.start[0] * s, world.start[1] * s, s, s, START)
    bmp.fill_rect(world.goal[0] * s, world.goal[1] * s, s, s, GOAL)
    return bmp


def ascii_view(world, passable, path=None, width=61) -> str:
    """A terminal picture, for `demo.py` and for debugging without a viewer."""
    path = set(path or ())
    step = max(1, world.w // width)
    rows = []
    for y in range(0, world.h, step):
        row = []
        for x in range(0, world.w, step):
            if (x, y) == world.start:
                row.append("A")
            elif (x, y) == world.goal:
                row.append("T")
            elif (x, y) in path:
                row.append("*")
            else:
                row.append("." if passable(x, y) else "#")
        rows.append("".join(row))
    return "\n".join(rows)


# ---------------------------------------------------------------- animation
#
# Everything below draws into palette indices rather than RGB, because that is
# what `anim.Gif` takes.  The index order here *is* the GIF's colour table.

#: purple, for the cell A* is expanding right now -- the search's head
CURRENT = (147, 51, 234)

PALETTE = [WALL, FREE_C, UNSEEN, CLOSED, OPEN_C, PATH, TRAIL, START, GOAL,
           DISCOVERED, CURRENT]
(I_WALL, I_FREE, I_UNSEEN, I_CLOSED, I_OPEN, I_PATH, I_TRAIL, I_START, I_GOAL,
 I_DISCOVERED, I_CURRENT) = range(len(PALETTE))


class IndexCanvas:
    """A canvas of palette indices, one byte per pixel."""

    __slots__ = ("w", "h", "px")

    def __init__(self, w, h, fill=I_FREE):
        self.w, self.h = w, h
        self.px = bytearray([fill]) * (w * h)

    def fill_rect(self, x0, y0, w, h, idx):
        row = bytes([idx]) * w
        for y in range(y0, min(y0 + h, self.h)):
            if y >= 0:
                i = y * self.w + max(0, x0)
                self.px[i:i + len(row)] = row

    def frame(self) -> bytes:
        return bytes(self.px)


def _cell_painter(canvas, scale):
    def paint(cell, idx):
        canvas.fill_rect(cell[0] * scale, cell[1] * scale, scale, scale, idx)
    return paint


def animate_search(world, passable, order, path, *, target=420, frames=160,
                   delay_cs=6, hold_cs=250):
    """A* expanding, one frame every few expansions.

    ``order`` is ``problem.order`` -- the expanded cells in the order they were
    expanded, which is why the problem has to be built with ``trace=True``.
    The frontier is painted incrementally as each expansion reveals it, so the
    animation shows the open list growing and being eaten, not just the closed
    list filling in.
    """
    from gridworld.anim import Gif

    s = _scale(world.w, target)
    canvas = IndexCanvas(world.w * s, world.h * s)
    paint = _cell_painter(canvas, s)
    for y in range(world.h):
        for x in range(world.w):
            paint((x, y), I_FREE if passable(x, y) else I_WALL)
    paint(world.start, I_START)
    paint(world.goal, I_GOAL)

    gif = Gif(canvas.w, canvas.h, PALETTE, delay_cs=delay_cs)
    gif.add(canvas.frame())

    every = max(1, len(order) // max(1, frames))
    seen = set()
    for i, cell in enumerate(order):
        seen.add(cell)
        paint(cell, I_CLOSED)
        for dx, dy in DIRS:
            nb = (cell[0] + dx, cell[1] + dy)
            if nb not in seen and passable(*nb):
                paint(nb, I_OPEN)
        if i % every == every - 1 or i == len(order) - 1:
            paint(cell, I_CURRENT)          # the head, for this frame only
            paint(world.goal, I_GOAL)
            gif.add(canvas.frame())
            paint(cell, I_CLOSED)

    for cell in path or ():
        paint(cell, I_PATH)
    paint(world.start, I_START)
    paint(world.goal, I_GOAL)
    gif.add(canvas.frame(), delay_cs=hold_cs)
    return gif


def animate_run(world, trajectory, blocked, marks, *, target=420, frames=200,
                delay_cs=6, hold_cs=250):
    """The agent walking a world it cannot see.

    ``marks[i]`` is how many blockages were known once the agent had made ``i``
    moves, so the walls appear exactly when the agent learned them rather than
    all at once at the end.  Everything unobserved stays flat grey: the picture
    is the agent's experience, not the answer key.
    """
    from gridworld.anim import Gif

    s = _scale(world.w, target)
    canvas = IndexCanvas(world.w * s, world.h * s, fill=I_UNSEEN)
    paint = _cell_painter(canvas, s)
    paint(world.goal, I_GOAL)
    paint(world.start, I_START)

    gif = Gif(canvas.w, canvas.h, PALETTE, delay_cs=delay_cs)
    gif.add(canvas.frame())

    every = max(1, len(trajectory) // max(1, frames))
    shown = 0
    for i, cell in enumerate(trajectory):
        want = marks[i] if i < len(marks) else len(blocked)
        while shown < want:
            paint(blocked[shown], I_DISCOVERED)
            shown += 1
        paint(cell, I_TRAIL)
        if i % every == every - 1 or i == len(trajectory) - 1:
            paint(cell, I_CURRENT)
            paint(world.goal, I_GOAL)
            gif.add(canvas.frame())
            paint(cell, I_TRAIL)

    paint(world.start, I_START)
    paint(world.goal, I_GOAL)
    gif.add(canvas.frame(), delay_cs=hold_cs)
    return gif


def bfs_order(passable, start, goal):
    """Breadth-first expansion order from ``start``.  Harness-owned.

    This exists so the tour has something to animate before any student code
    is written, and because it is the honest baseline: BFS is what searching
    without a heuristic looks like, and every picture A* produces is measured
    against how much smaller it is than this one.
    """
    from collections import deque
    seen = {start}
    q = deque([start])
    order, parent = [], {start: None}
    while q:
        cur = q.popleft()
        order.append(cur)
        if cur == goal:
            break
        for dx, dy in DIRS:
            nb = (cur[0] + dx, cur[1] + dy)
            if nb not in seen and passable(*nb):
                seen.add(nb)
                parent[nb] = cur
                q.append(nb)
    path = None
    if goal in parent:
        path, cur = [], goal
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()
    return order, path
