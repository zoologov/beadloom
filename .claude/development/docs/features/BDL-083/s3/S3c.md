# S3c — the rules, lint, liveness, debt-report, TUI lint panel and FSD entries, re-measured

- **Date:** 2026-10-20
- **Bead:** `beadloom-al1i`
- **Version:** Beadloom 9.0.0 as S2 ships it: a git worktree of `features/BDL-083` at
  `cdaf3f78428061e51479723f59d666d952bf774e`. `git diff --quiet 41245dc7 cdaf3f78 -- src
  pyproject.toml uv.lock docs tests .beadloom/_graph` exits 0, so the code, the tests and the
  documents measured are those of `main` at `41245dc7`.
- **Machine:** macOS 27.0 (Darwin 27.0.0), arm64, CPython 3.12.12 from `uv sync --frozen` in
  the worktree, with the extras `tui`, `dev` and `languages` added for #352/#292, #222 and
  #323. Node 18.20.8 and npm 10.8.2 for the Steiger half of #323.
- **Index:** the worktree's own, built by `beadloom reindex` inside it, and one index per
  scratch project. The main checkout's index was not read or written.
- **Projects:** this repository (the worktree); copies of the monorepo fixture
  `tests/fixtures/monorepo`, each a fresh `git init`, one copy per probe; a throwaway
  TypeScript project for #221; a throwaway FSD project for #323, built from the entities
  example of the specification's slice-groups page, run through `beadloom init --yes`, with a
  second copy holding `steiger` 0.7.0 and `@feature-sliced/steiger-plugin` 0.8.0.
- **Room:** one room, this machine. No Linux leg and no other interpreter was entered. None of
  the seventeen entries depends on the platform, and that is a reading of the code, not a
  measurement on another leg.

### #352

- **Command:** `beadloom tui`, the lint panel. Not driven interactively: the panel's own
  data provider and widget were called the way the app calls them, by a scratch script,
  `LintDataProvider(conn, project_root).get_violations()` into
  `LintPanelWidget(violations=...).render()`.
