"""Each test hands the brand compiler a piece of typical AI slop and proves it
gets refused. If one of these starts passing the slop through, the repo has
stopped doing its job."""

from __future__ import annotations

from pathlib import Path as FilePath

import pytest

from PIL import Image as PILImage

from nmsu.brand import (AGGIE_CRIMSON, AZURE_SKY, BLACK, DESERT_MONSOON, DESERT_SAND, LOGO_SETUP_CRIMSON,
                        LOGO_SETUP_WHITE, SAGEBRUSH_MINT, WHITE_SANDS, Medium, Paint, Style, Swatch, Tier)
from nmsu.export import publish
from nmsu.layout import Group, Image, Logo, Overflow, QRCode, Rect, Text, text_width
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


# ---- logos, photos, QR codes and screens --------------------------------

SCREEN_TEXT = Style(700, 32, 40, Paint(AGGIE_CRIMSON))


def photo(tmp_path: FilePath, w: int = 40, h: int = 60) -> FilePath:
    path = tmp_path / "photo.png"
    PILImage.new("RGBA", (w, h), (90, 90, 90, 255)).save(path)
    return path


def rules_for(layers: list[Group], medium: Medium = Medium.SCREEN) -> set[str]:
    return {f.rule for f in lint_model([page(800, 450), *layers], medium)[0]}


def test_text_crowding_the_logo_is_flagged() -> None:
    logo = Logo("logo", LOGO_SETUP_CRIMSON, 50, 50, 120)
    # The word starts halfway into the clear space without touching the logo itself.
    half = text_width("Commencement", SCREEN_TEXT) / 2
    cx = logo.x + logo.w + logo.clear_space / 2 + half
    crowding = Text("t", ["Commencement"], cx, 120, SCREEN_TEXT, 400)
    assert rules_for([Group("Slop", [logo, crowding])]) == {"logo-clear-space"}


def test_white_logo_on_a_white_page_is_flagged() -> None:
    logo = Logo("logo", LOGO_SETUP_WHITE, 50, 50, 120)
    assert "logo-variant" in rules_for([Group("Slop", [logo, Text("t", ["Hi"], 600, 400, SCREEN_TEXT, 300)])])


def test_logo_under_the_screen_minimum_is_flagged() -> None:
    logo = Logo("logo", LOGO_SETUP_CRIMSON, 50, 50, 40)
    assert "logo-min-size" in rules_for([Group("Slop", [logo, Text("t", ["Hi"], 600, 400, SCREEN_TEXT, 300)])])


def test_stretched_photo_is_refused(tmp_path: FilePath) -> None:
    with pytest.raises(ValueError, match="stretch"):
        Image("photo", photo(tmp_path, 40, 60), 0, 0, 80, 60)


def test_text_over_a_photo_is_flagged(tmp_path: FilePath) -> None:
    shot = Image("photo", photo(tmp_path), 100, 50, 200, 300)
    caption = Text("t", ["Congrats"], 200, 200, SCREEN_TEXT, 190)
    assert rules_for([Group("Slop", [shot, caption])]) == {"text-over-image"}


def test_qr_code_that_does_not_scan_is_refused(tmp_path: FilePath) -> None:
    qr = QRCode("qr", "https://commencement.nmsu.edu", 300, 100, module=6)
    sticker = Rect("sticker", qr.x + 60, qr.y + 60, 100, 100, fill=Paint(AGGIE_CRIMSON))
    with pytest.raises(BrandViolation) as err:
        publish([Group("Slop", [qr, sticker], layer=True)], width=800, height=450, out_dir=tmp_path,
                stem="slop", title="slop", medium=Medium.SCREEN)
    assert "qr-decode" in {f.rule for f in err.value.findings}


def test_publish_accepts_an_on_brand_screen(tmp_path: FilePath) -> None:
    """The screen control: a logo, a photo and a QR code get through, the
    PNG comes out at exactly the artboard's pixel size, and the photo and
    logo ship in assets/ next to the Illustrator script that links them."""
    band = Rect("band", 0, 300, 800, 150, fill=Paint(AGGIE_CRIMSON))
    layers = [Group("Design", [
        band,
        Image("Graduate", photo(tmp_path), 560, 40, 160, 240),
        Text("t", ["Welcome"], 260, 160, Style(800, 64, 72, Paint(AGGIE_CRIMSON)), 480),
        Logo("logo", LOGO_SETUP_WHITE, 40, 325, 100),
        QRCode("qr", "https://commencement.nmsu.edu", 600, 312, module=3),
    ], layer=True)]
    out = tmp_path / "out"
    publish(layers, width=800, height=450, out_dir=out, stem="ok", title="ok", medium=Medium.SCREEN)
    with PILImage.open(out / "ok.png") as im:
        assert im.size == (800, 450)
    assert sorted(p.name for p in (out / "assets").iterdir()) == ["nmsu-vertical-setup-white.svg", "photo.png"]
