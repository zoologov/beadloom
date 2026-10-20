# S3d — the init, scanning, index, doctor, ctx, impact and flow-setup entries, re-measured

- **Date:** 2026-10-20
- **Bead:** `beadloom-d9te`
- **Version:** Beadloom 9.0.0 as S2 ships it: a git worktree of `features/BDL-083` at
  `cdaf3f78428061e51479723f59d666d952bf774e`. `git diff --quiet 41245dc7 cdaf3f78 -- src
  pyproject.toml uv.lock docs` exits 0, so the code measured is `main` at `41245dc7`. A second
  worktree at `9f1b6fd2` (same paths, `git diff --quiet` 0) served #290's cold runs and `doctor`.
- **Machine:** macOS 27.0 (Darwin 27.0.0), arm64, CPython 3.12.12 from `uv sync --frozen`, with
  the `languages` extra for #338, #339 and #350. #324 ran in a second environment without it
  (`UV_PROJECT_ENVIRONMENT=<scratchpad>/venv-bare`), and #293 with `--all-extras`.
- **Index:** each worktree's own. The main checkout's index was not touched, and the throwaway
  projects and the monorepo fixture copies (`tests/fixtures/monorepo`) lived in the scratchpad.
- **Room:** one room, this machine. No Linux leg and no other interpreter was entered. For #293
  the CI logs of `ci.yml` since 2026-09-29 were read as well.

### #356

- **Command:** `beadloom setup-agentic-flow` (`--tool cursor`, then `tools: [claude, cursor]`),
  `beadloom setup-mcp --tool cursor`, `beadloom init --bootstrap`, `beadloom config-check`
- **Where:** a throwaway Python project (`src/app/`, `pyproject.toml`), `git init`, then
  `init --yes`, then the flow commands.
- **Printed:**

  ```
  Wrote .cursor/rules/beadloom-flow.mdc (cursor)          447 lines, "alwaysApply: true"
  Wrote .cursor/rules/beadloom-{coordinator,task-init,checkpoint,templates}.mdc (cursor)
  grep -c DOD-MARKER .cursor/rules/beadloom-flow.mdc       -> 1  (a line in .beadloom/flow/claude/CLAUDE.md)
  .cursor/mcp.json and .mcp.json (init --bootstrap):       "command": "beadloom", "args": ["mcp-serve"]
  task-init.md:137  plan="$(mktemp -d)/plan.json"   # an absolute path outside the project
  config-check, cursor-only: 0 lines naming .claude/agents
  config-check, both tools, beadloom-flow.mdc removed (rc 1):
    - .cursor: `cursor` lacks 3 layer(s) `claude` reads: core (1 fragment(s)), stack:python
      (1 fragment(s)), project (.beadloom/flow/claude/CLAUDE.md)
  config-check, tools: [claude], .cursor/rules/*.mdc left on disk: 0 lines naming .cursor/rules
  .beadloom/config.yml after init: no project_name key
  src/beadloom/services/mcp_server.py handle_complete_bead: no COMPLETED check (code read)
  ```

- **Outcome:** partly closed. (a), (e), (g) and both further defects are closed: Cursor gets the
  core, the project layer, the STACK overlay and the four commands as `alwaysApply` rules,
  `config-check` names a tool that lacks a layer, `docs/guides/project-overlays.md` states which
  kind reaches which tool, `setup-mcp` and `init --bootstrap` write the portable `beadloom`
  command, the plan file is under `mktemp -d`, and a cursor-only `config-check` no longer asks
  for `.claude/agents/`. Still live: (b) has no gate (no COMPLETED check in `complete_bead`).
  (c), (d) and (f) are features filed outside the epic. Two follow-ups also reproduce: a
  `.cursor/rules/` file left after `tools:` drops cursor is not reported (`beadloom-ba9w.26`),
  and `init` writes no `project_name:` (`beadloom-s9op`).
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `setup-agentic-flow --tool cursor` on a
  throwaway project wrote `.cursor/rules/beadloom-flow.mdc` (447 lines, `alwaysApply: true`, the
  project layer included) and four command rules, and `setup-mcp --tool cursor` wrote
  `"command": "beadloom"`. Parts (b), (c), (d) and (f) remain under their own beads.
