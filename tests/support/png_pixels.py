"""The pixels of a PNG file, decoded with the standard library alone.

BDL-080 S4e (``beadloom-af99.9``). Beadloom's PNG favicon is generated from its
SVG by ``tests/support/render_favicon_png.mjs``, and a test reads the result back
to hold what the PNG carries: its size and the colour of its glyph. Only the form
that script writes is read — 8-bit RGBA, not interlaced — and anything else is
refused by name rather than decoded wrongly.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_RGBA = 6
_BYTES_PER_PIXEL = 4
_BIT_DEPTH = 8

#: A pixel: red, green, blue, alpha, each 0..255.
Pixel = tuple[int, int, int, int]


@dataclass(frozen=True)
class PngImage:
    """A decoded image: its size and its rows of pixels, top to bottom."""

    width: int
    height: int
    rows: tuple[tuple[Pixel, ...], ...]

    def at(self, x: int, y: int) -> Pixel:
        """The pixel at column *x*, row *y*."""
        return self.rows[y][x]


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(_SIGNATURE):
        raise ValueError("not a PNG file: the signature is missing")
    found: list[tuple[bytes, bytes]] = []
    offset = len(_SIGNATURE)
    while offset < len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8]
        found.append((kind, data[offset + 8 : offset + 8 + length]))
        offset += 12 + length
    return found


def _paeth(left: int, up: int, corner: int) -> int:
    estimate = left + up - corner
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - corner))
    return (left, up, corner)[distances.index(min(distances))]


def _unfilter(kind: int, line: bytearray, previous: bytes) -> None:
    for index, value in enumerate(line):
        left = line[index - _BYTES_PER_PIXEL] if index >= _BYTES_PER_PIXEL else 0
        up = previous[index]
        corner = previous[index - _BYTES_PER_PIXEL] if index >= _BYTES_PER_PIXEL else 0
        predictor = (0, left, up, (left + up) // 2, _paeth(left, up, corner))[kind]
        line[index] = (value + predictor) % 256


def read_png(data: bytes) -> PngImage:
    """The image *data* holds; :class:`ValueError` for a form this reader does not take."""
    chunks = _chunks(data)
    header = next(body for kind, body in chunks if kind == b"IHDR")
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", header)
    if (depth, colour, interlace) != (_BIT_DEPTH, _RGBA, 0):
        raise ValueError(f"only 8-bit RGBA without interlace is read, not {depth}/{colour}")
    raw = zlib.decompress(b"".join(body for kind, body in chunks if kind == b"IDAT"))
    stride = width * _BYTES_PER_PIXEL
    previous = bytes(stride)
    rows: list[tuple[Pixel, ...]] = []
    for y in range(height):
        start = y * (stride + 1)
        line = bytearray(raw[start + 1 : start + 1 + stride])
        _unfilter(raw[start], line, previous)
        previous = bytes(line)
        rows.append(
            tuple(
                (line[x], line[x + 1], line[x + 2], line[x + 3])
                for x in range(0, stride, _BYTES_PER_PIXEL)
            )
        )
    return PngImage(width=width, height=height, rows=tuple(rows))
