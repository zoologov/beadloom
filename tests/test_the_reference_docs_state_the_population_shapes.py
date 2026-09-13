"""Every published document that states a parsed population shape states the emitted one.

BDL-070 `beadloom-5tcc.9`. The module this one replaces read `docs/services/cli.md`
and nothing else — the file the class was first found in — so it was green while the
same defect sat one directory away, twice: `docs/services/mcp.md` and the rule-engine
SPEC both promised "the same eight keys" after Release B had left five. A guard whose
population is one file is the defect this epic exists to remove, written into the
instrument against it.

Two shapes are machine-read rather than prose: the keys under
`summary.layer_populations[]` in `lint --format json`, and the marked record that leads
`--format porcelain`. A consumer that split the porcelain record on `:` and read field 7
got the skipped count where the document promised it the inherited one.

**The population is derived, not listed.** Every Markdown file under `docs/`, plus the
README pair, is scanned; a document enters the population by STATING one of the two
shapes — by enumerating the keys, by counting them ("the same eight keys"), or by
writing a porcelain template. A reference added tomorrow is covered without anyone
editing this module, which is the property the one-file version did not have.

**Dated records are outside it, with a reason.** `CHANGELOG.md` and the work-item
documents under `.claude/development/` describe the shape of releases that are over — a
superseded shape is correct there by construction, and checking it against today's code
would fail the sentence that records the supersession. `POPULATION_PHRASE` states that
exclusion beside the count, so the population this module ran over is readable rather
than assumed.

Every expectation is DERIVED from the code — the key set from `LayerReach.to_dict`, the
field count from the line `format_porcelain` really emits — so this module cannot pass by
agreeing with a second copy of a document's own claim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.linter import POPULATION_MARKER, LintResult, format_porcelain
from beadloom.graph.rules.layer_reach import LayerReach
from beadloom.graph.rules.layers import LayerPopulation

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The published reference tree, walked rather than enumerated.
DOCS_ROOT = REPO_ROOT / "docs"

#: The README pair ships to a reader as reference too, so it is in the population
#: even on the day neither file states a shape.
README_PAIR = (REPO_ROOT / "README.md", REPO_ROOT / "README.ru.md")

#: Named so the phrase below can say what this module did not read.
DATED_RECORDS = ("CHANGELOG.md", ".claude/development/")

#: A reach with this repository's own counts. Only its SHAPE is used — the numbers
#: move with the graph, and a guard that failed when an edge was added would be a
#: second defect rather than a check.
_A_REACH = LayerReach(
    rule_name="architecture-layers",
    edge_kind="depends_on",
    population=LayerPopulation(evaluated=357, skipped_untagged=8),
)

#: How far after a mention of `layer_populations` a claim about its keys is taken to
#: belong to that mention. Bounded twice: by the block the mention sits in (a table row
#: is one record, a paragraph is one thought) and by this distance, so a later sentence
#: naming other keys is not read as this claim.
_CLAIM_WINDOW = 200

_MENTION = re.compile(r"layer_populations")

#: Two or more backticked bare identifiers in a row — the shape of an enumerated key
#: list. A dotted or hyphenated token (`LintResult.fails_on_warn`, `--fail-on-warn`) is
#: not a key name and does not join a run.
_ENUMERATION = re.compile(r"`[a-z][a-z_]*`(?:\s*(?:,|and|or)\s*`[a-z][a-z_]*`)+")

_AN_IDENTIFIER = re.compile(r"`([a-z][a-z_]*)`")

#: A key list stated as a count rather than by name — how both stale documents stated it.
_CARDINALITY = re.compile(
    r"\b(?P<count>one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d+)"
    r"\s+keys\b"
)

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

_PORCELAIN_TEMPLATE = re.compile(
    rf"`{re.escape(POPULATION_MARKER)}layer_population:(?P<rest>[^`]+)`"
)

#: A record written with its tail elided states no field count, so it is not a claim.
_ABBREVIATIONS = ("…", "...")

#: A segment that could be a placeholder name — a value (`architecture-layers`, `357`)
#: cannot, which is how a concrete sample is told from a template.
_A_PLACEHOLDER_NAME = re.compile(r"^[a-z][a-z_]*$")


def _number(word: str) -> int:
    return _NUMBER_WORDS.get(word, 0) or int(word)


@dataclass(frozen=True)
class Site:
    """Where a claim is written, in the form a reader opens."""

    document: Path
    line: int

    def __str__(self) -> str:
        return f"{self.document.relative_to(REPO_ROOT)}:{self.line}"


@dataclass(frozen=True)
class KeyListClaim:
    """A document's statement of what keys `summary.layer_populations[]` carries."""

    site: Site
    quote: str
    #: The names, when the document enumerates them; `None` when it only counts them.
    keys: tuple[str, ...] | None
    count: int