- **Bead:** `beadloom-ybxm` (closed, S2h) for (a)/(e)/(g). Live: `beadloom-ujm0` (b),
  `beadloom-9yny` (c), `beadloom-vtul` (d), `beadloom-rkiu` (f), plus `beadloom-ba9w.26` and
  `beadloom-s9op`.

### #351

- **Command:** `beadloom init --yes`
- **Where:** a copy of the monorepo fixture with its hand-written `.beadloom/` moved aside,
  `git init`, one commit.
- **Printed:**

  ```
  Initialized beadloom (mode: bootstrap)
    Graph: 8 nodes, 7 edges (preset: monolith)
  scan_paths: [backend, frontend]
  nodes: mono351 (service), src, src-app, src-entities, src-features, src-pages, src-shared,
         src-widgets  — every source under frontend/src/, none under backend/
  ```

- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `init --yes` on a copy of the monorepo
  fixture wrote 8 nodes, all under `frontend/src/`, with preset `monolith`. The backend under
  `backend/pyproject.toml` got no node, and the summary did not say so.
- **Bead:** none found. Proposed: "[BDL-UX #351] init --yes on a monorepo writes nodes for the
  frontend only: a pyproject.toml below the root is not read as a project, and the summary does
  not name the project that got no node".

### #350

- **Command:** `beadloom ctx widgets-kpi-panel --json`
- **Where:** a copy of the monorepo fixture (its own `.beadloom/`), `reindex --full`.
  `KpiPanel.spec.ts` imports `vitest`, `frontend/package.json` names `vitest` and no jest.
- **Printed:** `"tests": {"framework": "jest", "test_files": ["frontend/src/widgets/kpi-panel/ui/KpiPanel.spec.ts"], "test_count": 1}`
- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `ctx widgets-kpi-panel --json` on the
  monorepo fixture printed `"framework": "jest"` for a spec file that imports `vitest`.
- **Bead:** none found. Proposed: "[BDL-UX #350] ctx --json names jest for a vitest spec file:
  the framework comes from the file pattern and not from its imports or the project's
  dependencies".

### #339

- **Command:** `beadloom reindex`, `beadloom ctx digest --json`, `ctx application-digest --json`
- **Where:** the monorepo fixture copy, `backend/tests/unit/digest/test_sections.py.fixture`
  renamed to `.py` (the fixture keeps it uncollected). The test imports `digest.sections`.
- **Printed:**

  ```
  Tests:   4 files (4 bound to a node (3 beside the code), 0 unplaced)
  test_files: backend/tests/unit/digest/test_sections.py | unit | application-digest | mirror
  ```

- **Outcome:** live. The deeper root wins, and no line says that two roots resolved.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): on the monorepo fixture,
  `backend/tests/unit/digest/test_sections.py` (which imports `digest.sections`) is bound to
  `application-digest` by mirror placement, with no warning.
- **Bead:** none found. Proposed: "[BDL-UX #339] test-mirror resolution lets a deeper root win on
  a directory that holds code: the module file must exist, or two resolutions are reported and
  none is bound".

### #338

- **Command:** `beadloom reindex --full`, `beadloom lint --strict`
- **Where:** the monorepo fixture copy, `languages` extra installed.
- **Printed:**

  ```
  edges: app-styles|entities-metric|depends_on|{"derived": "imports"}
  code_imports into entities-metric from frontend/src/app/: base.spec.ts only (base.ts, index.ts import none)
  # layer_population:fsd-layers:depends_on:7:9:2
  ```

- **Outcome:** live. The edge comes from the spec file alone, carries no test marker, and the
  layer rule judges it.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): on the monorepo fixture the edge
  `app-styles → entities-metric` is derived from `base.spec.ts` only, its `extra` is
  `{"derived": "imports"}`, and `fsd-layers` counts it among the 7 edges it judged.
