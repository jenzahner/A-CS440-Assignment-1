"""Animated GIFs, written from scratch.  DO NOT EDIT.

A finished search drawn as one picture tells you where A* went.  A search drawn
as an animation tells you the order it went there in, which is the part that
actually distinguishes the algorithms: breaking ties toward larger g looks like
a line advancing down a corridor, breaking them toward smaller g looks like a
puddle spreading, and Adaptive A* looks like the puddle getting smaller every
time the agent replans.  None of that is visible in a still.

There is no imaging library here either.  GIF89a is a container around
LZW-compressed palette indices, and both are short enough to write directly:

* frames are indices into one 16-colour global table, not RGB;
* every frame after the first stores only the **bounding box of what changed**,
  with the disposal method set to "leave in place", so a frame in which twenty
  cells changed costs twenty cells and not a whole grid.

That second point is what keeps a 300-frame animation of a 101x101 world down
to a few hundred kilobytes.
"""
from __future__ import annotations

import struct

#: the shared palette; `viz.PALETTE` holds the matching RGB triples
MAX_COLORS = 16


class _Bits:
    """LSB-first bit packer, which is the order GIF's LZW codes are stored in."""

    __slots__ = ("buf", "cur", "n")

    def __init__(self):
        self.buf = bytearray()
        self.cur = 0
        self.n = 0

    def write(self, code, size):
        self.cur |= code << self.n
        self.n += size
        while self.n >= 8:
            self.buf.append(self.cur & 0xFF)
            self.cur >>= 8
            self.n -= 8

    def flush(self) -> bytes:
        if self.n:
            self.buf.append(self.cur & 0xFF)
            self.cur = self.n = 0
        return bytes(self.buf)


def lzw_encode(data: bytes, min_code_size: int) -> bytes:
    """GIF-flavoured LZW.

    The one subtlety is when the code width grows.  A GIF decoder adds its
    table entry one step *behind* the encoder -- it cannot build the entry for a
    pair until it has seen the code that follows it -- so the encoder has to
    keep emitting at the narrower width for one code longer than its own table
    size suggests.  Hence ``next_code > (1 << code_size)`` below, not ``==``.
    Get this wrong by one and every decoder rejects the file outright, which is
    at least a loud failure rather than a quiet one.
    """
    clear = 1 << min_code_size
    end = clear + 1
    bits = _Bits()
    table: dict = {}
    next_code = 0
    code_size = min_code_size + 1

    def reset():
        nonlocal table, next_code, code_size
        table = {bytes([i]): i for i in range(clear)}
        next_code = end + 1
        code_size = min_code_size + 1

    reset()
    bits.write(clear, code_size)
    if not data:
        bits.write(end, code_size)
        return bits.flush()

    buf = data[0:1]
    for i in range(1, len(data)):
        ch = data[i:i + 1]
        nxt = buf + ch
        if nxt in table:
            buf = nxt
            continue
        bits.write(table[buf], code_size)
        if next_code < 4096:
            table[nxt] = next_code
            next_code += 1
            if next_code > (1 << code_size) and code_size < 12:
                code_size += 1
        else:
            bits.write(clear, code_size)
            reset()
        buf = ch
    bits.write(table[buf], code_size)
    bits.write(end, code_size)
    return bits.flush()


def _sub_blocks(data: bytes) -> bytes:
    """GIF carries data in chunks of at most 255 bytes, terminated by a zero."""
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        out.append(len(chunk))
        out += chunk
    out.append(0)
    return bytes(out)


class Gif:
    """An animated GIF being assembled frame by frame.

    ``palette`` is a list of (r, g, b) triples, at most :data:`MAX_COLORS` of
    them.  Frames are ``bytes`` of palette indices, ``w * h`` long.
    """

    def __init__(self, w, h, palette, delay_cs: int = 6, loop: bool = True):
        if len(palette) > MAX_COLORS:
            raise ValueError(f"palette has {len(palette)} colours; {MAX_COLORS} max")
        self.w, self.h = w, h
        self.delay = delay_cs
        self.frames: list[bytes] = []
        self.prev: bytes | None = None

        bits = max(1, (MAX_COLORS - 1).bit_length())      # 4 for 16 colours
        self.min_code_size = max(2, bits)
        table = bytearray()
        for i in range(1 << bits):
            r, g, b = palette[i] if i < len(palette) else (0, 0, 0)
            table += bytes((r, g, b))

        head = bytearray(b"GIF89a")
        head += struct.pack("<HH", w, h)
        head += bytes((0xF0 | (bits - 1), 0, 0))          # GCT present, size 2^bits
        head += table
        if loop:
            head += (b"\x21\xFF\x0B" + b"NETSCAPE2.0"
                     + b"\x03\x01" + struct.pack("<H", 0) + b"\x00")
        self.head = bytes(head)

    def add(self, frame: bytes, delay_cs: int | None = None) -> None:
        """Append one frame, storing only the rectangle that changed."""
        if len(frame) != self.w * self.h:
            raise ValueError("frame is not w*h palette indices")
        delay = self.delay if delay_cs is None else delay_cs

        if self.prev is None:
            box = (0, 0, self.w, self.h)
        else:
            box = self._changed_box(self.prev, frame)
            if box is None:                               # nothing moved
                if self.frames:
                    self._bump_last_delay(delay)
                    return
                box = (0, 0, 1, 1)
        self.frames.append(self._encode(frame, box, delay))
        self.prev = frame

    def _changed_box(self, a: bytes, b: bytes):
        w, h = self.w, self.h
        top, bottom = None, None
        for y in range(h):
            i = y * w
            if a[i:i + w] != b[i:i + w]:
                if top is None:
                    top = y
                bottom = y
        if top is None:
            return None
        left, right = w, -1
        for y in range(top, bottom + 1):
            i = y * w
            row_a, row_b = a[i:i + w], b[i:i + w]
            for x in range(w):
                if row_a[x] != row_b[x]:
                    if x < left:
                        left = x
                    if x > right:
                        right = x
        return (left, top, right - left + 1, bottom - top + 1)

    def _encode(self, frame: bytes, box, delay) -> bytes:
        x0, y0, bw, bh = box
        if (bw, bh) == (self.w, self.h):
            sub = frame
        else:
            sub = bytearray()
            for y in range(y0, y0 + bh):
                i = y * self.w + x0
                sub += frame[i:i + bw]
            sub = bytes(sub)
        out = bytearray()
        # graphic control: disposal 1 = leave the previous frame in place
        out += b"\x21\xF9\x04\x04" + struct.pack("<H", delay) + b"\x00\x00"
        out += b"\x2C" + struct.pack("<HHHH", x0, y0, bw, bh) + b"\x00"
        out.append(self.min_code_size)
        out += _sub_blocks(lzw_encode(sub, self.min_code_size))
        return bytes(out)

    def _bump_last_delay(self, extra):
        """Fold a no-change frame into the one before it, rather than storing it."""
        last = bytearray(self.frames[-1])
        cur = struct.unpack("<H", last[4:6])[0]
        last[4:6] = struct.pack("<H", min(65535, cur + extra))
        self.frames[-1] = bytes(last)

    def save(self, path) -> int:
        data = self.head + b"".join(self.frames) + b"\x3B"
        with open(path, "wb") as fh:
            fh.write(data)
        return len(data)

    def __len__(self):
        return len(self.frames)
