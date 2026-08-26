# Documentation Audit

Zero-config detection of stale facts in project markdown documentation.

Source: `src/beadloom/doc_sync/audit.py`, `src/beadloom/doc_sync/scanner.py`,
`src/beadloom/doc_sync/audit_coverage.py`

## Specification

### Purpose

The documentation audit feature detects stale numeric facts in markdown documentation by comparing mentioned values against ground-truth data extracted from the project. It uses a two-pass architecture: first collecting facts from project infrastructure (manifest files, graph DB, code symbols, MCP tools, CLI commands), then scanning documentation for keyword-proximate numbers and version strings, and finally comparing the two to produce stale/fresh findings.

### Architecture

The audit pipeline has three stages:

1. **FactRegistry** (`audit.py`) -- Collects ground-truth facts from multiple project data sources: `pyproject.toml` (version), graph DB (node/edge/test/framework/rule counts), the MCP tool catalog (tool count), Click CLI introspection (command count), and code_symbols (language count). Extra facts can be injected via `config.yml`. A source that cannot produce a value records the reason instead of dropping the fact, and the two surface facts are gated by `audit_self_surface.py` so they are declared only for the project that provides them.

2. **DocScanner** (`scanner.py`) -- Scans markdown files for numeric and version string mentions. A line is tokenized on whitespace first, and only a token whose whole core is a number is a candidate (Layer 0); each candidate is then associated with a fact type based on nearby keywords within a configurable proximity window. False positives (dates, hex colors, issue IDs, line references, version pins) are masked before extraction.

3. **Comparator** (`compare_facts` in `audit.py`) -- Matches mentions against facts and applies configurable tolerances. Version strings require exact match; numeric facts support percentage-based tolerances (e.g., +/-10% for growing metrics like node_count).

4. **Coverage** (`audit_coverage.py`) -- Reports, for every declared fact, whether the run checked anything at all, and the scan surface it ran over. A count of findings describes what the audit FOUND; coverage describes what it COVERED, and the two were measured to differ by a factor of nine (see *Coverage reporting*).

### Fact Types

| Fact Name | Source | Default Tolerance | Description |
|-----------|--------|-------------------|-------------|
| `version` | `pyproject.toml` / `package.json` / `Cargo.toml` | 0.0 (exact) | Project version string |
| `node_count` | graph DB `nodes` table | 0.10 (+/-10%) | Total graph nodes |
| `edge_count` | graph DB `edges` table | 0.10 (+/-10%) | Total graph edges |
| `language_count` | `code_symbols` file extensions | 0.0 (exact) | Distinct programming languages |
| `test_count` | `nodes.extra` JSON `tests.test_count` | 0.05 (+/-5%) | Total test count |
| `framework_count` | `nodes.extra` JSON `tests.framework` | 0.0 (exact) | Nodes with detected test frameworks |
| `mcp_tool_count` | `infrastructure.mcp_tools.MCP_TOOL_CATALOG` | 0.0 (exact) | Number of MCP tools. **Declared only for Beadloom itself** -- see Facts about the running package |
| `cli_command_count` | Click main group recursive traversal | 0.0 (exact) | Number of CLI commands. **Declared only for Beadloom itself** -- see Facts about the running package |
| `rule_type_count` | graph DB `rules` table | 0.0 (exact) | Number of architecture rules |

### Facts about the running package

Two of the nine facts are read out of the **running Beadloom package**, not out of the
project being audited: `mcp_tool_count` comes from `MCP_TOOL_CATALOG` and `cli_command_count`
from the live Click group. Both are true of Beadloom and false of everybody else, and until
3.0.1 both were collected unconditionally -- so in every adopter repository `docs audit`
declared two facts about the tool as facts about their documentation, and counted them in the
denominator of "N of 9 verified". Measured: a project named `invoice-svc` was told it had 18
MCP tools and 43 CLI commands.