- **Bead:** none found. Proposed: "[BDL-UX #338] an import from a spec file beside the code
  becomes an unmarked depends_on edge: edges carry whether their source is a test, and layer
  rules include or exclude them explicitly".

### #337

- **Command:** `beadloom ctx widgets-kpi-panel --json` after an `@node:widgets-kpi-panel` tag in
  `frontend/e2e/features/kpi.feature`; `beadloom doctor`; `beadloom lint --strict`
- **Where:** the monorepo fixture copy, `reindex` after adding the feature file.
- **Printed:** the JSON keys are `version, focus, graph, text_chunks, code_symbols, sync_status,
  constraints, intent, routes, tests, test_placements, test_unplaced, test_recognition, warning`.
  `scenario` and `kpi.feature` appear nowhere in it. `doctor` and `lint --strict` print no line
  about the file.
- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): an `@node:` tag in a `.feature` file
  outside `tests/acceptance/features/` reached neither `ctx --json` nor `doctor` nor `lint`.
- **Bead:** none found. Proposed: "[BDL-UX #337] a @node: tag in a .feature file outside the
  scenario rules' glob is read by nobody: ctx lists the node's scenarios, or doctor names the
  file no glob reaches".

### #324

- **Command:** `beadloom init` (the wizard), answering `cancel` at "Proceed with this graph?"
- **Where:** a throwaway TypeScript project (8 `.ts` files, `register` importing `login`), run
  in the environment without the `languages` extra. Control: the same project answered `yes`.
- **Printed:**

  ```
  yes:    Indexed 0 symbols, 0 imports ... 8 TypeScript files, no parser installed — install with: ...
  cancel: Cancelled — the graph was written before this prompt. .beadloom/_graph/ holds it: delete
          .beadloom/ to undo, or edit those files and run beadloom reindex.     (nothing else, rc 0)
          .beadloom/beadloom.db written by the run (233472 bytes)
  ```

- **Outcome:** live. The cancel branch still re-indexes (`setup.py:1979-1983`) and the line is
  echoed only under `if "reindex" in result:` (`setup.py:1985`).
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): the wizard answered `cancel` wrote
  `beadloom.db` and printed no line naming the 8 TypeScript files no parser read, while the
  `yes` answer printed it.
- **Bead:** none found. Proposed: "[BDL-UX #324] the init wizard cancelled at the graph review
  re-indexes and does not print the line naming the code no installed parser read".

### #320

- **Command:** `beadloom ctx graph --json --max-nodes 3`
- **Where:** the worktree of this repository.
- **Printed:** `nodes 3 edges 6 edges naming a node outside nodes 3`, for example
  `{'src': 'contracts', 'dst': 'amqp_body', 'kind': 'depends_on'}`. Edge keys are `dst, kind,
  src`, with no boundary marker.
- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `ctx graph --json --max-nodes 3`
  returned 3 nodes and 6 edges, 3 of which name a node absent from `nodes`, unmarked.
- **Bead:** `beadloom-ba9w.15`.

### #319

- **Command:** `beadloom ctx graph --json`, `beadloom ctx --help`
- **Where:** the worktree of this repository.
- **Printed:**

  ```
  options: --json --markdown --depth --max-nodes --max-chunks --intent --project   (no budget)
  10 chunks; lengths [1955, 1849, 1681, 1623, 1934, 1763, 716, 11, 274, 1468]
  owners: c4-diagrams/SPEC.md, services/cli.md, graph-diff/SPEC.md, import-resolver/SPEC.md,
          services/mcp.md, scenario-binding/SPEC.md, snapshot/SPEC.md, application/README.md,
          getting-started.md, c4-diagrams/SPEC.md
  ```

- **Outcome:** live. No token budget. The cap is a count (11 to 1955 characters per chunk), and
  the `graph` domain's own `README.md` is not among the 10 chunks.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `ctx graph --json` returned 10 chunks
  between 11 and 1955 characters, none from the focus node's own README, and `ctx` takes no
  budget option.
