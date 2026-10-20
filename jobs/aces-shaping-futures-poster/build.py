"""ACES "is shaping futures" poster, 11 x 17 in, built from source/request.md.

The request: the heading in the top 4 in, a grid of five or six photos in
different sizes in the next 8 in, the student tagline PNG below that, and
only Aggie Crimson and Azure Sky.

Choices we made:
  - the heading echoes the tagline's own type: a light Azure Sky line, a
    heavy crimson line, then a bold Azure Sky line, so the top and bottom
    of the poster read as one system.
  - no photos came with the request, so the grid is six empty photo slots
    for a designer to fill in Illustrator.
  - the crimson NMSU vertical setup sits beside the tagline. The brief
    doesn't ask for it, but NMSU requires a logo and the full university
    name on standalone pieces, and it can't go next to the college name in
    the heading, because that would make an unofficial unit setup.
  - the tagline PNG is 818 px wide once its empty border is trimmed, about
    130 ppi at this size, so it's placed FPO: a designer swaps in the vector
    original before print.
  - the heading copy is exactly as sent, line breaks included. The college's
    official name is "College of Agricultural, Consumer and Environmental
    Sciences", so "Agriculture" and the comma after "Consumer" are flagged
    with the requester rather than changed.
"""

from __future__ import annotations

from pathlib import Path as FilePath

from PIL import Image as PILImage

from nmsu.brand import AGGIE_CRIMSON, AZURE_SKY, LOGO_SETUP_CRIMSON, ROOT, Paint, Style
from nmsu.export import publish
from nmsu.layout import Group, Image, Item, Logo, PhotoSlot, Rect, centered_stack
from nmsu.photo import prepare_cutout

HERE = FilePath(__file__).resolve().parent
TAGLINE_SOURCE = HERE / "source" / "Tagline_Student.png"
TAGLINE = ROOT / ".cache" / "jobs" / HERE.name / "tagline-student.png"

# ---------------------------------------------------------------- content ----

THE_COLLEGE_OF = "THE COLLEGE OF"
COLLEGE = "Agriculture, Consumer,\nand Environmental Sciences"
SHAPING = "is shaping futures"

# ----------------------------------------------------------------- styles ----
# Three sizes (26 / 44 / 34 pt) in three weights (Medium / ExtraBold / Bold).

C = Paint(AGGIE_CRIMSON)
AZ = Paint(AZURE_SKY)

LEAD_IN = Style(500, 26, 32, AZ)
COLLEGE_STYLE = Style(800, 44, 50, C)
SHAPING_STYLE = Style(700, 34, 46, AZ)

# ----------------------------------------------------------------- layout ----

W, H = 11 * 72, 17 * 72   # 792 x 1224 pt
MARGIN = 36               # 0.5 in
HEADING_H = 4 * 72        # the top 4 in
GRID_H = 8 * 72           # the next 8 in
GUTTER = 12

# The photo grid is four columns by three rows, and each slot spans some of
# them: (column, row, columns wide, rows tall). Six slots in four sizes.
SLOTS = [
    (0, 0, 2, 2),   # large
    (2, 0, 2, 1),   # wide
    (2, 1, 1, 1),   # small
    (3, 1, 1, 2),   # tall
    (0, 2, 1, 1),   # small
    (1, 2, 2, 1),   # wide
]
COLS, ROWS = 4, 3


def photo_grid(x: float, y: float, w: float, h: float) -> list[Item]:
    col_w = (w - (COLS - 1) * GUTTER) / COLS
    row_h = (h - (ROWS - 1) * GUTTER) / ROWS
    slots: list[Item] = []
    for n, (c, r, cs, rs) in enumerate(SLOTS, 1):
        sw, sh = cs * col_w + (cs - 1) * GUTTER, rs * row_h + (rs - 1) * GUTTER
        slots.append(PhotoSlot(f"Photo {n} ({sw / 72:.2f} x {sh / 72:.2f} in)",
                               x + c * (col_w + GUTTER), y + r * (row_h + GUTTER), sw, sh))
    return slots


def build() -> list[Group]:
    heading_box = Rect("Heading area", MARGIN, 0, W - 2 * MARGIN, HEADING_H)
    heading: list[Item] = [*centered_stack("Heading", heading_box, [
        (THE_COLLEGE_OF, LEAD_IN),
        (COLLEGE, COLLEGE_STYLE),
        (SHAPING, SHAPING_STYLE),
    ])]

    grid_y = HEADING_H
    photos = photo_grid(MARGIN, grid_y, W - 2 * MARGIN, GRID_H)

    # The tagline and the logo share the bottom 5 in, centered on it.
    prepare_cutout(TAGLINE_SOURCE, TAGLINE)
    with PILImage.open(TAGLINE) as im:
        aspect = im.width / im.height
    footer_cy = (grid_y + GRID_H + H) / 2
    tag_w = 470
    tag_h = tag_w / aspect
    tagline = Image("Tagline", TAGLINE, MARGIN, footer_cy - tag_h / 2, tag_w, tag_h, fpo=True)
    logo_h = 124
    logo = Logo("NMSU logo", LOGO_SETUP_CRIMSON, 0, footer_cy - logo_h / 2, logo_h)
    logo.x = W - MARGIN - logo.w

    return [
        Group("Heading", heading, layer=True),
        Group("Photos", photos, layer=True),
        Group("Tagline and logo", [tagline, logo], layer=True),
    ]


if __name__ == "__main__":
    publish(build(), width=W, height=H, out_dir=HERE / "out", stem="ACES_Shaping_Futures_Poster",
            title="ACES is shaping futures poster, 11 x 17")
