# beadloom:domain=application
# beadloom:feature=site-generation
"""Where a project's Markdown holds code, which the portal leaves exactly as written.

Two passes change a project's own text on its way onto a portal page: its links
are rebased (:mod:`.markdown_links`) and it is made inert to Vue's template
compiler (:mod:`.project_text`). Neither may touch code. A link in a code example
is an example, and VitePress already wraps a fenced block in ``v-pre``.

:func:`code_regions` reads code the way CommonMark does, as far as a portal page
needs it (BDL-076, ``beadloom-ujzb.12``):

- YAML front matter at the very top;
- a fenced block, of backticks or tildes, from its opening line to the closing
  fence of the same character and at least the same length, or to the end of the
  text; a fence may sit in a block quote or a list item;
- an indented block: lines indented four columns or more that follow a blank line,
  outside a list, and do not continue a paragraph;
- a code span: a run of backticks up to the next run of the same length within one
  block; a run with no partner, or opened by an escaped backtick, is literal.
  :func:`block_breaks` says where a block begins: after a blank line, and at a
  list item, a heading, a table row or the first line of a block quote.

The reading is deliberately smaller than CommonMark's: an indented block nested
inside a list item is read as the item's paragraph, not as code.
"""

# beadloom:domain=application

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

#: Columns of indentation that make a line outside a list an indented code block.
_CODE_INDENT = 4
_TAB_WIDTH = 4

# A fence line: block-quote markers or a list marker may come first.
_FENCE_OPEN_RE = re.compile(
    r"^(?:[ \t]*(?:>[ \t]?|(?:[-+*]|\d{1,9}[.)])[ \t]+))*[ \t]*"
    r"(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)$"
)
_FENCE_CLOSE_RE = re.compile(r"^(?:[ \t]*>[ \t]?)*[ \t]*(?P<fence>`{3,}|~{3,})[ \t]*$")
_LIST_ITEM_RE = re.compile(r"^ {0,3}(?:[-+*]|\d{1,9}[.)])(?:[ \t]|$)")
_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_FRONT_MATTER_OPEN = "---"
_FRONT_MATTER_CLOSE = frozenset({"---", "..."})

_BACKTICKS_RE = re.compile(r"`+")
# A line that starts a block of its own even with no blank line before it.
_OWN_BLOCK_RE = re.compile(
    r"^(?:[ \t]*(?:[-+*]|\d{1,9}[.)])(?:[ \t]|$)| {0,3}#{1,6}(?:[ \t]|$)|[ \t]*\|)"
)
_QUOTE_RE = re.compile(r"^ {0,3}>")


@dataclass(frozen=True)
class CodeRegion:
    """A run of code: ``kind`` is ``frontmatter``, ``fence``, ``indented`` or ``code_span``."""

    start: int
    end: int
    kind: str


def code_regions(markdown: str) -> list[CodeRegion]:
    """Every code region of *markdown*, sorted by position and never overlapping."""
    blocks = _block_regions(markdown)
    breaks = block_breaks(markdown)
    regions: list[CodeRegion] = []
    cursor = 0
    for block in blocks:
        regions.extend(_code_spans(markdown, cursor, block.start, breaks))
        regions.append(block)
        cursor = block.end
    regions.extend(_code_spans(markdown, cursor, len(markdown), breaks))
    return regions


def _block_regions(markdown: str) -> list[CodeRegion]:
    """Front matter, fenced blocks and indented blocks, read line by line."""
    lines = markdown.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    regions: list[CodeRegion] = []
    index = _front_matter_end(lines)
    if index:
        regions.append(CodeRegion(0, starts[index], "frontmatter"))
    reader = _LineState()
    while index < len(lines):
        end, kind = _block_at(lines, index, reader)
        if kind:
            regions.append(CodeRegion(starts[index], starts[end], kind))
        index = end
    return regions


def _front_matter_end(lines: list[str]) -> int:
    """The index of the line after the front matter, ``0`` when there is none."""
    if not lines or lines[0].rstrip() != _FRONT_MATTER_OPEN:
        return 0
    for index in range(1, len(lines)):
        if lines[index].rstrip() in _FRONT_MATTER_CLOSE:
            return index + 1
    return 0


