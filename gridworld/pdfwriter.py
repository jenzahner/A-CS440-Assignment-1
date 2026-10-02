"""A very small PDF writer.  DO NOT EDIT.

Enough of the format to lay out a single page of text, rules, and images with
no third-party dependencies: base-14 Helvetica for type and Flate-compressed
DeviceRGB for pictures.

Coordinates are given with the ORIGIN AT THE TOP-LEFT and y increasing
downwards, which is how the report layout is written; the y-axis is flipped on
the way out to PDF's bottom-left origin.
"""
from __future__ import annotations

import zlib

LETTER = (612.0, 792.0)

#: Helvetica advance widths (1/1000 em) for the printable ASCII range.
_W = (
    "278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 "
    "556 556 556 556 556 556 556 556 556 556 278 278 584 584 584 556 "
    "1015 667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 "
    "667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 "
    "333 556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 "
    "556 556 333 500 278 556 500 722 500 500 500 334 260 334 584"
).split()
_WB = (
    "278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 "
    "556 556 556 556 556 556 556 556 556 556 333 333 584 584 584 611 "
    "975 722 722 722 722 667 611 778 722 278 556 722 611 833 722 778 "
    "667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 "
    "333 556 611 556 611 556 333 611 611 278 278 556 278 889 611 611 "
    "611 611 389 556 333 611 556 778 556 556 500 389 280 389 584"
).split()


def text_width(s: str, size: float, bold: bool = False) -> float:
    table = _WB if bold else _W
    total = 0
    for ch in s:
        i = ord(ch) - 32
        total += int(table[i]) if 0 <= i < len(table) else 556
    return total * size / 1000.0


def fit(s: str, size: float, width: float, bold: bool = False) -> str:
    """Truncate with an ellipsis so `s` fits inside `width`."""
    if text_width(s, size, bold) <= width:
        return s
    while s and text_width(s + "...", size, bold) > width:
        s = s[:-1]
    return s + "..."


def wrap(s: str, size: float, width: float, bold: bool = False) -> list[str]:
    """Greedy word wrap to `width`, honouring existing newlines."""
    out: list[str] = []
    for para in s.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if text_width(trial, size, bold) <= width or not line:
                line = trial
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def _esc(s: str) -> str:
    return (s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)"))


class PDF:
    def __init__(self, size=LETTER):
        self.w, self.h = size
        self.ops: list[str] = []
        self.images: dict[str, tuple] = {}

    # -- coordinate helper ---------------------------------------------
    def _y(self, y):
        return self.h - y

    # -- drawing -------------------------------------------------------
    def text(self, x, y, s, size=9, bold=False, color=(0, 0, 0)):
        if not s:
            return
        f = "/F2" if bold else "/F1"
        r, g, b = color
        self.ops.append(
            f"BT {r:.3f} {g:.3f} {b:.3f} rg {f} {size:.2f} Tf "
            f"1 0 0 1 {x:.2f} {self._y(y) - size:.2f} Tm ({_esc(s)}) Tj ET")

    def text_right(self, x, y, s, size=9, bold=False, color=(0, 0, 0)):
        self.text(x - text_width(s, size, bold), y, s, size, bold, color)

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=0.6):
        if fill:
            r, g, b = fill
            self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg "
                            f"{x:.2f} {self._y(y + h):.2f} {w:.2f} {h:.2f} re f")
        if stroke:
            r, g, b = stroke
            self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG {lw:.2f} w "
                            f"{x:.2f} {self._y(y + h):.2f} {w:.2f} {h:.2f} re S")

    def line(self, x1, y1, x2, y2, color=(0, 0, 0), lw=0.6):
        r, g, b = color
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG {lw:.2f} w "
                        f"{x1:.2f} {self._y(y1):.2f} m {x2:.2f} {self._y(y2):.2f} l S")

    def image(self, name, img, x, y, w, h):
        """Place a :class:`gridworld.viz.Bitmap` (or any (w, h, bytes) triple)."""
        if name not in self.images:
            iw, ih, raw = img.w, img.h, bytes(img.px)
            self.images[name] = (iw, ih, zlib.compress(raw, 6))
        self.ops.append(f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {self._y(y + h):.2f} cm "
                        f"/{name} Do Q")

    def polyline(self, pts, color=(0, 0, 0), lw=1.0):
        """Stroke a connected run of points given in top-left coordinates."""
        if len(pts) < 2:
            return
        r, g, b = color
        d = [f"{r:.3f} {g:.3f} {b:.3f} RG {lw:.2f} w"]
        d.append(f"{pts[0][0]:.2f} {self._y(pts[0][1]):.2f} m")
        for px, py in pts[1:]:
            d.append(f"{px:.2f} {self._y(py):.2f} l")
        d.append("S")
        self.ops.append(" ".join(d))

    def dot(self, x, y, r, color=(0, 0, 0)):
        """A small filled square marker -- cheaper than a Bezier circle."""
        self.rect(x - r, y - r, 2 * r, 2 * r, fill=color)

    # -- output --------------------------------------------------------
    def save(self, path):
        objs: list[bytes] = []

        def add(b):
            objs.append(b)
            return len(objs)          # 1-based object number

        content = zlib.compress("\n".join(self.ops).encode("latin-1"), 6)

        img_ids = {}
        for name, (iw, ih, data) in self.images.items():
            img_ids[name] = add(
                b"<< /Type /XObject /Subtype /Image /Width " + str(iw).encode()
                + b" /Height " + str(ih).encode()
                + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 "
                b"/Filter /FlateDecode /Length " + str(len(data)).encode()
                + b" >>\nstream\n" + data + b"\nendstream")

        f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                 b"/Encoding /WinAnsiEncoding >>")
        f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                 b"/Encoding /WinAnsiEncoding >>")
        cont = add(b"<< /Filter /FlateDecode /Length " + str(len(content)).encode()
                   + b" >>\nstream\n" + content + b"\nendstream")

        xo = b" ".join(f"/{n} {img_ids[n]} 0 R".encode() for n in self.images)
        res = (b"<< /Font << /F1 " + str(f1).encode() + b" 0 R /F2 "
               + str(f2).encode() + b" 0 R >> /XObject << " + xo + b" >> >>")

        pages_num = len(objs) + 2      # page is next, pages after it
        page = add(b"<< /Type /Page /Parent " + str(pages_num).encode()
                   + b" 0 R /MediaBox [0 0 " + f"{self.w:.0f} {self.h:.0f}".encode()
                   + b"] /Resources " + res + b" /Contents " + str(cont).encode()
                   + b" 0 R >>")
        pages = add(b"<< /Type /Pages /Kids [" + str(page).encode()
                    + b" 0 R] /Count 1 >>")
        catalog = add(b"<< /Type /Catalog /Pages " + str(pages).encode() + b" 0 R >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, body in enumerate(objs, start=1):
            offsets.append(len(out))
            out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n"
        out += b"0000000000 65535 f \n"
        for off in offsets[1:]:
            out += f"{off:010d} 00000 n \n".encode()
        out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode()
                + b" /Root " + str(catalog).encode() + b" 0 R >>\nstartxref\n"
                + str(xref).encode() + b"\n%%EOF\n")
        with open(path, "wb") as fh:
            fh.write(bytes(out))
        return len(out)
