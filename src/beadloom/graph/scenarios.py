# beadloom:domain=graph
# beadloom:feature=scenario-binding
"""Read the acceptance suite and say what each scenario binds itself to.

**One responsibility:** turn ``.feature`` files and the documents that reference
them into the two facts a coverage check needs — *which graph node and which bead
does this scenario claim*, and *which scenario does this document claim exists*.
Nothing here evaluates anything; the verdict is
:mod:`beadloom.graph.rules.scenario_coverage`'s.

Why the file holds the text (BDL-061 CONTEXT, option (b)): the ``.feature`` file is
the **source of truth** and the PRD states intent and references it. An executable
artifact cannot silently lie — it either runs or it does not — whereas a generator
sitting between a statement and an executable becomes a synchronisation problem of
its own. That decision is what makes this module a *reader* and never a writer.

The binding is carried by Gherkin **tags** (``@bead:…``, ``@node:…``) rather than
by the header comment the RFC sketched, because a tag is part of the Gherkin
language: every parser, runner and IDE already understands it, ``pytest-bdd``
exposes it for selection, and a comment is understood by nobody but us. Tags
follow Gherkin's own inheritance — a tag on ``Feature:`` or ``Rule:`` applies to
the scenarios beneath it — so one file binds to a node once.

Three honest limits, stated because a reader that overstates its reach is the
defect it exists to catch:

* **The bead's existence is not verified.** Reading the tracker from the rule
  engine would make a domain depend on the application layer; what is checked is
  that a scenario *names* one. The node reference IS verified — it is in the graph.
* **A dialect this module does not ship is reported, never counted as zero
  scenarios** (`.46`/`.47`: unverifiable is not clean). The same is true of a file
  that does not decode as UTF-8.
* **Only the structure is parsed** — keywords, tags, names. Steps are not
  interpreted, so a scenario that binds correctly and asserts nothing is invisible
  here; that is the mutation duty's job, not this module's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

#: Where the acceptance suite lives unless a rule says otherwise (Q3). The layout
#: is the one proven in the dogfood project — ``features/`` beside ``steps/`` —
#: and it is a *default*, not a convention we impose: an adopter's rule names its
#: own glob and this constant is never consulted again.
DEFAULT_FEATURE_GLOB = "tests/acceptance/features/**/*.feature"

#: Where the step implementations live by convention (Q3's other half). Referenced
#: by the role templates so an author is told one layout, not two; no check reads
#: it, and it is stated here so the two halves of the convention sit together.
DEFAULT_STEPS_DIRNAME = "tests/acceptance/steps"

#: The tag that names the bead a scenario was written for.
BEAD_TAG_PREFIX = "@bead:"

#: The tag that names the graph node whose behaviour a scenario pins.
NODE_TAG_PREFIX = "@node:"


@dataclass(frozen=True)
class _Dialect:
    """The keyword spellings of one Gherkin language."""

    feature: tuple[str, ...]
    rule: tuple[str, ...]
    scenario: tuple[str, ...]
    examples: tuple[str, ...]


#: The dialects this parser can read. Deliberately small: every entry is a
#: promise that a team writing in that language is checked rather than silently
#: reported as having no scenarios, and a promise nobody verified is worse than
#: an absence that says so. ``ru`` is here because #136's motivating adopter
#: writes in Russian; anything else is reported by name (see :func:`parse_feature`).
_DIALECTS: dict[str, _Dialect] = {
    "en": _Dialect(
        feature=("Feature", "Business Need", "Ability"),
        rule=("Rule",),
        scenario=("Scenario", "Scenario Outline", "Scenario Template", "Example"),
        examples=("Examples", "Scenarios"),
    ),
    "ru": _Dialect(
        feature=("Функция", "Функциональность", "Функционал", "Свойство", "Функциональнось"),
        rule=("Правило",),
        scenario=("Сценарий", "Пример", "Структура сценария", "Шаблон сценария"),
        examples=("Примеры",),
    ),
}

#: ``# language: xx`` — Gherkin's own way of declaring the dialect.
_LANGUAGE_DIRECTIVE = re.compile(r"^#\s*language\s*:\s*([A-Za-z0-9-]+)\s*$")

#: A keyword line: everything before the first colon is the candidate keyword.
_KEYWORD_LINE = re.compile(r"^(?P<keyword>[^:]+):(?P<rest>.*)$")

#: Doc-string delimiters. A line whose stripped form starts with one opens or
#: closes a payload block, and Gherkin inside a payload is text, not structure.
_DOCSTRING_DELIMITERS = ('"""', "```")