@dataclass(frozen=True)
class PorcelainClaim:
    """A documented `# layer_population:…` record — template or concrete sample."""

    site: Site
    quote: str
    fields: tuple[str, ...]

    @property
    def is_template(self) -> bool:
        return all(_A_PLACEHOLDER_NAME.match(field.strip("<>")) for field in self.fields[1:])


def _documents() -> list[Path]:
    """The published reference set, derived by walking it."""
    return sorted(DOCS_ROOT.rglob("*.md")) + [p for p in README_PAIR if p.exists()]


@dataclass(frozen=True)
class Block:
    """A table row or a paragraph, and the lines its characters came from.

    The line matters: a finding that names the paragraph a claim starts in sends a
    reader to the wrong sentence of a forty-line bullet list.
    """

    text: str
    #: `(offset, line)` for each source line, in order.
    origins: tuple[tuple[int, int], ...]

    def line_at(self, offset: int) -> int:
        line = self.origins[0][1]
        for start, number in self.origins:
            if start > offset:
                break
            line = number
        return line


def _blocks(text: str) -> Iterator[Block]:
    """Every table row and every paragraph of a document.

    A table row is its own block because a row is one record: a claim in one cell must
    not be read as a claim about the row below it. A paragraph is joined into one line
    so that a claim wrapped at 95 columns is still read as one sentence.
    """
    parts: list[str] = []
    origins: list[tuple[int, int]] = []
    width = 0

    def flush() -> Iterator[Block]:
        if parts:
            yield Block(" ".join(parts), tuple(origins))

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        is_row = line.startswith("|")
        if is_row or not line:
            yield from flush()
            parts, origins, width = [], [], 0
            if is_row:
                yield Block(line, ((0, number),))
            continue
        origins.append((width, number))
        parts.append(line)
        width += len(line) + 1
    yield from flush()


def _quote(block: Block, at: int) -> str:
    return block.text[max(0, at - 40) : at + _CLAIM_WINDOW].strip()


def _is_a_key_list(introduction: str, names: tuple[str, ...]) -> bool:
    """Whether a run of identifiers after a mention is that mention's key list.

    Two ways to be one, because prose has two. Either the run is APPOSED to the
    mention — introduced by a dash, a colon, or the word "keys" — or it names at least
    one key the code emits. Neither alone is enough: rule-engine SPEC:992 enumerates
    `inert_rule_names` and `suppressed_crossings` one clause after a mention of
    `LintResult.layer_populations`, and that is what it is counted BESIDE rather than
    what it carries.
    """
    apposed = any(mark in introduction for mark in ("—", "--", ":", "keys"))
    return apposed or bool(set(names) & set(_A_REACH.to_dict()))


def _key_list_claims(document: Path, text: str) -> list[KeyListClaim]:
    claims: list[KeyListClaim] = []
    for block in _blocks(text):
        for mention in _MENTION.finditer(block.text):
            window = block.text[mention.end() : mention.end() + _CLAIM_WINDOW]
            site = Site(document, block.line_at(mention.start()))
            quote = _quote(block, mention.start())
            enumeration = _ENUMERATION.search(window)
            if enumeration is not None:
                names = tuple(_AN_IDENTIFIER.findall(enumeration.group()))
                if _is_a_key_list(window[: enumeration.start()], names):
                    claims.append(KeyListClaim(site, quote, names, len(names)))
            cardinality = _CARDINALITY.search(window)
            if cardinality is not None:
                claims.append(KeyListClaim(site, quote, None, _number(cardinality.group("count"))))
    return claims


def _porcelain_claims(document: Path, text: str) -> list[PorcelainClaim]:
    claims: list[PorcelainClaim] = []
    for block in _blocks(text):
        for match in _PORCELAIN_TEMPLATE.finditer(block.text):
            rest = match.group("rest")
            if any(mark in rest for mark in _ABBREVIATIONS):
                continue
            fields = ("layer_population", *rest.split(":"))
            site = Site(document, block.line_at(match.start()))
            claims.append(PorcelainClaim(site, rest, fields))
    return claims


@dataclass(frozen=True)
class Population:
    """What this module read, so a green run is a measurement and not a silence."""

    documents: tuple[Path, ...]
    key_lists: tuple[KeyListClaim, ...]
    porcelain: tuple[PorcelainClaim, ...]

    @property
    def stating(self) -> tuple[Path, ...]:
        claimed = {claim.site.document for claim in self.key_lists}
        claimed |= {claim.site.document for claim in self.porcelain}
        return tuple(sorted(claimed))

    @property
    def phrase(self) -> str:
        stating = ", ".join(str(p.relative_to(REPO_ROOT)) for p in self.stating)
        return (
            f"read {len(self.documents)} published document(s) under "
            f"{DOCS_ROOT.name}/ and the README pair; {len(self.stating)} state a shape "
            f"({stating or 'none'}), over {len(self.key_lists)} key-list claim(s) and "
            f"{len(self.porcelain)} porcelain record(s). Outside this population: "
            f"{', '.join(DATED_RECORDS)} — a superseded shape is correct in a record of "
            "the release that superseded it"
        )