@dataclass
class _LineState:
    """What the lines read so far leave open: a paragraph, a list."""

    paragraph: bool = False
    in_list: bool = False
    after_blank: bool = True


def _block_at(lines: list[str], index: int, state: _LineState) -> tuple[int, str]:
    """The line after the block starting at *index*, and its kind (``""`` for prose)."""
    line = lines[index].rstrip("\n")
    fence = _FENCE_OPEN_RE.match(line)
    if fence is not None and not (fence["fence"][0] == "`" and "`" in fence["info"]):
        state.paragraph, state.after_blank = False, False
        return _fence_end(lines, index, fence["fence"]), "fence"
    if not line.strip():
        state.paragraph, state.after_blank = False, True
        return index + 1, ""
    indent = _indent(line)
    if indent >= _CODE_INDENT and not state.paragraph and not state.in_list:
        return _indented_end(lines, index), "indented"
    if _LIST_ITEM_RE.match(line):
        state.in_list = True
    elif state.after_blank and indent < 2:
        state.in_list = False
    state.paragraph = not _HEADING_RE.match(line)
    state.after_blank = False
    return index + 1, ""


def _fence_end(lines: list[str], index: int, opening: str) -> int:
    for close in range(index + 1, len(lines)):
        match = _FENCE_CLOSE_RE.match(lines[close].rstrip("\n"))
        if match and match["fence"][0] == opening[0] and len(match["fence"]) >= len(opening):
            return close + 1
    return len(lines)


def _indented_end(lines: list[str], index: int) -> int:
    """The line after an indented block: its last indented line, trailing blanks excluded."""
    last = index
    for probe in range(index + 1, len(lines)):
        line = lines[probe].rstrip("\n")
        if not line.strip():
            continue
        if _indent(line) < _CODE_INDENT:
            break
        last = probe
    return last + 1


def _indent(line: str) -> int:
    columns = 0
    for char in line:
        if char == " ":
            columns += 1
        elif char == "\t":
            columns += _TAB_WIDTH - columns % _TAB_WIDTH
        else:
            break
    return columns


def block_breaks(markdown: str) -> list[int]:
    """The line starts where a new block begins, sorted: no inline construct crosses one.

    A block begins on the line after a blank line, and at a list item, a
    heading, a table row, or the first line of a block quote.
    """
    breaks: list[int] = []
    previous = ""
    position = 0
    for line in markdown.splitlines(keepends=True):
        if position and (not previous.strip() or _starts_own_block(line, previous)):
            breaks.append(position)
        previous = line
        position += len(line)
    return breaks


def _starts_own_block(line: str, previous: str) -> bool:
    if _QUOTE_RE.match(line):
        return not _QUOTE_RE.match(previous)
    return _OWN_BLOCK_RE.match(line) is not None


def _code_spans(markdown: str, start: int, end: int, breaks: list[int]) -> list[CodeRegion]:
    """The code spans between *start* and *end*, which hold no block of code."""
    spans: list[CodeRegion] = []
    position = start
    while True:
        opening = _BACKTICKS_RE.search(markdown, position, end)
        if opening is None:
            return spans
        if is_escaped(markdown, opening.start()):
            position = opening.start() + 1
            continue
        closing = _partner(markdown, opening, end, breaks)
        if closing is None:
            position = opening.end()
            continue
        spans.append(CodeRegion(opening.start(), closing, "code_span"))
        position = closing


def _partner(markdown: str, opening: re.Match[str], end: int, breaks: list[int]) -> int | None:
    """Where the span *opening* starts closes, or ``None`` when it closes nowhere."""
    length = len(opening.group())
    position = opening.end()
    next_break = bisect.bisect_right(breaks, opening.end())
    limit = min(end, breaks[next_break]) if next_break < len(breaks) else end
    while True:
        run = _BACKTICKS_RE.search(markdown, position, limit)
        if run is None:
            return None
        if len(run.group()) == length:
            return run.end()
        position = run.end()


def is_escaped(markdown: str, index: int) -> bool:
    """Whether the character at *index* is escaped by an odd run of backslashes."""
    backslashes = 0
    while index - backslashes - 1 >= 0 and markdown[index - backslashes - 1] == "\\":
        backslashes += 1
    return backslashes % 2 == 1