- **Bead:** `beadloom-ba9w.14`.

### #317

- **Command:** `beadloom ctx graph|context-oracle|cli --json`, `beadloom ctx graph`
- **Where:** the worktree of this repository.
- **Printed:**

  ```
  rules table: 15 rule types (cardinality 7, deny 1, doc_area_coherence 1, forbid_cycles 1,
    forbid_import 4, layers 2, module_coverage 1, require 3, scenario_binding 1, ...)
  graph 4 ['deny', 'require']  (the same 4 for context-oracle and cli)
  Markdown output: 0 lines naming domain-needs-parent / no-domain-depends-on-service / architecture-layers
  ```

- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): over an index of 15 rule types, `ctx
  --json` listed 4 constraints of types `deny` and `require` only for three different nodes,
  and the Markdown output listed none.
- **Bead:** `beadloom-ba9w.12`.

### #314

- **Command:** `beadloom init`, and `write_text_atomic` called directly on an existing 0644 file
- **Where:** throwaway projects, umask `022`.
- **Printed:** `-rw-------` for the init-written `config.yml`, `rules.yml` and `services.yml`.
  `t.yml` at 0644, after `write_text_atomic`: `-rw-------`.

- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): under umask 022, `init` wrote
  `config.yml` and `rules.yml` at 0600, and `write_text_atomic` turned an existing 0644 file into
  0600.
- **Bead:** `beadloom-ba9w.6`.

### #293

- **Command:** `uv run pytest --cov=src/beadloom`, over the whole suite (run as `.venv/bin/python
  -m pytest -q --cov=src/beadloom --cov-report=term -p no:cacheprovider`)
- **Where:** the worktree of this repository, with an index built inside it before the run, so
  the reporter's "no index at the start" condition was not reproduced. Also the `ci.yml` runs
  on GitHub created on or after 2026-09-29.
- **Printed:**

  ```
  --all-extras, 07:55-08:37Z: 8 failed, 15014 passed, 150 skipped, 13 xfailed in 2531.82s, TOTAL 95%
    0 lines matching "database disk image is malformed" or "OperationalError: disk I/O error"
    the 8 are room assertions: "extras: this run has all, dev, graphql, ... and the leg does not"
  the 4 files of the 8, under the tests leg's extras (dev languages tui watch graphql): 60 passed
  ci.yml since 2026-09-29: 34 runs (19 success, 10 cancelled, 5 failure)
  failed-job logs of the 5 failures (1206, 13760, 1067, 897, 3998 lines):
    0 lines matching "database disk image is malformed" or "OperationalError: disk I/O error"
  (39227020301's tests (3.13) failed 2 tests on "ValueError: filedescriptor out of range in select()")
  ```

- **Outcome:** closed on the evidence. Its own condition is one month without the signature
  (about 2026-10-29), and 21 days have been measured clean. The 10 cancelled runs were not read.
  If the owner holds the full month, S3z keeps the entry open without a bead until 2026-10-29.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): the whole suite under `--cov` on macOS
  arm64, CPython 3.12.12, printed no `malformed` or `disk I/O error` line, and the failed-job
  logs of all 5 failed `ci.yml` runs since 2026-09-29 hold none either.
- **Bead:** `beadloom-qq6m` (closed 2026-09-29). No new bead proposed.

### #290

- **Command:** `beadloom reindex --full` three times from an empty index, then `beadloom lint
  --strict --format porcelain`
- **Where:** a fresh worktree at `9f1b6fd2` (same code), no `beadloom.db` at the start.
- **Printed:**

  ```
  run 1: 503 depends_on; tui/app.py -> graph-reads; status_bar -> graph-reads
  run 2: 503 depends_on; tui/app.py -> graph-reads; status_bar -> graph-reads
  run 3: 503 depends_on; tui/app.py -> graph-reads; status_bar -> graph-reads
  code_imports dumps: 3703 rows each, diff run1/run2 and run2/run3 empty
  # layer_population:architecture-layers:depends_on:494:503:9
  ```

