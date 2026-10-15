"""Write the NMSU palette as swatch libraries designers can load directly.

  brand/swatches/NMSU_RGB.ase    Illustrator / InDesign, screen work
  brand/swatches/NMSU_CMYK.ase   Illustrator / InDesign, process print
  brand/swatches/NMSU.gpl        Inkscape / GIMP

The files are generated from nmsu.brand.PALETTE so they can't drift from
it: python -m nmsu.swatches
"""

from __future__ import annotations

import struct
from collections.abc import Iterable
from pathlib import Path

from .brand import PALETTE, ROOT, Swatch

OUT = ROOT / "brand" / "swatches"
GROUP = "NMSU Brand"


def _name(s: str) -> bytes:
    """ASE strings: UTF-16 code-unit count including the terminator, then
    UTF-16BE text, then a 16-bit null."""
    return struct.pack(">H", len(s) + 1) + s.encode("utf-16-be") + b"\x00\x00"


def _block(kind: int, body: bytes) -> bytes:
    return struct.pack(">HI", kind, len(body)) + body


def ase(swatches: Iterable[Swatch], model: str) -> bytes:
    blocks = [_block(0xC001, _name(GROUP))]
    for s in swatches:
        if model == "RGB":
            values = struct.pack(">3f", *(c / 255 for c in s.rgb))
            tag = b"RGB "
        else:
            values = struct.pack(">4f", *(c / 100 for c in s.cmyk))
            tag = b"CMYK"
        blocks.append(_block(0x0001, _name(s.name) + tag + values + struct.pack(">H", 0)))  # 0 = global
    blocks.append(_block(0xC002, b""))
    return b"ASEF" + struct.pack(">HHI", 1, 0, len(blocks)) + b"".join(blocks)


def gpl(swatches: Iterable[Swatch]) -> str:
    rows = [f"{r:3d} {g:3d} {b:3d}\t{s.name}{f' ({s.pms})' if s.pms else ''}"
            for s in swatches for r, g, b in [s.rgb]]
    return "\n".join(["GIMP Palette", f"Name: {GROUP}", "Columns: 3", "#", *rows, ""])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files: list[tuple[Path, bytes]] = [
        (OUT / "NMSU_RGB.ase", ase(PALETTE, "RGB")),
        (OUT / "NMSU_CMYK.ase", ase(PALETTE, "CMYK")),
        (OUT / "NMSU.gpl", gpl(PALETTE).encode()),
    ]
    for path, data in files:
        path.write_bytes(data)
        print(path)


if __name__ == "__main__":
    main()
