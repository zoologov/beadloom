"""A file-history entry: one recorded upload."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    """One upload: the file's name and the number of rows it held."""

    name: str
    rows: int
