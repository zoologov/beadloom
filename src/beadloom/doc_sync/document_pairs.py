# beadloom:domain=doc-sync
# beadloom:feature=document-pairs
"""A declared pair of documents, compared by SHAPE and never by text.

This repository ships ``README.md`` and ``README.ru.md`` and nothing held them
against each other. On 2026-09-10 the Russian file carried a paragraph the
English file had folded into its neighbour, and an opening sentence the English
file did not have at all. The only number that differed between the two files
was a line count — 362 against 360 — which nothing reads and which a translator
wrapping two sentences differently moves by the same amount. The drift was found
by a person reading the files side by side.

**Only the shape is comparable, because the files are in two languages.** A text
comparison over a translation is a check that has to be switched off, and a
check somebody switches off is the defect class this module was written under
(BDL-069). What survives translation is the sequence of blocks a document is
built from — heading, paragraph, code, list, table — with the heading levels and
the row counts of the lists and the tables. A paragraph that exists in one
language and not the other changes that sequence and is reported; a paragraph
the translator wrapped over three lines instead of two does not.

**The pair is DECLARED, never guessed.** An adopter's translated README is their
business and a check that assumes ``README.<lang>.md`` would turn somebody's
green tree red on the upgrade that ships it. The declaration is modelled on
``issue_log:`` — a block in ``.beadloom/config.yml``, absent by default, and a
project that declares none is not judged.

**The table reading is not this module's.** ``doc_sync.tables`` already answers
what a table row is and where one table ends, and two answers to that question
is how one section holding two tables was read as one, twice (BDL-UX #213,
#244). This module is a caller of it, not a fifth reader of markdown.

What it does NOT compare, and the reason in each case:

* the line count of a paragraph or of a code block — line wrapping is a property
  of the text, and a translated sample of a command's output can legitimately
  differ in length;
* the prose itself, in any form;
* a blockquote and a thematic break, which read as paragraph blocks. The check
  reports five kinds, and both are one-line blocks whose PRESENCE is still
  compared — what is lost is a paragraph rewritten as a quote in one language
  only.

A finding names the position at which the two sequences diverge, and the heading
it stands under. It cannot name WHICH of several indistinguishable paragraphs
went missing — they have the same shape, which is the whole reason the check can
compare across languages — so the heading is what tells a reader where to look.
"""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.doc_sync.tables import cells_of, table_blocks

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The ``.beadloom/config.yml`` block that declares the pairs. A project that
#: declares none is not judged: nothing here guesses a filename.
CONFIG_KEY = "document_pairs"
SOURCE_KEY = "source"
FOLLOWER_KEY = "follower"

#: The five block kinds. A document is a sequence of these, and that sequence is
#: the only thing compared across two languages.
HEADING = "heading"
PARAGRAPH = "paragraph"
CODE = "code"
LIST = "list"
TABLE = "table"

BLOCK_KINDS: tuple[str, ...] = (HEADING, PARAGRAPH, CODE, LIST, TABLE)

#: A block one file has and the other does not.
UNPAIRED_BLOCK = "unpaired-block"
#: Two blocks that face each other and are of different kinds, or two headings
#: at different levels.
BLOCK_KIND = "block-kind"
#: Two aligned lists or tables whose row counts differ.
ROW_COUNT = "row-count"

#: Every check, in report order. One list, so a summary counting findings per
#: check cannot silently omit one.
CHECK_NAMES: tuple[str, ...] = (UNPAIRED_BLOCK, BLOCK_KIND, ROW_COUNT)

#: Only these two kinds carry a row count worth comparing. A paragraph's line
#: count is a wrapping decision and a code block's can differ with the sample.
_COUNTED_KINDS: frozenset[str] = frozenset({LIST, TABLE})

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s+")


