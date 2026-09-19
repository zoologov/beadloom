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

**The population is derived, not listed.** Every Markdown file under `docs/`, the README
pair, `.beadloom/AGENTS.md` and every `*.md.txt` role and command template under
`src/beadloom/onboarding/templates/` is scanned; a document enters the population by
STATING one of the two shapes in one of five forms — inline, by enumerating the keys in
backticks, by counting them ("the same eight keys"), or by writing a backticked porcelain
record; fenced, as a JSON object carrying the emitted keys or a line opening
`# layer_population:`. A reference added tomorrow under those roots, in one of those
forms, is covered without anyone editing this module, which is the property the one-file
version did not have. A shape stated in any other form — a table of keys, key names
without backticks — is NOT read, and `POPULATION.phrase` says so beside the counts. The
templates joined the population in B7 (`beadloom-57wl`), after a claim about the layer
rule was found in one that no walk of `docs/` could reach.

**Dated records are outside it, with a reason.** `CHANGELOG.md` and the work-item
documents under `.claude/development/` describe the shape of releases that are over — a
superseded shape is correct there by construction, and checking it against today's code
would fail the sentence that records the supersession. `POPULATION.phrase` states that
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
from tests.package_under_test import PACKAGE_ROOT

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The published reference tree, walked rather than enumerated.
DOCS_ROOT = REPO_ROOT / "docs"

#: The README pair ships to a reader as reference too, so it is in the population
#: even on the day neither file states a shape.
README_PAIR = (REPO_ROOT / "README.md", REPO_ROOT / "README.ru.md")

#: The role and command templates every adopter's agent is composed from. They are
#: reference an agent acts on, and B7 (`beadloom-57wl`) found a claim about the layer
#: rule in one of them that no walk of `docs/` could reach.
#: Derived from the IMPORTED package rather than from this file: under
#: `mutmut run` the suite is copied beside the mutated sources, so a root built
#: from `__file__` answers about the copy (BDL-UX #289). This walk reads
#: `*.md.txt`, which mutmut copies rather than mutates, so the move keeps the
#: population identical and removes the shape.
TEMPLATES_ROOT = PACKAGE_ROOT / "onboarding" / "templates"

#: The agent-facing summary `beadloom setup-rules` writes, committed in this repository.
AGENTS_MD = REPO_ROOT / ".beadloom" / "AGENTS.md"

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
    named = [p for p in (*README_PAIR, AGENTS_MD) if p.exists()]
    return sorted(DOCS_ROOT.rglob("*.md")) + named + sorted(TEMPLATES_ROOT.rglob("*.md.txt"))


def _fences(text: str) -> Iterator[tuple[tuple[int, str], ...]]:
    """The content lines of every fenced code block, each with its line number."""
    inside = False
    lines: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if raw.lstrip().startswith(("```", "~~~")):
            if inside:
                yield tuple(lines)
                lines = []
            inside = not inside
            continue
        if inside:
            lines.append((number, raw))


#: A flat JSON object — the innermost braces, which is where a population entry sits.
_FLAT_OBJECT = re.compile(r"\{[^{}]*\}")

_A_JSON_KEY = re.compile(r'"([a-z][a-z_]*)"\s*:')

#: How many emitted keys other than `rule` a fenced object must carry to be read as a
#: population entry. `rule` alone is every finding object's key too.
_SHARED_KEYS_FOR_AN_ENTRY = 2


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
    return claims + _fenced_key_list_claims(document, text)


def _fenced_key_list_claims(document: Path, text: str) -> list[KeyListClaim]:
    """A JSON sample in a code block whose flat object carries the emitted keys."""
    distinctive = set(_A_REACH.to_dict()) - {"rule"}
    claims: list[KeyListClaim] = []
    for fence in _fences(text):
        joined = "\n".join(raw for _, raw in fence)
        for match in _FLAT_OBJECT.finditer(joined):
            keys = tuple(_A_JSON_KEY.findall(match.group()))
            if len(distinctive & set(keys)) < _SHARED_KEYS_FOR_AN_ENTRY:
                continue
            line = fence[joined.count("\n", 0, match.start())][0]
            site = Site(document, line)
            claims.append(KeyListClaim(site, match.group().strip(), keys, len(keys)))
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
    return claims + _fenced_porcelain_claims(document, text)


