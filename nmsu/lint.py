"""The brand compiler: the rules a design has to pass before it may publish.

Two passes. The model pass runs on the layout before anything is drawn and
checks type, contrast and logo placement. The render pass runs on the
rendered PNG: it checks how much of the visible page each color actually
covers, since that's what NMSU's proportion rules are about and layout
geometry can't see overlaps, and it scans every QR code to make sure it
opens the address it's supposed to.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path as FilePath

import numpy as np
import zxingcpp
from PIL import Image as PILImage

from .brand import (AGGIE_CRIMSON, CONTRAST_LARGE, CONTRAST_NORMAL, DARK_BACKGROUND, LARGE_BOLD_TEXT_PT,
                    LARGE_TEXT_PT, LOGO_MIN_CONTRAST, LOGO_MIN_HEIGHT, MAX_TYPE_SIZES, MAX_TYPE_WEIGHTS, MIN_TEXT,
                    TERTIARY_MAX_SHARE, WHITE_SANDS, Medium, Paint, Swatch, Tier, contrast_ratio, contrast_rgb,
                    relative_luminance)
from .layout import (Circle, Group, Image, Item, Leaf, Logo, Path, QRCode, Rect, Text, cap_height,
                     text_width)


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


Box = tuple[float, float, float, float]   # x0, y0, x1, y1


def flatten(layers: list[Group]) -> list[tuple[str, Leaf]]:
    """Every drawable item in paint order (first is painted first), with a
    slash path of group names so a finding says where it is."""
    out: list[tuple[str, Leaf]] = []

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
        elif isinstance(it, QRCode):
            used.update((it.paint, it.background))
        elif isinstance(it, (Rect, Circle, Path)):
            used.update(p for p in (it.fill, it.stroke) if p is not None)
    return used


def bbox(it: Leaf) -> Box:
    if isinstance(it, Text):
        half = max(text_width(line, it.style) for line in it.lines) / 2
        return (it.cx - half, it.y - cap_height(it.style), it.cx + half, it.last_baseline + 0.25 * it.style.size)
    if isinstance(it, (Image, Logo)):
        return (it.x, it.y, it.x + it.w, it.y + it.h)
    if isinstance(it, QRCode):
        return (it.x, it.y, it.x + it.size, it.y + it.size)
    pad = it.sw / 2 if it.stroke else 0.0
    if isinstance(it, Rect):
        return (it.x - pad, it.y - pad, it.x + it.w + pad, it.y + it.h + pad)
    if isinstance(it, Circle):
        return (it.cx - it.r - pad, it.cy - it.r - pad, it.cx + it.r + pad, it.cy + it.r + pad)
    xs, ys = [x for x, _ in it.pts], [y for _, y in it.pts]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def _overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _encloses(outer: Box, inner: Box) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _contains(it: Leaf, x: float, y: float) -> bool:
    if isinstance(it, Text):
        return False
    if isinstance(it, Rect) and it.fill is not None:
        return it.x <= x <= it.x + it.w and it.y <= y <= it.y + it.h
    if isinstance(it, Circle) and it.fill is not None:
        return (x - it.cx) ** 2 + (y - it.cy) ** 2 <= it.r ** 2
    if isinstance(it, Path):
        if not (it.closed and it.fill is not None):
            return False
        inside, pts = False, it.pts
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
        return inside
    if isinstance(it, (Image, Logo, QRCode)):
        x0, y0, x1, y1 = bbox(it)
        return x0 <= x <= x1 and y0 <= y <= y1
    return False


def _behind(flat: list[tuple[str, Leaf]], index: int, x: float, y: float) -> Leaf | None:
    """What a reader sees behind (x, y): the topmost opaque item painted
    before the item at `index`."""
    for _, it in reversed(flat[:index]):
        if _contains(it, x, y):
            return it
    return None


@dataclass(frozen=True)
class ModelReport:
    sizes: list[float]
    weights: list[int]
    min_contrast: float


def _lint_text(flat: list[tuple[str, Leaf]], i: int, where: str, t: Text, medium: Medium,
               findings: list[Finding]) -> float:
    s = t.style
    worst = float("inf")
    if s.size < MIN_TEXT[medium]:
        findings.append(Finding("min-size", where, f"{s.size:g} is under the {MIN_TEXT[medium]:g} floor "
                                                   f"for {medium.value}"))
    large = s.size >= LARGE_TEXT_PT or (s.weight >= 700 and s.size >= LARGE_BOLD_TEXT_PT)
    need = CONTRAST_LARGE if large else CONTRAST_NORMAL
    # Sample both ends and the middle of every line, so text that straddles
    # two backgrounds is judged on the worse one.
    for line, base in zip(t.lines, t.baselines()):
        half = text_width(line, s) / 2
        y = base - cap_height(s) / 2
        for x in (t.cx - half + 1, t.cx, t.cx + half - 1):
            under = _behind(flat, i, x, y)
            if under is None:
                findings.append(Finding("no-background", where, f"nothing painted behind {line!r}"))
                return worst
            if isinstance(under, (Image, Logo)):
                findings.append(Finding("text-over-image", where,
                                        f"{line!r} sits on {under.name}; put text on a solid brand color, "
                                        f"where it stays readable and its contrast can be checked"))
                return worst
            if isinstance(under, QRCode):
                findings.append(Finding("text-over-qr", where, f"{line!r} sits on the QR code"))
                return worst
            assert isinstance(under, (Rect, Circle, Path)) and under.fill is not None
            ratio = contrast_ratio(s.paint, under.fill)
            worst = min(worst, ratio)
            if ratio < need:
                findings.append(Finding(
                    "contrast", where,
                    f"{s.paint.swatch.name} on {under.fill.swatch.name} {under.fill.tint}% is {ratio:.2f}:1, "
                    f"needs {need}:1 ({line!r})"))
                return worst
    return worst


def _lint_logo(flat: list[tuple[str, Leaf]], i: int, where: str, logo: Logo, medium: Medium,
               findings: list[Finding]) -> None:
    art = logo.art
    floor = LOGO_MIN_HEIGHT[(art.kind, medium)]
    if logo.h < floor:
        findings.append(Finding("logo-min-size", where, f"{logo.h:g} tall is under NMSU's {floor:g} "
                                                        f"minimum for a {art.kind} in {medium.value}"))

    under = _behind(flat, i, logo.x + logo.w / 2, logo.y + logo.h / 2)
    if isinstance(under, (Rect, Circle, Path)) and under.fill is not None:
        dark = relative_luminance(under.fill.rgb) < DARK_BACKGROUND
        if art.on_dark != dark:
            findings.append(Finding("logo-variant", where,
                                    f"{art.file.name} is the {'white' if art.on_dark else 'crimson'} logo, "
                                    f"but it sits on {'dark' if dark else 'light'} {under.fill.swatch.name}"))
        h = art.color.lstrip("#")
        ratio = contrast_rgb((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)), under.fill.rgb)
        if ratio < LOGO_MIN_CONTRAST:
            findings.append(Finding("logo-contrast", where, f"the logo is {ratio:.2f}:1 against "
                                                            f"{under.fill.swatch.name}, needs {LOGO_MIN_CONTRAST}:1"))
    else:
        findings.append(Finding("logo-background", where,
                                "the logo has to sit on a solid brand color, not on a photo or another graphic"))

    # Clear space: nothing may come within one S-height of the logo, except
    # the background it sits on, which encloses the whole clear-space zone.
    c = logo.clear_space
    zone = (logo.x - c, logo.y - c, logo.x + logo.w + c, logo.y + logo.h + c)
    for j, (other_where, other) in enumerate(flat):
        if j == i:
            continue
        box = bbox(other)
        if _overlaps(box, zone) and not _encloses(box, zone):
            findings.append(Finding("logo-clear-space", where,
                                    f"{other_where} comes within the logo's clear space ({c:.1f}, "
                                    f"the height of the S in State)"))


def lint_model(layers: list[Group], medium: Medium = Medium.PRINT) -> tuple[list[Finding], ModelReport]:
    findings: list[Finding] = []
    flat = flatten(layers)
    texts = [t for _, t in flat if isinstance(t, Text)]

    sizes = sorted({t.style.size for t in texts})
    weights = sorted({t.style.weight for t in texts})
    if len(sizes) > MAX_TYPE_SIZES:
        findings.append(Finding("type-sizes", "document",
                                f"{len(sizes)} sizes {sizes}; NMSU asks for two or three per piece"))
    if len(weights) > MAX_TYPE_WEIGHTS:
        findings.append(Finding("type-weights", "document",
                                f"{len(weights)} weights {weights}; NMSU asks for two or three per piece"))

    worst = float("inf")
    for i, (where, it) in enumerate(flat):
        if isinstance(it, Text):
            worst = min(worst, _lint_text(flat, i, where, it, medium, findings))
        elif isinstance(it, Logo):
            _lint_logo(flat, i, where, it, medium, findings)

    if not any(p.swatch == AGGIE_CRIMSON for p in paints_used(layers)):
        findings.append(Finding("crimson-present", "document", "Aggie Crimson must always be present"))
    return findings, ModelReport(sizes, weights, worst)


def coverage(png: FilePath, layers: list[Group], width: float) -> dict[Swatch, float]:
    """Visible area per swatch in px, read off the render. A tint counts in
    proportion to its strength. Photos and logos are masked out, since their
    colors aren't ours to count. Anti-aliased edge pixels match no paint and
    are left out, which undercounts thin text a little in every color."""
    paints = sorted(paints_used(layers), key=lambda p: (p.swatch.name, p.tint))
    colors = np.array([p.rgb for p in paints], dtype=np.int16)
    img = np.asarray(PILImage.open(png).convert("RGB"), dtype=np.int16)
    scale = img.shape[1] / width
    keep = np.ones(img.shape[:2], dtype=bool)
    for _, it in flatten(layers):
        if isinstance(it, (Image, Logo)):
            x0, y0, x1, y1 = (round(v * scale) for v in bbox(it))
            keep[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = False
    pixels = img[keep]
    totals = np.zeros(len(paints))
    for start in range(0, len(pixels), 250_000):
        chunk = pixels[start:start + 250_000]
        dist = np.abs(chunk[:, None, :] - colors[None, :, :]).max(axis=2)
        nearest = dist.argmin(axis=1)
        exact = dist[np.arange(len(chunk)), nearest] <= 2
        totals += np.bincount(nearest[exact], minlength=len(paints))
    out: dict[Swatch, float] = {}
    for p, n in zip(paints, totals):
        weight = 1.0 if p.swatch == WHITE_SANDS else p.tint / 100
        out[p.swatch] = out.get(p.swatch, 0.0) + float(n) * weight
    return out


def _scan_qr_codes(png: FilePath, layers: list[Group], width: float) -> list[Finding]:
    """Decode every QR code straight off the render, the way a phone would."""
    findings: list[Finding] = []
    with PILImage.open(png) as im:
        page = im.convert("L")
    scale = page.width / width
    for where, it in flatten(layers):
        if not isinstance(it, QRCode):
            continue
        x0, y0, x1, y1 = (round(v * scale) for v in bbox(it))
        found = [r.text for r in zxingcpp.read_barcodes(np.asarray(page.crop((x0, y0, x1, y1))))]
        if it.data not in found:
            findings.append(Finding("qr-decode", where, f"scanning the render gives {found or 'nothing'}, "
                                                        f"expected {it.data!r}"))
    return findings


def lint_render(png: FilePath, layers: list[Group], width: float) -> tuple[list[Finding], dict[Swatch, float]]:
    findings = _scan_qr_codes(png, layers, width)
    area = coverage(png, layers, width)
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
