"""Fall 2026 Commencement welcome screen, built from source/request.md.

The request: a 1920 x 1080 slide for the big screen before the ceremony that
says it starts shortly, gives the program URL and a QR code to it, the
#NMSUGrad hashtag and the NMSU logo, plus either the hand-and-cap graphic or
a photo of a graduate holding a diploma.

Choices we made:
  - the graduate photo (source/NMSU_SpringCommencement_051025-19.tif) rather
    than the hand-and-cap graphic, because it's genuine NMSU photography and
    carries more at this size. The cap graphic is still in
    source/graphics.zip if the requester prefers it.
  - the QR code opens https://commencement.nmsu.edu, the page the copy names.
  - the copy is exactly as sent. The URL line breaks after ".edu" so the
    address stays on one line.
"""

from __future__ import annotations

from pathlib import Path as FilePath

from PIL import Image as PILImage

from nmsu.brand import AGGIE_CRIMSON, DESERT_SAND, LOGO_SETUP_CRIMSON, ROOT, WHITE_SANDS, Medium, Paint, Style
from nmsu.export import publish
from nmsu.layout import Group, Image, Item, Logo, Path, QRCode, Rect, Text, cap_height, wrap
from nmsu.photo import prepare_cutout

HERE = FilePath(__file__).resolve().parent
PHOTO_SOURCE = HERE / "source" / "NMSU_SpringCommencement_051025-19.tif"
PHOTO = ROOT / ".cache" / "jobs" / HERE.name / "graduate.png"

# ---------------------------------------------------------------- content ----

WELCOME = "WELCOME!"
BEGIN = "We will begin shortly"
EVENT = "Class of 2026 Commencement"
VISIT = "Visit commencement.nmsu.edu\nfor more information."
HASHTAG = "#NMSUGrad"
PROGRAM_URL = "https://commencement.nmsu.edu"

# ----------------------------------------------------------------- styles ----
# Three sizes (160 / 64 / 44 px) in three weights (ExtraBold / Bold / Medium).

C = Paint(AGGIE_CRIMSON)
WH = Paint(WHITE_SANDS)

HEADLINE = Style(800, 160, 170, WH)
BEGIN_STYLE = Style(500, 64, 76, WH)
EVENT_STYLE = Style(700, 64, 76, WH)
VISIT_STYLE = Style(500, 44, 56, WH)
HASHTAG_STYLE = Style(800, 64, 76, C)

# ----------------------------------------------------------------- layout ----

W, H = 1920, 1080
BAND_Y = 840              # crimson field above, white band below
MESSAGE_CX = 640          # the message is centered in the space left of the photo
MESSAGE_W = 1080


def build() -> list[Group]:
    field = Rect("Crimson field", 0, 0, W, BAND_Y, fill=C)

    # The graduate stands on the band: the photo's cropped bottom edge sits
    # on the crimson field's bottom edge. Prepared at 2x for Illustrator.
    photo_h = 790
    prepare_cutout(PHOTO_SOURCE, PHOTO, 2 * photo_h)
    with PILImage.open(PHOTO) as im:
        photo_w = photo_h * im.width / im.height
    photo = Image("Graduate", PHOTO, 1290, BAND_Y - photo_h, photo_w, photo_h)

    # The message stack, centered vertically on the crimson field.
    visit_lines = wrap(VISIT, VISIT_STYLE, MESSAGE_W)
    to_begin, to_rule, to_event, to_visit = 100, 60, 85, 80
    span = (cap_height(HEADLINE) + to_begin + to_rule + to_event + to_visit
            + (len(visit_lines) - 1) * VISIT_STYLE.leading)
    welcome_y = (BAND_Y - span) / 2 + cap_height(HEADLINE)
    begin_y = welcome_y + to_begin
    rule_y = begin_y + to_rule
    event_y = rule_y + to_event
    message: list[Item] = [
        Text("Welcome", [WELCOME], MESSAGE_CX, welcome_y, HEADLINE, MESSAGE_W),
        Text("Begin shortly", [BEGIN], MESSAGE_CX, begin_y, BEGIN_STYLE, MESSAGE_W),
        Path("Divider", [(MESSAGE_CX - 90, rule_y), (MESSAGE_CX + 90, rule_y)], stroke=Paint(DESERT_SAND), sw=4),
        Text("Event", [EVENT], MESSAGE_CX, event_y, EVENT_STYLE, MESSAGE_W),
        Text("Visit", visit_lines, MESSAGE_CX, event_y + to_visit, VISIT_STYLE, MESSAGE_W),
    ]

    # The footer band: logo, hashtag, QR code, each centered on the band.
    band_cy = (BAND_Y + H) / 2
    logo_h = 170
    qr = QRCode("Program QR code", PROGRAM_URL, 0, 0, module=6)
    qr.x, qr.y = W - 90 - qr.size, round(band_cy - qr.size / 2)
    footer: list[Item] = [
        Logo("NMSU logo", LOGO_SETUP_CRIMSON, 90, band_cy - logo_h / 2, logo_h),
        Text("Hashtag", [HASHTAG], W / 2, band_cy + cap_height(HASHTAG_STYLE) / 2, HASHTAG_STYLE, 600),
        qr,
    ]

    return [
        Group("Crimson field", [field], layer=True),
        Group("Photo", [photo], layer=True),
        Group("Message", message, layer=True),
        Group("Footer", footer, layer=True),
    ]


if __name__ == "__main__":
    publish(build(), width=W, height=H, out_dir=HERE / "out", stem="Commencement_Welcome_Fall2026",
            title="Fall 2026 Commencement welcome screen", medium=Medium.SCREEN)
