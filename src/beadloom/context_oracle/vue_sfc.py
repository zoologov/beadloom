"""Vue single-file components: the script blocks a component carries, and where they sit.

A ``.vue`` file is not written in one language. It holds a ``<template>``, a
``<style>`` and up to two script blocks — ``<script>`` and ``<script setup>`` —
each in JavaScript or, with ``lang="ts"``, TypeScript. Only the script blocks are
code in the sense the index means, so this module finds them and says, for each,
which grammar parses it and on which line of the file its text begins. Parsing
is not done here: the caller hands each block to the JS/TS grammar it already
has, and moves the rows it gets back by :attr:`ScriptBlock.line_offset`.

Until BDL-076 J3 (``beadloom-tmxa``) nothing found the blocks, so a component was
hashed and nothing more: 0 symbols from every component A0 measured.
"""

# beadloom:domain=context-oracle
# beadloom:feature=code-indexer

from __future__ import annotations

import re
from dataclasses import dataclass

#: A script block and its content. ``(?=[\s>])`` keeps a custom block whose tag
#: only begins with ``script`` (``<script-docs>``) from being read as code.
_SCRIPT_BLOCK_RE = re.compile(
    r"<script(?=[\s>])(?P<attributes>[^>]*)>(?P<text>.*?)</script\s*>",
    re.DOTALL | re.IGNORECASE,
)
_LANG_RE = re.compile(r"""\blang\s*=\s*["']?(?P<lang>[\w-]+)""", re.IGNORECASE)

#: The ``lang`` values with a grammar of their own; any other value, and no
#: ``lang`` at all, is read as JavaScript, which is what Vue does with it.
_LANG_EXTENSIONS: dict[str, str] = {"ts": ".ts", "tsx": ".tsx", "jsx": ".jsx"}
_DEFAULT_EXTENSION = ".js"


@dataclass(frozen=True)
class ScriptBlock:
    """One ``<script>`` block of a component: its text, its place, its grammar."""

    #: The content between the opening and the closing tag, verbatim.
    text: str
    #: The 0-based line of the file on which :attr:`text` begins.
    line_offset: int
    #: The script extension whose grammar parses :attr:`text` (``.js``, ``.ts``, …).
    extension: str

    def file_line(self, row: int) -> int:
        """The 1-based line of the file that holds 0-based *row* of the block."""
        return self.line_offset + row + 1


def script_blocks(source: str) -> tuple[ScriptBlock, ...]:
    """The script blocks of a component's *source*, in the order the file has them."""
    return tuple(
        ScriptBlock(
            text=match.group("text"),
            line_offset=source.count("\n", 0, match.start("text")),
            extension=_extension_of(match.group("attributes")),
        )
        for match in _SCRIPT_BLOCK_RE.finditer(source)
    )


def _extension_of(attributes: str) -> str:
    """The script extension a block's ``lang`` attribute names."""
    match = _LANG_RE.search(attributes)
    if match is None:
        return _DEFAULT_EXTENSION
    return _LANG_EXTENSIONS.get(match.group("lang").lower(), _DEFAULT_EXTENSION)