def _fenced_porcelain_claims(document: Path, text: str) -> list[PorcelainClaim]:
    """A record shown as output in a code block — a line, not a backticked span."""
    lead = f"{POPULATION_MARKER}layer_population:"
    claims: list[PorcelainClaim] = []
    for fence in _fences(text):
        for number, raw in fence:
            line = raw.strip()
            if not line.startswith(lead):
                continue
            rest = line.removeprefix(lead)
            if any(mark in rest for mark in _ABBREVIATIONS):
                continue
            fields = ("layer_population", *rest.split(":"))
            claims.append(PorcelainClaim(Site(document, number), rest, fields))
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
        templates = sum(1 for p in self.documents if TEMPLATES_ROOT in p.parents)
        return (
            f"read {len(self.documents)} document(s): every *.md under "
            f"{DOCS_ROOT.name}/, the README pair, {AGENTS_MD.relative_to(REPO_ROOT)} and "
            f"{templates} *.md.txt template(s) under "
            f"{TEMPLATES_ROOT.relative_to(REPO_ROOT)}/. {len(self.stating)} state a shape "
            f"in a form this module reads ({stating or 'none'}), over "
            f"{len(self.key_lists)} key-list claim(s) and {len(self.porcelain)} porcelain "
            "record(s). Five forms are read: an inline backticked key list, an inline "
            "count of keys, an inline backticked porcelain record, a fenced JSON object "
            "carrying two emitted keys besides rule, and a fenced line opening "
            "'# layer_population:'. A shape stated any other way — a table of keys, key "
            "names without backticks — is not read. Outside this population: "
            f"{', '.join(DATED_RECORDS)} — a superseded shape is correct in a record of "
            "the release that superseded it — and the composed .claude/ copies, which "
            "test_live_flow_equals_its_composition holds to the templates"
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

    def test_the_shipped_templates_and_the_agents_file_are_read(self) -> None:
        """What ships to an adopter's agent is reference too, and B7 found claims there."""
        read = set(POPULATION.documents)
        assert REPO_ROOT / ".beadloom" / "AGENTS.md" in read, POPULATION.phrase
        assert any(TEMPLATES_ROOT in path.parents for path in read), POPULATION.phrase

    def test_the_phrase_names_the_forms_it_reads_and_the_roots_it_walked(self) -> None:
        """A population statement that omits its own limit is the claim this epic retires."""
        phrase = POPULATION.phrase
        assert "src/beadloom/onboarding/templates/" in phrase
        assert ".beadloom/AGENTS.md" in phrase
        assert "fenced" in phrase
        assert "not read" in phrase


_FENCE = "```"


class TestTheReaderSeesAFencedSample:
    """A sample in a code block is how a document most often shows output."""

    def test_a_fenced_porcelain_record_is_a_claim(self) -> None:
        text = f"Prose.\n\n{_FENCE}text\n# layer_population:r:depends_on:1:2:1:9\n{_FENCE}\n"
        claims = _porcelain_claims(Path("x.md"), text)
        assert [claim.fields for claim in claims] == [
            ("layer_population", "r", "depends_on", "1", "2", "1", "9")
        ]
        assert claims[0].site.line == 4

    def test_a_fenced_record_with_its_tail_elided_is_not_a_claim(self) -> None:
        text = f"{_FENCE}\n# layer_population:r:depends_on:…\n{_FENCE}\n"
        assert _porcelain_claims(Path("x.md"), text) == []

    def test_a_porcelain_record_outside_a_fence_is_not_read_by_the_fenced_form(self) -> None:
        """A Markdown heading that happens to start the same way is not a record."""
        assert _porcelain_claims(Path("x.md"), "# layer_population:r:d:1:2:3\n") == []

    def test_a_fenced_json_object_carrying_emitted_keys_is_a_key_list_claim(self) -> None:
        text = (
            f"{_FENCE}json\n"
            '{"summary": {"layer_populations": [\n'
            '  {"rule": "r", "edge_kind": "depends_on", "evaluated": 1,\n'
            '   "total": 2, "skipped_untagged": 1, "unjudged": 0}\n'
            "]}}\n"
            f"{_FENCE}\n"
        )
        claims = _key_list_claims(Path("x.md"), text)
        assert [claim.keys for claim in claims] == [
            ("rule", "edge_kind", "evaluated", "total", "skipped_untagged", "unjudged")
        ]
        assert claims[0].site.line == 3

    def test_a_fenced_finding_object_sharing_only_rule_is_not_a_key_list_claim(self) -> None:
        text = f'{_FENCE}json\n{{"rule": "r", "severity": "error", "node": "a"}}\n{_FENCE}\n'
        assert _key_list_claims(Path("x.md"), text) == []


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