def _derive_population() -> Population:
    documents = _documents()
    key_lists: list[KeyListClaim] = []
    porcelain: list[PorcelainClaim] = []
    for document in documents:
        text = document.read_text(encoding="utf-8")
        key_lists.extend(_key_list_claims(document, text))
        porcelain.extend(_porcelain_claims(document, text))
    return Population(tuple(documents), tuple(key_lists), tuple(porcelain))


POPULATION = _derive_population()


def _emitted_keys() -> list[str]:
    return list(_A_REACH.to_dict())


def _emitted_porcelain_fields() -> list[str]:
    porcelain = format_porcelain(LintResult(layer_populations=[_A_REACH]))
    marked = [line for line in porcelain.splitlines() if line.startswith(POPULATION_MARKER)]
    assert len(marked) == 1, f"expected one marked population line, got {marked!r}"
    return marked[0].removeprefix(POPULATION_MARKER).split(":")


class TestThePopulationIsEveryDocumentThatStatesAShape:
    """The widening itself, asserted — a one-file guard is the defect, not the check."""

    def test_more_than_one_document_is_read_for_the_shapes(self) -> None:
        assert len(POPULATION.stating) > 1, (
            "this guard is back to a single document, which is how the same stale key "
            f"list survived in two files; {POPULATION.phrase}"
        )

    def test_the_key_list_is_stated_somewhere_at_all(self) -> None:
        assert POPULATION.key_lists, (
            "no published document states what keys summary.layer_populations[] "
            f"carries; the contract is parsed by consumers, so state it. {POPULATION.phrase}"
        )

    def test_the_porcelain_record_is_stated_somewhere_at_all(self) -> None:
        assert POPULATION.porcelain, (
            f"no published document shows the porcelain population record; {POPULATION.phrase}"
        )

    def test_the_population_is_recorded_with_the_run(
        self, record_property: Callable[[str, object], None]
    ) -> None:
        """The phrase travels with the result, so a green names what it covered."""
        record_property("layer_population_docs", POPULATION.phrase)
        assert POPULATION.documents, f"no published document was read: {POPULATION.phrase}"


@pytest.mark.parametrize(
    "claim",
    POPULATION.key_lists,
    ids=[f"{claim.site}" for claim in POPULATION.key_lists],
)
def test_a_documented_key_list_is_the_key_list_the_code_emits(claim: KeyListClaim) -> None:
    """`summary.layer_populations[]` — named one by one, because a consumer reads a name."""
    emitted = _emitted_keys()
    if claim.keys is not None:
        assert list(claim.keys) == emitted, (
            f"{claim.site} documents {list(claim.keys)} for summary.layer_populations[]; "
            f"LayerReach.to_dict emits {emitted}. Quote: {claim.quote!r}. "
            f"{POPULATION.phrase}"
        )
    assert claim.count == len(emitted), (
        f"{claim.site} states {claim.count} key(s) for summary.layer_populations[]; "
        f"LayerReach.to_dict emits {len(emitted)} ({emitted}). Quote: {claim.quote!r}. "
        f"{POPULATION.phrase}"
    )


@pytest.mark.parametrize(
    "claim",
    POPULATION.porcelain,
    ids=[f"{claim.site}" for claim in POPULATION.porcelain],
)
def test_a_documented_porcelain_record_has_the_emitted_shape(claim: PorcelainClaim) -> None:
    """The marked line a consumer splits on `:`."""
    emitted = _emitted_porcelain_fields()

    assert len(claim.fields) == len(emitted), (
        f"{claim.site} documents {len(claim.fields)} colon-separated fields "
        f"({list(claim.fields)}); format_porcelain emits {len(emitted)} ({emitted}). "
        f"{POPULATION.phrase}"
    )

    if claim.is_template:
        placeholders = [field.strip("<>") for field in claim.fields[1:]]
        keys = _emitted_keys()
        assert placeholders[: len(keys) - 1] == keys[:-1], (
            f"{claim.site} documents placeholders {placeholders}; the emitted record "
            f"carries {keys}. {POPULATION.phrase}"
        )
    else:
        counts = list(claim.fields[-3:])
        assert all(field.isdigit() for field in counts), (
            f"{claim.site} shows a sample record whose last three fields are {counts}; "
            f"format_porcelain emits evaluated, total and skipped there. "
            f"{POPULATION.phrase}"
        )