`doc_sync/audit_self_surface.py` gates both. A surface fact is declared only when the project
under audit **is** the distribution whose surfaces this process can introspect, decided from
the name the project declares for itself (`pyproject.toml`, `package.json`, `Cargo.toml`)
against the running package's name. There is deliberately no directory-name fallback: a
project that names itself nowhere is unknown, and unknown must not resolve to a match.

A project with its own MCP server or CLI declares the count itself:

```yaml
docs_audit:
  extra_facts:
    mcp_tool_count:
      value: 7
      source: "our MCP server"
```

An `extra_facts` value withdraws the decline -- the fact is audited like any other. This is
the escape hatch every decline reason names in its own text.

### Three populations

A fact that could not be computed used to be dropped without trace, so the denominator moved
in silence: measured in-process on this repository, an unregistered CLI surface turned
`3 of 9 declared fact(s) verified` into `3 of 8` and nothing named the fact that left. Every
collector now records why it declared nothing, and the audit reports three populations:

| Population | Where it appears | Meaning |
|------------|------------------|---------|
| verified | `verified_facts`, `coverage[*].status == "verified"` | A document stated the fact and it was judged |
| not applicable to this project | `not_applicable[name].reason` | The audit declared no value here, and says why. Outside the denominator entirely |
| declared but unverified | `unverified_facts` | A value exists and nothing checked it. Named, never counted as fine |

`version` on this repository sits in the third population with zero mentions -- every version
literal in the tree is a dependency pin or a `docs_audit.ignore` triple with a stated reason,
so the audit is correctly reporting that no document states the current version as a claim.

### False-Positive Filtering

Extraction starts from a token boundary rule (Layer 0), then applies a 3-layer
false-positive reduction pipeline that reduces FP rate from ~60% to ~11%:

#### Layer 0: Token Boundary

