# Version Surface

Every place a project states its own version, each attributed to the instrument whose population
holds it, and the places no instrument holds.

**Source:** `src/beadloom/doc_sync/version_surface.py`

---

## Specification

### Purpose

Cutting the release that preceded BDL-069 measured the shape this module answers (BDL-UX #281).
The version was stated in nine places. Four instruments judged parts of that population, no two of
those parts overlapped, and three places were judged by nothing. Every instrument was individually
correct; the union was unnamed. So the release bumped the four places its author remembered,
believed the job done, and met the rest one at a time — a `lint --strict` error at `severity:
error` and two assertions inside the suite, both arriving after the work was believed finished.

**The list was derived by hand first and was wrong by two, by the person who had just written it.**
`docs audit` reported a line in the CLI reference its author had already read and classified as an
example rather than a claim, and grepping for its twin found the same sentence in a document no
check reads.

That is the argument for a derivation rather than a checklist, made against the checklist's own
author. No place is named anywhere in the module, and `tests/test_version_surface.py` parses the
source with its docstrings stripped and fails if one appears.

### Why the instruments are named and the places are not

An instrument's name is a fact about this codebase: it changes when an instrument is added, which
is a change to the code that adds it. A place is a fact about the tree, and it changes on every
release. What each instrument's name is attached to — its population — is derived from the
project's own declarations, never listed:

| Instrument | The population, and where it is derived from |
|---|---|
| `packaging-manifest` | the one assignment a build back end reads, followed from `pyproject.toml`: a static `[project] version`, a static `[tool.poetry] version`, or a `dynamic` version through `[tool.hatch.version] path` |
| `docs-audit` | the documents `DocScanner.resolve_surface` resolves as the audit's own surface, with the audit's own exclusion reason carried verbatim for every document it leaves out |
| `graph-summary-facts` | the `summary:` lines under `.beadloom/_graph/`, judged only where the project declares the rule in its rules file — the declared severity is reported with the place |
| `doctor` | the `beadloom:auto-start project-info` auto-region of the agent-instruction adapters `.beadloom/flow-manifest.json` records as written |
| `test-suite` | the `assert` statements — parsed, not matched — in the Python files under the manifest's `[tool.pytest.ini_options] testpaths` |

A place is attributed to every instrument whose population holds it, and an unjudged place still
carries a reason: which population came closest, and why the line falls outside it. A row a reader
cannot act on is the thing this epic removes.

### What is extracted is the scanner's notion of a version

Every candidate line is confirmed through `DocScanner.scan_line`, so the token boundaries, the
false-positive filters and the subject vocabulary are the audit's and the lint rule's rather than a
second set. A token the audit attributes to another product is reported as that product's and is
not a place: `docs audit` reads the line and never compares the token with this project's version.

The one deliberate difference from the audit is code fences. The audit skips a fenced block; this
sweep does not, because a version inside an example block is still a place a release has to edit —
which is exactly how the nine grew from seven.

### The sweep is by the current literal, which is the limit to read first

A place that ALREADY states an old version is invisible to the sweep. **Run this before the bump,
not after.**

The alternative was measured rather than assumed. Reading every version token this project's prose
attributes to itself returns 674 claims across 137 files on this repository, because the planning
archive records every version the project ever had, and a report of 674 rows is a report nobody
finishes. Catching a place that has gone stale is what the instruments are for, and which places
have one is what this report names.

### What it does not distinguish

A place that STATES the version and a place that RECORDS a measurement taken on a release — "the
current release is X" against "measured on the published X wheel" — are told apart by no structure
the module can read. A literal used as fixture data is the same problem in a third coat.

A tense heuristic here would be a second notion of what a version claim is, beside
`DocScanner.scan_line`, and a second notion is how the next drift class starts. Inside an
instrument's population the instrument makes the distinction; outside it, the reader does.

### The population it searched

The report carries its own sweep: the files read, the directories pruned, the suffixes read, the
suffixes NOT read with a count each, and every file that could not be decoded with its reason. A
lock file states its dependencies' versions and a database states nothing; both would otherwise
leave the population looking complete.

### Restated rather than imported

The auto-region markers are read by `onboarding.scanner.claude_md` and the graph directory by
`onboarding.graph_files`. `doc_sync` may import neither: `graph.rules.summary_facts` imports this
domain and `onboarding` imports `graph`, so an import in either direction closes a cycle
`no-dependency-cycles` refuses at `error` severity. It is the structural half of the reason
`onboarding/graph_files.py` already states for its own three exemptions, and closing it means
moving those bodies into a layer every reader may import — `beadloom-4axf`.

This reader does not read `.beadloom/_graph/` for NODES. It reads lines for one key, so its answer
moves when a comment is added to a graph file and a node reader's does not, which puts it outside
`each_graph_file`'s population by nature — in the words BDL-069 S2 narrowed that policy to.

## API

### Module `src/beadloom/doc_sync/version_surface.py`

- `read_version_surface(project_root: Path) -> VersionSurface` — every place *project_root* states
  its own version, each with its checker. A project declaring no version this reader can follow
  gets an empty `places` and a `unresolved` reason; an empty answer and an empty answer with a
  reason are different answers, and the caller prints the difference.
- `VersionSurface` — `source_of_truth`, `unresolved`, `places`, `instruments`, `population`, and
  the `unchecked` projection: the places no instrument's population holds.
- `SourceOfTruth` — `path`, `line`, `value`, `derived_from`: the declaration chain followed, so a
  reader can check the value against the manifest rather than trusting it.
- `VersionPlace` — `path`, `line`, `excerpt`, `checkers`, `reason`. `checkers` is empty for an
  unjudged place; `reason` is never empty.
- `Instrument` — `name`, `population`, `resolved`, `reason`. An instrument a project declares
  nothing for is unresolved with its reason, not absent.
- `Population` — `files_read`, `directories_skipped`, `suffixes_read`, `not_read`, `unreadable`.
- `PACKAGING_MANIFEST`, `DOCS_AUDIT`, `GRAPH_SUMMARY_FACTS`, `DOCTOR`, `TEST_SUITE` — the five
  instrument names.
- `SKIPPED_DIRECTORIES`, `READ_SUFFIXES` — the sweep's declared bounds, reported on every run.

## Measured on this repository

On 2026-09-11, against `4.0.0` as the manifest declares it: **41 places across 20 files**, read out
of 1 375 files. Eight are judged — one by `packaging-manifest`, three by `docs-audit`, one by
`graph-summary-facts`, one by `doctor`, two by `test-suite` — and 33 by nothing.

The nine of 2026-09-10 are all among them, each with the checker that measurement recorded. The
count is a floor and not a ceiling: this epic's own first two waves added documents that state the
current release, which is the question the hand-written list of nine kept getting wrong.