- **Where:** the worktree (this repository's index) and a copy of the monorepo fixture.
- **Printed:**

  ```
  this repository:     severities from the engine: {'warn': 68}
                       panel header: Lint ℹ 68 info
  monorepo fixture:    severities from the engine: {'info': 1, 'warn': 2}
                       panel header: Lint ℹ 3 info
  ```

  `src/beadloom/tui/widgets/lint_panel.py` still compares with the literal `"warning"` in
  `_severity_icon`, `_severity_style` and the header's `warning_count`.
- **Outcome:** live. It is the same defect as #292, filed a second time from a reading of the
  two literals. The measurement above is the first one taken on a running widget for #352.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): the TUI lint panel rendered
  `Lint ℹ 68 info` over 68 findings the engine emitted at `warn` on this repository, and
  `Lint ℹ 3 info` over one `info` and two `warn` on the monorepo fixture.
- **Bead:** `beadloom-vu0a` (filed for #292. The same fix closes both, and S3z may archive
  #352 as a duplicate of #292 when it does).

### #341

- **Command:** `beadloom lint --strict` with a `forbid_import` rule whose `from:` is a tag
  matcher.
- **Where:** a copy of the monorepo fixture, rule `domain-no-io-imports-digest-os` rewritten
  from `from: "backend/src/digest/**"` to `from: { tag: layer-domain }`.
- **Printed:**

  ```
  Error: Invalid rules configuration: Rule 'domain-no-io-imports-digest-os':
  forbid_import.from must be a non-empty string                              (exit 2)
  ```

  The second half of the entry, an inert copy that reads like a glob typo, is gone with #328:
  on the unchanged fixture the `os/**` copy now prints `nothing_to_ban` at `info`, and a glob
  that names a source root prints "looks unmatchable" at `warn` (see #328).
- **Outcome:** live, for its first half: `forbid_import.from` still accepts one glob string
  and no tag matcher, so a layer-wide ban is still one rule per domain per library.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): `lint --strict` on the
  monorepo fixture with `forbid_import.from: { tag: layer-domain }` exited 2 with
  "forbid_import.from must be a non-empty string", and the inert-versus-typo half is closed
  by #328's fix.
- **Bead:** none exists. Proposed: `[BDL-UX #341] forbid_import.from accepts the matcher forms
  test_import_boundary.of accepts, a tag among them`.

### #340

- **Command:** `beadloom lint --strict` with a `require` rule whose `has_edge_to.kind` is a
  list.
- **Where:** a copy of the monorepo fixture, rule `feature-needs-domain` rewritten to
  `has_edge_to: { kind: [domain, service] }`.
- **Printed:**

  ```
  Error: Invalid rules configuration: Rule 'feature-needs-domain' require.has_edge_to:
  invalid kind '['domain', 'service']', must be one of ['adr', 'component', 'domain',
  'entity', 'feature', 'service']                                             (exit 2)
  ```

- **Outcome:** live. The list is refused, so the rule does not silently degrade, but the rule
  language still has no any-of for `kind`, and the refusal reads as a misspelled kind name
  rather than saying that a list is not accepted. The author is still left to write the
  weaker `has_edge_to: {}`.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): `lint --strict` on the
  monorepo fixture with `has_edge_to: { kind: [domain, service] }` exited 2 with
  "invalid kind '['domain', 'service']'", and no any-of form exists.
- **Bead:** none exists. Proposed: `[BDL-UX #340] the node matcher's kind accepts a list
  (any-of), or the loader refuses a list by saying lists are not accepted`.

### #328

- **Command:** `beadloom lint --strict`, with and without sabotage.
- **Where:** a copy of the monorepo fixture, whose `rules.yml` carries the entry's own shape,
  `domain-no-io-imports-digest-os` with `to: "os/**"`. `beadloom ci` in a clean room was not
  re-run: `ci` reads the same findings through the same engine, and the lint verdict is the
  claim the entry makes.
- **Printed:**

  ```
  clean tree, lint --strict --format json                                     (exit 0)
    domain-no-io-imports-digest-os nothing_to_ban info | 0 imports of `os/**` in the
    project; the rule is live: its `to` glob 'os/**' matches 0 of 4 indexed import
    paths, and an import of `os` would fire it
  sabotage: `import os`, `from os import path`, `import os.path` in
  backend/src/digest/sections.py                                              (exit 1)
    forbid_import error backend/src/digest/sections.py 18 | ... imports 'os' ...
    forbid_import error backend/src/digest/sections.py 19 | ... imports 'os' ...
    forbid_import error backend/src/digest/sections.py 20 | ... imports 'os.path' ...
  control: `to: "backend/src/os/**"`, a source root in `to:`                   (exit 0)
    rule_liveness warn | Rule 'domain-no-io-imports-digest-os' looks unable to fire: its
    `to` glob 'backend/src/os/**' matches 0 of 4 indexed import paths and looks
    unmatchable: it begins with 'backend', a directory of the project's source files ...
  ```

- **Outcome:** closed. A live rule with nothing to ban is told from an unmatchable glob, at a
  different severity and in different words, which is the entry's Expected. Fixed by S1b
  (`beadloom-q8x6`).
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): on the monorepo fixture
  `lint --strict` reported `to: os/**` as `nothing_to_ban` at `info` ("the rule is live ... an
  import of `os` would fire it"), three sabotage imports gave three errors and exit 1, and a
  `to:` naming a source root was reported as "looks unmatchable" at `warn`.
- **Bead:** none (closed by `beadloom-q8x6`).

### #323

- **Command:** `beadloom lint --strict` after `beadloom init --yes`; `steiger ./src` (Steiger
  0.7.0, `@feature-sliced/steiger-plugin` 0.8.0, recommended set), the project's
  `lint:fsd` script.
- **Where:** a throwaway FSD project: `src/app`, `src/shared/lib`, and the entities example
  `entities/payment/{invoice,receipt,transaction}`, `entities/user`, `entities/product`, each
  slice with `model/`, `ui/` and an index. `init --yes` chose the `fsd` preset (9 nodes,
  `fsd-layers`, `fsd-public-api`, `fsd-slice-shape`, the cohesion rules). The receipt model
  imports invoice through an `@x` API under three namings.
- **Printed:**

  ```
  naming                                   Beadloom lint --strict       Steiger forbidden-imports
  invoice/@x/receipt.ts                    exit 0, edge via: @x         1
  invoice/@x/payment-receipt.ts            exit 1: fsd-layers,          1
                                           fsd-public-api
  invoice/@x/payment/receipt/index.ts      exit 1: fsd-layers,          0
                                           fsd-public-api
  ```

  Steiger also printed four `fsd/insignificant-slice` findings in every naming. They come
  from the probe's thin slices and are the same in all three rows.
  `docs/domains/graph/features/rule-engine/SPEC.md` "Where Beadloom and Steiger differ" still
  lists five rows and not this one.
- **Outcome:** live. No naming of a grouped slice's `@x` API passes both linters. The
  measurement is the entry's, row for row.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7) with Steiger 0.7.0: on a probe
  of the slice-groups entities example, `invoice/@x/receipt` was clean in Beadloom and a
  Steiger `forbidden-imports` finding, `invoice/@x/payment/receipt/index` was clean in Steiger
  and two Beadloom errors (`fsd-layers`, `fsd-public-api`), and the SPEC's difference table
  does not name the case.
- **Bead:** none exists. Proposed: `[BDL-UX #323] a grouped slice's @x API has a form both
  Beadloom and Steiger accept, or the difference is a row of the SPEC table and a sentence of
  the FSD overlays` (the entry leaves the choice to the owner).

### #312

- **Command:** `beadloom lint`, `beadloom config-check`.
- **Where:** a copy of the monorepo fixture, `scope: no-such-node-anywhere` added to the
  `require` rule `feature-needs-domain` and to the `forbid_import` rule
  `domain-no-io-imports-digest-os`.
- **Printed:**

  ```
  lint --strict                                                              (exit 0)
    stderr: empty
    stdout: the same five rows as without the key
  config-check                                                               (exit 0)
    no line names `scope`
  ```

- **Outcome:** live. The loader accepts a `scope:` that names no node on two rule types that
  never read it, and neither command says so.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): on the monorepo fixture
  `scope: no-such-node-anywhere` on a `require` and a `forbid_import` rule left `lint
  --strict` at exit 0 with an empty stderr and `config-check` at exit 0 with no line about
  the key.
- **Bead:** `beadloom-ba9w.4`.

### #295

- **Command:** `beadloom lint`.
- **Where:** a copy of the monorepo fixture with one hand-written node added to
  `backend.yml`, `ref_id: stray`, `kind: domain`, `tags: 3`, reachable by no rule.
- **Printed:**

  ```
  beadloom reindex                                                           (exit 0)
    nothing about the node; nodes.extra for stray = {"tags": 3, "config": {}}
  beadloom lint --strict --no-reindex                                        (exit 1)
    File ".../src/beadloom/graph/rules/node_tags.py", line 85, in _read_all_tags
      tags[str(row[0])] = set(declared)
    TypeError: 'int' object is not iterable
  ```

- **Outcome:** live. One malformed node fails the whole run with a traceback, and the indexer
  wrote it without a word.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): a fixture node written
  `tags: 3` was indexed at exit 0 without a message, and `lint --strict` then exited 1 with
  `TypeError: 'int' object is not iterable` from `node_tags.py:85`.
- **Bead:** `beadloom-efcb`.

### #294

- **Command:** any reader of node tags; measured at the function, as the entry was:
  `graph.rules.node_tags.NodeTags.of(ref)` against `graph.loader.get_node_tags(conn, ref)`
  over an in-memory `nodes` table, by a scratch script.
- **Where:** the worktree's environment. The table is the script's own.
- **Printed:**

  ```
  extra        batch     one-at-a-time
  SQL NULL     set()     set()
  null         set()     raises builtins.AttributeError
  3            set()     raises builtins.AttributeError
  "x"          set()     raises builtins.AttributeError
  {not json    set()     raises json.decoder.JSONDecodeError
  ```

  The disagreement is stated in the docstring of `node_tags._read_all_tags`, with this same
  table. The docstring of `loader.get_node_tags` does not mention it.
- **Outcome:** live. The one-at-a-time reader still raises exceptions this project does not
  define and that name no node, and the difference is stated on one side of the pair only.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): `loader.get_node_tags` raised
  `AttributeError` on `extra` values `null`, `3` and `"x"` and `JSONDecodeError` on
  `{not json`, where `NodeTags.of` answered `set()` for all four.
- **Bead:** `beadloom-ui47`.

### #292

- **Command:** `beadloom tui`, the Lint panel; measured as in #352, through the panel's data
  provider and widget.
- **Where:** the worktree (this repository's index).
- **Printed:** `severities from the engine: {'warn': 68}` and `panel header: Lint ℹ 68 info`.
  `VALID_RULE_SEVERITIES` is still `frozenset({"error", "warn"})`
  (`graph/rules/types.py:27`), with `INFO_SEVERITY = "info"` beside it since S1b, and the
  panel still branches on `"warning"`.
- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): the TUI lint panel rendered
  `Lint ℹ 68 info` and no warning count over this repository's 68 `warn` findings.
- **Bead:** `beadloom-vu0a`.

### #291

- **Command:** `beadloom status --debt-report --json`; the collector's
  `_count_violations(conn, root)` called directly by a scratch script.
- **Where:** the worktree (this repository's index).
- **Printed:**

  ```
  status --debt-report --json                                                (exit 0)
    "name": "rule_violations", "score": 0.0, "details": {"errors": 0, "warnings": 0}
  _count_violations -> 0 0 {}
  lint --strict --no-reindex over the same index: 68 findings at warn
  ```

  `application/debt_report/collect.py:326-331` still tries `<root>/rules.yml`, then
  `<root>/.beadloom/rules.yml`, and returns zero when neither is a file. The rules live in
  `.beadloom/_graph/rules.yml`.
- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): the debt report's
  `rule_violations` category read 0 errors and 0 warnings on this repository while `lint`
  over the same index reported 68 warnings, because the collector looks for `rules.yml` in
  two places neither of which holds it.
- **Bead:** `beadloom-is2z`.

### #222

- **Command:** `uv run pytest tests/test_init_one_table_over_every_axis.py`.
- **Where:** the worktree, `dev` extra installed.
- **Printed:**

  ```
  172 passed in 8.33s
  ```

  The module's invariant 3 still reads "where THIS run wrote both the rules and the graph
  file the failing node came from", and `RunOutcome` still carries
  `wrote_the_failing_graph_file` and computes `corner` from it, while the product decides at
  the node grain in `services/commands/setup.py` `_this_run_wrote_the_node_that_fails`.
- **Outcome:** live. The suite passing is the entry's point: the cross-check computes the
  file grain and cannot tell the two rules apart on any tree it builds.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): the module passed 172 tests
  and still states invariant 3 and computes `RunOutcome.corner` at the graph-file grain the
  implementation stopped using.
- **Bead:** `beadloom-tgo8`. By subject the entry belongs to `init`'s bootstrap report (S3d's
  area), and it was measured here as the PLAN assigns it.

### #221

- **Command:** `beadloom init --bootstrap` on a project carrying an inherited
  `.beadloom/_graph/legacy.yml`.
- **Where:** a throwaway TypeScript project (`package.json`, `src/index.ts`), committed, with
  `legacy.yml` holding one domain `ledger` with no parent and no `docs:`.
- **Printed:**

  ```
  init --bootstrap                                                           (exit 1)
    Error: the graph this command just wrote does not pass the rules this command wrote
    alongside it.
      domain-needs-parent: ledger (.beadloom/_graph/legacy.yml)
    This is a defect in Beadloom's bootstrap rather than in your project — please report
    it with the rule name(s) above.
  git diff .beadloom/_graph/legacy.yml
    +  docs:
    +  - docs/domains/ledger/README.md
  ```

- **Outcome:** live. The run added only a `docs:` field to a node an earlier run wrote, and
  the report asks the adopter for a bug report about it.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): `init --bootstrap` over a
  `legacy.yml` holding one undocumented orphan exited 1 with "This is a defect in Beadloom's
  bootstrap rather than in your project — please report it", having changed only that node's
  `docs:` field.
- **Bead:** `beadloom-0mb5`. By subject the entry belongs to `init`'s bootstrap report (S3d's
  area), and it was measured here as the PLAN assigns it.

### #201

- **Command:** `beadloom lint --no-reindex --format porcelain` (the default when stdout is
  not a terminal) against `--format json` over the same index.
- **Where:** the worktree (this repository's index).
- **Printed:**

  ```
  porcelain:  site-fsd-layers:rule_liveness:warn::::
  json:       "message": "Rule 'site-fsd-layers' cannot fire: no live 'depends_on' edge
              runs between two of its layers. It is counted as evaluated but checks nothing"
  ```

  `graph/linter.py` `format_porcelain` still writes
  `rule_name:rule_type:severity:file_path:line:from_ref:to_ref` and no message. Its docstring
  now names `severity`, so the entry's `m7` remark is closed.
- **Outcome:** live. Every advisory row with no file or node collapses to its rule name, type
  and severity, so two findings of one rule that differ only in their message are
  byte-identical in porcelain.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): piped `lint` printed
  `site-fsd-layers:rule_liveness:warn::::` for a finding whose JSON message explains why the
  rule cannot fire, and the porcelain record still carries no message field.
- **Bead:** none exists. Proposed: `[BDL-UX #201] lint's porcelain record carries the
  finding's message, so a stand-down and a per-claim finding are not byte-identical`.

### #197

- **Command:** `beadloom lint --strict`.
- **Where:** a copy of the monorepo fixture with three probe rules added, each at
  `severity: error` and each wholly unable to fire: `scenario_coverage` over
  `features: "no-such-suite/**/*.feature"`, `module_coverage` over
  `source_root: no-such-root/`, `unregistered_feature_candidate` over `for: { kind: entity }`
  (the fixture holds no entity).
- **Printed:**

  ```
  lint --strict --format json                                                (exit 0)
    s197-candidates rule_liveness warn | ... its `for` kind 'entity' matches none of the 12
      nodes in the graph. It is counted as evaluated but checks nothing
    s197-modules    rule_liveness warn | ... its source_root 'no-such-root/' holds no
      module, on disk or in the index ...
    s197-scenarios  rule_liveness warn | the acceptance suite glob
      `no-such-suite/**/*.feature` matches no file, so no node was checked ...
    summary: rules_inert 4, error_count 0
  ```

- **Outcome:** live, for all three rule types the 2026-08-27 amendment left open: a total
  stand-down of a rule declared `error` is reported at `warn` and `lint --strict` exits 0.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): on the monorepo fixture,
  `scenario_coverage`, `module_coverage` and `unregistered_feature_candidate` rules declared
  `severity: error` and wholly inert each reported their stand-down at `warn`, and
  `lint --strict` exited 0 with `error_count 0`.
