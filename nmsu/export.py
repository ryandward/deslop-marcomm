"""Publishing: the one way a design leaves this repo.

publish() lints the layout, writes the SVG and the Illustrator build script,
renders the PDF and PNGs, lints the render, and proves the Illustrator script
rebuilds the same picture. Files only reach out_dir if every step passes; a
rejected render stays in out_dir/.staging/ so we can look at what failed.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path as FilePath
from xml.sax.saxutils import escape

from .brand import FONT_DIR, GOTHAM_FOR, PALETTE, ROOT, WHITE_SANDS, LogoArt, Medium, Paint, Swatch
from .layout import Circle, Group, Image, Item, Logo, Path, QRCode, Rect, Text, text_width
from .lint import BrandViolation, Finding, flatten, lint_model, lint_render

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

CACHE = ROOT / ".cache"
MOCK = ROOT / "tools" / "illustrator_mock.js"


# ----------------------------------------------------------------- SVG ----

def _id(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")


def _paint_attrs(fill: Paint | None, stroke: Paint | None, sw: float) -> str:
    a = f'fill="{fill.hex}"' if fill else 'fill="none"'
    if stroke:
        a += f' stroke="{stroke.hex}" stroke-width="{sw:g}" stroke-linejoin="round"'
    return a


def _svg_item(it: Item, depth: int) -> list[str]:
    pad = "  " * depth
    if isinstance(it, Group):
        layer = f' inkscape:groupmode="layer" inkscape:label="{escape(it.name)}"' if it.layer else ""
        out = [f'{pad}<g id="{_id(it.name)}"{layer}>']
        for child in it.items:
            out += _svg_item(child, depth + 1)
        return out + [f"{pad}</g>"]
    if isinstance(it, Rect):
        r = f' rx="{it.r:g}" ry="{it.r:g}"' if it.r else ""
        return [f'{pad}<rect x="{it.x:.2f}" y="{it.y:.2f}" width="{it.w:.2f}" height="{it.h:.2f}"{r} '
                f'{_paint_attrs(it.fill, it.stroke, it.sw)}/>']
    if isinstance(it, Circle):
        return [f'{pad}<circle cx="{it.cx:.2f}" cy="{it.cy:.2f}" r="{it.r:g}" '
                f'{_paint_attrs(it.fill, it.stroke, it.sw)}/>']
    if isinstance(it, Path):
        d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in it.pts) + (" Z" if it.closed else "")
        return [f'{pad}<path d="{d}" {_paint_attrs(it.fill, it.stroke, it.sw)}/>']
    if isinstance(it, Image):
        # Embedded, so the SVG is one self-contained file to hand over.
        data = base64.b64encode(it.file.read_bytes()).decode()
        return [f'{pad}<image id="{_id(it.name)}" x="{it.x:.2f}" y="{it.y:.2f}" width="{it.w:.2f}" '
                f'height="{it.h:.2f}" preserveAspectRatio="none" xlink:href="data:image/png;base64,{data}"/>']
    if isinstance(it, Logo):
        bx, by, _, bh = it.art.box
        k = it.h / bh
        return [f'{pad}<g id="{_id(it.name)}" transform="translate({it.x - bx * k:.3f} {it.y - by * k:.3f}) '
                f'scale({k:.6f})">', _logo_markup(str(it.art.file)), f"{pad}</g>"]
    if isinstance(it, QRCode):
        out = [f'{pad}<g id="{_id(it.name)}">']
        for module_run in it.rects():
            out += _svg_item(module_run, depth + 1)
        return out + [f"{pad}</g>"]
    # Each line is its own <text> at a measured left edge, so every renderer,
    # Illustrator included, puts it exactly where the lint measured it.
    # Illustrator matches the PostScript name; browsers fall through to the
    # family name plus weight.
    s = it.style
    font = f'font-family="{s.postscript}, Montserrat" font-weight="{s.weight}" font-size="{s.size:g}"'
    out = [f'{pad}<g id="{_id(it.name)}">']
    for line, y in zip(it.lines, it.baselines()):
        x = it.cx - text_width(line, s) / 2
        out.append(f'{pad}  <text x="{x:.2f}" y="{y:.2f}" {font} fill="{s.paint.hex}">{escape(line)}</text>')
    return out + [f"{pad}</g>"]


@cache
def _logo_markup(path: str) -> str:
    """A logo file's artwork as SVG markup, unchanged except that its CSS
    classes become presentation attributes. NMSU's files each define their
    own .cls-1, .st0 and so on, so inlining them as-is would let one logo's
    classes recolor another's."""
    root = ET.parse(path).getroot()
    rules: dict[str, dict[str, str]] = {}
    for style in root.iter(f"{{{SVG_NS}}}style"):
        for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", style.text or ""):
            props = dict((k.strip(), v.strip()) for k, v in
                         (decl.split(":", 1) for decl in body.split(";") if ":" in decl))
            for sel in selectors.split(","):
                if sel.strip().startswith("."):
                    rules.setdefault(sel.strip()[1:], {}).update(props)
    parts = []
    for child in root:
        if child.tag.split("}")[-1] in ("defs", "style", "title", "desc", "metadata"):
            continue
        for el in child.iter():
            for cls in el.attrib.pop("class", "").split():
                for k, v in rules.get(cls, {}).items():
                    el.set(k, v)
            el.attrib.pop("id", None)
            el.attrib.pop("data-name", None)
        parts.append(ET.tostring(child, encoding="unicode"))
    return "".join(parts)


