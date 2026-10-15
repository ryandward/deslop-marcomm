"""The brand compiler: the rules a design has to pass before it may publish.

Two passes. The model pass runs on the layout before anything is drawn and
checks type and contrast. The render pass runs on the rendered PNG and checks
how much of the visible page each color actually covers, since that's what
NMSU's proportion rules are about and layout geometry can't see overlaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path as FilePath

import numpy as np
from PIL import Image

from .brand import (AGGIE_CRIMSON, CONTRAST_LARGE, CONTRAST_NORMAL, LARGE_BOLD_TEXT_PT, LARGE_TEXT_PT,
                    MAX_TYPE_SIZES, MAX_TYPE_WEIGHTS, MIN_TEXT_PT, TERTIARY_MAX_SHARE, WHITE_SANDS,
                    Paint, Swatch, Tier, contrast_ratio)
from .layout import Circle, Group, Item, Path, Rect, Text, cap_height, text_width


@dataclass(frozen=True)
class Finding:
    rule: str
    where: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.where}: {self.detail}"


class BrandViolation(Exception):
    def __init__(self, findings: list[Finding]):
        self.findings = findings
        super().__init__("design is off-brand:\n  " + "\n  ".join(map(str, findings)))


Shape = Rect | Circle | Path


def flatten(layers: list[Group]) -> list[tuple[str, Rect | Circle | Path | Text]]:
    """Every drawable item in paint order (first is painted first), with a
    slash path of group names so a finding says where it is."""
    out: list[tuple[str, Rect | Circle | Path | Text]] = []

    def walk(it: Item, parent: str) -> None:
        here = f"{parent}/{it.name}" if parent else it.name
        if isinstance(it, Group):
            for child in it.items:
                walk(child, here)
        else:
            out.append((here, it))

    for layer in layers:
        walk(layer, "")
    return out


def paints_used(layers: list[Group]) -> set[Paint]:
    used: set[Paint] = set()
    for _, it in flatten(layers):
        if isinstance(it, Text):
            used.add(it.style.paint)
        else:
            used.update(p for p in (it.fill, it.stroke) if p is not None)
    return used


def _contains(shape: Shape, x: float, y: float) -> bool:
    if isinstance(shape, Rect):
        return shape.x <= x <= shape.x + shape.w and shape.y <= y <= shape.y + shape.h
    if isinstance(shape, Circle):
        return (x - shape.cx) ** 2 + (y - shape.cy) ** 2 <= shape.r ** 2
    if not shape.closed:
        return False
    inside, pts = False, shape.pts
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _background(flat: list[tuple[str, Rect | Circle | Path | Text]], index: int,
                x: float, y: float) -> Paint | None:
    """The fill a reader sees behind (x, y): the topmost filled shape painted
    before the text at `index`."""
    for _, it in reversed(flat[:index]):
        if not isinstance(it, Text) and it.fill is not None and _contains(it, x, y):
            return it.fill
    return None


@dataclass(frozen=True)
class ModelReport:
    sizes: list[float]
    weights: list[int]
    min_contrast: float


def lint_model(layers: list[Group]) -> tuple[list[Finding], ModelReport]:
    findings: list[Finding] = []
    flat = flatten(layers)
    texts = [(i, where, it) for i, (where, it) in enumerate(flat) if isinstance(it, Text)]

    sizes = sorted({t.style.size for _, _, t in texts})
    weights = sorted({t.style.weight for _, _, t in texts})
    if len(sizes) > MAX_TYPE_SIZES:
        findings.append(Finding("type-sizes", "document",
                                f"{len(sizes)} sizes {sizes}; NMSU asks for two or three per piece"))
    if len(weights) > MAX_TYPE_WEIGHTS:
        findings.append(Finding("type-weights", "document",
                                f"{len(weights)} weights {weights}; NMSU asks for two or three per piece"))

    worst = float("inf")
    for i, where, t in texts:
        s = t.style
        if s.size < MIN_TEXT_PT:
            findings.append(Finding("min-size", where, f"{s.size}pt is under the {MIN_TEXT_PT}pt floor"))
        large = s.size >= LARGE_TEXT_PT or (s.weight >= 700 and s.size >= LARGE_BOLD_TEXT_PT)
        need = CONTRAST_LARGE if large else CONTRAST_NORMAL
        # Sample both ends and the middle of every line, so text that
        # straddles two backgrounds is judged on the worse one.
        for line, base in zip(t.lines, t.baselines()):
            half = text_width(line, s) / 2
            y = base - cap_height(s) / 2
            for x in (t.cx - half + 1, t.cx, t.cx + half - 1):
                bg = _background(flat, i, x, y)
                if bg is None:
                    findings.append(Finding("no-background", where, f"nothing painted behind {line!r}"))
                    break
                ratio = contrast_ratio(s.paint, bg)
                worst = min(worst, ratio)
                if ratio < need:
                    findings.append(Finding(
                        "contrast", where,
                        f"{s.paint.swatch.name} on {bg.swatch.name} {bg.tint}% is {ratio:.2f}:1, "
                        f"needs {need}:1 ({line!r})"))
                    break

    if not any(p.swatch == AGGIE_CRIMSON for p in paints_used(layers)):
        findings.append(Finding("crimson-present", "document", "Aggie Crimson must always be present"))
    return findings, ModelReport(sizes, weights, worst)


def coverage(png: FilePath, layers: list[Group]) -> dict[Swatch, float]:
    """Visible area per swatch in px, read off the render. A tint counts in
    proportion to its strength. Anti-aliased edge pixels match no paint and
    are left out, which undercounts thin text a little in every color."""
    paints = sorted(paints_used(layers), key=lambda p: (p.swatch.name, p.tint))
    colors = np.array([p.rgb for p in paints], dtype=np.int16)
    img = np.asarray(Image.open(png).convert("RGB"), dtype=np.int16).reshape(-1, 3)
    totals = np.zeros(len(paints))
    for start in range(0, len(img), 250_000):
        chunk = img[start:start + 250_000]
        dist = np.abs(chunk[:, None, :] - colors[None, :, :]).max(axis=2)
        nearest = dist.argmin(axis=1)
        exact = dist[np.arange(len(chunk)), nearest] <= 2
        totals += np.bincount(nearest[exact], minlength=len(paints))
    out: dict[Swatch, float] = {}
    for p, n in zip(paints, totals):
        weight = 1.0 if p.swatch == WHITE_SANDS else p.tint / 100
        out[p.swatch] = out.get(p.swatch, 0.0) + float(n) * weight
    return out


def lint_render(png: FilePath, layers: list[Group]) -> tuple[list[Finding], dict[Swatch, float]]:
    findings: list[Finding] = []
    area = coverage(png, layers)
    crimson = area.get(AGGIE_CRIMSON, 0.0)
    white = area.get(WHITE_SANDS, 0.0)
    colored = {s: a for s, a in area.items() if s != WHITE_SANDS}
    total = sum(colored.values()) or 1.0
    shares = {s: a / total for s, a in colored.items()}

    tertiary = sum(a for s, a in shares.items() if s.tier is Tier.TERTIARY)
    if tertiary > TERTIARY_MAX_SHARE:
        findings.append(Finding("tertiary-share", "document",
                                f"tertiary colors cover {tertiary:.0%} of the color; NMSU caps them at "
                                f"{TERTIARY_MAX_SHARE:.0%}"))
    # "Aggie Crimson ... should always be present and the dominant color":
    # no other chromatic color may outweigh it.
    for s, a in colored.items():
        if s.chromatic and s != AGGIE_CRIMSON and a > crimson:
            findings.append(Finding("crimson-dominant", "document",
                                    f"{s.name} covers more than Aggie Crimson ({a:.0f} vs {crimson:.0f} px)"))
    # "Aggie Crimson, along with white, should always be the most prominent."
    for s, a in colored.items():
        if s != AGGIE_CRIMSON and a > crimson + white:
            findings.append(Finding("crimson-white-prominent", "document",
                                    f"{s.name} covers more than Aggie Crimson and White Sands together"))
    return findings, shares
