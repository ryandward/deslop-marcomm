"""NMSU brand definitions: the only place a color, a typeface, or a brand
rule is allowed to come from.

Every value here traces to brand.nmsu.edu (snapshots retrieved 2026-10-14 are
in reference/brand-site/). House rules that NMSU doesn't state are marked
HOUSE so nobody mistakes them for NMSU policy. BRAND.md is the readable
version of this file; when one changes, the other changes with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "brand" / "fonts"
LOGO_DIR = ROOT / "brand" / "logos"


# ---------------------------------------------------------------- color ----

class Tier(Enum):
    CORE = "core"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    TEXT = "text"            # black type; NMSU allows it but doesn't list it as a brand color


@dataclass(frozen=True)
class Swatch:
    name: str
    hex: str
    cmyk: tuple[int, int, int, int]
    pms: str
    tier: Tier
    text_ok: bool = True

    @property
    def rgb(self) -> tuple[int, int, int]:
        h = self.hex.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    @property
    def chromatic(self) -> bool:
        """True for colors that could compete with crimson for attention.
        Desert Sand, Organ Mountain and Desert Monsoon are warm and cool
        grays (chroma under 20); Azure Sky, Sagebrush Mint and Mesilla
        Valley Sunset are not (chroma over 80)."""
        r, g, b = self.rgb
        return max(r, g, b) - min(r, g, b) > 40


# brand.nmsu.edu/color: core palette
AGGIE_CRIMSON = Swatch("NMSU Aggie Crimson", "#8C0B42", (10, 97, 37, 43), "PMS 208", Tier.CORE)
WHITE_SANDS = Swatch("NMSU White Sands", "#FFFFFF", (0, 0, 0, 0), "", Tier.CORE)
# secondary: "background colors for info boxes and tables"
ORGAN_MOUNTAIN = Swatch("NMSU Organ Mountain", "#B6A5AD", (25, 30, 20, 5), "PMS 5225 C", Tier.SECONDARY)
DESERT_SAND = Swatch("NMSU Desert Sand", "#D7C9C4", (10, 15, 15, 5), "PMS 7604 C", Tier.SECONDARY)
# tertiary: "used sparingly", at most 20 percent of the design's color
AZURE_SKY = Swatch("NMSU Azure Sky", "#009DB8", (100, 0, 22, 10), "PMS 2229 C", Tier.TERTIARY)
DESERT_MONSOON = Swatch("NMSU Desert Monsoon", "#6D6E71", (0, 0, 0, 70), "Cool Grey 10", Tier.TERTIARY)
SAGEBRUSH_MINT = Swatch("NMSU Sagebrush Mint", "#6CC3BC", (56, 2, 30, 0), "PMS 7472 C", Tier.TERTIARY,
                        text_ok=False)   # "should not be used as a font color"
MESILLA_VALLEY_SUNSET = Swatch("NMSU Mesilla Valley Sunset", "#F2824F", (1, 60, 75, 0), "PMS 1575 C",
                               Tier.TERTIARY)
# "White Sands and black font colors help with legibility"; #231F20 is 100K in RGB
BLACK = Swatch("NMSU Black", "#231F20", (0, 0, 0, 100), "Process Black", Tier.TEXT)

PALETTE: tuple[Swatch, ...] = (AGGIE_CRIMSON, WHITE_SANDS, ORGAN_MOUNTAIN, DESERT_SAND, AZURE_SKY,
                               DESERT_MONSOON, SAGEBRUSH_MINT, MESILLA_VALLEY_SUNSET, BLACK)

# The NMSU logo files carry #8C1844, not #8C0B42. "Don't change the color of
# the NMSU logo", so placed logo art is never recolored to match the palette.
LOGO_CRIMSON = "#8C1844"


@dataclass(frozen=True)
class Paint:
    """A palette swatch, optionally as a tint (percent of full strength)."""
    swatch: Swatch
    tint: int = 100

    def __post_init__(self) -> None:
        if self.swatch not in PALETTE:
            raise ValueError(f"{self.swatch.name} is not an NMSU brand color")
        if not 0 < self.tint <= 100:
            raise ValueError(f"tint {self.tint} out of range")

    @property
    def rgb(self) -> tuple[int, int, int]:
        t = self.tint / 100
        r, g, b = (round(255 - t * (255 - c)) for c in self.swatch.rgb)
        return r, g, b

    @property
    def hex(self) -> str:
        return "#" + "".join(f"{c:02X}" for c in self.rgb)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_rgb(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast_ratio(a: Paint, b: Paint) -> float:
    return contrast_rgb(a.rgb, b.rgb)


# ----------------------------------------------------------- typefaces ----

# brand.nmsu.edu/typeface: Gotham is primary; Montserrat is the free
# substitute we set everything in, so the output renders the same everywhere.
MONTSERRAT_WEIGHTS = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold",
                      800: "ExtraBold", 900: "Black"}
# Gotham headline styles are Black, Medium and Book. When a machine has
# Gotham, the Illustrator script swaps each Montserrat weight for these.
GOTHAM_FOR = {"Montserrat-Regular": "Gotham-Book", "Montserrat-Medium": "Gotham-Book",
              "Montserrat-SemiBold": "Gotham-Medium", "Montserrat-Bold": "Gotham-Bold",
              "Montserrat-ExtraBold": "Gotham-Black", "Montserrat-Black": "Gotham-Black"}


@dataclass(frozen=True)
class Style:
    weight: int          # Montserrat weight class
    size: float          # pt
    leading: float       # pt, baseline to baseline
    paint: Paint

    def __post_init__(self) -> None:
        if self.weight not in MONTSERRAT_WEIGHTS:
            raise ValueError(f"weight {self.weight} is not a brand weight "
                             f"({sorted(MONTSERRAT_WEIGHTS)})")
        if not self.paint.swatch.text_ok:
            raise ValueError(f"{self.paint.swatch.name} may not be used as a font color")
        if self.leading < self.size:
            raise ValueError(f"leading {self.leading} is tighter than size {self.size}")

    @property
    def postscript(self) -> str:
        return f"Montserrat-{MONTSERRAT_WEIGHTS[self.weight]}"

    @property
    def font_file(self) -> Path:
        return FONT_DIR / "montserrat" / f"{self.postscript}.ttf"


# --------------------------------------------------------------- rules ----

MAX_TYPE_SIZES = 3        # "use only two or three different font styles and sizes
MAX_TYPE_WEIGHTS = 3      #  in a single printed piece"
TERTIARY_MAX_SHARE = 0.20  # "should not take up more than 20 percent"
CONTRAST_NORMAL = 4.5     # WCAG 2.2 AA, which brand.nmsu.edu/color asks for
CONTRAST_LARGE = 3.0
LARGE_TEXT_PT = 18.0      # WCAG "large": 18pt, or 14pt bold
LARGE_BOLD_TEXT_PT = 14.0
FIT_MARGIN = 0.98         # HOUSE: a line may fill 98% of its box, so another
                          # Montserrat build (Adobe Fonts, older Google zip)
                          # can't push it over the edge


# --------------------------------------------------------------- media ----

class Medium(Enum):
    """What a piece is for. It sets the units (points for print, pixels for
    screens), how the preview PNG is rendered, and which minimums apply."""
    PRINT = "print"
    SCREEN = "screen"


MIN_TEXT = {Medium.PRINT: 7.0, Medium.SCREEN: 16.0}   # HOUSE: 7 pt in print, 16 px on screens
# HOUSE: image pixels per artboard unit. Print wants 300 ppi at final size
# (300 px per 72 pt); a screen should never upscale a photo past 1 px per px.
MIN_IMAGE_DENSITY = {Medium.PRINT: 300 / 72, Medium.SCREEN: 1.0}


# ---------------------------------------------------------------- logos ----

@dataclass(frozen=True)
class LogoArt:
    """One of NMSU's logo files, always placed exactly as provided.

    box is the artwork's own bounds (x, y, w, h) in the file's units, which
    can differ from its viewBox; the white setup's canvas runs well below its
    artwork. s_height is the height of the S in "State", the unit NMSU
    measures clear space in. Both were measured on 2026-10-15 with
    `inkscape --query-all` and, for the crimson setup whose letters are cut
    out of one shape, from a 960 dpi render.
    """
    file: Path
    kind: Literal["setup", "mark"]
    on_dark: bool          # the white versions, for crimson or dark backgrounds
    box: tuple[float, float, float, float]
    s_height: float
    color: str             # the logo's main color, for checking it stands out

    @property
    def aspect(self) -> float:
        return self.box[2] / self.box[3]


LOGO_SETUP_CRIMSON = LogoArt(LOGO_DIR / "nmsu-vertical-setup-crimson.svg", "setup", False,
                             (0.0, 0.0, 345.81, 213.89), 25.3, LOGO_CRIMSON)
LOGO_SETUP_WHITE = LogoArt(LOGO_DIR / "nmsu-vertical-setup-white.svg", "setup", True,
                           (0.1, -0.9, 98.7, 88.4), 12.2, "#FFFFFF")
LOGOS: tuple[LogoArt, ...] = (LOGO_SETUP_CRIMSON, LOGO_SETUP_WHITE)

# "Mark must be at least a half-inch high" in print and 75 px on screens;
# setups "use above .4375 in tall" in print and 50 px on screens.
LOGO_MIN_HEIGHT: dict[tuple[str, Medium], float] = {
    ("mark", Medium.PRINT): 36.0, ("mark", Medium.SCREEN): 75.0,
    ("setup", Medium.PRINT): 31.5, ("setup", Medium.SCREEN): 50.0,
}
LOGO_MIN_CONTRAST = 3.0    # HOUSE: WCAG's 3:1 for graphics, for "the greatest visibility"
DARK_BACKGROUND = 0.25     # HOUSE: relative luminance under this takes the white logo

QR_QUIET_MODULES = 4       # ISO/IEC 18004: four light modules on every side