def write_svg(path: FilePath, layers: list[Group], width: float, height: float, title: str) -> None:
    body: list[str] = []
    for layer in layers:
        body += _svg_item(layer, 1)
    path.write_text("\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width / 72:g}in" height="{height / 72:g}in" viewBox="0 0 {width:g} {height:g}">',
        f"  <title>{escape(title)}</title>",
        *body,
        "</svg>",
        "",
    ]))


# --------------------------------------------------------- Illustrator ----

JSX_TEMPLATE = r"""//@target illustrator
// Builds "__TITLE__" as a native Illustrator document in NMSU branding.
// Generated by deslop-marcomm; edit the job's build.py, not this file.
//
// Run: Illustrator > File > Scripts > Other Script... > pick this file.
// Then File > Save As... > Adobe Illustrator (.ai).
//
// Colors are global process swatches in an "NMSU Brand" swatch group, so
// recoloring a swatch recolors everything that uses it, and light fills
// are tints of those swatches. Each box and its text are grouped and named.

// Set to true on a machine that has Gotham (NMSU's primary typeface).
// Otherwise Montserrat is used, which NMSU approves as its substitute.
var PREFER_GOTHAM = false;

__DATA__

(function () {
    // Photos and logos are linked from the assets folder next to this script.
    var HERE = new File($.fileName).parent.fsName;
    function asset(name) {
        var f = new File(HERE + "/assets/" + name);
        if (!f.exists) throw new Error("Can't find " + f.fsName + ". Keep the assets folder next to this script.");
        return f;
    }

    var savedCoords = app.coordinateSystem;
    app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;

    var doc = app.documents.add(DocumentColorSpace.RGB, W, H);
    // artboardRect is [left, top, right, bottom] with y growing upward; the
    // layout is written top-down from the artboard's top-left corner.
    var ab = doc.artboards[0].artboardRect;
    function X(x) { return ab[0] + x; }
    function Y(y) { return ab[1] - y; }

    var brand = doc.swatchGroups.add();
    brand.name = "NMSU Brand";
    var spots = {};
    for (var i = 0; i < SWATCHES.length; i++) {
        var s = SWATCHES[i];
        var c = new RGBColor();
        c.red = s.rgb[0]; c.green = s.rgb[1]; c.blue = s.rgb[2];
        var spot = doc.spots.add();
        spot.name = s.name;
        spot.colorType = ColorModel.PROCESS;
        spot.color = c;
        brand.addSpot(spot);
        spots[s.name] = spot;
    }
    function paint(p) {
        if (!p) return null;
        var sc = new SpotColor();
        sc.spot = spots[p[0]];
        sc.tint = p[1];
        return sc;
    }

    var fonts = {}, missing = [];
    function font(ps) {
        if (fonts.hasOwnProperty(ps)) return fonts[ps];
        var names = PREFER_GOTHAM ? [GOTHAM[ps], ps] : [ps];
        for (var i = 0; i < names.length; i++) {
            try { return (fonts[ps] = app.textFonts.getByName(names[i])); } catch (e) {}
        }
        missing.push(ps);
        return (fonts[ps] = null);
    }

    function finish(p, it) {
        p.name = it.name;
        var f = paint(it.fill), s = paint(it.stroke);
        p.filled = !!f;
        if (f) p.fillColor = f;
        p.stroked = !!s;
        if (s) { p.strokeColor = s; p.strokeWidth = it.sw; p.strokeJoin = StrokeJoin.ROUNDENDJOIN; }
        return p;
    }

    function draw(parent, it) {
        var p;
        if (it.kind === "group") {
            var g = parent.groupItems.add();
            g.name = it.name;
            for (var i = 0; i < it.items.length; i++) draw(g, it.items[i]);
        } else if (it.kind === "rect") {
            p = it.r ? parent.pathItems.roundedRectangle(Y(it.y), X(it.x), it.w, it.h, it.r, it.r)
                     : parent.pathItems.rectangle(Y(it.y), X(it.x), it.w, it.h);
            finish(p, it);
        } else if (it.kind === "circle") {
            p = parent.pathItems.ellipse(Y(it.cy - it.r), X(it.cx - it.r), 2 * it.r, 2 * it.r);
            finish(p, it);
        } else if (it.kind === "path") {
            p = parent.pathItems.add();
            var pts = [];
            for (var j = 0; j < it.pts.length; j++) pts.push([X(it.pts[j][0]), Y(it.pts[j][1])]);
            p.setEntirePath(pts);
            p.closed = it.closed;
            finish(p, it);
        } else if (it.kind === "image") {
            // Linked; embed it from the Links panel to make the .ai self-contained.
            p = parent.placedItems.add();
            p.file = asset(it.file);
            p.name = it.name;
            p.width = it.w;
            p.height = it.h;
            p.position = [X(it.x), Y(it.y)];
        } else if (it.kind === "logo") {
            // NMSU's own logo file, imported as vector art and only scaled.
            var lg = parent.groupItems.createFromFile(asset(it.file));
            lg.name = it.name;
            lg.width = it.w;
            lg.height = it.h;
            lg.position = [X(it.x), Y(it.y)];
        } else if (it.kind === "text") {
            var t = parent.textFrames.pointText([X(it.cx), Y(it.y)]);
            t.contents = it.lines.join("\r");
            t.name = it.name;
            var r = t.textRange;
            r.paragraphAttributes.justification = Justification.CENTER;
            var a = r.characterAttributes;
            var f = font(it.font);
            if (f) a.textFont = f;
            a.size = it.size;
            a.autoLeading = false;
            a.leading = it.leads[0];
            a.fillColor = paint(it.paint);
            // Extra space above a line is carried as that line's leading.
            for (var k = 1; k < it.leads.length; k++) {
                t.paragraphs[k].characterAttributes.leading = it.leads[k];
            }
            // Point text is anchored on its first baseline; make sure the
            // centered lines straddle cx however the anchor behaved.
            var gb = t.geometricBounds;
            var dx = X(it.cx) - (gb[0] + gb[2]) / 2;
            if (Math.abs(dx) > 0.25) t.translate(dx, 0);
        }
    }

    // LAYERS runs bottom to top, and layers.add() stacks each new one on top.
    for (var n = 0; n < LAYERS.length; n++) {
        var layer = n === 0 ? doc.layers[0] : doc.layers.add();
        layer.name = LAYERS[n].name;
        for (var m = 0; m < LAYERS[n].items.length; m++) draw(layer, LAYERS[n].items[m]);
        layer.locked = LAYERS[n].locked;
    }

    app.coordinateSystem = savedCoords;
    doc.selection = null;
    app.redraw();
    if (missing.length) {
        alert("Built, but these fonts are not installed:\n  " + missing.join("\n  ") +
              "\n\nInstall Montserrat (brand/fonts/montserrat in deslop-marcomm, or Google " +
              "Fonts), or set PREFER_GOTHAM = true if Gotham is installed, then run again.");
    }
})();
"""