- **Outcome:** closed. The cold build now gives the warm answer, and the whole `code_imports`
  table is identical across the cold and the warm builds.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): three `reindex --full` runs from an empty
  index on this repository gave 503 `depends_on` edges each, resolved `tui/app.py`'s import to
  `graph-reads` on the first run, and produced row-identical `code_imports` tables (3703 rows).
- **Bead:** `beadloom-xzvp` (closed 2026-10-06).

### #278

- **Command:** `beadloom setup-agentic-flow` on a flow declaring `cursor` alone
- **Where:** the throwaway project of #356.
- **Printed:**

  ```
  Wrote .claude/commands/{coordinator,task-init,checkpoint,templates}.md
  Wrote .claude/CLAUDE.md
  Wrote .claude/hooks/beadloom-guard.sh (guard hook adapter)    (+ .claude/settings.json)
  agentic-flow-setup SPEC: "The `.claude/` files are still written for every flow, Cursor-only included."
  ```

- **Outcome:** live. The SPEC now states the fact without a reason and the output does not
  state it, so the entry's second answer is half taken. The guard hook and `settings.json` are
  two more artifacts the entry did not list.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): on a cursor-only flow,
  `setup-agentic-flow` wrote `.claude/CLAUDE.md`, the four commands, `.claude/hooks/beadloom-guard.sh`
  and `.claude/settings.json`. The SPEC states this without a reason, and the output does not
  state it at all.
- **Bead:** none found. Proposed: "[BDL-UX #278] setup-agentic-flow on a cursor-only flow writes
  .claude/CLAUDE.md, the four commands and the guard hook: gate them on tools:, or state the
  reason in the output and the SPEC".

### #277

- **Command:** `beadloom config-check`, and the test holding the finding
- **Where:** the #356 throwaway with `tools: [claude]`, a manifest row
  `.windsurf/agents/dev.md` and that file on disk. The test is
  `tests/unit/application/waves/test_the_populations_the_last_four_beads_report_over.py`.
- **Printed:**

  ```
  config-check: 0 lines naming .windsurf; 5 "orphaned adapter" lines, all .cursor/agents/*
  XFAIL ...::test_an_adapter_under_a_tool_this_release_does_not_ship_is_reported - FINDING BDL-068.S6-9
  30 passed, 2 xfailed
  ```

- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): with a manifest row and a file under
  `.windsurf/agents/`, `config-check` named none of it while it reported the five `.cursor/agents`
  orphans, and the strict xfail still fails.
- **Bead:** none found. Proposed: "[BDL-UX #277] the orphaned-adapter check takes its tool
  population from TOOL_AGENT_DIRS: derive the tool from the manifest row's directory, or state
  the constant as the population".

### #263

- **Command:** `uv run pytest tests/test_locale_independent_io.py tests/test_decode_handlers.py`
- **Where:** the worktree of this repository. The vocabulary moved to
  `tests/support/decoding_calls.py`.
- **Printed:**

  ```
  46 passed, 1 skipped
  vocabulary: TEXT_READWRITE, SUBPROCESS_CALLS, CONTAINER_OPENERS, DESCRIPTOR_OPENERS — names only,
    no count of calls it did not classify
  os.fdopen in src/beadloom: atomic_io.py:56, atomic_io.py:88, issue_numbers.py:504
  ```

- **Outcome:** live. The instrument is green and silent about three `os.fdopen` sites, one more
  than when the entry was written. By surface this is a test-suite instrument (S3f's area). It
  was assigned here and measured here.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): the codec sweep passed (46 passed, 1
  skipped) while `src/beadloom` holds three `os.fdopen` calls its call-name vocabulary does not
  know, and it reports no unclassified count.
- **Bead:** none found. Proposed: "[BDL-UX #263] the codec sweep recognises decoding calls by
  name: decoding_calls.py states how many calls it did not classify, and both instruments
  report that count".

### #225