@dataclass(frozen=True)
class Block:
    """One block of a document: what it is, where it starts, how big it is.

    ``rows`` counts list items and table data rows — the two sizes that survive
    translation. For a paragraph it is the line count and for a code block the
    number of lines inside the fence; both are recorded because a report reads
    better with them, and neither is compared.
    """

    kind: str
    line: int
    rows: int = 1
    level: int = 0
    title: str = ""

    @property
    def signature(self) -> tuple[str, int]:
        """What the two sequences are aligned on: the kind and, for a heading, its level."""
        return (self.kind, self.level)


@dataclass(frozen=True)
class DocumentPair:
    """A declared pair: the source of truth and the document that follows it."""

    source: Path
    follower: Path


@dataclass(frozen=True)
class Finding:
    """One divergence, named against both files and the heading it sits under."""

    check: str
    kind: str
    source_line: int | None
    follower_line: int | None
    section: str
    detail: str


@dataclass(frozen=True)
class Comparison:
    """The result of comparing two block sequences, with the population it read."""

    source_blocks: int
    follower_blocks: int
    compared: int
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class PairComparison:
    """One declared pair's comparison, or the reason it could not be made."""

    pair: DocumentPair
    source_blocks: int
    follower_blocks: int
    compared: int
    findings: tuple[Finding, ...]
    unreadable: tuple[str, ...]


@dataclass(frozen=True)
class PairReport:
    """Every declared pair, what was compared, and what was not read.

    ``declared`` is false for a project that declares no pair, which is the
    state every adopter is in until they opt in. A caller renders that as a
    skip with a reason rather than as a pass.
    """

    declared: bool
    comparisons: tuple[PairComparison, ...]

    @property
    def findings(self) -> tuple[Finding, ...]:
        return tuple(f for comparison in self.comparisons for f in comparison.findings)

    @property
    def compared(self) -> int:
        """How many block pairs the whole report compared."""
        return sum(comparison.compared for comparison in self.comparisons)

    @property
    def unreadable(self) -> tuple[str, ...]:
        """Every declared path that could not be read, in declaration order."""
        return tuple(path for comparison in self.comparisons for path in comparison.unreadable)


# ---------------------------------------------------------------------------
# The block reader
# ---------------------------------------------------------------------------


def read_blocks(text: str) -> tuple[Block, ...]:
    """*text* as its sequence of blocks.

    A blank line ends a block, and so does a line of a different kind. A fenced
    block is opaque: a ``#`` inside it is a comment in somebody's shell session
    and not a heading, which is the one lookalike a shape comparison would
    otherwise trip over on this project's own READMEs.
    """
    reader = _BlockReader()
    for number, line in enumerate(text.splitlines(), start=1):
        reader.feed(number, line)
    return reader.finish()


class _BlockReader:
    """The state one pass over a document needs, kept out of the free function.

    Two states only: inside a fence or not. Everything else is decided from the
    current line and the kind of the block being accumulated.
    """

    def __init__(self) -> None:
        self._blocks: list[Block] = []
        self._kind: str | None = None
        self._start = 0
        self._rows = 0
        self._fence: str | None = None
        self._table_lines: list[tuple[int, str]] = []

    def feed(self, number: int, line: str) -> None:
        if self._fence is not None:
            self._feed_inside_fence(number, line)
            return
        fence = _FENCE_RE.match(line)
        if fence is not None:
            self._flush()
            self._fence = fence.group(1)
            self._kind = CODE
            self._start = number
            self._rows = 0
            return
        if not line.strip():
            self._flush()
            return
        heading = _HEADING_RE.match(line)
        if heading is not None:
            self._flush()
            self._blocks.append(
                Block(
                    kind=HEADING,
                    line=number,
                    rows=1,
                    level=len(heading.group(1)),
                    title=heading.group(2),
                )
            )
            return
        self._feed_body(number, line)

    def _feed_inside_fence(self, number: int, line: str) -> None:
        fence = _FENCE_RE.match(line)
        if fence is not None and fence.group(1) == self._fence:
            self._fence = None
            self._flush()
            return
        self._rows += 1

    def _feed_body(self, number: int, line: str) -> None:
        kind = self._kind_of(line)
        if self._kind is not None and kind != self._kind:
            self._flush()
        if self._kind is None:
            self._kind = kind
            self._start = number
            self._rows = 0
        if kind == TABLE:
            self._table_lines.append((number, line))
        elif kind == LIST and _LIST_ITEM_RE.match(line) is None:
            # An indented continuation of the item above: part of the list, not
            # a row of it.
            return
        else:
            self._rows += 1

    def _kind_of(self, line: str) -> str:
        if cells_of(line) is not None:
            return TABLE
        if _LIST_ITEM_RE.match(line) is not None:
            return LIST
        if self._kind == LIST and line[:1].isspace():
            return LIST
        return PARAGRAPH

    def _flush(self) -> None:
        if self._kind is None:
            return
        rows = self._rows
        if self._kind == TABLE:
            tables = table_blocks(self._table_lines)
            rows = sum(len(table) for table in tables)
            self._table_lines = []
        self._blocks.append(Block(kind=self._kind, line=self._start, rows=rows))
        self._kind = None
        self._rows = 0

    def finish(self) -> tuple[Block, ...]:
        """Every block, the last one closed even when its fence never was."""
        self._fence = None
        self._flush()
        return tuple(self._blocks)


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------