#: Markdown fences, for the reference reader. A fenced block in a TO-BE document
#: is a *form* (``templates.md`` ships the scenario shape in one) and a form is
#: not a claim that a scenario exists.
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Scenario:
    """One scenario, and what it binds itself to.

    ``beads`` and ``nodes`` are the tags of the scenario plus those inherited
    from its ``Rule:`` and ``Feature:``, de-duplicated, in order of first
    appearance so a report reads the way the file does.
    """

    name: str
    feature: str
    path: str
    line: int
    beads: tuple[str, ...]
    nodes: tuple[str, ...]


@dataclass(frozen=True)
class UnreadableDocument:
    """A file this module could not read, and why.

    Never silently an empty file: an unread file with no finding is how a
    coverage check reports the whole suite missing and calls it a clean zero. The
    same vocabulary serves both readers here — a `.feature` whose scenarios are
    unknown, and a planning document whose intent is unknown (`.66`, `.62`).
    """

    path: str
    reason: str


#: The name this class shipped under in 2.2.0, when only the suite reader used it.
UnreadableFeatureFile = UnreadableDocument


@dataclass(frozen=True)
class ScenarioSuite:
    """Everything the acceptance suite says about itself.

    ``files`` is what the glob matched — the population any statement about the
    suite is a fraction OF. ``empty_files`` parsed cleanly and declared no
    scenario; ``unreadable`` could not be parsed at all. The three are kept apart
    because they need different remedies and only one of them is a bug.
    """

    scenarios: tuple[Scenario, ...] = ()
    files: tuple[str, ...] = ()
    empty_files: tuple[str, ...] = ()
    unreadable: tuple[UnreadableDocument, ...] = ()

    @property
    def is_empty(self) -> bool:
        """True when the glob matched no file at all — nothing to check against."""
        return not self.files


@dataclass(frozen=True)
class ScenarioReference:
    """A scenario a TO-BE document claims exists, and where it says so."""

    name: str
    path: str
    line: int


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    """Order-preserving de-duplication."""
    seen: dict[str, None] = {}
    for value in values:
        seen.setdefault(value, None)
    return tuple(seen)


def _tags_on(line: str) -> list[str]:
    """The tags of a Gherkin tag line (``@a @b:c``)."""
    return [token for token in line.split() if token.startswith("@")]


def _bindings(tags: Iterable[str], prefix: str) -> list[str]:
    """The values of every ``prefix``-carrying tag, empty values dropped."""
    return [
        tag[len(prefix) :].strip() for tag in tags if tag.startswith(prefix) and tag[len(prefix) :]
    ]


def _keyword_kind(keyword: str, dialect: _Dialect) -> str | None:
    """Which Gherkin construct *keyword* names, or ``None``.

    ``Examples`` is tested before ``Example`` — in English and in Russian the
    scenario keyword is a prefix of the table keyword, and getting the order
    wrong turns every outline's data table into a phantom scenario.
    """
    for kind, spellings in (
        ("examples", dialect.examples),
        ("scenario", dialect.scenario),
        ("rule", dialect.rule),
        ("feature", dialect.feature),
    ):
        if keyword in spellings:
            return kind
    return None


def _unknown_dialect_reason(language: str) -> str:
    known = ", ".join(sorted(_DIALECTS))
    return (
        f"declares `# language: {language}` — this parser ships the dialects "
        f"{known} and cannot read its keywords, so its scenarios are UNKNOWN "
        f"rather than absent. Write the file in a shipped dialect, or drop the "
        f"directive if the keywords are English"
    )