- **Command:** `beadloom impact src/pkg/sub/writer.py` (and `--json`)
- **Where:** a throwaway `src/pkg/sub/writer.py` (`def run()`) beside `scripts/main.py`, which
  calls `run()`. `init --yes` first.
- **Printed:**

  ```
  root swept: src/pkg
  ## who else calls this
  - none found.
  ## unresolved (1)
  - [no-seed] ...
  JSON: callers.resolved True; unresolved kinds ['no-seed']   (no sweep-narrower-than-the-project)
  ```

- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `impact` on `src/pkg/sub/writer.py`
  swept `src/pkg` only, reported no caller although `scripts/main.py` calls `run()`, and marked
  `callers.resolved` true.
- **Bead:** `beadloom-f7kb`.

### #220

- **Command:** `beadloom init --bootstrap` with a hand-edited `.beadloom/_graph/legacy.yml`
- **Where:** three throwaway projects, one per shape.
- **Printed:**

  ```
  date scalar (added: 2026-09-02): TypeError: Object of type date is not JSON serializable, rc 1
                                   (src/beadloom/graph/loader.py:534 load_graph, via reindex/full.py:116)
  top-level list:                  rc 0, "Next steps"
  unparseable YAML:                rc 0
  ```

- **Outcome:** live, the residue the 2026-09-29 amendment names. The other two shapes stay
  closed.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `init --bootstrap` over a graph file with
  a date scalar still prints a `TypeError` traceback from `graph/loader.py:534` and exits 1,
  while a top-level list and an unparseable file finish at exit 0.
- **Bead:** `beadloom-l22o`.

### #218

- **Command:** `beadloom init --bootstrap` and `beadloom init --yes` on an initialised project
- **Where:** the #225 throwaway with a line `# hand edit` appended to `services.yml`.
- **Printed:**

  ```
  --bootstrap: ✓ Graph: 3 nodes, 2 edges ... rc 0; services.yml md5 778edc9d... -> 8033780c..., the hand edit gone
  --yes:       Warning: .beadloom/ already exists. Use --force to overwrite.
  auto_link_docs call sites: init_flow.py:104 and :341 only
  ```

- **Outcome:** live. The three sequences still differ: `--bootstrap` re-bootstraps over an
  existing graph silently where `--yes` refuses.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `init --bootstrap` on an initialised
  project rewrote a hand-edited `services.yml` without a word and exited 0, while `init --yes`
  on the same tree refused with "already exists".
- **Bead:** `beadloom-6i5q`.

### #217

- **Command:** `beadloom init --yes --mode import`, then `beadloom init --bootstrap`
- **Where:** a throwaway with `src/{auth,billing}` and `docs/domains/{auth,billing}/README.md`.
- **Printed:**

  ```
  Initialized beadloom (mode: import) ... Imported: 2 documents   (nodes readme, readme-domain)
  Error: the graph already in .beadloom/_graph/ does not pass the rules this command wrote alongside it.
    domain-needs-parent: readme (.beadloom/_graph/imported.yml)
    domain-needs-parent: readme-domain (.beadloom/_graph/imported.yml)
  `beadloom ci` will fail its lint step: 2 error(s), 0 warning(s)          rc 0
  ```

- **Outcome:** live, as the entry describes: the report is honest, the orphans stay unparented,
  and the decision (a)/(b)/(c) is not taken.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `init --bootstrap` after an import-only
  run named both imported domains as `domain-needs-parent` errors, parented neither, and exited 0.
- **Bead:** `beadloom-gv0z`.

### #215

- **Command:** `beadloom ci --no-reindex`
- **Where:** a copy of the #225 throwaway (valid `rules.yml`), its `beadloom.db*` moved out.
- **Printed:** `::notice::lint FAIL: rules configuration error`, then `::error::lint: index
  not found at .../.beadloom/beadloom.db — nothing to lint against.`, rc 1.