A number that is part of a **larger token** is an identifier, not a claim, and is never
extracted. The bead reference `BDL-061.33`, the version `v2.2.0`, the language version
`Python 3.10`, the reference `PR #33`, the location `cli.py:645` and the ratio `33/40` all
end in digits that mean nothing on their own. Scanning for digits near a keyword read those
tails as facts and failed the Gate twice (BDL-UX #169).

**The boundary is whitespace, and only whitespace.** Whitespace is the one separator every
prose convention agrees on; `.` `-` `/` `:` `#` and `=` are precisely the characters that
hold identifiers together, so treating them as boundaries is the defect rather than the fix.

A token's **core** is the token with *wrapping* characters removed — markdown emphasis and
bracket/quote punctuation at either end, plus sentence punctuation at the **end** only
(`33.`, `33,`, `33:`). Sentence punctuation is deliberately not stripped from the start: a
leading `.` `#` or `-` is exactly what an identifier tail looks like once its prefix is
masked (masking `BDL-061` leaves `.33`), and stripping it would restore the bug.

A token becomes a fact candidate only when its whole core is a number — either all digits,
or digits in thousands groups (`6,390`, read whole as `6390`). Reading a grouped number by
its tail is the audit's worst available outcome: `1,067 nodes` used to extract as `067`,
compare equal to a project count of 67, and stamp a false claim **verified**.

This single rule subsumes the per-pattern skips it replaced (`0xFF`, `>=0.80`, `limit=10`,
`20+`, `33%`, `0-100`, `L42`, `file.py:15`) — none of those cores is a number.

#### Layer 1: Blocklist Modifiers

Numbers near modifier words or phrases are skipped as configuration parameters or thresholds, not factual claims. Checked within a +/-3 token window around the number, **scoped to the number's own clause** (see *Clause scope*).

**Single-word modifiers:** `default`, `max`, `minimum`, `limit`, `cap`, `target`, `threshold`, `about`, `approximately`, `per`, `depth`, `days`, `hours`, `minutes`, `seconds`.

**Multi-word phrases:** `up to`, `at least`, `at most`, `no more than`, `capped at`.

**Regex-based modifiers:** share patterns written with a space (`N %`). The no-space forms `N%`, `N+` and `key=N` are not number tokens at all and are rejected by Layer 0.

#### Layer 2: Proximity Scoring

When multiple fact keywords appear near a number, the closest keyword wins. On ties, keywords appearing *after* the number are preferred (e.g., "63 edges") over those before it. Uses the same `PROXIMITY_WINDOW = 5` but with distance-based ranking via `_keyword_distance()`, **scoped to the number's own clause**.

#### Clause scope

Both windows above stop at a phrase separator (`,` `;` `:` and the em/en dash). A word on the
far side of one neither modifies the number nor names what it counts, and a flat +/-N window
was measured wrong in both directions (BDL-UX #173):

| Sentence | Old behaviour | With clause scope |
|----------|---------------|-------------------|
| `The graph holds 316 edges, one per import.` | nothing extracted — `per` is in the window | `edge_count = 316` |
| `exposes 18 tools: 14 over the graph` | `tools` bound the `14` too, so a **breakdown** read as a restatement of the **total** | only the `18` |

Punctuation is a coarse proxy for syntax; it is also the only one available without a parser,
and it is what distinguishes *what this number counts* from *what the rest of the sentence
talks about*. The separator set was chosen by measurement rather than taste:

- Parentheses are deliberately **not** separators. They would cost the true verification in
  `MCP tools (18):` — an appositive restates its noun — and a lost true verification is
  precisely the silent false negative this rule exists to remove.
- Digit groups inside a number belong to the number: the comma in `6,390` is not a boundary
  between the number and the next word.

MEASURED repo-wide: 0 mentions gained, 5 lost, and all five were confirmed false positives
that had needed a `docs_audit.ignore` entry to stay quiet. Three of those entries were
retired with this change, because a suppression that matches nothing reads as coverage it
does not have.

#### Layer 3: File-Type Heuristics

Files with lower-confidence names suppress count-type fact matching (versions still matched):

- **Low-confidence filenames:** `SPEC.md`, `CONTRIBUTING.md`
- **Excluded glob patterns:** `_graph/features/*/SPEC.md`, `docs/**/features/*/SPEC.md`, `docs/**/features/**/SPEC.md`

The heuristic is load-bearing and was re-measured before being kept: shadow-scanning the 33
files it hides on this repo yields 17 count/version matches, **all** of them local examples,
historical figures ("edge count went from 51 to 146"), table rows or Python interpreter
versions. What changed is that the files are no longer hidden silently -- every one of them
is named on the scan surface with the pattern that excluded it (`--verbose`, or
`scan_surface` in `--json`).

#### Pattern Masking

The DocScanner also masks the following patterns before number extraction to prevent false matches:

| Pattern | Example | Regex |
|---------|---------|-------|
| ISO dates | `2026-02-19` | `\b\d{4}-\d{2}-\d{2}\b` |
| Month-year dates | `Feb 2026` | Month name + 4-digit year |
| Issue IDs | `#123`, `BDL-021` | `#\d+`, `[A-Z]+-\d+` |
| Hex colors | `#FF0000` | `#[0-9a-fA-F]{3,8}` |
| Hex literals | `0xFF` | `0x[0-9a-fA-F]+` |
| Version pins | `>=0.80`, `^1.2.3` | Operator + version |
| Line references | `:15`, `line 42`, `L42` | Various patterns |

Numbers 0 and 1 are always skipped as too common and ambiguous.

Several masks above are now subsumed by Layer 0 (`#123`, `0xFF`, `>=0.80`, `:15`, `L42`,
`0-100` are not number tokens). They are retained as defence in depth, because masking also
governs version extraction and the word positions used for proximity.

#### Declared blind spots (measured 2026-08-23, resolved 2026-08-24)

A false positive announces itself by failing the Gate; a false negative is silent. The three
silent ones measured on this repo are all settled -- one by a fix, two by being **declared in
the output** rather than left implicit. Nothing here is silenced by a tolerance or an
`ignore` entry: those hide a true-positive channel to quiet a false one.

| Blind spot | Resolution |
|------------|------------|
| A Layer 1 modifier word suppressed a number it did not modify (`316 edges, one per import`) | **Fixed** -- windows are clause-scoped (see *Clause scope*) |
| Counts below `MIN_READABLE_COUNT` (10) are not extracted for `*_count` facts, and 0/1 are never extracted at all | **Kept, and reported.** Removing the floor was re-measured: binding a single digit to an immediately following keyword yields 14 extra mentions on this repo, 13 of them ordinals (`5. Domain list`), table cells (`\| 5 \| tests \|`) and category breakdowns (`(4 tools):`) -- several of which would have failed the Gate. The floor stays; the facts it costs are now named `unreadable` in the coverage report, so nothing reads green about them |
| `SPEC.md` / `CONTRIBUTING.md` suppress count facts, and `docs/**/features/*/SPEC.md` is excluded outright (33 of 79 markdown files on this repo) | **Reported.** Every skipped file is named on the scan surface with the reason it was skipped |

The residual, and it is stated rather than hidden: a doc claim written below the floor
(`indexes 7 languages`) is invisible whether it is right or wrong. The floor is a property of
the extractor, so `unreadable_reason()` states it against the fact rather than leaving the
reader to infer it from a zero.

### Coverage reporting

`N mention(s) fresh` counts what the audit FOUND. It says nothing about the facts nothing was
found for, and on this repo the gap was the whole report: **9 facts declared, 13
verifications, all thirteen of the same fact.** A green `docs-audit` meant "one fact of nine
was checked" and printed as a clean bill of health (BDL-UX #173).

Every declared fact therefore carries a `FactCoverage`:

| Status | Meaning |
|--------|---------|
| `verified` | At least one mention was compared against the fact. This is about being **checked**, not about being right -- a stale mention is coverage |
| `not_covered` | No document states the fact. Nothing to check, said out loud |
| `unreadable` | The scanner cannot read a claim of this fact at all -- its value is below an extraction floor, or no keywords are registered for it. The fact is structurally unverifiable, and `reason` says why |

Two consequences hold by construction:

- A mention dropped by a `docs_audit.ignore` rule is **not** coverage. A suppression that
  hides the only mention of a fact leaves that fact unchecked.
- A fact with zero judged mentions is never counted as passing. It is named -- in the
  `Ground Truth` block, in `unverified_facts`, and on the `beadloom ci` line.

Coverage does not fail or WARN the gate step, deliberately. Silence in the documentation
about a fact is not a defect in the code, and a WARN that every project would carry on every
run would spend the channel `sync-check` needs for a genuinely missing baseline. The number
rides on the line everybody reads, and `--fail-if unverified>N` is there for a project that
wants every declared fact stated somewhere.

### Keyword-Proximity Matching

The DocScanner uses a sliding window of `PROXIMITY_WINDOW = 5` word positions around each detected number. If any keyword associated with a fact type appears within this window, the number is classified as a mention of that fact type.

Each fact type has a list of associated keywords:

| Fact Type | Keywords |
|-----------|----------|
| `language_count` | language, lang, programming language |
| `mcp_tool_count` | MCP, tool, server tool |
| `cli_command_count` | command, CLI, subcommand |
| `rule_type_count` | rule type, rule kind, rule |
| `node_count` | node, module, domain, component |
| `edge_count` | edge, dependency, connection |
| `test_count` | test, spec, assertion |
| `framework_count` | framework, supported framework |

Keywords use prefix matching (e.g., "language" matches "languages").

### Tolerance System

Tolerances control how much a mentioned value may deviate from the ground truth before being flagged as stale:

- **Exact match** (tolerance = 0.0): The mentioned integer must equal the ground truth exactly.
- **Percentage tolerance** (tolerance > 0.0): The mentioned value must fall within `[actual * (1 - t), actual * (1 + t)]`.
- **Version strings**: Always exact string comparison (leading `v` prefix is stripped).
- **Special case**: When the ground truth is 0, only an exact match of 0 is accepted (regardless of tolerance).

Tolerances are merged in order: built-in defaults, then user overrides from `config.yml`.

### Data Structures

#### Fact (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Fact identifier (e.g., `"version"`, `"node_count"`) |
| `value` | `str \| int` | Ground-truth value |
| `source` | `str` | Human-readable origin (e.g., `"pyproject.toml"`, `"graph DB"`) |

#### Mention (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `fact_name` | `str` | Associated fact type |
| `value` | `str \| int` | Mentioned value |
| `file` | `Path` | Source markdown file |
| `line` | `int` | Line number |
| `context` | `str` | Stripped line content for display |

#### AuditFinding (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `mention` | `Mention` | The documentation mention |
| `fact` | `Fact` | The ground-truth fact it was compared against |
| `status` | `str` | `"stale"` or `"fresh"` |
| `tolerance` | `float` | Applied tolerance |

#### AuditResult (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `facts` | `dict[str, Fact]` | All collected ground-truth facts |
| `findings` | `list[AuditFinding]` | Findings for matched mentions |
| `unmatched` | `list[Mention]` | Mentions with no corresponding fact |
| `coverage` | `dict[str, FactCoverage]` | Per-fact coverage -- what the run checked |
| `surface` | `ScanSurface \| None` | Documents read and skipped (`None` when built from mentions directly) |
| `not_applicable` | `dict[str, str]` | Fact name -> the reason no value was declared for it here |

`verified_facts` and `unverified_facts` (properties) name the first and third populations,
sorted; `not_applicable` carries the second with its reasons.

#### FactSet (frozen dataclass)

What `FactRegistry.collect_set()` returns: `facts` (`dict[str, Fact]`) and `not_applicable`
(`dict[str, str]`, fact name -> reason). The two are disjoint -- a name is in exactly one.
`FactRegistry.collect()` returns `facts` alone and cannot tell an absent fact from a declined
one, which is why a caller that reports coverage wants `collect_set()`.

#### FactCoverage (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `fact` | `Fact` | The declared fact |
| `mentions` | `int` | Mentions judged against it |
| `status` | `str` | `verified` / `not_covered` / `unreadable` |
| `reason` | `str \| None` | For `unreadable`, the scanner's statement of the limit |

#### ScanSurface (frozen dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `scanned` | `tuple[Path, ...]` | Files read for mentions |
| `excluded` | `tuple[ExcludedDoc, ...]` | Files never opened, each with `path` + `reason` |
| `count_suppressed` | `tuple[Path, ...]` | Files read for versions only (subset of `scanned`) |

### CLI Interface

```
beadloom docs audit [--json] [--fail-if EXPR] [--stale-only] [--verbose] [--path GLOB] [--project DIR]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json` | flag | `False` | Output results as structured JSON |
| `--fail-if` | `str` | `None` | CI gate expression (e.g., `stale>0`, `stale>=5`) |
| `--stale-only` | flag | `False` | Show only stale findings |
| `--verbose` | flag | `False` | Include extra detail (unmatched mentions, fact sources) |
| `--path` | `str` (multiple) | `None` | Override default scan paths with custom glob patterns |
| `--project` | `Path` | current directory | Project root |

The `--fail-if` expression supports the `stale` and `unverified` metrics with `>` and `>=`
operators. When the condition is met, the command exits with code 1.

- `stale>N` -- mentions that disagree with ground truth.
- `unverified>N` -- **declared facts the run checked nothing for** (`not_covered` +
  `unreadable`). Opt-in: a project that wants every fact it declares to be stated somewhere
  enforces it here.

`--verbose` additionally names the documents that were not read and those whose counts were
suppressed. `--json` carries `coverage`, `verified_facts`, `unverified_facts`,
`not_applicable`, `scan_surface`, and a `summary` with `declared_fact_count` /
`verified_fact_count` / `unverified_count` / `unreadable_count` / `not_applicable_count`
alongside the existing counts. `verified_facts`, `not_applicable` and
`summary.not_applicable_count` were added in 3.0.1; nothing was removed, so a consumer
parsing the 3.0.0 payload keeps working.

### Configuration

Tolerance overrides and extra facts are configured in `.beadloom/config.yml`:

```yaml
docs_audit:
  tolerances:
    test_count: 0.10
    node_count: 0.05
  extra_facts:
    custom_metric:
      value: 42
      source: "manual config"
```

- `tolerances`: Per-fact tolerance overrides merged on top of built-in defaults.
- `extra_facts`: User-defined facts with a `value` (str or int) and optional `source` label.
  A project declares its own `mcp_tool_count` or `cli_command_count` here; the value
  withdraws the decline described under Facts about the running package.

### Debt Report Integration

The docs audit contributes to the debt report under the `meta_doc_staleness` category. Stale findings from the audit increase the architecture debt score.

### Default Scan Paths

The DocScanner resolves markdown files using these default glob patterns:

- `*.md` -- Root-level markdown files
- `docs/**/*.md` -- All markdown files under `docs/`
- `.beadloom/*.md` -- Beadloom configuration markdown files

`CHANGELOG.md` is always excluded. Directories `.git`, `__pycache__`, `.venv`, `venv`, and `node_modules` are also excluded.

## API

### Public Functions

```python
def run_audit(
    project_root: Path,
    db: sqlite3.Connection,
    *,
    scan_paths: list[str] | None = None,
) -> AuditResult
```
Full audit facade: collect facts, scan docs, compare. Loads tolerance overrides from config if present.

```python
def compare_facts(
    facts: dict[str, Fact],
    mentions: list[Mention],
    tolerances: dict[str, float] | None = None,
    ignore: list[IgnoreRule] | None = None,
    not_applicable: dict[str, str] | None = None,
) -> AuditResult
```
Compare mentions against ground-truth facts with configurable tolerances. `not_applicable` is
carried through to the result unchanged, so the report can name the facts no value was
declared for.

```python
def foreign_project_reason(project_root: Path) -> str | None
```
Why Beadloom's own surfaces do not describe `project_root` -- `None` when the project under
audit is this distribution. `declared_project_name(project_root)` is the manifest read it
rests on, and returns `None` rather than a directory-name fallback.

```python
def parse_fail_condition(expr: str) -> tuple[str, str, int]
```
Parse a `--fail-if` expression. Returns `(metric, operator, threshold)`. Raises `click.BadParameter` on invalid input.

```python
def fail_condition_triggered(
    condition: tuple[str, str, int], *, stale_count: int, unverified_count: int
) -> bool
```
Whether the run crosses the condition's threshold. One place decides what each metric means, so the reported number and the exit code cannot disagree.

```python
def assess_coverage(
    facts: dict[str, Fact], findings: list[AuditFinding]
) -> dict[str, FactCoverage]
```
Per-fact coverage: what the run checked, as opposed to what it found (`audit_coverage.py`).

```python
def unreadable_reason(fact_name: str, value: str | int) -> str | None
```
The scanner's own statement of why no document could state this fact readably -- or `None` when one could (`scanner.py`).

### Public Classes

```python
class FactRegistry:
    def collect_set(self, project_root: Path, db: sqlite3.Connection) -> FactSet: ...
    def collect(self, project_root: Path, db: sqlite3.Connection) -> dict[str, Fact]: ...

class DocScanner:
    def scan(self, paths: list[Path]) -> list[Mention]: ...
    def scan_file(self, file_path: Path) -> list[Mention]: ...
    def resolve_paths(self, project_root: Path, scan_globs: list[str] | None = None) -> list[Path]: ...
    def resolve_surface(self, project_root: Path, scan_globs: list[str] | None = None) -> ScanSurface: ...

@dataclass(frozen=True)
class Fact: ...

@dataclass(frozen=True)
class FactSet: ...

@dataclass(frozen=True)
class Mention: ...

@dataclass(frozen=True)
class AuditFinding: ...

@dataclass(frozen=True)
class AuditResult: ...

@dataclass(frozen=True)
class FactCoverage: ...

@dataclass(frozen=True)
class ScanSurface: ...

@dataclass(frozen=True)
class ExcludedDoc: ...
```

## Invariants

- `FactRegistry.collect_set` never raises; each data source is wrapped in try/except, and a
  source that fails records its reason in `not_applicable` rather than dropping the fact.
- A fact is in `facts` or in `not_applicable`, never in both and never in neither.
- A fact read from the running Beadloom package is declared only when the project under
  audit is that distribution. Being correct about Beadloom does not excuse stating it
  about somebody else.
- Version extraction uses a priority fallback: `pyproject.toml` > `package.json` > `Cargo.toml` (first match wins).
- The DocScanner skips code blocks (lines between triple-backtick fences).
- False-positive masking replaces matched patterns with spaces of equal length to preserve character positions.
- Each number in a line is matched to at most one fact type (first keyword match wins).
- A modifier or keyword on the far side of a phrase separator is never matched to the number.
- A fact with zero judged mentions is never counted as verified, and is named in the output.
- A mention suppressed by `docs_audit.ignore` is not coverage.
- Tolerance merging order: built-in `DEFAULT_TOLERANCES` < user overrides from config.
- When ground truth is 0 and tolerance > 0, only an exact mention of 0 is accepted.

## Constraints

- Requires a populated SQLite database. Running the audit before `beadloom reindex` will produce no findings (no facts to collect from DB).
- Keyword-proximity matching is heuristic; it may produce false positives for numbers near unrelated keywords.
- The scanner only processes `.md` files; other documentation formats are not supported.
- Version detection relies on regex, not full TOML/JSON parsing, which may miss edge cases.
- The `--fail-if` expression only supports the `stale` and `unverified` metrics with `>` and `>=` operators.
- Coverage answers "was this fact checked", never "is this fact stated correctly everywhere" -- the scanner cannot know about a claim it did not extract, which is why the extraction floors are reported as `unreadable` rather than inferred from a zero.

## Testing

Test files: `tests/test_docs_audit_cli.py`, `tests/test_doc_scanner.py`,
`tests/test_doc_scanner_tokenization.py`, `tests/test_docs_audit_coverage.py`,
`tests/test_audit_ignore.py`

Key scenarios:

- **Fact collection**: Verify facts are collected from pyproject.toml, graph DB, MCP tools, CLI commands.
- **Version extraction**: Verify semantic versions are detected and version pins are ignored.
- **Number extraction**: Verify keyword-proximity matching for each fact type.
- **False-positive masking**: Verify dates, issue IDs, hex colors, line refs are masked.
- **Tolerance comparison**: Verify exact match, percentage tolerance, and zero-value special case.
- **Code block skipping**: Verify numbers inside code fences are ignored.
- **Config loading**: Verify tolerance overrides and extra facts from config.yml.
- **Full audit pipeline**: Verify `run_audit` end-to-end with stale and fresh findings.
- **Fail condition parsing**: Verify valid and invalid `--fail-if` expressions.
- **CLI integration**: Verify `beadloom docs audit` command options, output formats (JSON/Rich), and CI gate behavior.
- **Clause scope**: Verify a modifier in another clause does not suppress a genuine count, that one in the same clause still does, and that a breakdown after a separator is not bound to the total's noun.
- **Coverage**: Verify a stated fact reads `verified`, an unstated one `not_covered`, one below the extraction floor `unreadable`, that a stale mention still counts as coverage, and that an ignored mention does not.
- **Scan surface**: Verify excluded and count-suppressed documents are named with their reason in both the Rich and JSON output.