- **Bead:** none exists. Proposed: `[BDL-UX #197] scenario_coverage, module_coverage and
  unregistered_feature_candidate report a total stand-down at the rule's declared severity`.

### #158

- **Command:** `beadloom lint --strict` with a subtree cardinality key.
- **Where:** a copy of the monorepo fixture with a `check` rule
  `for: { kind: service }, max_subtree_symbols: 1`.
- **Printed:**

  ```
  Error: Invalid rules configuration: Rule 's158-subtree': check must specify at least one
  of 'max_symbols', 'max_files', or 'min_doc_coverage'                       (exit 2)
  ```

  `graph/rules/loader.py` reads `max_symbols`, `max_files` and `min_doc_coverage` under
  `check:` and no subtree or child-count key.
- **Outcome:** live. The "bounded context too large overall" question still has no key.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): a `check` rule with
  `max_subtree_symbols` was refused at exit 2, and the loader knows only `max_symbols`,
  `max_files` and `min_doc_coverage`.
- **Bead:** `beadloom-1d70`.

### #148

- **Command:** `beadloom lint --strict --no-reindex` with stdout and stderr each sent to a
  file.
- **Where:** the worktree (this repository's index).
- **Printed:**

  ```
  exit 0; stdout 70 lines: 2 `# layer_population:...` lines and 68 porcelain records;
  stderr empty; no line holds `Errors:`, `Warnings:` or `rules evaluated`
  ```

  On a terminal the same run ends `Errors: 0, Warnings: N (M rules evaluated, ...)` (seen
  with `--format rich` on the monorepo fixture). `lint --help` now states `--format`
  "(default: rich if TTY, porcelain if piped)".
- **Outcome:** live. The shape still switches on the terminal, and the piped shape carries no
  summary line. The help text now says so, which is the documentation half only.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): piped `lint --strict` printed
  porcelain rows and no `Errors/Warnings` summary on either stream, while `--help` names the
  terminal-dependent default.
- **Bead:** none exists. Proposed: `[BDL-UX #148] lint keeps one output shape by default
  whether or not stdout is a terminal, or prints its summary line in both`.

### #147

- **Command:** `beadloom lint` against `beadloom lint --no-reindex`, by the sha256 of
  `.beadloom/beadloom.db`; then both forms over a tree changed after the index was built;
  then `beadloom ci --no-reindex` over that tree.
- **Where:** a copy of the monorepo fixture, index rebuilt fresh, `journal_mode=wal`.
- **Printed:**

  ```
  before:                          e9b5bfb0d26c   .beadloom: beadloom.db
  after lint --no-reindex --strict e9b5bfb0d26c   .beadloom: beadloom.db, -shm, -wal
  after lint --strict              13cfbe51ce82
  `import os` appended to backend/src/digest/sections.py, index not rebuilt:
    lint --no-reindex --strict     exit 0, stderr empty, no word about the index's age
                                   Errors: 0, Warnings: 2 (4 rules evaluated, ...)
    lint --strict                  exit 1
    ci --no-reindex                exit 1 on sync-check, and
                                   lint PASS: 0 error(s), 2 warning(s), ...
  ```

- **Outcome:** live, as the 2026-09-29 re-measurement left it. Fixed and still fixed: the
  default names its write in `--help`, and `--no-reindex` leaves `beadloom.db` byte-identical.
  Both residues reproduce: (a) the read-only form leaves `beadloom.db-wal` and
  `beadloom.db-shm` beside a WAL index, and (b) it answers about a stale index without
  saying so, and `ci --no-reindex` reports `lint PASS` over a live `forbid_import` error.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`main` 41245dc7): `lint --no-reindex` left the
  index file's sha256 unchanged but created `-wal` and `-shm`, and over a tree with a new
  `import os` it exited 0 silently where plain `lint --strict` exited 1, and `ci --no-reindex`
  printed `lint PASS` over the same violation.
- **Bead:** none exists. Proposed: `[BDL-UX #147] lint --no-reindex says when the index is
  older than the tree, and leaves no -wal or -shm beside a WAL index`.

## Not this area

None of the seventeen. #221 and #222 are about `init`'s bootstrap report by subject, which is
S3d's area. They were measured here because the PLAN assigns them here, and their beads are
named above.

## Summary

| Entry | Outcome | Bead |
|---|---|---|
| #352 | live (duplicate of #292) | `beadloom-vu0a` |
| #341 | live (its second half closed by #328) | proposed: `from:` accepts a tag matcher |
| #340 | live | proposed: kind accepts a list, or the refusal names the list |
| #328 | closed | none (closed by `beadloom-q8x6`) |
| #323 | live | proposed: a grouped `@x` form both linters accept, or a SPEC row |
| #312 | live | `beadloom-ba9w.4` |
| #295 | live | `beadloom-efcb` |
| #294 | live | `beadloom-ui47` |
| #292 | live | `beadloom-vu0a` |
| #291 | live | `beadloom-is2z` |
| #222 | live | `beadloom-tgo8` |
| #221 | live | `beadloom-0mb5` |
| #201 | live | proposed: porcelain carries the message |
| #197 | live | proposed: three rule types stand down at their declared severity |
| #158 | live | `beadloom-1d70` |
| #148 | live | proposed: one output shape by default, or the summary in both |
| #147 | live (two residues) | proposed: `--no-reindex` names a stale index, no -wal/-shm |

Counts: 1 closed, 16 live, 0 Won't-fix candidates, 0 not reproducible, 0 not this area.
Of the 16 live entries, 9 have an existing bead (`beadloom-vu0a` covers two) and 7 need a
bead under `beadloom-ba9w`. The proposed titles are above.