def _paint_ref(p: Paint | None) -> list[object] | None:
    return [p.swatch.name, p.tint] if p else None


def _jsx_item(it: Item) -> dict[str, object]:
    if isinstance(it, Group):
        return {"kind": "group", "name": it.name, "items": [_jsx_item(c) for c in it.items]}
    if isinstance(it, Rect):
        return {"kind": "rect", "name": it.name, "x": it.x, "y": it.y, "w": it.w, "h": it.h, "r": it.r,
                "fill": _paint_ref(it.fill), "stroke": _paint_ref(it.stroke), "sw": it.sw}
    if isinstance(it, Circle):
        return {"kind": "circle", "name": it.name, "cx": it.cx, "cy": it.cy, "r": it.r,
                "fill": _paint_ref(it.fill), "stroke": _paint_ref(it.stroke), "sw": it.sw}
    if isinstance(it, Path):
        return {"kind": "path", "name": it.name, "pts": [list(pt) for pt in it.pts], "closed": it.closed,
                "fill": _paint_ref(it.fill), "stroke": _paint_ref(it.stroke), "sw": it.sw}
    if isinstance(it, Image):
        return {"kind": "image", "name": it.name, "file": it.file.name, "x": it.x, "y": it.y, "w": it.w, "h": it.h}
    if isinstance(it, Logo):
        return {"kind": "logo", "name": it.name, "file": it.art.file.name, "x": it.x, "y": it.y,
                "w": it.w, "h": it.h}
    if isinstance(it, QRCode):
        return {"kind": "group", "name": it.name, "items": [_jsx_item(r) for r in it.rects()]}
    return {"kind": "text", "name": it.name, "lines": it.lines, "cx": it.cx, "y": it.y,
            "font": it.style.postscript, "size": it.style.size, "leads": it.leads(),
            "paint": _paint_ref(it.style.paint)}


