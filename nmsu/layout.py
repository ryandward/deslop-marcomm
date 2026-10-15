"""Measured text and the drawing primitives every job builds from.

Coordinates are points, origin at the artboard's top-left, y growing down.
Text is measured with HarfBuzz against the same font files the renderer
uses, so a line that passes the fit check here is the line that prints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

import uharfbuzz as hb
from fontTools.ttLib import TTFont

from .brand import FIT_MARGIN, Paint, Style


# --------------------------------------------------------- measurement ----

@cache
def _shaper(path: str) -> tuple[hb.Font, int]:
    face = hb.Face(hb.Blob.from_file_path(path))
    return hb.Font(face), face.upem


@cache
def _cap_em(path: str) -> float:
    font = TTFont(path)
    return float(font["OS/2"].sCapHeight) / float(font["head"].unitsPerEm)


def cap_height(style: Style) -> float:
    """Cap height in pt, for centering text on what the eye sees."""
    return _cap_em(str(style.font_file)) * style.size


def text_width(s: str, style: Style) -> float:
    font, upem = _shaper(str(style.font_file))
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    return sum(p.x_advance for p in buf.glyph_positions) * style.size / upem


def _greedy(words: list[str], style: Style, max_w: float) -> list[str]:
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}" if cur else w
        if cur and text_width(trial, style) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    return lines + [cur]


def wrap(text: str, style: Style, max_w: float) -> list[str]:
    """Wrap into the fewest lines that fit, then rebalance them so centered
    text doesn't end on a one-word stub. Newlines in `text` are kept."""
    limit = max_w * FIT_MARGIN
    out: list[str] = []
    for para in text.split("\n"):
        words = para.split()
        n = len(_greedy(words, style, limit))
        lo, hi = 0.0, limit
        for _ in range(30):
            mid = (lo + hi) / 2
            if len(_greedy(words, style, mid)) <= n:
                hi = mid
            else:
                lo = mid
        out += _greedy(words, style, hi)
    return out


class Overflow(Exception):
    pass


# ---------------------------------------------------------- primitives ----

@dataclass
class Rect:
    name: str
    x: float
    y: float
    w: float
    h: float
    r: float = 0
    fill: Paint | None = None
    stroke: Paint | None = None
    sw: float = 0


@dataclass
class Circle:
    name: str
    cx: float
    cy: float
    r: float
    fill: Paint | None = None
    stroke: Paint | None = None
    sw: float = 0


@dataclass
class Path:
    name: str
    pts: list[tuple[float, float]]
    closed: bool = False
    fill: Paint | None = None
    stroke: Paint | None = None
    sw: float = 0


@dataclass
class Text:
    """Centered lines in one style, anchored on the first baseline.

    gaps[i] is extra space above line i on top of the style's leading. It
    lets one text frame hold a list whose items wrap, with a little air
    between items so a wrapped line doesn't read as a new item.
    max_w is the width of the box the text has to fit inside; the line is
    measured against it the moment the Text is built.
    """
    name: str
    lines: list[str]
    cx: float
    y: float
    style: Style
    max_w: float
    gaps: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.gaps:
            self.gaps = [0.0] * len(self.lines)
        if len(self.gaps) != len(self.lines):
            raise ValueError(f"{self.name}: {len(self.gaps)} gaps for {len(self.lines)} lines")
        for line in self.lines:
            if not line.strip():
                raise ValueError(f"{self.name}: empty line (use gaps for space)")
            w = text_width(line, self.style)
            if w > self.max_w * FIT_MARGIN + 0.01:
                raise Overflow(f"{self.name}: {line!r} is {w:.1f}pt wide, "
                               f"its box allows {self.max_w * FIT_MARGIN:.1f}pt")

    def baselines(self) -> list[float]:
        ys, y = [], self.y
        for i, g in enumerate(self.gaps):
            if i:
                y += self.style.leading + g
            ys.append(y)
        return ys

    def leads(self) -> list[float]:
        return [self.style.leading + g for g in self.gaps]

    @property
    def last_baseline(self) -> float:
        return self.baselines()[-1]


@dataclass
class Group:
    name: str
    items: list[Item]
    layer: bool = False
    locked: bool = False


Item = Rect | Circle | Path | Text | Group


# ------------------------------------------------------------- helpers ----

def arrow_down(name: str, x: float, y1: float, y2: float, paint: Paint, sw: float,
               head_len: float = 6.5, head_half_w: float = 3.75) -> Group:
    """A vertical connector whose arrowhead tip lands exactly on y2. Heads are
    filled triangles rather than stroke markers, because Illustrator can't
    script arrowheads and drops SVG markers on import."""
    return Group(name, [
        Path("shaft", [(x, y1), (x, y2 - head_len + 0.5)], stroke=paint, sw=sw),
        Path("head", [(x - head_half_w, y2 - head_len), (x + head_half_w, y2 - head_len), (x, y2)],
             closed=True, fill=paint),
    ])


def centered_stack(name: str, box: Rect, runs: list[tuple[str, Style]], pad: float = 8) -> list[Text]:
    """Wrap each run to the box and center the whole stack on the box,
    measuring from the first line's cap height to the last baseline, which
    is where the eye judges vertical centering."""
    inner = box.w - 2 * pad
    wrapped = [(wrap(t, s, inner), s) for t, s in runs]
    span = cap_height(wrapped[0][1])
    for i, (lines, s) in enumerate(wrapped):
        span += (len(lines) - 1) * s.leading + (s.leading if i else 0)
    y = box.y + (box.h - span) / 2 + cap_height(wrapped[0][1])
    out = []
    for i, (lines, s) in enumerate(wrapped):
        if i:
            y += s.leading
        t = Text(f"{name} {i + 1}", lines, box.x + box.w / 2, y, s, inner)
        out.append(t)
        y = t.last_baseline
    return out