def compare_documents(source: Sequence[Block], follower: Sequence[Block]) -> Comparison:
    """*source* and *follower* aligned by shape, with the population compared.

    The alignment is :class:`difflib.SequenceMatcher` over block signatures. It
    reports where the sequences diverge, which is not the same as which of
    several identical-looking paragraphs went missing — nothing can tell those
    apart, and a finding says where to look by naming the heading it is under.
    """
    matcher = difflib.SequenceMatcher(
        a=[block.signature for block in source],
        b=[block.signature for block in follower],
        autojunk=False,
    )
    findings: list[Finding] = []
    compared = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            compared += i2 - i1
            findings.extend(_row_count_findings(source, follower, i1, i2, j1))
            continue
        if tag == "replace":
            paired = min(i2 - i1, j2 - j1)
            compared += paired
            findings.extend(_kind_findings(source, follower, i1, j1, paired))
            findings.extend(_unpaired(source, i1 + paired, i2, follower_side=False))
            findings.extend(_unpaired(follower, j1 + paired, j2, follower_side=True))
            continue
        if tag == "delete":
            findings.extend(_unpaired(source, i1, i2, follower_side=False))
        elif tag == "insert":
            findings.extend(_unpaired(follower, j1, j2, follower_side=True))
    return Comparison(
        source_blocks=len(source),
        follower_blocks=len(follower),
        compared=compared,
        findings=tuple(findings),
    )


def _section_of(blocks: Sequence[Block], index: int) -> str:
    """The nearest heading at or before *index*, or an empty string above the first."""
    for position in range(min(index, len(blocks) - 1), -1, -1):
        block = blocks[position]
        if block.kind == HEADING:
            return block.title
    return ""


def _row_count_findings(
    source: Sequence[Block], follower: Sequence[Block], i1: int, i2: int, j1: int
) -> Iterable[Finding]:
    for offset in range(i2 - i1):
        left = source[i1 + offset]
        right = follower[j1 + offset]
        if left.kind not in _COUNTED_KINDS or left.rows == right.rows:
            continue
        yield Finding(
            check=ROW_COUNT,
            kind=left.kind,
            source_line=left.line,
            follower_line=right.line,
            section=_section_of(source, i1 + offset),
            detail=f"{left.kind}: {left.rows} row(s) in the source, {right.rows} in the follower",
        )


def _kind_findings(
    source: Sequence[Block], follower: Sequence[Block], i1: int, j1: int, paired: int
) -> Iterable[Finding]:
    for offset in range(paired):
        left = source[i1 + offset]
        right = follower[j1 + offset]
        yield Finding(
            check=BLOCK_KIND,
            kind=left.kind,
            source_line=left.line,
            follower_line=right.line,
            section=_section_of(source, i1 + offset),
            detail=(
                f"{_describe(left)} in the source faces {_describe(right)} in the follower"
            ),
        )