def _round(o: object) -> object:
    if isinstance(o, float):
        return round(o, 2)
    if isinstance(o, list):
        return [_round(v) for v in o]
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    return o


def write_jsx(path: FilePath, layers: list[Group], width: float, height: float, title: str) -> None:
    def swatch(s: Swatch) -> dict[str, object]:
        return {"name": s.name, "rgb": list(s.rgb)}
    data: dict[str, object] = {
        "W": width, "H": height, "GOTHAM": GOTHAM_FOR,
        "SWATCHES": [swatch(s) for s in PALETTE],
        "LAYERS": [{"name": l.name, "locked": l.locked, "items": [_jsx_item(c) for c in l.items]}
                   for l in layers],
    }
    decls = "\n".join(f"var {k} = {json.dumps(_round(v), ensure_ascii=True)};" for k, v in data.items())
    path.write_text(JSX_TEMPLATE.replace("__TITLE__", title.replace('"', "'")).replace("__DATA__", decls))


# -------------------------------------------------------------- assets ----

def _normalized_logo(art: LogoArt) -> str:
    """The logo file with its canvas (viewBox) trimmed to the artwork and
    every byte of the artwork itself left alone. Illustrator sizes an
    imported SVG by its artwork, so this keeps the .jsx, the SVG and the
    mock all measuring the same box."""
    text = art.file.read_text()
    bx, by, bw, bh = art.box
    svg_tag = re.search(r"<svg\b[^>]*>", text)
    assert svg_tag, art.file
    tag = re.sub(r'viewBox="[^"]*"', f'viewBox="{bx:g} {by:g} {bw:g} {bh:g}"', svg_tag.group(0))
    return text[:svg_tag.start()] + tag + text[svg_tag.end():]


def write_assets(layers: list[Group], out: FilePath) -> list[FilePath]:
    """Copy every photo and logo the design uses into out/, under the names
    the Illustrator script links to."""
    written: dict[str, FilePath] = {}
    for _, it in flatten(layers):
        if isinstance(it, Image):
            name, src = it.file.name, it.file
        elif isinstance(it, Logo):
            name, src = it.art.file.name, it.art.file
        else:
            continue
        if name in written:
            if written[name] != src:
                raise ValueError(f"two different assets are both named {name}")
            continue
        out.mkdir(parents=True, exist_ok=True)
        if isinstance(it, Logo):
            (out / name).write_text(_normalized_logo(it.art))
        else:
            shutil.copyfile(src, out / name)
        written[name] = src
    return [out / n for n in written]


# -------------------------------------------------------------- render ----

def _tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"`{name}` is not installed; publish needs inkscape, node and magick")
    return found


def font_env() -> dict[str, str]:
    """Point fontconfig at the repo's fonts and nothing else, so renders use
    the exact files the lint measured, whatever is installed system-wide."""
    CACHE.mkdir(exist_ok=True)
    conf = CACHE / "fonts.conf"
    conf.write_text('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
                    f"<fontconfig>\n  <dir>{escape(str(FONT_DIR))}</dir>\n"
                    f"  <cachedir>{escape(str(CACHE / 'fontconfig'))}</cachedir>\n</fontconfig>\n")
    return {**os.environ, "FONTCONFIG_FILE": str(conf)}


def _inkscape(svg: FilePath, out: FilePath, *extra: str) -> None:
    subprocess.run([_tool("inkscape"), str(svg), f"--export-filename={out}", *extra],
                   env=font_env(), check=True, capture_output=True)


def _png_size(medium: Medium, width: float) -> str:
    """Screens get exactly one pixel per artboard unit; print previews 200 dpi."""
    return f"--export-width={round(width)}" if medium is Medium.SCREEN else "--export-dpi=200"