class _FeatureParser:
    """One pass over one ``.feature`` file.

    A class rather than a closure-heavy function because the parse is genuinely
    stateful — inherited tags, the current dialect, whether we are inside a
    payload — and the alternative is threading six values through five helpers.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._dialect = _DIALECTS["en"]
        self._language = "en"
        self._seen_keyword = False
        self._docstring: str | None = None
        self._pending: list[str] = []
        self._feature_tags: list[str] = []
        self._rule_tags: list[str] = []
        self._feature_name = ""
        self.scenarios: list[Scenario] = []
        self.reason: str | None = None

    def parse(self, text: str) -> None:
        for number, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.strip()
            if self._in_docstring(stripped):
                continue
            if not stripped:
                continue
            if stripped.startswith("#"):
                self._maybe_language(stripped)
                if self.reason is not None:
                    return
                continue
            if stripped.startswith("@"):
                self._pending.extend(_tags_on(stripped))
                continue
            self._keyword_or_step(stripped, number)

    def _in_docstring(self, stripped: str) -> bool:
        """Track the payload block; return True when this line is inside one."""
        if self._docstring is not None:
            if stripped.startswith(self._docstring):
                self._docstring = None
            return True
        for delimiter in _DOCSTRING_DELIMITERS:
            if stripped.startswith(delimiter):
                self._docstring = delimiter
                return True
        return False

    def _maybe_language(self, stripped: str) -> None:
        match = _LANGUAGE_DIRECTIVE.match(stripped)
        if match is None or self._seen_keyword:
            return
        language = match.group(1).lower()
        dialect = _DIALECTS.get(language)
        if dialect is None:
            self.reason = _unknown_dialect_reason(match.group(1))
            return
        self._language = language
        self._dialect = dialect

    def _keyword_or_step(self, stripped: str, number: int) -> None:
        match = _KEYWORD_LINE.match(stripped)
        kind = (
            None
            if match is None
            else _keyword_kind(match.group("keyword").strip(), self._dialect)
        )
        if match is None or kind is None:
            # A step. Tags may only precede a keyword, so anything still pending
            # was dangling and must not attach itself to the NEXT scenario.
            self._pending.clear()
            return
        self._seen_keyword = True
        name = match.group("rest").strip()
        if kind == "feature":
            if self._feature_name:
                # The Gherkin specification allows one Feature per file, and
                # ``pytest-bdd`` refuses the file outright. A parser that read the
                # second Feature would count its scenarios as covering their nodes
                # while NOTHING executed — a false green of exactly the shape this
                # rule exists to remove. Measured: the real runner raises
                # ``Multiple features are not allowed in a single feature file``.
                self.reason = (
                    "declares more than one `Feature:` — the Gherkin specification "
                    "allows one per file and a runner refuses the whole file, so its "
                    "scenarios are UNKNOWN rather than present. Split it"
                )
                return
            self._feature_name = name
            self._feature_tags = list(self._pending)
            self._rule_tags = []
        elif kind == "rule":
            self._rule_tags = list(self._pending)
        elif kind == "scenario":
            self._emit(name, number)
        self._pending.clear()

    def _emit(self, name: str, number: int) -> None:
        tags = [*self._feature_tags, *self._rule_tags, *self._pending]
        self.scenarios.append(
            Scenario(
                name=name,
                feature=self._feature_name,
                path=self._path,
                line=number,
                beads=_dedupe(_bindings(tags, BEAD_TAG_PREFIX)),
                nodes=_dedupe(_bindings(tags, NODE_TAG_PREFIX)),
            )
        )


def parse_feature(text: str, *, path: str) -> tuple[tuple[Scenario, ...], str | None]:
    """Parse one ``.feature`` file into bound scenarios.

    Returns ``(scenarios, reason)``. ``reason`` is ``None`` when the file was
    read; otherwise it is why its scenarios are unknown, and ``scenarios`` is
    empty *because nothing could be read* rather than because nothing is there.
    """
    parser = _FeatureParser(path)
    parser.parse(text)
    if parser.reason is not None:
        return (), parser.reason
    return tuple(parser.scenarios), None


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def load_suite(project_root: Path, glob: str) -> ScenarioSuite:
    """Read every ``.feature`` file *glob* matches under *project_root*.

    Results are sorted by path so a report is stable across filesystems — the
    ordering a formatter, a diff and a test all depend on.
    """
    scenarios: list[Scenario] = []
    files: list[str] = []
    empty: list[str] = []
    unreadable: list[UnreadableDocument] = []
    for path in sorted(project_root.glob(glob)):
        if not path.is_file():
            continue
        relative = _relative_posix(path, project_root)
        files.append(relative)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(
                UnreadableDocument(
                    relative,
                    f"could not be read as utf-8 text: {exc.__class__.__name__}: {exc}",
                )
            )
            continue
        parsed, reason = parse_feature(text, path=relative)
        if reason is not None:
            unreadable.append(UnreadableDocument(relative, reason))
            continue
        if not parsed:
            empty.append(relative)
        scenarios.extend(parsed)
    return ScenarioSuite(
        scenarios=tuple(scenarios),
        files=tuple(files),
        empty_files=tuple(empty),
        unreadable=tuple(unreadable),
    )


# ---------------------------------------------------------------------------
# References from a TO-BE document
# ---------------------------------------------------------------------------

#: Every dialect's scenario keyword, longest first so ``Scenario Outline`` wins
#: over ``Scenario`` when a document quotes the longer form.
_REFERENCE_KEYWORDS: tuple[str, ...] = tuple(
    sorted(
        {spelling for dialect in _DIALECTS.values() for spelling in dialect.scenario},
        key=len,
        reverse=True,
    )
)

#: Leading markdown that carries no meaning for a reference: quote markers, list
#: bullets, ordered-list numbers and task checkboxes.
_LIST_MARKER = re.compile(r"^(?:>\s*)*(?:[-*+]\s+|\d+[.)]\s+)?(?:\[[ xX]\]\s+)?")


def _normalise_reference_line(line: str) -> tuple[str, bool]:
    """The candidate reference text and whether the author MARKED it as one.

    **A backticked span is delimited by its backticks.** The form this project's
    own PRD uses puts the whole reference in code style and the commentary
    outside it — ``- [ ] `Scenario: A guard leaves the index unchanged` (read-only,
    #147)``. Stripping backticks globally and taking the rest of the line would
    fold that commentary into the scenario NAME, and the check would then report
    every one of those references as missing under a name nobody wrote.

    *marked* is True when the line carried a list bullet, a quote marker or a
    backticked span — the forms an author uses to say "this is a name, not a
    sentence". It is what the prose-shaped keywords are held to (see
    :data:`_PROSE_SHAPED_KEYWORDS`); every one of this repository's 33 real
    references is marked.
    """
    stripped = line.replace("**", "").replace("__", "").strip()
    text = _LIST_MARKER.sub("", stripped).strip()
    marked = text != stripped
    if text.startswith("`"):
        closing = text.find("`", 1)
        return (text[1:] if closing == -1 else text[1:closing]), True
    return text.replace("`", ""), marked


#: Emphasis and sentence punctuation that may wrap a referenced name. Trimmed to
#: a fixpoint rather than in one pass: ``*an order is placed*.`` ends with the
#: punctuation OUTSIDE the emphasis, so a single ordered strip leaves one of them.
_REFERENCE_TRIM = "*_ .;,"


def _trim_reference_name(rest: str) -> str | None:
    """The bare scenario name inside whatever markdown wrapped it."""
    name = rest.strip()
    while name and name[-1] in _REFERENCE_TRIM:
        name = name[:-1]
    while name and name[0] in _REFERENCE_TRIM:
        name = name[1:]
    return name or None


#: Scenario keywords that are also ordinary words. Gherkin's ``Example`` (en) and
#: ``Пример`` (ru) open an explanatory paragraph in any PRD ever written, so a
#: bare line starting with one is prose until the author MARKS it — bulleted,
#: quoted or backticked. Measured (`.14`): ``Example: a nested import inside a
#: function is still an import.`` yielded the reference ``a nested import inside a
#: function``, which the rule then demanded someone write a scenario for. This
#: repository has zero such lines and an adopter's PRD has many.
_PROSE_SHAPED_KEYWORDS: frozenset[str] = frozenset({"Example", "Пример"})


def _reference_name(text: str, *, marked: bool) -> str | None:
    """The scenario name *text* references, or ``None`` when it references none.

    The keyword must LEAD the line once markdown is stripped. Prose that mentions
    a scenario in passing — ``proved by one scenario: the inert one`` — is not a
    reference, and a check that treated it as one would report a document for a
    sentence rather than for a claim. A prose-shaped keyword additionally needs
    the line to be *marked*.
    """
    for keyword in _REFERENCE_KEYWORDS:
        if not text.startswith(keyword):
            continue
        rest = text[len(keyword) :].lstrip()
        if not rest.startswith(":"):
            continue
        if keyword in _PROSE_SHAPED_KEYWORDS and not marked:
            return None
        return _trim_reference_name(rest[1:])
    return None


def _is_indented_code(raw: str) -> bool:
    """True for a line markdown reads as an indented code block.

    Markdown has two code-block syntaxes and this reader knew one. The reason for
    skipping a fence — a FORM is not a claim that a scenario exists — applies
    identically to four spaces of indentation, and ``templates.md`` is exactly the
    kind of document that carries the Gherkin form that way (`.14`).

    A deeply nested list item is not code: it is indented, but it opens with a
    bullet or a quote marker, and an author who bulleted a reference meant it as
    one. That is the discriminator, rather than CommonMark's full rule about which
    paragraph an indented chunk continues, which needs a block parser this reader
    is not.
    """
    body = raw.expandtabs(4)
    if len(body) - len(body.lstrip(" ")) < 4:
        return False
    marker = _LIST_MARKER.match(body.strip())
    return marker is None or marker.end() == 0


def parse_scenario_references(text: str, *, path: str) -> tuple[ScenarioReference, ...]:
    """Every scenario a document claims exists, in document order.

    A form is skipped in both of markdown's code syntaxes — fenced and indented —
    and a keyword that is also an ordinary word is read only when the line is
    marked as a name. Both are false-positive removals, and a false positive here
    reports an author for a sentence they wrote rather than for a claim they made.
    """
    references: list[ScenarioReference] = []
    fence: str | None = None
    for number, raw in enumerate(text.splitlines(), start=1):
        fence_match = _FENCE.match(raw)
        if fence_match is not None:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is not None or _is_indented_code(raw):
            continue
        candidate, marked = _normalise_reference_line(raw)
        name = _reference_name(candidate, marked=marked)
        if name is not None:
            references.append(ScenarioReference(name=name, path=path, line=number))
    return tuple(references)


@dataclass(frozen=True)
class ReferenceSet:
    """Everything the documents that state intent say about themselves.

    ``dead_globs`` matched no document; ``unreadable`` matched and could not be
    read. Both are kept because the alternative for either is an empty
    ``references`` tuple, which is also what a document with nothing wrong in it
    returns. The suite reader has held this shape since `.66`; the reference
    reader did not, and swallowed ``OSError`` and ``UnicodeDecodeError`` with a
    bare ``continue`` one function away from it.
    """

    references: tuple[ScenarioReference, ...] = ()
    dead_globs: tuple[str, ...] = ()
    unreadable: tuple[UnreadableDocument, ...] = ()


def load_references(project_root: Path, globs: Sequence[str]) -> ReferenceSet:
    """Read scenario references from every document the globs match.

    A glob that matched no document is reported rather than ignored: a reference
    check whose documents moved reports nothing and looks exactly like one that
    found no problem (BDL-UX #172). A document that matched and could not be
    DECODED is reported for the same reason and it is the sharper case, because
    the remedy is invisible: measured (`.14`), a cp1251 PRD naming one scenario
    yielded no reference, no dead glob and no finding, so the rule stated that
    document's intent was fully met. Adding one file in the wrong encoding took a
    document out of the checked population and nothing said so.
    """
    references: list[ScenarioReference] = []
    dead: list[str] = []
    unreadable: list[UnreadableDocument] = []
    for glob in globs:
        matched = False
        for path in sorted(project_root.glob(glob)):
            if not path.is_file():
                continue
            matched = True
            relative = _relative_posix(path, project_root)
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                unreadable.append(
                    UnreadableDocument(
                        relative,
                        f"could not be read as utf-8 text: "
                        f"{exc.__class__.__name__}: {exc}",
                    )
                )
                continue
            references.extend(parse_scenario_references(text, path=relative))
        if not matched:
            dead.append(glob)
    return ReferenceSet(tuple(references), tuple(dead), tuple(unreadable))
