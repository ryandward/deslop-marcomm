"""Getting photos from what a requester sent into something we can place."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def prepare_cutout(src: Path, dst: Path, height: int) -> Path:
    """Trim a cut-out photo's transparent border and save it as an 8-bit RGBA
    PNG `height` px tall. The original in source/ is never touched; this
    writes a working copy, usually under .cache/, that publish then ships in
    out/assets/. For a layered TIFF, the first page is the flattened image."""
    magick = shutil.which("magick")
    if not magick:
        raise RuntimeError("`magick` (ImageMagick) is not installed")
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([magick, f"{src}[0]", "-trim", "+repage", "-resize", f"x{height}", "-depth", "8",
                    f"PNG32:{dst}"], check=True, capture_output=True)
    return dst