- **Outcome:** live. By surface it is a Gate entry (S3a's area). It was assigned here and
  measured here.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `ci --no-reindex` with a valid
  `rules.yml` and no index printed "lint FAIL: rules configuration error" above "index not
  found".
- **Bead:** `beadloom-uz8x`.

### #184

- **Command:** `beadloom config-check --project <dir>`
- **Where:** (1) a directory with code and no `.beadloom/`. (2) The #215 copy: `.beadloom/`
  present, `beadloom.db` absent.
- **Printed:**

  ```
  (1) rc 1, stdout 0 bytes, stderr 2848 bytes: Traceback ... src/beadloom/infrastructure/db.py:325 open_db
      sqlite3.OperationalError: unable to open database file
  (2) rc 0: "Agent-config in sync — no blocking drift." and .beadloom/beadloom.db now exists
  ```

- **Outcome:** live. Both streams are no longer empty, because the traceback reaches stderr.
  The answer is still a raw sqlite exception at exit 1. Case (2) shows a neighbouring defect:
  the check creates an empty index as a side effect and reports in sync.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `config-check --project` on a directory
  without `.beadloom/` exited 1 with a `sqlite3.OperationalError: unable to open database file`
  traceback, and on one with `.beadloom/` and no index it created `beadloom.db` and exited 0.
- **Bead:** none found. Proposed: "[BDL-UX #184] config-check on a project with no index answers
  with a raw sqlite traceback, or creates an empty index and reports in sync: an absent index is
  an answer with its own exit code".

### #176

- **Command:** `beadloom reindex` (incremental), after adding `src/pkg/caller.py` with one import
- **Where:** the #225 throwaway.
- **Printed:** `Symbols: 2`, `Imports: 0`, `Rules:   0`. The index after the run holds 1
  `code_imports` row and 1 `rules` row.

- **Outcome:** live.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): an incremental `reindex` that indexed a
  new import printed `Imports: 0` and `Rules: 0` over an index holding 1 import and 1 rule.
- **Bead:** none found. Proposed: "[BDL-UX #176] an incremental reindex prints Imports: 0 and
  Rules: 0: backfill both from the index as Symbols: is, or omit them on that path".

### #162

- **Command:** `beadloom doctor`
- **Where:** the worktree of this repository at `9f1b6fd2`, its own index.
- **Printed:** rc 0 and 298 lines, from packages to isolated nodes and unlinked docs. No line
  matches `island`, `unexplained`, `leaf` or `without evidence`.
- **Outcome:** live. None of the three proposed checks exists.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `doctor` on this repository ran no
  code-island, unexplained-leaf or claim-without-evidence check.
- **Bead:** `beadloom-uxqc`.

### #145

- **Command:** `beadloom ctx <ref> --json`, counting `code_symbols`
- **Where:** the worktree of this repository at `9f1b6fd2`. The index holds 4430 symbols.
- **Printed:**

  ```
  graph-reads (source: one file with 0 symbols): code_symbols 1274 from 146 files, 20 nodes
  cli: code_symbols 3291, 20 nodes
  doc-sync --max-nodes 1: code_symbols 276 (index: 282 under src/beadloom/doc_sync/; 35 from
    services/commands/docsync.py)
  ```

- **Outcome:** live in a narrower form. The array is no longer repo-wide (1274 of 4430). It is
  the whole subgraph's by annotation (`_collect_code_symbols`, `builder.py:262`), and no field
  separates the focus node's own symbols. The entry's use case, counting a node's symbols for a
  `max_symbols` rule, still reads 1274 for a node that owns 0.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `ctx graph-reads --json` returned 1274
  `code_symbols` (of 4430 in the index) for a node whose one source file has none. The array is
  scoped to the 20-node subgraph, not to the focus node.
- **Bead:** none found. Proposed: "[BDL-UX #145] ctx --json code_symbols is the subgraph's, not
  the focus node's: name the field for what it holds and add the focus node's own symbols".

### #95