def render(svg: FilePath, stem: str, out_dir: FilePath, medium: Medium, width: float) -> list[FilePath]:
    pdf, png, gray = (out_dir / f"{stem}.pdf", out_dir / f"{stem}.png", out_dir / f"{stem}_grayscale.png")
    _inkscape(svg, pdf, "--export-type=pdf")
    _inkscape(svg, png, "--export-type=png", _png_size(medium, width))
    # NMSU: "check that the design works in black and white". A person has
    # to judge that one, so we hand them the grayscale render to look at.
    subprocess.run([_tool("magick"), str(png), "-colorspace", "Gray", str(gray)], check=True)
    return [pdf, png, gray]


def _pixels_differing(a: FilePath, b: FilePath) -> float:
    res = subprocess.run([_tool("magick"), "compare", "-metric", "AE", "-fuzz", "10%", str(a), str(b), "null:"],
                         capture_output=True, text=True)
    if res.returncode > 1:
        raise RuntimeError(f"magick compare failed: {res.stderr.strip()}")
    return float(res.stderr.split()[0])


def verify_jsx(jsx: FilePath, svg: FilePath, work: FilePath, width: float) -> None:
    """Run the Illustrator script against a strict mock of Illustrator's DOM
    under both artboard coordinate conventions, redraw what it built, and
    require the result to match the SVG pixel for pixel (10% fuzz for
    anti-aliasing). The mock can only hold the script to our model of the
    Illustrator API; a real Illustrator run is still the final word."""
    ref = work / "verify_ref.png"
    size = f"--export-width={round(min(width * 150 / 72, 2400))}"
    _inkscape(svg, ref, "--export-type=png", size)
    for mode in ("cc", "legacy"):
        rebuilt_svg, rebuilt_png = work / f"verify_{mode}.svg", work / f"verify_{mode}.png"
        res = subprocess.run([_tool("node"), str(MOCK), str(jsx), str(rebuilt_svg), mode],
                             capture_output=True, text=True)
        if res.returncode:
            raise RuntimeError(f"Illustrator script failed on the mock ({mode}):\n{res.stderr}")
        _inkscape(rebuilt_svg, rebuilt_png, "--export-type=png", size, "--export-background=white")
        diff = _pixels_differing(ref, rebuilt_png)
        if diff:
            raise RuntimeError(f"Illustrator script ({mode} coordinates) draws something different from "
                               f"the SVG: {diff:.0f} pixels differ; see {work}")


# ------------------------------------------------------------- publish ----

def publish(layers: list[Group], *, width: float, height: float, out_dir: FilePath, stem: str,
            title: str, medium: Medium = Medium.PRINT) -> None:
    page = Group("Background", [Rect("Page", 0, 0, width, height, fill=Paint(WHITE_SANDS))],
                 layer=True, locked=True)
    layers = [page, *layers]

    problems, model = lint_model(layers, medium)
    if problems:
        raise BrandViolation(problems)

    out_dir.mkdir(parents=True, exist_ok=True)
    staging = out_dir / ".staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    svg, jsx = staging / f"{stem}.svg", staging / f"{stem}_build.jsx"
    write_svg(svg, layers, width, height, title)
    write_jsx(jsx, layers, width, height, title)
    assets = write_assets(layers, staging / "assets")
    rendered = render(svg, stem, staging, medium, width)

    problems, shares = lint_render(staging / f"{stem}.png", layers, width)
    if problems:
        raise BrandViolation(problems + [Finding("rejected", str(staging), "render kept here to inspect")])
    verify_jsx(jsx, svg, staging, width)

    for f in (svg, jsx, *rendered):
        f.replace(out_dir / f.name)
    shutil.rmtree(out_dir / "assets", ignore_errors=True)
    if assets:
        (staging / "assets").replace(out_dir / "assets")
    shutil.rmtree(staging)

    print(f"published {title!r} to {out_dir}")
    if medium is Medium.SCREEN:
        print(f"  artboard  {width:g} x {height:g} px, for screens")
    else:
        print(f"  artboard  {width:g} x {height:g} pt ({width / 72:.2f} x {height / 72:.2f} in), for print")
    unit = "px" if medium is Medium.SCREEN else "pt"
    print(f"  type      sizes {model.sizes} {unit}, weights {model.weights}")
    print(f"  contrast  lowest text contrast {model.min_contrast:.2f}:1")
    print("  color     " + ", ".join(f"{s.name.removeprefix('NMSU ')} {v:.0%}"
                                      for s, v in sorted(shares.items(), key=lambda kv: -kv[1])))
    print("  verified  Illustrator script rebuilds the SVG on the DOM mock (both coordinate conventions)")
    print(f"  look at   {out_dir / (stem + '.png')} and {out_dir / (stem + '_grayscale.png')}")
