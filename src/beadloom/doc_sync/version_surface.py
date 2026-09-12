# beadloom:domain=doc-sync
# beadloom:feature=version-surface
"""Every place this project states its own version, and what judges each one.

**One responsibility:** find the places, attribute each to the instrument whose
population holds it, and name the ones no instrument holds.

Cutting the release that preceded this epic measured the shape this module
answers (BDL-UX #281). The version was stated in nine places; four instruments
judged parts of that population and no two of those parts overlapped; three
places were judged by nothing. Every instrument
was individually correct and the union was unnamed, so the release bumped the
four places its author remembered, believed the job done, and met the rest one
at a time — a ``lint --strict`` error at ``severity: error`` and two assertions
inside the suite, both arriving after the work was believed finished.

**The list was derived by hand first and was wrong by two, by the person who had
just written it.** ``docs audit`` reported a line in the CLI reference its author
had already read and classified as an example rather than a claim, and grepping
for its twin found the same sentence in a document no check reads. That is the
argument for a derivation rather than a checklist, made against the checklist's
own author — so **no place is named anywhere in this module**, and
``tests/test_version_surface.py`` parses this file with its docstrings stripped
and fails if one appears.

The instruments ARE named, and that is a different thing from naming a place. An
instrument's name is a fact about this codebase that changes when an instrument
is added; a place is a fact about the tree that changes on every release. What
each instrument's name is attached to — its population — is derived here from
the project's own declarations: the manifest for the packaging version and the
test paths, the rules file for the lint rule, the scanner's own surface
resolution for the documentation audit, and the flow manifest for the
agent-instruction adapters.

THE SWEEP IS BY THE CURRENT LITERAL, AND THAT IS THE LIMIT TO READ FIRST. A
place that ALREADY states an old version is invisible to it. The alternative was
measured rather than assumed: reading every version token this project's prose
attributes to itself returns 674 claims across 137 files on this repository,
because the planning archive records every version it ever had, and a report of
674 rows is a report nobody finishes. Catching a place that has gone stale is
what the INSTRUMENTS are for, and which places have one is exactly what this
module reports. The operating consequence is one line and belongs in the SPEC:
**run it before the bump, not after.**

WHAT IT DOES NOT DISTINGUISH, stated because the report reads as though it might.
A place that STATES the version and a place that RECORDS a measurement taken on
a release — "the current release is X" against "measured on the published X
wheel" — are told apart by no structure this module can read. It has one further
coat: a literal used as FIXTURE DATA reads the same as both. A tense
heuristic here would be a second notion of what a version claim is, beside
:meth:`~beadloom.doc_sync.scanner.DocScanner.scan_line`, and a second notion is
how the next drift class starts — the reason ``graph-summary-facts`` refused to
build one. Inside an instrument's population the instrument makes the
distinction; outside it, the reader does.

WHAT IS EXTRACTED IS THE SCANNER'S NOTION OF A VERSION, never a second one.
Every candidate line is confirmed through ``scan_line``, so the token boundaries,
the false-positive filters and the subject vocabulary are the audit's and the
lint rule's, not this module's. The one deliberate difference is code fences:
the audit skips a fenced block and this sweep does not, because a version inside
an example block is still a place a release has to edit.

WHY THE MARKERS AND PATHS BELOW ARE RESTATED RATHER THAN IMPORTED. The
auto-region markers are read by ``onboarding.scanner.claude_md`` and the graph
directory by ``onboarding.graph_files``. ``doc_sync`` may import neither:
``graph.rules.summary_facts`` imports this domain and ``onboarding`` imports
``graph``, so an import in either direction closes a cycle ``no-dependency-cycles``
refuses at error severity. It is the structural half of the reason
``onboarding/graph_files.py`` already states for its own three exemptions, and
closing it means moving those bodies into a layer every reader may import, which
is ``beadloom-4axf`` rather than a line here.

And this reader does NOT read ``.beadloom/_graph/`` for nodes. It reads lines for
one key, so its answer moves when a comment is added and a node reader's does
not — the policy in ``graph_files.each_graph_file`` is inapplicable to it by
nature, in the words BDL-069 S2 narrowed that policy to.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import yaml

from beadloom.doc_sync.scanner import DocScanner
from beadloom.doc_sync.version_subjects import derive_version_subjects

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

#: The five instruments. A name here is a fact about this codebase; what it is
#: attached to is derived per project, below.
PACKAGING_MANIFEST = "packaging-manifest"
DOCS_AUDIT = "docs-audit"
GRAPH_SUMMARY_FACTS = "graph-summary-facts"
DOCTOR = "doctor"
TEST_SUITE = "test-suite"

#: Directories that hold no statement this project makes about itself: a virtual
#: environment, a build product, a cache, a vendored tree, or the tracker's own
#: export, which ``bd`` regenerates and no release edits.
SKIPPED_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        "site",
        "htmlcov",
        "dist",
        "build",
        ".beads",
        ".eggs",
    }
)

#: The kinds a project writes prose and code in. Everything else is COUNTED as
#: not read rather than dropped: a lock file states its dependencies' versions
#: and a database states nothing, and both would otherwise leave the population
#: looking complete.
READ_SUFFIXES: frozenset[str] = frozenset(
    {
        ".md",
        ".py",
        ".yml",
        ".yaml",
        ".toml",
        ".cfg",
        ".ini",
        ".txt",
        ".feature",
        ".rst",
    }
)

_GRAPH_DIRECTORY = (".beadloom", "_graph")
_RULES_FILE = "rules.yml"
_FLOW_MANIFEST = (".beadloom", "flow-manifest.json")

#: ``[section]`` up to the next table header, and the same header when it is the
#: last table in the file. Read without ``tomllib`` for the reason
#: ``application/typed_surface.py`` states: ``tomllib`` is 3.11+ and ``tomli`` is
#: not a runtime dependency, so a parse would answer differently per room, and a
#: module whose subject is what a check covers must not have a room-dependent
#: answer.
_SECTION_RE = r"^\[{name}\]\s*$(?P<body>.*?)(?=^\[|\Z)"
_STATIC_VERSION_RE = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_DYNAMIC_RE = re.compile(r'^\s*dynamic\s*=\s*\[[^\]]*["\']version["\']', re.MULTILINE)
_HATCH_PATH_RE = re.compile(r'^\s*path\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_DUNDER_VERSION_RE = re.compile(r'^\s*__version__\s*=\s*["\']([^"\']+)["\']')
_TESTPATHS_RE = re.compile(r"^\s*testpaths\s*=\s*\[(?P<body>[^\]]*)\]", re.MULTILINE)
_QUOTED_RE = re.compile(r"""(["'])(?P<value>(?:(?!\1).)*)\1""")

#: The auto-region ``setup-agentic-flow`` writes the project's facts into, and
#: the one ``doctor`` reads its version claim out of.
_REGION_NAME = "project-info"
_REGION_START_RE = re.compile(r"<!--\s*beadloom:auto-start\s+([\w-]+)\s*-->")
_REGION_END_RE = re.compile(r"<!--\s*beadloom:auto-end\s*-->")

#: A node summary, as a line rather than as a node. See the module docstring.
_SUMMARY_KEY_RE = re.compile(r"^\s*summary\s*:\s")


@dataclass(frozen=True)
class Instrument:
    """One check that judges a version token, and the population it holds.

    ``resolved`` is false when the project declares nothing for this instrument
    to run over — a rule it does not enable, a test-path key it does not set.
    An unresolved instrument is not an absent one: its ``reason`` is what the
    report prints beside the places it would otherwise have covered.
    """

    name: str
    population: str
    resolved: bool
    reason: str = ""


@dataclass(frozen=True)
class SourceOfTruth:
    """The value every other place restates, and how it was arrived at."""

    path: Path
    line: int
    value: str
    derived_from: str


@dataclass(frozen=True)
class VersionPlace:
    """One line that states this project's version.

    ``checkers`` is every instrument whose population holds this line, and is
    empty for a place nothing judges. ``reason`` is never empty: for a judged
    place it says which population holds it, and for an unjudged one it says
    which population came closest and why the line falls outside.
    """

    path: Path
    line: int
    excerpt: str
    checkers: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class Population:
    """The sweep's own account of what it read and what it did not."""

    files_read: int
    directories_skipped: tuple[str, ...]
    suffixes_read: tuple[str, ...]
    not_read: tuple[tuple[str, int], ...]
    unreadable: tuple[tuple[Path, str], ...]


@dataclass(frozen=True)
class VersionSurface:
    """Where this project states its version, and what holds each place."""

    source_of_truth: SourceOfTruth | None
    unresolved: str
    places: tuple[VersionPlace, ...]
    instruments: tuple[Instrument, ...]
    population: Population

    @property
    def unchecked(self) -> tuple[VersionPlace, ...]:
        """The places no instrument's population holds."""
        return tuple(place for place in self.places if not place.checkers)


def read_version_surface(project_root: Path) -> VersionSurface:
    """Every place *project_root* states its own version, with its checker.

    Returns a surface whose ``places`` is empty and whose ``unresolved`` carries
    a reason when the project declares no version this reader can follow. An
    empty answer with a reason is a different thing from an empty answer, and
    the caller prints the difference.
    """
    source, unresolved = _read_source_of_truth(project_root)
    if source is None:
        return VersionSurface(
            source_of_truth=None,
            unresolved=unresolved,
            places=(),
            instruments=(),
            population=Population(0, tuple(sorted(SKIPPED_DIRECTORIES)), (), (), ()),
        )

    scanner = DocScanner(derive_version_subjects(project_root))
    occurrences, population = _sweep(project_root, source.value, scanner)
    instruments = _build_instruments(project_root, source, scanner)
    places = tuple(
        _attribute(relative, line, excerpt, instruments) for relative, line, excerpt in occurrences
    )
    return VersionSurface(
        source_of_truth=source,
        unresolved="",
        places=places,
        instruments=tuple(holder.instrument for holder in instruments),
        population=population,
    )


# ---------------------------------------------------------------------------
# The source of truth


def _section(text: str, name: str) -> str | None:
    match = re.search(_SECTION_RE.format(name=re.escape(name)), text, re.MULTILINE | re.DOTALL)
    return match.group("body") if match else None


def _read_source_of_truth(project_root: Path) -> tuple[SourceOfTruth | None, str]:
    """The version the manifest declares, and the file that carries the literal.

    Three declarations are followed, in the order a build back end would consult
    them: a static ``[project] version``, a static ``[tool.poetry] version``, and
    a ``dynamic`` version through ``[tool.hatch.version]``. A project declaring
    something else is UNRESOLVED with the forms that were looked for, because a
    version guessed from somewhere else would put every place on this report
    under a value nothing builds from.
    """
    manifest = project_root / "pyproject.toml"
    if not manifest.is_file():
        return None, "no pyproject.toml: this project declares no version to follow"
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return None, f"pyproject.toml could not be read: {error}"

    for table in ("project", "tool.poetry"):
        body = _section(text, table)
        if body is None:
            continue
        static = _STATIC_VERSION_RE.search(body)
        if static:
            declared_line = text[: text.index(static.group(0))].count("\n") + 1
            return (
                SourceOfTruth(
                    path=Path("pyproject.toml"),
                    line=declared_line,
                    value=static.group(1),
                    derived_from=f"pyproject.toml [{table}] version",
                ),
                "",
            )

    hatch = _section(text, "tool.hatch.version")
    if hatch is None:
        return None, (
            "pyproject.toml declares no version this reader can follow: it holds "
            "no [project] version, no [tool.poetry] version and no "
            "[tool.hatch.version] path"
        )
    path_match = _HATCH_PATH_RE.search(hatch)
    if path_match is None:
        return None, "[tool.hatch.version] declares no path: nothing to follow"

    relative = Path(path_match.group(1))
    target = project_root / relative
    if not target.is_file():
        return None, (
            f"[tool.hatch.version] path names {path_match.group(1)}, "
            "which this project does not hold"
        )
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return None, f"{path_match.group(1)} could not be read: {error}"

    for number, line in enumerate(lines, 1):
        found = _DUNDER_VERSION_RE.match(line)
        if found:
            return (
                SourceOfTruth(
                    path=relative,
                    line=number,
                    value=found.group(1),
                    derived_from=(
                        "pyproject.toml dynamic version through [tool.hatch.version] path"
                    ),
                ),
                "",
            )
    dynamic = " and declares it dynamic" if _DYNAMIC_RE.search(text) else ""
    return None, (
        f"{path_match.group(1)} assigns no __version__{dynamic}: "
        "this project declares no version this reader can follow"
    )


# ---------------------------------------------------------------------------
# The sweep


def _each_file(directory: Path) -> Iterator[Path]:
    """Every file under *directory*, pruning the skipped directories as it goes."""
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.is_dir():
            if entry.name in SKIPPED_DIRECTORIES:
                continue
            yield from _each_file(entry)
        elif entry.is_file():
            yield entry


def _normalise(value: object) -> str:
    return str(value).lstrip("vV")


def _sweep(
    project_root: Path, version: str, scanner: DocScanner
) -> tuple[list[tuple[Path, int, str]], Population]:
    """Every line stating *version*, and the account of what was read to find it."""
    occurrences: list[tuple[Path, int, str]] = []
    not_read: Counter[str] = Counter()
    unreadable: list[tuple[Path, str]] = []
    files_read = 0

    for path in _each_file(project_root):
        relative = path.relative_to(project_root)
        if path.suffix.lower() not in READ_SUFFIXES:
            not_read[path.suffix or "(no suffix)"] += 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            unreadable.append((relative, "not valid UTF-8 text"))
            continue
        except OSError as error:
            unreadable.append((relative, str(error)))
            continue
        files_read += 1
        occurrences.extend(_lines_stating(path, relative, text, version, scanner))

    population = Population(
        files_read=files_read,
        directories_skipped=tuple(sorted(SKIPPED_DIRECTORIES)),
        suffixes_read=tuple(sorted(READ_SUFFIXES)),
        not_read=tuple(sorted(not_read.items(), key=lambda item: (-item[1], item[0]))),
        unreadable=tuple(unreadable),
    )
    occurrences.sort(key=lambda item: (str(item[0]), item[1]))
    return occurrences, population


def _lines_stating(
    path: Path, relative: Path, text: str, version: str, scanner: DocScanner
) -> Iterator[tuple[Path, int, str]]:
    """The lines of *text* the scanner reads as stating *version*.

    The substring test is a narrowing and never the judgement: ``scan_line``
    decides, so the token boundaries are the ones every other check applies.
    """
    for number, line in enumerate(text.splitlines(), 1):
        if version not in line:
            continue
        mentions = scanner.scan_line(line, origin=path, line_number=number)
        if any(
            mention.fact_name == "version" and _normalise(mention.value) == version
            for mention in mentions
        ):
            yield relative, number, line.strip()


# ---------------------------------------------------------------------------
# The instruments


class _Holder(Protocol):
    """An instrument, the files it could judge, and the lines it does."""

    @property
    def instrument(self) -> Instrument:
        """The instrument this holder derives a population for."""

    def applies(self, relative: Path) -> bool:
        """Whether a file of this kind is the sort this instrument judges."""

    def covers(self, relative: Path, line: int) -> tuple[bool, str]:
        """Whether this line is inside the population, and the reason either way."""


@dataclass(frozen=True)
class _PackagingManifest:
    """The one assignment a build back end reads the distribution's version from."""

    instrument: Instrument
    source: SourceOfTruth

    def applies(self, relative: Path) -> bool:
        return relative == self.source.path

    def covers(self, relative: Path, line: int) -> tuple[bool, str]:
        if line == self.source.line:
            return True, f"the source of truth — {self.source.derived_from}"
        return False, (
            f"{self.source.path} states the version at line {self.source.line}; "
            "this line is not that assignment"
        )


@dataclass(frozen=True)
class _DocsAudit:
    """The documents ``docs audit`` resolved as its own surface, reasons included."""

    instrument: Instrument
    scanned: frozenset[Path]
    excluded: dict[Path, str]
    mentions: dict[tuple[Path, int], str | None]

    def applies(self, relative: Path) -> bool:
        return relative.suffix.lower() == ".md"

    def covers(self, relative: Path, line: int) -> tuple[bool, str]:
        key = (relative, line)
        if key in self.mentions:
            subject = self.mentions[key]
            if subject is None:
                return True, "docs audit reads this line as this project's own claim"
            return False, (
                f"docs audit reads this line and attributes the token to {subject!r}, "
                "so it is never compared with this project's version"
            )
        if relative in self.scanned:
            return False, (
                "docs audit reads this document but not this line — a fenced block, "
                "or a match its false-positive filter removed"
            )
        if relative in self.excluded:
            return False, f"docs audit does not read it: {self.excluded[relative]}"
        return False, "outside docs audit's scan globs"


@dataclass(frozen=True)
class _GraphSummaryFacts:
    """Node summaries, where the project declares the rule that judges them."""

    instrument: Instrument
    graph_directory: Path
    declared: bool
    severity: str
    summary_lines: dict[Path, frozenset[int]]

    def applies(self, relative: Path) -> bool:
        return relative.parent == self.graph_directory and relative.suffix.lower() in {
            ".yml",
            ".yaml",
        }

    def covers(self, relative: Path, line: int) -> tuple[bool, str]:
        in_summary = line in self.summary_lines.get(relative, frozenset())
        if not in_summary:
            return False, "not a node summary: no other line of a graph file is judged"
        if not self.declared:
            return False, (
                f"{GRAPH_SUMMARY_FACTS} is not declared in this project's rules, "
                "so no summary is compared with anything"
            )
        return True, f"a node summary, and the rule is declared at severity {self.severity}"


@dataclass(frozen=True)
class _Doctor:
    """The ``project-info`` region of the adapters the flow manifest recorded."""

    instrument: Instrument
    regions: dict[Path, tuple[tuple[int, int], ...]]
    written: frozenset[Path]

    def applies(self, relative: Path) -> bool:
        return relative in self.written

    def covers(self, relative: Path, line: int) -> tuple[bool, str]:
        for start, end in self.regions.get(relative, ()):
            if start <= line <= end:
                return True, (
                    f"inside the {_REGION_NAME} auto-region, which doctor reads as "
                    "the agent instructions' version claim"
                )
        return False, (
            f"outside the {_REGION_NAME} auto-region: doctor reads the claim in that "
            "region and no other line of the file"
        )


@dataclass(frozen=True)
class _TestSuite:
    """A literal the suite asserts, as against one it merely carries."""

    instrument: Instrument
    testpaths: tuple[Path, ...]
    assert_lines: dict[Path, frozenset[int]]

    def applies(self, relative: Path) -> bool:
        return relative.suffix.lower() == ".py"

    def covers(self, relative: Path, line: int) -> tuple[bool, str]:
        if not self._under_testpaths(relative):
            declared = ", ".join(str(path) for path in self.testpaths) or "none"
            return False, f"not under this project's declared testpaths ({declared})"
        if line in self.assert_lines.get(relative, frozenset()):
            return True, "the suite asserts this literal"
        return False, ("under testpaths but not inside an assert, so nothing compares it")

    def _under_testpaths(self, relative: Path) -> bool:
        return any(relative == root or root in relative.parents for root in self.testpaths)


def _attribute(
    relative: Path, line: int, excerpt: str, holders: tuple[_Holder, ...]
) -> VersionPlace:
    """One occurrence, judged by every instrument whose population could hold it."""
    checkers: list[str] = []
    held: list[str] = []
    missed: list[str] = []
    for holder in holders:
        if not holder.applies(relative):
            continue
        covered, reason = holder.covers(relative, line)
        if covered:
            checkers.append(holder.instrument.name)
            held.append(reason)
        else:
            missed.append(reason)
    reasons = held or missed or ["no instrument's population reaches a file of this kind"]
    return VersionPlace(
        path=relative,
        line=line,
        excerpt=excerpt,
        checkers=tuple(checkers),
        reason="; ".join(reasons),
    )


def _build_instruments(
    project_root: Path, source: SourceOfTruth, scanner: DocScanner
) -> tuple[_Holder, ...]:
    return (
        _packaging_holder(source),
        _docs_audit_holder(project_root, scanner),
        _graph_holder(project_root),
        _doctor_holder(project_root),
        _test_suite_holder(project_root),
    )


def _packaging_holder(source: SourceOfTruth) -> _PackagingManifest:
    return _PackagingManifest(
        instrument=Instrument(
            name=PACKAGING_MANIFEST,
            population=f"{source.path}:{source.line} — {source.derived_from}",
            resolved=True,
        ),
        source=source,
    )


def _docs_audit_holder(project_root: Path, scanner: DocScanner) -> _DocsAudit:
    surface = scanner.resolve_surface(project_root)
    scanned = frozenset(path.relative_to(project_root) for path in surface.scanned)
    excluded = {entry.path.relative_to(project_root): entry.reason for entry in surface.excluded}
    mentions: dict[tuple[Path, int], str | None] = {}
    for path in surface.scanned:
        # A file on the audit's own surface that this reader cannot decode: the
        # audit reads it with its own error handling and reports it its own way,
        # and a report about the audit must not fail where the audit does not.
        try:
            found = scanner.scan_file(path)
        except (UnicodeDecodeError, OSError):
            logger.debug("Could not scan %s", path)
            continue
        for mention in found:
            if mention.fact_name != "version":
                continue
            key = (mention.file.relative_to(project_root), mention.line)
            if mention.subject is None or key not in mentions:
                mentions[key] = mention.subject
    return _DocsAudit(
        instrument=Instrument(
            name=DOCS_AUDIT,
            population=(
                f"{len(scanned)} document(s) the scanner resolved as the audit's "
                f"surface; {len(excluded)} excluded with a reason"
            ),
            resolved=bool(scanned),
            reason="" if scanned else "no document resolved into the audit's surface",
        ),
        scanned=scanned,
        excluded=excluded,
        mentions=mentions,
    )


def _graph_holder(project_root: Path) -> _GraphSummaryFacts:
    graph_directory = Path(*_GRAPH_DIRECTORY)
    declared, severity = _rule_declaration(project_root / graph_directory / _RULES_FILE)
    summary_lines = _summary_lines(project_root / graph_directory, graph_directory)
    return _GraphSummaryFacts(
        instrument=Instrument(
            name=GRAPH_SUMMARY_FACTS,
            population=(
                f"{sum(len(lines) for lines in summary_lines.values())} node "
                f"summary line(s) under {graph_directory}"
            ),
            resolved=declared,
            reason=(
                ""
                if declared
                else f"{GRAPH_SUMMARY_FACTS} is not declared in this project's rules"
            ),
        ),
        graph_directory=graph_directory,
        declared=declared,
        severity=severity,
        summary_lines=summary_lines,
    )


def _rule_declaration(rules_file: Path) -> tuple[bool, str]:
    """Whether the project declares the summary rule, and at what severity."""
    if not rules_file.is_file():
        return False, ""
    try:
        data = yaml.safe_load(rules_file.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError, UnicodeDecodeError):
        logger.debug("Could not read %s", rules_file)
        return False, ""
    if not isinstance(data, dict):
        return False, ""
    rules = data.get("rules")
    if not isinstance(rules, list):
        return False, ""
    for rule in rules:
        if isinstance(rule, dict) and rule.get("name") == GRAPH_SUMMARY_FACTS:
            severity = rule.get("severity")
            return True, str(severity) if severity else "warn"
    return False, ""


def _summary_lines(graph_directory: Path, relative_directory: Path) -> dict[Path, frozenset[int]]:
    """The lines under *graph_directory* that carry a ``summary:`` key."""
    found: dict[Path, frozenset[int]] = {}
    if not graph_directory.is_dir():
        return found
    for path in sorted(graph_directory.glob("*.yml")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = frozenset(
            number
            for number, line in enumerate(text.splitlines(), 1)
            if _SUMMARY_KEY_RE.match(line)
        )
        if lines:
            found[relative_directory / path.name] = lines
    return found


def _doctor_holder(project_root: Path) -> _Doctor:
    written = _flow_written(project_root)
    regions = {
        relative: _regions_of(project_root / relative)
        for relative in written
        if (project_root / relative).is_file()
    }
    regions = {relative: spans for relative, spans in regions.items() if spans}
    return _Doctor(
        instrument=Instrument(
            name=DOCTOR,
            population=(
                f"the {_REGION_NAME} auto-region of {len(regions)} agent-instruction "
                f"adapter(s) the flow manifest records as written"
            ),
            resolved=bool(regions),
            reason=(
                ""
                if regions
                else (f"no adapter the flow manifest records holds a {_REGION_NAME} auto-region")
            ),
        ),
        regions=regions,
        written=frozenset(written),
    )


def _flow_written(project_root: Path) -> tuple[Path, ...]:
    """The adapter files ``setup-agentic-flow`` recorded itself as writing."""
    manifest = project_root / Path(*_FLOW_MANIFEST)
    if not manifest.is_file():
        return ()
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        logger.debug("Could not read %s", manifest)
        return ()
    if not isinstance(data, dict):
        return ()
    written = data.get("written")
    if not isinstance(written, dict):
        return ()
    return tuple(Path(str(name)) for name in sorted(written))


def _regions_of(path: Path) -> tuple[tuple[int, int], ...]:
    """The line spans of the ``project-info`` auto-regions *path* holds."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return ()
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for number, line in enumerate(lines, 1):
        opened = _REGION_START_RE.search(line)
        if opened is not None:
            start = number if opened.group(1) == _REGION_NAME else None
            continue
        if _REGION_END_RE.search(line) and start is not None:
            spans.append((start, number))
            start = None
    return tuple(spans)


def _test_suite_holder(project_root: Path) -> _TestSuite:
    testpaths = _declared_testpaths(project_root)
    assert_lines: dict[Path, frozenset[int]] = {}
    for root in testpaths:
        directory = project_root / root
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            if any(part in SKIPPED_DIRECTORIES for part in path.parts):
                continue
            lines = _assert_lines(path)
            if lines:
                assert_lines[path.relative_to(project_root)] = lines
    return _TestSuite(
        instrument=Instrument(
            name=TEST_SUITE,
            population=(
                f"assert statements in the Python files under "
                f"{', '.join(str(path) for path in testpaths) or 'no declared testpath'}"
            ),
            resolved=bool(testpaths),
            reason=(
                ""
                if testpaths
                else "pyproject.toml declares no [tool.pytest.ini_options] testpaths"
            ),
        ),
        testpaths=testpaths,
        assert_lines=assert_lines,
    )


def _declared_testpaths(project_root: Path) -> tuple[Path, ...]:
    manifest = project_root / "pyproject.toml"
    if not manifest.is_file():
        return ()
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ()
    body = _section(text, "tool.pytest.ini_options")
    if body is None:
        return ()
    declared = _TESTPATHS_RE.search(body)
    if declared is None:
        return ()
    return tuple(
        Path(match.group("value")) for match in _QUOTED_RE.finditer(declared.group("body"))
    )


def _assert_lines(path: Path) -> frozenset[int]:
    """Every line an ``assert`` statement of *path* spans.

    Parsed rather than matched: a literal inside a docstring, a comment or a
    printed message is carried by the file and compared with nothing, and only
    the parse tells the two apart.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError, OSError, UnicodeDecodeError):
        return frozenset()
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            end = node.end_lineno or node.lineno
            lines.update(range(node.lineno, end + 1))
    return frozenset(lines)