- **Command:** `beadloom ctx <id>`, read with `builder.py`
- **Where:** the worktree of this repository.
- **Printed:** `src/beadloom/context_oracle/builder.py:273: for row in conn.execute("SELECT *
  FROM code_symbols").fetchall():` followed by `json.loads(row["annotations"])` per row.
- **Outcome:** live, the residue the 2026-09-29 amendment names. The L2 cache is on the build
  path, but a cache miss still scans and parses every symbol row. This is a code reading, not a
  timing: at 4430 symbols the scan is not visible.
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): on a cache miss, `_collect_code_symbols`
  still runs `SELECT * FROM code_symbols` and parses every row's annotations in Python
  (`builder.py:273`).
- **Bead:** none found. Proposed: "[BDL-UX #95] a ctx cache miss scans every code_symbols row and
  parses its JSON: filter by the subgraph's ref_ids in SQL".

### #73

- **Command:** `beadloom doctor`
- **Where:** the #225 throwaway (version 0.1, one package `pkg/sub`) with a hand-written
  `.claude/CLAUDE.md` claiming `Version: 1.9.0` and seven Beadloom packages.
- **Printed:**

  ```
  [warn] Version drift: CLAUDE.md claims 1.9.0, this project declares 0.1
  [warn] Package drift: claimed but missing: context_oracle, doc_sync, graph, infrastructure, onboarding, services, tui; undocumented: sub
  ```

- **Outcome:** won't-fix candidate. The warnings still fire on a user-authored `CLAUDE.md`, but
  they now compare its claims with **this project's** declared version and packages
  ("this project declares 0.1"). In the entry's own scenario, a `CLAUDE.md` carried over from
  another project, the file is in fact stale for the project it sits in. The reason for the
  owner: the warning is true and at `warn`, and limiting the check to the auto regions would
  stop it from catching exactly that staleness. If the owner prefers the entry's Expected, the
  bead is "doctor reads version and package claims only inside the beadloom auto regions of
  CLAUDE.md".
- **Evidence:** 2026-10-20, Beadloom 9.0.0 (`41245dc7`): `doctor` with a hand-written
  `CLAUDE.md` claiming 1.9.0 warned "CLAUDE.md claims 1.9.0, this project declares 0.1" and
  named seven claimed packages the project does not have.
- **Bead:** none, pending the owner's ruling.

## Not this area

None. #215 (the Gate, S3a) and #263 (a test-suite instrument, S3f) sit elsewhere by surface and
are measured completely above.

## Summary

| Entry | Outcome | Bead |
|---|---|---|
| #356 | partly closed: (a), (e), (g) and both further defects closed; (b), (c), (d), (f) live | `beadloom-ybxm` (closed); live `beadloom-ujm0`, `beadloom-9yny`, `beadloom-vtul`, `beadloom-rkiu`, `beadloom-ba9w.26`, `beadloom-s9op` |
| #351 | live | proposed |
| #350 | live | proposed |
| #339 | live | proposed |
| #338 | live | proposed |
| #337 | live | proposed |
| #324 | live | proposed |
| #320 | live | `beadloom-ba9w.15` |
| #319 | live | `beadloom-ba9w.14` |
| #317 | live | `beadloom-ba9w.12` |
| #314 | live | `beadloom-ba9w.6` |
| #293 | closed (its own month ends about 2026-10-29) | `beadloom-qq6m` (closed) |
| #290 | closed | `beadloom-xzvp` (closed) |
| #278 | live | proposed |
| #277 | live | proposed |
| #263 | live | proposed |
| #225 | live | `beadloom-f7kb` |
| #220 | live (the date-scalar residue) | `beadloom-l22o` |
| #218 | live | `beadloom-6i5q` |
| #217 | live (decision pending) | `beadloom-gv0z` |
| #215 | live | `beadloom-uz8x` |
| #184 | live | proposed |
| #176 | live | proposed |
| #162 | live | `beadloom-uxqc` |
| #145 | live (narrower: subgraph-wide, not repo-wide) | proposed |
| #95 | live (the SQL residue) | proposed |
| #73 | won't-fix candidate | none, pending the owner |