def _unpaired(
    blocks: Sequence[Block], start: int, stop: int, *, follower_side: bool
) -> Iterable[Finding]:
    side = "follower" if follower_side else "source"
    for index in range(start, stop):
        block = blocks[index]
        yield Finding(
            check=UNPAIRED_BLOCK,
            kind=block.kind,
            source_line=None if follower_side else block.line,
            follower_line=block.line if follower_side else None,
            section=_section_of(blocks, index),
            detail=f"{_describe(block)} in the {side} faces nothing on the other side",
        )


def _describe(block: Block) -> str:
    if block.kind == HEADING:
        return f"a level-{block.level} heading"
    return f"a {block.kind}"


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------


def resolve_document_pairs(project_root: Path) -> tuple[DocumentPair, ...]:
    """The pairs the project declares, or an empty tuple when it declares none.

    A half-written entry is refused rather than completed by a guess: the whole
    point of the declaration is that no filename is assumed.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.is_file():
        return ()
    import yaml

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        logger.warning("Failed to read .beadloom/config.yml for %s", CONFIG_KEY)
        return ()
    if not isinstance(data, dict):
        return ()
    block = data.get(CONFIG_KEY)
    if not isinstance(block, list):
        return ()
    pairs: list[DocumentPair] = []
    for entry in block:
        pair = _pair_from(project_root, entry)
        if pair is not None:
            pairs.append(pair)
    return tuple(pairs)


def _pair_from(project_root: Path, entry: object) -> DocumentPair | None:
    if not isinstance(entry, dict):
        logger.warning("%s: each entry needs %r and %r", CONFIG_KEY, SOURCE_KEY, FOLLOWER_KEY)
        return None
    source = entry.get(SOURCE_KEY)
    follower = entry.get(FOLLOWER_KEY)
    if not isinstance(source, str) or not isinstance(follower, str):
        logger.warning("%s: each entry needs %r and %r", CONFIG_KEY, SOURCE_KEY, FOLLOWER_KEY)
        return None
    resolved = _inside(project_root, source), _inside(project_root, follower)
    if resolved[0] is None or resolved[1] is None:
        logger.warning("%s: %r and %r must be inside the project", CONFIG_KEY, source, follower)
        return None
    return DocumentPair(source=resolved[0], follower=resolved[1])


def _inside(project_root: Path, declared: str) -> Path | None:
    """*declared* under *project_root*, or ``None`` when it points outside it."""
    candidate = project_root / declared
    try:
        candidate.resolve().relative_to(project_root.resolve())
    except ValueError:
        return None
    return candidate


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------


def check_document_pairs(project_root: Path) -> PairReport:
    """Compare every declared pair, and say what was compared and what was not read."""
    pairs = resolve_document_pairs(project_root)
    if not pairs:
        return PairReport(declared=False, comparisons=())
    return PairReport(
        declared=True,
        comparisons=tuple(_compare_pair(project_root, pair) for pair in pairs),
    )


def _compare_pair(project_root: Path, pair: DocumentPair) -> PairComparison:
    source_text = _read(pair.source)
    follower_text = _read(pair.follower)
    unreadable = tuple(
        _relative(project_root, path)
        for path, text in ((pair.source, source_text), (pair.follower, follower_text))
        if text is None
    )
    if source_text is None or follower_text is None:
        return PairComparison(
            pair=pair,
            source_blocks=0,
            follower_blocks=0,
            compared=0,
            findings=(),
            unreadable=unreadable,
        )
    result = compare_documents(read_blocks(source_text), read_blocks(follower_text))
    return PairComparison(
        pair=pair,
        source_blocks=result.source_blocks,
        follower_blocks=result.follower_blocks,
        compared=result.compared,
        findings=result.findings,
        unreadable=(),
    )


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)
