"""Each test hands the brand compiler a piece of typical AI slop and proves it
gets refused. If one of these starts passing the slop through, the repo has
stopped doing its job."""

from __future__ import annotations

from pathlib import Path as FilePath

import pytest

from nmsu.brand import (AGGIE_CRIMSON, AZURE_SKY, BLACK, DESERT_MONSOON, DESERT_SAND, SAGEBRUSH_MINT,
                        WHITE_SANDS, Paint, Style, Swatch, Tier)
from nmsu.export import publish
from nmsu.layout import Group, Overflow, Rect, Text
from nmsu.lint import BrandViolation, lint_model

CRIMSON_BODY = Style(500, 9, 11, Paint(AGGIE_CRIMSON))


def page(w: float = 300, h: float = 200) -> Group:
    return Group("Background", [Rect("Page", 0, 0, w, h, fill=Paint(WHITE_SANDS))], layer=True)


def test_off_palette_color_cannot_be_constructed() -> None:
    purple = Swatch("ChatGPT Purple", "#7B2FBE", (40, 80, 0, 0), "", Tier.TERTIARY)
    with pytest.raises(ValueError, match="not an NMSU brand color"):
        Paint(purple)


def test_sagebrush_mint_is_never_a_font_color() -> None:
    with pytest.raises(ValueError, match="font color"):
        Style(500, 9, 11, Paint(SAGEBRUSH_MINT))


def test_text_that_overflows_its_box_is_refused() -> None:
    with pytest.raises(Overflow):
        Text("t", ["Revolutionizing brine management"], 50, 50, CRIMSON_BODY, max_w=60)


def test_four_type_sizes_and_gray_on_beige_are_flagged() -> None:
    beige = Rect("box", 10, 10, 280, 60, fill=Paint(DESERT_SAND))
    gray = Style(500, 9, 11, Paint(DESERT_MONSOON))
    layers = [page(), Group("Slop", [
        beige,
        Text("on beige", ["Low contrast caption"], 150, 40, gray, 260),
        Text("a", ["Title"], 150, 100, Style(800, 20, 24, Paint(AGGIE_CRIMSON)), 260),
        Text("b", ["Heading"], 150, 130, Style(700, 12, 14, Paint(BLACK)), 260),
        Text("c", ["Body"], 150, 160, Style(500, 7.5, 9, Paint(BLACK)), 260),
    ])]
    rules = {f.rule for f in lint_model(layers)[0]}
    assert rules == {"type-sizes", "contrast"}


def test_design_without_crimson_is_flagged() -> None:
    layers = [page(), Group("Slop", [Text("t", ["Hello"], 150, 100, Style(500, 9, 11, Paint(BLACK)), 260)])]
    assert {f.rule for f in lint_model(layers)[0]} == {"crimson-present"}


def test_publish_refuses_a_page_flooded_with_an_accent_color(tmp_path: FilePath) -> None:
    flood = Rect("hero", 0, 0, 300, 170, fill=Paint(AZURE_SKY))
    caption = Text("t", ["Water Futures"], 150, 190, CRIMSON_BODY, 260)
    with pytest.raises(BrandViolation) as err:
        publish([Group("Slop", [flood, caption], layer=True)], width=300, height=200,
                 out_dir=tmp_path, stem="slop", title="slop")
    rules = {f.rule for f in err.value.findings}
    assert {"tertiary-share", "crimson-dominant", "crimson-white-prominent"} <= rules
    # Nothing but the rejected render in staging reaches the output folder.
    assert sorted(p.name for p in tmp_path.iterdir()) == [".staging"]


def test_publish_accepts_an_on_brand_design(tmp_path: FilePath) -> None:
    """The control: good work gets through, and getting through exercises the
    whole toolchain (inkscape, magick, node), so a fresh machine that passes
    this can publish."""
    box = Rect("box", 75, 40, 150, 50, 6, fill=Paint(AGGIE_CRIMSON))
    layers = [Group("Design", [
        box,
        Text("label", ["Office of the Provost"], 150, 69, Style(700, 9, 11, Paint(WHITE_SANDS)), 150),
        Text("caption", ["New Mexico State University"], 150, 130, Style(500, 9, 11, Paint(BLACK)), 260),
    ], layer=True)]
    publish(layers, width=300, height=200, out_dir=tmp_path, stem="ok", title="ok")
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "ok.pdf", "ok.png", "ok.svg", "ok_build.jsx", "ok_grayscale.png"]
