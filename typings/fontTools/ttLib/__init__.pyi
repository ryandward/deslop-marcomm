# The slice of fontTools.ttLib that nmsu.layout uses: two tables, two fields.
from typing import Literal, overload

class _OS2Table:
    sCapHeight: int

class _HeadTable:
    unitsPerEm: int

class TTFont:
    def __init__(self, file: str) -> None: ...
    @overload
    def __getitem__(self, tag: Literal["OS/2"]) -> _OS2Table: ...
    @overload
    def __getitem__(self, tag: Literal["head"]) -> _HeadTable: ...
