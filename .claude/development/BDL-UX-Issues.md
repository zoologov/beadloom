# BDL UX Feedback Log

> Collected during development and dogfooding.
> Total: 120 issues | Open: 16 | Improvements: 16 | Excluded: 7 | Closed: 81
> 2026-06-02 (BDL-043 fix): CLOSED #120 — `dashboard.data.json` 404'd on GitHub Pages (widgets blank): the generator wrote it to the VitePress srcDir root (`site/`), which VitePress does NOT copy to the built `dist/` (only `site/public/` is copied verbatim); the dev server masked it by serving srcDir. FIXED: emit to `site/public/dashboard.data.json` → copied to dist root → the widgets' `withBase("/dashboard.data.json")` fetch resolves in the static build. Another "works in dev, breaks in the static build" class (cf. the F4 dead-links + F4.4 mermaid render) — the dogfood must hit the DEPLOYED/built site, not just `docs:dev`. Total 119→120, Closed 80→81.
> 2026-06-02 (BDL-041 F4.4 BEAD-05): VERIFIED #117 (dogfood SUCCESS — F4.4 render fixes: the two F4 Mermaid bugs are fixed and the generation-time guard passes the real 26-diagram site with 0 issues; `npm run docs:build` exit 0; dashboard mounts the 4 ECharts widgets via `<ClientOnly>` with honest text fallback; `dashboard.data.json` carries `trends` (2 real points, sparse-honest) + 7 `recommendations`; automated render-validation green (build exit 0, no page-HTML error markers), live UX pan/zoom + charts PENDING owner re-check in-browser on the fixed site). Opened #118 (process: parallel dev subagents in a SHARED working tree don't conflict on disjoint *files* but DO collide on the pre-commit *hook* — it lints the whole tree, so one agent's commit catches the other's in-progress WIP; BEAD-02 had to `--no-verify` staging only its `site/**`. Mitigation: use git-worktree isolation for true parallel, or run dev beads sequentially; `merge-slot` serializes *who* commits but does not isolate tree state). Opened #119 (LOW: `graph` domain now 202 symbols > 200 `domain-size-limit` — non-blocking warning; F2/F3/F4 grew it via contracts.py/sdl.py/site_mermaid_guard.py etc.; candidate future split). Total 116→119, Open 14→16, Closed 79→80.
> 2026-06-02 (BDL-040 F4 BEAD-05): Dogfood — generated + built Beadloom's own VitePress site. CLOSED #113 (generator bug: `publish_docs` copied hidden/OS-junk like `docs/.DS_Store` into `site/docs/` — non-deterministic + pollution; FIXED: skip dot-prefixed path parts; RED→GREEN regression test). CLOSED #114 (lockfile: `site/package-lock.json` now committed → `npm ci` reproducible). CLOSED #116 (generator bug surfaced by the dogfood build: node-page doc links + `/docs/` nav target were dead in the built site — FIXED by rooting doc links at `/docs/` + emitting a generated `site/docs/index.md` landing page; node-free dead-link guards added; `npm run docs:build` now exit 0, no `ignoreDeadLinks`). VERIFIED #115 (dogfood SUCCESS — 57 files, honest-by-construction dashboard matched `beadloom ci`, build green). Total 115→116, Open 15→14, Closed 77→79.
> 2026-06-02 (BDL-039 F3 BEAD-09): Opened #112 (incremental reindex displays `Symbols: 0` — per-run delta, not backfilled like nodes/edges per #88; cosmetic, zero gate impact). Total 111→112, Open 12→13.
> 2026-06-02 (BDL-039 F3 BEAD-06): VERIFIED #109 #110 #111 (dogfood SUCCESS — the F3 gate BLOCKS all three break-classes: boundary violation, cross-service BREAKING, drifted agent-config — each with a non-zero exit + agent-actionable output). Committed anonymized fixtures under `tests/fixtures/f3_gate/`. See Closed §BDL-039. Total 108→111, Closed 73→76.
> 2026-06-01 (BDL-038 F2 BEAD-08): VERIFIED #107 (live GraphQL contract mismatch caught before ship — the F2 success criterion) + #108 (paradigm-agnostic FSD round-trip + external native modules + nested company-landscape). See Closed §BDL-038. Closed 71→73.
> 2026-06-01 (BDL-038 F2 BEAD-01): Opened #105 (domain doc re-stales against all member files when one file is added) + #106 (no non-interactive `mark_synced` CLI). Open 10→12.
> Last reviewed: BDL-037 (F1: Federation Foundation)
> 2026-06-01 (BDL-037 F1): CLOSED #100 #101 #102 #103 (federation dogfood findings — FIXED in BEAD-09, commit d48bfeb) and #104 (federation dogfood SUCCESS — VERIFIED, BEAD-05). See Closed §BDL-037. Open 15→10, Closed 66→71.
> 2026-05-30 (BDL-036 Phase 0): CLOSED #91 #88 #92 #93 #94 #86 #89 #90 #71 #98 (honesty gate — see Closed §BDL-036). Opened #99 (repo-wide doc refresh — sync-check has ~30 pre-existing stale doc pairs unrelated to Phase 0; the sync-check *mechanism* is now honest, the doc *content* needs a dedicated pass). Still open: #72, #73, #95, #97 (external), #99. Exact category recount folded into #99.
> 2026-05-28: added #91–#96 from the comprehensive architecture/code review (see `.claude/development/REVIEW.md`); refined #88 root cause.

# Beadloom UX Issues

> Dogfooding feedback: issues, friction points, and improvement ideas collected while using Beadloom in the Bob project.
>
> **How to use:** Add entries during development. Each entry should include date, context, and severity.

---

## Template

```markdown
### [YYYY-MM-DD] Short description

**Severity:** low | medium | high | critical
**Command:** `beadloom <command>`
**Context:** What were you trying to do?
**Issue:** What went wrong or felt awkward?
**Expected:** What would be better?
**Workaround:** How did you work around it? (if applicable)
```

---

## Open Issues

> Issues awaiting code fixes in Beadloom.

114. [2026-06-02] [LOW] Committed VitePress scaffold ships no `package-lock.json` — `npm ci` cannot run on a fresh checkout

    **Severity:** low
    **Command:** `cd site && npm ci`
    **Context:** BDL-040 F4 BEAD-05 dogfood. The BEAD-01 scaffold committed `site/package.json` (pinned deps) but no `site/package-lock.json`. The bead instructions (and the scaffold's own header comment) say to run `npm ci && npm run docs:build`, but `npm ci` hard-requires a lockfile and errors out without one — so the very first build must use `npm install` (which then generates the lockfile).
    **Issue:** Mismatch between the documented build command (`npm ci`) and what a fresh checkout actually supports (`npm install` only, until a lockfile is committed).
    **Expected:** Either commit a `package-lock.json` alongside `package.json` (so `npm ci` works + the build is reproducible/pinned), or change the documented first-run command to `npm install`. Committing the lockfile is preferable — it pins the transitive dep tree for a deterministic dogfood/CI build.
    **Workaround:** Use `npm install` for the first build; commit the resulting `package-lock.json` so subsequent `npm ci` works.
    **Resolution (BEAD-05 follow-up):** `site/package-lock.json` is now committed (generated by `npm install`), so `npm ci` works on a fresh checkout and the dogfood build is reproducible/pinned. `site/node_modules` + `site/.vitepress/dist` stay gitignored.

112. [2026-06-02] [INFO/LOW] Incremental reindex displays `Symbols: 0` — per-run delta, not backfilled to the live total

    **Severity:** info / low (cosmetic display only — zero gate impact)
    **Command:** `beadloom reindex` (incremental path)
    **Context:** Observed during BDL-039 F3 tech-writer doc edits. After #88 was fixed, the incremental reindex now backfills `nodes`/`edges` to the true live-DB totals on the docs/code-only path. The `symbols_indexed` counter, however, still reports only the **per-run delta** (symbols touched this run), so a CLI run that changes only docs can print "Symbols: 0" while the DB actually holds all indexed symbols.
    **Issue:** Inconsistent reporting semantics between counters: `nodes`/`edges` show the live total (per #88), but `symbols_indexed` shows the run delta. A reader can misread "Symbols: 0" as "no symbols indexed."
    **Expected:** Either backfill `symbols_indexed` to the live DB symbol total on the incremental path (consistent with nodes/edges per #88), or label it explicitly as a delta ("Symbols indexed this run: 0").
    **Impact:** None on correctness or any gate — `sync-check` / `lint` / `doctor` / `beadloom ci` all read the DB, not this counter. Purely a cosmetic CLI-display artifact.

105. [2026-06-01] [MEDIUM] Adding a new source file to a domain re-stales the domain doc against ALL its member files

    **Severity:** medium
    **Command:** `beadloom reindex && beadloom sync-check`
    **Context:** BDL-038 BEAD-01 added one new module (`src/beadloom/graph/contracts.py`) to the `graph` domain and edited one sibling (`federation.py`). Before the change `sync-check` was honest 0; after, it reported **8 stale pairs** for `domains/graph/README.md` — including files I never touched (`diff.py`, `snapshot.py`, `linter.py`, `rule_engine.py`, `import_resolver.py`, `cli.py`), all with reason `symbols_changed`. Verified by stashing the change: at HEAD the same pairs are clean.
    **Issue:** The domain doc's symbol-drift baseline appears to be keyed on the domain's **aggregate** symbol set, so adding any symbol anywhere in the domain invalidates the `symbols_hash` for **every** doc↔file pair in that node — not just the pair whose code actually changed. One new file → N false `symbols_changed` pairs.
    **Expected:** `symbols_changed` should fire only for the pair(s) whose own code symbols changed. A genuinely-new module should surface as a single `untracked_files` signal on the doc, not re-stale every unrelated sibling pair. (Compare #89: per-file granularity was the fix there too.)
    **Workaround:** Document the new module in the domain README, then `mark_synced_by_ref(conn, '<domain>', root)` to re-baseline all pairs, then re-run to fixpoint (see #106).

106. [2026-06-01] [LOW] No non-interactive CLI to attest sync baseline (`mark_synced`) — only the interactive `sync-update`

    **Severity:** low
    **Command:** `beadloom sync-update <ref>` (interactive: `click.confirm` + `click.edit`)
    **Context:** After a doc refresh, re-baselining the sync state requires `mark_synced` / `mark_synced_by_ref` (`doc_sync.engine`). The only CLI surface is `sync-update`, which opens an editor and prompts — unusable in an agent/CI flow. BEAD-01 had to call the engine directly via `uv run python -c "...mark_synced_by_ref..."`.
    **Issue:** There is no `beadloom sync-update <ref> --mark-synced` (or `beadloom sync-mark <ref>`) for non-interactive attestation. Agents must reach past the CLI into the engine.
    **Expected:** A non-interactive attest flag/command, e.g. `beadloom sync-update <ref> --mark-synced` or `beadloom sync-mark [--ref R | --all]`, that recomputes hashes + `symbols_hash` and sets `status='ok'` without an editor. Pairs with the F4.1 AI-tech-writer loop (STRATEGY-3) which must attest non-interactively. Re-running `reindex && sync-check` after attest to a stable 0 is mandatory (F4.1 loop invariant — clearing `symbols_changed` surfaces masked `untracked_files`, as it did for `contracts.py` here).

71. [2026-03-10] [MEDIUM] `beadloom init --bootstrap` generates rules that immediately produce lint violations

    **Severity:** medium
    **Command:** `beadloom init --bootstrap -y` → `beadloom lint --strict`
    **Context:** Bootstrapping Beadloom on a production FastAPI monolith project provided for field-testing. The project has a clean architecture with domain packages containing `graphql/` sub-packages.
    **Issue:** The auto-generated `rules.yml` includes a `feature-needs-domain` rule that requires every feature to be `part_of` a domain. However, the bootstrap classifier creates features inside services too (e.g., `core-rest` feature → `part_of` core service; `tasks-graphql` feature → `part_of` tasks service). Running `beadloom lint --strict` immediately after init exits with 2 violations — a "broken out of the box" experience.
    **Expected:** Either (a) the default rule should accept features inside both domains and services (`has_edge_to: {}`), or (b) the bootstrap classifier should only classify nodes as `feature` when they are inside a `domain`-kind parent (not `service`-kind). Zero violations should be the norm after a clean bootstrap.
    **Workaround:** Manually edit `.beadloom/_graph/rules.yml`: change `has_edge_to: { kind: domain }` to `has_edge_to: {}` and rename the rule to `feature-needs-parent`.

72. [2026-03-10] [LOW] `beadloom setup-rules` doesn't detect IDE when marker directory is gitignored

    **Severity:** low
    **Command:** `beadloom setup-rules`
    **Context:** The project has `.cursor/` listed in `.gitignore`, so the directory doesn't exist on a fresh clone, but does exist in the working tree.
    **Issue:** `setup-rules` outputs `No IDE markers detected` and creates no files. The `.cursor/` directory was present in the filesystem but gitignored. Auto-detection apparently checks for marker files but the detection logic may miss directories that exist but are in `.gitignore`.
    **Expected:** If marker directories exist on disk (regardless of gitignore), they should be detected. Alternatively, if no markers are found, print a helpful hint: `"No IDE markers detected. Use --tool cursor|windsurf|cline to specify."` so the user doesn't have to run `--help` to discover the flag.
    **Workaround:** Explicitly pass `--tool cursor`.

73. [2026-03-10] [LOW] `beadloom doctor` reports "Version drift" and "Package drift" by checking `.claude/CLAUDE.md`

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** After bootstrapping on an external project, the existing `.claude/CLAUDE.md` contained content from a previous project (Beadloom itself) with `Version: 1.9.0` and DDD package references (`context_oracle/`, `doc_sync/`, etc.).
    **Issue:** `doctor` checks `.claude/CLAUDE.md` for version and package claims, finding `CLAUDE.md claims 1.9.0, actual is 1.7.0` and `Package drift: claimed but missing: context_oracle, doc_sync, graph, infrastructure, onboarding, services, tui`. These are false positives — CLAUDE.md is a user-maintained file that may describe the project in custom terms, not necessarily matching Beadloom's internal structure.
    **Expected:** `doctor` should validate `.beadloom/AGENTS.md` (which Beadloom generates and controls) rather than `.claude/CLAUDE.md` (which is user-authored and project-specific). If CLAUDE.md is checked at all, it should be limited to `<!-- beadloom:auto-start -->` / `<!-- beadloom:auto-end -->` sections.
    **Workaround:** Ignore the warnings; they're false positives caused by stale CLAUDE.md content from another project.

88. [2026-03-11] [HIGH] Incremental `beadloom reindex` returns 0 nodes after doc enrichment

    **Severity:** high
    **Command:** `beadloom reindex`
    **Context:** After enriching 18 documentation files (replacing skeleton content with detailed descriptions), an incremental `beadloom reindex` was run to update the index.
    **Issue:** Incremental reindex returned `Nodes: 0, Edges: 0, Symbols: 0, Imports: 0` — completely empty index. The `services.yml` was verified to be intact (18 nodes, 34 edges, correct YAML block format). Running `beadloom reindex --full` immediately after returned `Nodes: 18, Edges: 34, Symbols: 272` — completely normal.
    **Root cause hypothesis:** Incremental reindex likely detects that many files changed (18 doc files + potentially cached state) and incorrectly drops the entire index instead of updating it. The SQLite cache may have become inconsistent after bulk doc writes by parallel agents.
    **Expected:** Incremental reindex should never return 0 nodes when `services.yml` is valid. If the incremental path detects inconsistency, it should auto-fallback to `--full` reindex rather than returning an empty result. At minimum, print a warning: `"Incremental reindex returned 0 nodes — possible cache inconsistency. Retry with --full."`.
    **Workaround:** Always use `beadloom reindex --full` after bulk changes. Do not rely on incremental reindex after modifying many files simultaneously.
    **Root cause (confirmed 2026-05-28 code review):** NOT cache inconsistency. `incremental_reindex` (`infrastructure/reindex.py:1088-1296`) never assigns `result.nodes_loaded`/`edges_loaded` on the docs/code-only path — they keep their `ReindexResult` default of `0`, and the CLI prints them verbatim (`services/cli.py:288-289`). The index is intact; this is a **display bug**, not data loss. Trivial fix: query live DB totals (as the `nothing_changed` branch already does at `cli.py:274-279`). Note this is a recurrence — the same symptom (#21) was "fixed" in v1.5.0.

86. [2026-03-10] [HIGH] YAML flow-style edges silently produce 0 nodes on reindex

    **Severity:** high
    **Command:** `beadloom reindex`
    **Context:** During manual graph editing of `services.yml`, edges were written in YAML inline/flow format: `- { src: houses, dst: core-external-inspection-system, kind: depends_on }`. This is perfectly valid YAML per the spec. Nodes were written in block format.
    **Issue:** After saving `services.yml` with flow-style edges, `beadloom reindex` returned `Nodes: 0, Edges: 0` — a complete silent failure. No error, no warning. The YAML parser appears to not handle inline mapping syntax for edge entries. Rewriting all edges in block format (`- src: X\n  dst: Y\n  kind: Z`) fixed the issue immediately (18 nodes returned).
    **Expected:** Either (a) the YAML parser should correctly handle flow-style mappings (they are valid YAML), or (b) if the parser has limitations, it should detect the issue and emit a clear error: `"Error: edges at line N use unsupported inline format. Use block format instead."` Silent 0-node results are the worst possible failure mode — the user thinks the graph is empty.
    **Workaround:** Always use YAML block format for edges. Never use `- { key: value }` inline format in `services.yml`.

91. [2026-05-28] [CRITICAL] Beadloom violates its own architecture rules; `lint --strict` is configured to pass anyway

    **Severity:** critical
    **Command:** `beadloom lint --strict` (exits 0) vs. actual graph state
    **Context:** Self-audit during the comprehensive architecture/code review (2026-05-28). The product's core value proposition is enforcing architecture boundaries and catching dependency cycles.
    **Issue:** `beadloom lint --strict` exits **0** on Beadloom itself despite **12 real violations** (verified live). Two compounding problems:
    - (1) **The coupling is real.** `infrastructure` is a god-package: `infrastructure/reindex.py` (~1296 LOC) orchestrates every domain and imports them at module level (`infrastructure/reindex.py:14-16` → `context_oracle`, `doc_sync`, `graph`). Meanwhile `graph/linter.py:98` and `graph/import_resolver.py:820,882` import back into `infrastructure.reindex`, creating cycles. The cycle is openly acknowledged in a code comment (`graph/linter.py:95-96`: *"Lazy import to avoid circular dependency…"*) and worked around with function-local lazy imports instead of being fixed. Per the layer rule, `infrastructure` sits BELOW domains yet imports all of them.
    - (2) **The alarm is silenced.** In `.beadloom/_graph/rules.yml`, `no-dependency-cycles` (line 39) and `architecture-layers` (line 45) are set `severity: warn`. `--strict` only fails on `error`-severity, so a graph full of cycles passes green.
    **Expected:** A tool that sells architecture enforcement must pass its own enforcement. (a) Break the `infrastructure` god-package — extract reindex orchestration into a `services`-layer module, or invert the dependency so `infrastructure` stops importing domains; (b) restore `no-dependency-cycles`/`architecture-layers` to `severity: error`. Until then this is a credibility hole reproducible by any skeptic in two commands.
    **Workaround:** None — structural issue, not a usage issue.

92. [2026-05-28] [HIGH] `doctor` reports false "Version drift" on Beadloom itself (reads stale `importlib.metadata`, not `__version__`)

    **Severity:** high
    **Command:** `beadloom doctor`
    **Context:** Self-audit (2026-05-28). Distinct from #73 (which is about doctor reading the user-authored `.claude/CLAUDE.md` on an *external* project). This is about doctor's notion of the "actual" version being wrong even on Beadloom's own repo.
    **Issue:** `doctor` reports *"Version drift: CLAUDE.md claims 1.9.0, actual is 1.7.0"* while `src/beadloom/__init__.py:3` is `__version__ = "1.9.0"` and `status` shows 1.9.0. Root cause: `_get_actual_version()` (`infrastructure/doctor.py:274-281`) returns `importlib.metadata.version("beadloom")` first — stale editable-install metadata — and only falls back to source `__version__` on `PackageNotFoundError`. A diagnostic that confidently emits a wrong diagnosis erodes trust in all of doctor's output.
    **Expected:** Treat the in-tree `__version__` as the source of truth for "actual version" (or compare directly against it). Installed-package metadata must not override the source version.
    **Workaround:** Reinstall the package to refresh metadata; ignore the warning.

93. [2026-05-28] [LOW] `AGENTS.md` MCP tool list is stale (documents 13 tools, actual is 14)

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** Self-audit (2026-05-28). doctor reports *"MCP tool drift: AGENTS.md documents 13 tools, actual is 14"*.
    **Issue:** The generated `AGENTS.md` lists 13 MCP tools but 14 are registered. Unlike the won't-fix README case (#20), `AGENTS.md` IS agent-facing and HAS a `generate_agents_md()` regeneration path — so this is a real regeneration/sync gap that should never drift.
    **Expected:** `generate_agents_md()` should enumerate MCP tools from the live registry so the count can't drift; `setup-rules --refresh` (or a doctor `--fix`) should bring it back in sync.
    **Workaround:** Regenerate `AGENTS.md`.

94. [2026-05-28] [MEDIUM] Over-broad `except Exception` for "table missing" can swallow real errors silently

    **Severity:** medium
    **Command:** internal (reindex / metadata reads)
    **Context:** Self-audit (2026-05-28). Same silent-failure class as #86 / #88.
    **Issue:** `infrastructure/reindex.py:125`, `:863`, `:926` use bare `except Exception` to mean "table doesn't exist on first run" and then return `{}` / skip. As written they also swallow genuine `sqlite3` corruption, IO errors, and programming errors — silently returning empty and masking real failures behind a "first run" assumption.
    **Expected:** Catch the specific `sqlite3.OperationalError` (and verify it's a missing-table case, e.g. via `PRAGMA table_info`) so only the intended condition is handled; let all other exceptions propagate.
    **Workaround:** None.

95. [2026-05-28] [MEDIUM] Per-bundle full table scan of `code_symbols` won't scale; L2 `bundle_cache` is not on the build path

    **Severity:** medium
    **Command:** `beadloom prime` / `beadloom ctx <id>`
    **Context:** Self-audit (2026-05-28). Invisible on this repo (506 symbols); a latent scale problem for the large monorepos a "context oracle" targets.
    **Issue:** `build_context` (`context_oracle/builder.py:377`) calls `_collect_code_symbols` (`:256`), which runs `SELECT * FROM code_symbols` (`:267`) and `json.loads(row["annotations"])` per row (`:268`) on EVERY bundle build, then filters to the subgraph in Python — O(total symbols in repo) per `prime`/`ctx` call. A SQLite L2 cache exists (`context_oracle/cache.py` → `bundle_cache` table) but `build_context` does not consult it on the hot path.
    **Expected:** Filter symbols in SQL by the subgraph's ref_ids (indexed join), avoid per-row JSON parsing of non-matching rows (e.g. a `symbol_annotations(ref_id, symbol_id)` table or an indexed `ref_id` column), and/or wire `build_context` through the existing `bundle_cache`.
    **Workaround:** None needed at small scale.

---

## Improvements

> Enhancement proposals for existing features. Not bugs — current behavior works but can be better.

74. [2026-03-10] [MEDIUM] Bootstrap classifies test directories as domains — clutters graph and prime output

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** Field-testing on a production project with `app/tests/` containing subdirectories per domain (`tests/houses/`, `tests/pdf/`, `tests/plans/`, `tests/users/`, `tests/integrations/`).
    **Issue:** Bootstrap creates 7 test-related nodes (`tests`, `tests-houses`, `tests-pdf`, `tests-plans`, `tests-users`, `tests-integrations`, `tests-core`) classified as domains. These nodes:
    - Clutter `beadloom prime` output (7 of 17 "domains" are actually test suites)
    - Inflate the graph (30 nodes → ~23 without tests)
    - Add noise to `beadloom graph` Mermaid diagram
    - Create spurious `depends_on` edges (tests naturally import everything)
    **Expected:** Option to exclude test directories from the architecture graph: `beadloom init --bootstrap --exclude-tests` or a `config.yml` setting like `exclude_paths: [app/tests/]`. Alternatively, classify test directories as a separate `kind: test-suite` that can be filtered in `prime`/`graph` output.

75. [2026-03-10] [MEDIUM] Auto-generated node summaries are mechanical and don't convey purpose

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** Project has README.md with a clear description of each domain's purpose, plus `__init__.py` files with module docstrings.
    **Issue:** Generated summaries are purely structural: `"Domain: configs — 1 class, 2 fns"`, `"Domain: houses — 2 classes, 6 fns"`. These tell an AI agent nothing about what the domain does. The information needed is available in:
    - Project README.md (describes each domain conceptually)
    - `__init__.py` module docstrings
    - Existing documentation in `doc/` directory
    **Expected:** During bootstrap, attempt to extract meaningful summaries from:
    1. `__init__.py` docstring of the package (highest priority)
    2. README.md sections that mention the domain name
    3. Existing docs in the project's `doc/` or `docs/` directory
    Fall back to the mechanical format only if no semantic source is available.

76. [2026-03-10] [LOW] `beadloom init` doesn't support combined bootstrap + import mode in one step

    **Severity:** low
    **Command:** `beadloom init --bootstrap --import doc/`
    **Context:** The project has both source code in `app/` and existing documentation in `doc/` (API specs, integration guides). The user wants to bootstrap from code AND import existing docs.
    **Issue:** `--bootstrap` and `--import` are mutually exclusive on the CLI. The user must run two commands: `beadloom init --bootstrap -y` then `beadloom init --import doc/`. The `--mode both` flag exists in help but it's unclear how it interacts with `--import DIRECTORY`.
    **Expected:** `beadloom init --bootstrap --import doc/ -y` should work in a single invocation: bootstrap the graph from code, then import and classify docs from the specified directory.

77. [2026-03-10] [MEDIUM] No automated CLAUDE.md adaptation for target project stack

    **Severity:** medium
    **Command:** `beadloom setup-rules --refresh`
    **Context:** After bootstrapping on a new project, the `.claude/CLAUDE.md` file contained a generic template (from a previous project) with wrong stack references (Python 3.10 instead of 3.13, `mypy` instead of `ty`, `src/beadloom/` paths instead of `app/`, etc.). Manual adaptation required ~30 minutes of an AI agent's time to:
    - Analyze the project stack (pyproject.toml, CI config, pre-commit)
    - Rewrite the Project Info section
    - Rewrite the Architecture section
    - Update all quality gate commands
    - Update all `.claude/commands/*.md` files (dev, review, test, templates, coordinator, checkpoint)
    **Issue:** Beadloom bootstraps the architecture graph automatically but doesn't help with adapting the AI agent instruction files. The `setup-rules --refresh` only updates `<!-- beadloom:auto-start -->` sections, which cover a small fraction of CLAUDE.md.
    **Expected:** A new command or flag like `beadloom setup-rules --adapt-claude` that:
    1. Reads `pyproject.toml`, CI configs, pre-commit config to detect the project's stack
    2. Updates `CLAUDE.md` section `0.1 Project` with detected stack, tooling, architecture
    3. Updates quality gate commands (test runner, linter, type checker) throughout CLAUDE.md
    4. Optionally adapts `.claude/commands/dev.md` code patterns section with project-appropriate examples
    This would make Beadloom initialization a truly one-command experience for AI-assisted projects.

78. [2026-03-10] [LOW] Bootstrap should auto-validate generated rules and warn on immediate violations — see also #71

    **Severity:** low
    **Command:** `beadloom init --bootstrap -y`
    **Context:** After bootstrap, user expects a clean state but `beadloom lint --strict` fails (see issue #71).
    **Issue:** Bootstrap generates `rules.yml` and `services.yml` independently. It doesn't validate that the generated rules are satisfied by the generated graph. The user discovers violations only when they manually run `lint`.
    **Expected:** At the end of bootstrap, automatically run `lint` internally. If violations are found, either:
    - (a) Auto-fix the rules to match the generated graph (preferred), or
    - (b) Print a warning: `"⚠ 2 lint violations detected in the generated graph. Run 'beadloom lint' to see details and fix .beadloom/_graph/rules.yml"`

79. [2026-03-10] [INFO] Field-testing metrics: Beadloom bootstrap on a production FastAPI monolith

    **Severity:** info
    **Command:** `beadloom init --bootstrap -y`
    **Context:** Field-testing on a production Python 3.13 FastAPI + Strawberry GraphQL monolith with 6 business domains, ~50 Python source files, ~30 test files, Docker + k8s deployment, GitLab CI.
    **Results:**
    - **Bootstrap time:** ~3 seconds
    - **Auto-detected:** preset=monolith, language=.py, scan_paths=[app]
    - **Generated graph:** 30 nodes, 47 raw edges (95 after reindex with import analysis), 272 symbols
    - **Classification accuracy:** ~80% — correctly identified 6 business domains, 6 features (graphql sub-packages), root service. Misclassified: test dirs as domains (7 nodes), some service/domain kind swaps.
    - **Lint violations:** 2 out of the box (rules-vs-graph mismatch, see #71)
    - **Doc coverage:** 97% (29/30 nodes had auto-generated docs)
    - **beadloom prime:** correct and useful output after rules fix — 0 stale docs, 0 lint violations
    - **Total time to fully operational state (bootstrap + rules fix + .claude adaptation + .gitignore + verify):** ~15 minutes with AI agent assistance
    - **Improvement vs. previous field test (#37):** Bootstrap quality improved from ~35% to ~80% architecture capture. The main remaining gap is test-directory noise and dry summaries.

80. [2026-03-10] [HIGH] Bootstrap graph accuracy: comprehensive improvement plan for all supported languages

    **Severity:** high
    **Command:** `beadloom init --bootstrap`
    **Context:** Field-testing on a production project revealed that the bootstrapped graph is ~80% accurate but has systematic misclassifications. These are NOT project-specific — they stem from heuristics that apply across all 12 supported languages. This issue consolidates the root causes and proposes a phased improvement plan.

    **Root causes identified:**

    **A. Test directories inside scan_paths are not excluded.**
    `_SKIP_DIRS` in `scanner.py` includes `"test", "tests"` but only for top-level directory detection in `detect_source_dirs()`. Once a scan_path is chosen (e.g., `app/`), subdirectories like `app/tests/`, `app/__tests__/`, `app/spec/` are scanned and classified as domains. This affects:
    - Python: `app/tests/`, `tests/` inside packages
    - TypeScript/JavaScript: `__tests__/`, `*.test.ts` collocated files
    - Go: `*_test.go` files (collocated by convention)
    - Java/Kotlin: `src/test/` mirroring `src/main/`
    - Swift: `*Tests/` directories
    - Rust: `tests/` directory, inline `#[cfg(test)]` modules

    **B. `_SERVICE_DIRS` regex over-matches internal domain layers.**
    The regex `^(services?|core|engine|workers?|jobs?|tasks?|processors?)$` matches both:
    - Top-level packages that ARE architectural services (correct: `services/`, `core/`)
    - Sub-packages within a domain that are internal layers (incorrect: `app/pdf/services/`, `app/pdf/tasks/`)
    The classifier doesn't distinguish depth — a `services/` directory 2 levels deep inside a domain should NOT create a standalone service node.

    **C. No composition root detection.**
    Files that import from ALL or most domains (e.g., `schema.py`, `urls.py`, `routes/index.ts`, `main.go`) are not recognized as composition roots. This creates inverted dependency edges: the composition root's parent gets `depends_on` edges pointing toward every domain, when architecturally the domains are independent and the root just wires them together. Affected patterns across languages:
    - Python: `schema.py` (GraphQL), `urls.py` (Django), `main.py` (FastAPI)
    - TypeScript: `routes/index.ts`, `app.module.ts` (NestJS)
    - Go: `cmd/server/main.go`, `wire.go`
    - Java/Kotlin: `@Configuration` classes, `Application.java`
    - Rust: `main.rs`, `lib.rs`

    **D. Framework-detected metadata is not used for classification tuning.**
    `_detect_framework()` in `scanner.py` correctly identifies 11+ frameworks (FastAPI, Django, NestJS, Spring Boot, Express, etc.) but the result is only stored as metadata on the root node. It is NOT used to:
    - Adjust which directories become features vs. domains (e.g., Django `apps.py` = domain, FastAPI `graphql/` = transport layer within domain)
    - Set framework-specific layer rules
    - Choose appropriate `rules.yml` templates

    **Proposed solution — phased approach:**

    **Phase 1: Test exclusion (LOW effort, HIGH impact)**
    - Add `exclude_paths` to `config.yml` schema (list of glob patterns)
    - Auto-populate with detected test directories during bootstrap using existing `test_mapper.py` patterns:
      - Python: `**/tests/`, `**/test/`, `**/__tests__/`
      - JS/TS: `**/__tests__/`, `**/*.test.*`, `**/*.spec.*`
      - Go: skip `*_test.go` from node creation (they're collocated)
      - Java/Kotlin: `**/src/test/`
      - Swift: `**/*Tests/`
      - Rust: `**/tests/` (integration tests dir)
    - Bootstrap output: `"Excluded 7 test directories (override in config.yml)"`
    - Estimated impact: removes 20-30% of graph noise across all languages.

    **Phase 2: Depth-aware kind classification (MEDIUM effort, HIGH impact)**
    - Change `_SERVICE_DIRS` / `_FEATURE_DIRS` matching to consider directory depth relative to scan_path root.
    - Rule: directories matching `_SERVICE_DIRS` or `_FEATURE_DIRS` at depth ≥ 2 inside an already-classified domain should be **absorbed into the parent** (not create separate nodes), unless they have 5+ files of their own.
    - Examples:
      - `app/pdf/services/` (depth 2 inside `app/`) → part of `pdf` domain, NOT a separate `pdf-services` service node
      - `app/core/redis/` (depth 2 inside `app/`) → sub-domain of `core`, keep as-is (has its own distinct responsibility)
      - `services/` at top level (depth 0) → standalone service node (correct)
    - This fixes: `pdf-services`, `pdf-tasks`, `users-services`, `tests-core` misclassifications.
    - Language-specific depth thresholds may be needed:
      - Python: depth 2+ = internal
      - Java/Kotlin: depth 3+ (due to `src/main/java/com/...` convention)
      - Go: depth 1+ (flat package convention)

    **Phase 3: Composition root detection (MEDIUM effort, MEDIUM impact)**
    - After import-graph construction, identify files with fan-out ≥ 70% of all domains:
      ```
      composition_root = file where (imported_domains / total_domains) >= 0.7
      ```
    - For composition root files:
      - Do NOT create `depends_on` edges from the root's parent to imported domains
      - Instead, mark the file with `# composition-root` annotation in graph metadata
      - Optionally create `wires` edges (a new edge kind) for documentation purposes
    - Language-specific patterns to aid detection:
      - Python: file imports `strawberry.Schema`, `urlpatterns`, `FastAPI()` + imports from 3+ domains
      - TypeScript: file contains `@Module({ imports: [...] })` (NestJS) or `createApp()` (Vue)
      - Go: `main.go` in `cmd/` importing 3+ internal packages
      - Java: class annotated `@SpringBootApplication` or `@Configuration`
      - Rust: `main.rs` or `lib.rs` with `mod` declarations for 3+ modules

    **Phase 4: Framework-specific classification rules (MEDIUM effort, HIGH impact)**
    - Use detected framework to apply classification overrides:

    | Framework | Rule |
    |-----------|------|
    | **FastAPI** | `graphql/`, `api/`, `routers/` inside domain → transport layer (feature), not separate domain |
    | **Django** | Directory with `apps.py` → domain; `urls.py` → composition root; `admin.py` → skip |
    | **NestJS** | `*.module.ts` → domain boundary; `*.controller.ts` → transport; `*.service.ts` → absorbed |
    | **Spring Boot** | `@Controller`/`@RestController` → transport; `@Service` → absorbed; `@Repository` → adapter |
    | **Express** | `routes/` → transport; `middleware/` → infrastructure; `controllers/` → absorbed |
    | **Go (stdlib)** | `cmd/` → entry points; `internal/` → domains; `pkg/` → shared |
    | **Rust (Actix)** | `handlers/` → transport; `models/` → entities; `services/` → domains |
    | **React/Vue** | `components/` → features; `hooks/`/`composables/` → shared; `pages/`/`views/` → transport |

    - Store active framework in `config.yml`:
      ```yaml
      framework: fastapi   # auto-detected, user can override
      ```

    **Phase 5: Docstring/README mining for summaries (LOW effort, MEDIUM impact)**
    - During bootstrap, for each classified node:
      1. Read entry-point file's module docstring (language-specific):
         - Python: `__init__.py` or `module.py` top-level docstring
         - Go: package comment in first `.go` file
         - Rust: `//!` doc comments in `lib.rs` / `mod.rs`
         - Java/Kotlin: Javadoc on main class
         - TypeScript: JSDoc on default export or `/** @module */`
      2. Search project README.md for sections mentioning the directory name
      3. Search `doc/` or `docs/` for files named after the domain
      4. Fallback: current mechanical format `"Domain: X — N classes, M fns"`

    **Phase 6: AI-assisted graph refinement via MCP (HIGH effort, HIGHEST impact)**
    - New command: `beadloom refine` (or `beadloom init --bootstrap --refine`)
    - After mechanical bootstrap, invoke an AI agent (via MCP or direct prompt) with:
      - Generated graph (nodes + edges as JSON)
      - README.md content
      - Import-graph summary (top-10 highest fan-out files)
      - Detected framework + entry points
    - Agent reviews and returns corrections:
      - kind reclassification
      - edge direction fixes
      - summary enrichment
      - nodes to merge or exclude
    - Agent output written as `services.yml` patch → user confirms → apply
    - Requires: MCP write tools (`update_node`) already exist; need a "review prompt" template

    **Priority and impact matrix:**

    | Phase | Effort | Impact | Fixes |
    |-------|--------|--------|-------|
    | 1. Test exclusion | Low | High | #74, ~25% noise reduction |
    | 2. Depth-aware kinds | Medium | High | service/domain misclassification |
    | 3. Composition roots | Medium | Medium | inverted dependencies |
    | 4. Framework rules | Medium | High | language-specific accuracy |
    | 5. Summary mining | Low | Medium | #75, useless summaries |
    | 6. AI refinement | High | Highest | remaining ~10% gap |

    Phases 1-3 are language-agnostic and fix structural issues. Phase 4 is the largest effort but delivers per-language accuracy. Phase 5 is a quick win. Phase 6 is the endgame for "perfect out of the box" but depends on LLM availability.

81. [2026-03-10] [HIGH] Import-graph based dependency direction validation

    **Severity:** high
    **Command:** `beadloom init --bootstrap` → `beadloom reindex`
    **Context:** After reindex, import analysis produces 305 import edges. These are used for `forbid_import` rules but NOT for validating bootstrap-generated `depends_on` edge directions.
    **Issue:** Bootstrap generates `depends_on` edges based on import analysis, but doesn't distinguish between:
    - **Real architectural dependency**: domain A's business logic imports from domain B's public API
    - **Composition wiring**: a top-level file (schema.py, urls.py, main.go) imports from all domains to wire them together
    - **Test imports**: test files import from production code (not a real architectural dependency)
    The result: `core` appears to depend on `houses`, `pdf`, `plans`, `tasks`, `users` — when the real dependency is the reverse.
    **Expected:** After import-graph construction:
    1. Identify composition-root files (fan-out ≥ 70% of domains) and exclude their imports from `depends_on` edge generation
    2. Identify test files and exclude their imports from `depends_on` edge generation
    3. For remaining imports, determine dependency direction by counting: if A imports B more than B imports A, then A depends_on B
    4. Flag bidirectional dependencies for user review (potential circular dependency or misclassification)

82. [2026-03-10] [MEDIUM] Bootstrap `config.yml` should support `exclude_paths` for user-controlled noise reduction

    **Severity:** medium
    **Command:** `beadloom init --bootstrap` → `beadloom reindex`
    **Context:** After bootstrap, the user wants to exclude test directories, migration directories, or generated code from the architecture graph without manually editing `services.yml`.
    **Issue:** `config.yml` only supports `scan_paths` (what to include) but not `exclude_paths` (what to skip within scan_paths). The user must manually delete nodes from `services.yml` and re-run `reindex` — fragile and lost on next bootstrap.
    **Expected:** Add `exclude_paths` to `config.yml`:
    ```yaml
    scan_paths:
    - app
    exclude_paths:
    - "app/tests/"
    - "app/migrations/"
    - "**/generated/"
    ```
    The exclude list should support glob patterns and be respected by both `init --bootstrap` and `reindex`. Auto-populated during bootstrap with detected test directories (per-language patterns from `test_mapper.py`).

83. [2026-03-10] [MEDIUM] Two-phase bootstrap: draft → review → commit

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** Bootstrap generates a final graph in one step. The user discovers issues only after running `lint`, `doctor`, or manually inspecting `services.yml`. By then, they're editing YAML by hand — defeating the purpose of automation.
    **Issue:** No review step between graph generation and commit. The user can't validate or correct the graph before it's written to disk. This is especially problematic for large projects where manual YAML editing is tedious.
    **Expected:** Two-phase bootstrap:
    ```bash
    # Phase 1: Generate draft graph (write to .beadloom/_graph/services.draft.yml)
    beadloom init --bootstrap --draft

    # Phase 2: Interactive review (or AI-assisted)
    beadloom review-graph              # shows draft, asks questions, accepts corrections
    beadloom review-graph --auto-fix   # auto-fix known issues (test exclusion, depth-aware kinds)

    # Phase 3: Apply (rename draft to final)
    beadloom apply-graph
    ```
    In non-interactive mode (`-y`), Phase 2 applies `--auto-fix` automatically. In interactive mode, it presents a summary and asks for confirmation.
    For AI agents via MCP: expose a `review_bootstrap_graph` tool that returns the draft graph + suggested fixes as JSON, and an `apply_bootstrap_fixes` tool that applies corrections.

84. [2026-03-10] [MEDIUM] Framework-specific preset rules: use detected framework to tune classification

    **Severity:** medium
    **Command:** `beadloom init --bootstrap`
    **Context:** `_detect_framework()` in `scanner.py` correctly identifies 11+ frameworks (FastAPI, Django, NestJS, Spring Boot, Express, Vue, React, Actix, Flask, Next.js, Gatsby). The detected framework is stored as metadata on the root node's `extra.tech_stack` — but NOT used to adjust classification heuristics.
    **Issue:** Framework detection is "fire and forget" — the information exists but doesn't influence how nodes are classified. Each framework has known conventions:
    - Django: directory with `apps.py` = domain boundary, `urls.py` = composition root
    - NestJS: `*.module.ts` = domain boundary, `*.controller.ts` = transport layer
    - Spring Boot: `@Service` annotated classes = domain services (not standalone service nodes)
    - FastAPI: `graphql/`, `routers/` inside domain = transport layer, not separate domains
    - Go: `cmd/` = entry points, `internal/` = domains, `pkg/` = shared library
    **Expected:** After framework detection, apply framework-specific classification overrides:
    1. Store detected framework in `config.yml` (user-overridable): `framework: fastapi`
    2. Load framework-specific rules from a built-in registry (e.g., `src/beadloom/onboarding/frameworks/`)
    3. Rules override default `_SERVICE_DIRS` / `_FEATURE_DIRS` / `_ENTITY_DIRS` regex patterns
    4. Rules define composition root patterns, test directory patterns, and layer conventions
    5. Users can extend with custom rules in `config.yml`:
       ```yaml
       framework: fastapi
       classification_overrides:
         - pattern: "*/graphql/"
           kind: feature
           absorb_into_parent: true
       ```

87. [2026-03-10] [LOW] No automated cleanup of orphaned docs after node deletion from graph

    **Severity:** low
    **Command:** `beadloom doctor`
    **Context:** During manual graph refinement, 12 nodes were deleted from `services.yml` (test directories, internal layers). After `beadloom reindex`, the auto-generated doc skeletons for those deleted nodes remained on disk.
    **Issue:** `beadloom doctor` correctly reports orphaned docs as "unlinked from graph" — but the user must manually `rm` each file. For 12 deleted nodes, this means 12 manual deletions across the `docs/` tree. There is no `beadloom docs cleanup` or `beadloom docs prune` command.
    **Expected:** Either:
    - (a) `beadloom docs prune` command that deletes doc files not linked to any graph node (with `--dry-run` preview)
    - (b) `beadloom reindex --prune-docs` flag that auto-cleans orphaned docs during reindex
    - (c) `beadloom doctor --fix` that offers to delete orphaned docs interactively
    For AI agents via MCP: a `prune_orphaned_docs` tool that returns the list of files to delete and accepts confirmation.
    **Workaround:** Manually delete each orphaned doc file reported by `beadloom doctor`.

89. [2026-03-11] [MEDIUM] `sync-check` reports `untracked_files` for annotated and documented files

    **Severity:** medium
    **Command:** `beadloom sync-check`
    **Context:** After adding `# beadloom:domain=` / `# beadloom:feature=` annotations to ALL 55 source files AND enriching all 18 docs with detailed content mentioning every module, `sync-check` still reports 19 of 48 pairs as stale with reason `untracked_files`.
    **Issue:** Files like `app/core/broker.py` have both:
    - Code annotation: `# beadloom:domain=core`
    - Doc mention: `docs/services/core.md` describes `broker.py` in detail
    - Doc marker: `<!-- beadloom:track=app/core/broker.py -->`
    Yet sync-check reports: `core: untracked_files - broker.py` and marks ALL other pairs in the same node as stale (6 stale entries for one untracked file).
    **Pattern:** The affected files are always the ones listed in `beadloom doctor` as "untracked source files". These are files inside the node's `source` directory that exist on disk but apparently aren't indexed as individual tracked items. The multiplier effect (1 untracked file → N stale pairs) inflates the stale count significantly.
    **Expected:** If a file has a `# beadloom:domain=X` annotation AND the doc mentions it (or has a `beadloom:track` marker), sync-check should mark it as OK, not `untracked_files`. The annotation is an explicit signal that the file belongs to node X and should be tracked.
    **Impact:** On the field-tested project, this prevents reaching 100% sync-check OK even with comprehensive annotations and documentation. Max achievable: 60% (29/48).
    **Workaround:** None. Accept the stale warnings as false positives.

90. [2026-03-11] [MEDIUM] `<!-- beadloom:track=... -->` HTML comments in docs have no effect on sync-check

    **Severity:** medium
    **Command:** `beadloom sync-check`
    **Context:** During documentation enrichment, `<!-- beadloom:track=app/core/broker.py -->` HTML comments were added to docs following the convention observed in the `beadloom prime` output hint: `"New features: add # beadloom:feature=REF_ID annotations"`. AI agents naturally extend this to docs with `<!-- beadloom:track=... -->`.
    **Issue:** These HTML comments have no effect on the sync engine. Adding `<!-- beadloom:track=app/core/external-inspection-system/constants.py -->` before a section describing `constants.py` does NOT make sync-check recognize the file as tracked. The comments are inert — they don't participate in staleness detection, freshness tracking, or coverage calculation.
    **Expected:** Either:
    - (a) Recognize `<!-- beadloom:track=<path> -->` in docs as an explicit file-to-doc binding. When present, sync-check should create a tracked pair and monitor both the doc section and the source file for changes.
    - (b) If this convention is not supported, document it clearly in `beadloom prime` / `AGENTS.md` / `docs generate` output so AI agents don't waste effort adding markers that do nothing.
    Option (a) would be a powerful feature: it creates a lightweight, explicit doc-code binding without requiring the full annotation + reindex workflow. AI agents writing docs could simply add `<!-- beadloom:track=... -->` and sync-check would start monitoring.
    **Workaround:** Do not use `<!-- beadloom:track=... -->` comments. They have no functional effect.

85. [2026-03-10] [INFO] Bootstrap accuracy target: 95%+ across all supported languages

    **Severity:** info
    **Context:** Consolidation of all bootstrap accuracy improvements (#74, #75, #77, #78, #80, #81, #82, #83, #84) into a measurable quality target.
    **Current state (measured on 2 field tests):**
    - Field test #37 (React Native / Expo): ~35% accuracy → improved to ~94% after manual refinement
    - Field test #79 (Python / FastAPI): ~80% accuracy → improved to ~95% after rules fix + manual refinement
    **Target:** Bootstrap should produce a graph that is ≥95% accurate (measured as: nodes with correct `kind` + edges with correct direction / total nodes + edges) WITHOUT manual intervention, for projects using any of the 12 supported languages.
    **Measurement plan:**
    - Create a test suite of reference projects (1 per supported language/framework combination)
    - Each reference project has a manually curated `services.golden.yml` (ground truth)
    - CI job: `beadloom init --bootstrap -y` → compare generated graph vs golden → report accuracy %
    - Track accuracy over time as heuristics improve
    **Reference projects needed:**
    | Language | Framework | Project type |
    |----------|-----------|-------------|
    | Python | FastAPI | Monolith API |
    | Python | Django | Monolith web app |
    | TypeScript | NestJS | Monolith API |
    | TypeScript | React + Next.js | Frontend monolith |
    | Go | stdlib net/http | Microservice |
    | Rust | Actix | Microservice |
    | Java | Spring Boot | Monolith API |
    | Kotlin | Spring Boot | Monolith API |
    | Swift | Vapor or SwiftUI | iOS app |
    | TypeScript | Express | Microservices |
    | TypeScript | React Native/Expo | Mobile app |
    | Multi-language | — | Monorepo |

96. [2026-05-28] [MEDIUM] Test suite is volume-heavy but brittle: implementation-coupled and rarely parametrized

    **Severity:** medium
    **Context:** Self-audit (2026-05-28). Test:source ratio ≈1.9:1 (~48K test LOC / ~25K src LOC), 2576 test functions.
    **Issue:** The volume reflects breadth, not depth: only ~4 uses of `@pytest.mark.parametrize` (test bodies are copy-pasted instead of data-driven), and ~193 accesses to private attributes (`._foo`) in tests — assertions welded to current internals that will break on refactor. `test_tui.py` alone is ~5989 LOC for a low-value surface. This brittleness will make the #91 architecture refactor far more painful than necessary.
    **Expected:** Before the #91 refactor: (a) convert copy-pasted test groups to `parametrize`; (b) replace private-attribute assertions with behavior / public-API assertions; (c) reassess whether the TUI warrants ~6K LOC of tests. Treat coverage as a means, not the `fail_under=80` number as the goal.

---

## Excluded Issues

> Issues excluded from the backlog with justification. Not planned for implementation.

20. [2026-02-14] [LOW] `.beadloom/README.md` MCP tools list stale after BDL-014 — Listed 8 tools, missing `get_status` and `prime`. The file is generated once by BDL-013 but never auto-updated. Unlike AGENTS.md which has `generate_agents_md()`, README.md has no regeneration mechanism.
    > **Won't fix.** Static guide, not agent-facing. Low severity, manual update sufficient.

31. [2026-02-16] [LOW] `bd dep remove` reports success but dependency persists — Running `bd dep remove beadloom-3v0 beadloom-53o` reports success, but `bd show beadloom-3v0` still shows the dependency. Workaround: `bd update --status in_progress --claim` ignores blocks.
    > **External.** Bug in `steveyegge/beads` CLI, not in beadloom.

35. [2026-02-17] [MEDIUM] Init doesn't offer `docs generate` — doc coverage 0% after bootstrap — After `beadloom init`, user must run `beadloom docs generate` + `beadloom reindex` separately. The init flow could offer doc skeleton generation as a final step.
    > **Deferred.** Enhancement to onboarding workflow. Current workaround exists. Planned for future init improvements.

36. [2026-02-17] [LOW] Existing docs not auto-linked to graph nodes — Target project had 20 existing docs in `docs/`. All reported as "unlinked from graph" by `doctor`. No auto-discovery mechanism to match existing docs to nodes by path or content similarity.
    > **Deferred.** Requires fuzzy doc-to-node matching — a standalone feature. Deferred to Phase 14+ (semantic analysis).

37. [2026-02-17] [INFO] `beadloom init` bootstrap quality metrics — Auto-generated graph captures ~35% of real architecture (Nodes 6→17, Edges 8→49, Symbols 23→380, Doc Coverage 0%→94% after manual improvement).
    > **Tracking.** Observation, not a bug. Baseline metric for future onboarding quality improvements.

97. [2026-05-29] [LOW] `bd close --suggest-next` reports still-blocked beads as "Newly unblocked" — During BDL-035, closing `beadloom-ji9.4` printed `Newly unblocked: beadloom-ji9.6`, but `bd ready` / `bd dep tree` show ji9.6 is still BLOCKED by ji9.2/.3/.5. `--suggest-next` appears to list beads where the closed issue was *a* blocker without checking whether *other* blockers remain — a false "ready" signal. Workaround: treat `--suggest-next` as candidates only; `bd ready` is authoritative.
    > **External.** Bug in `steveyegge/beads` CLI (1.0.4), not in beadloom. Captured during dogfooding; report upstream if desired.

98. [2026-05-30] [LOW] `test_git_activity.py` date-relative flake + internally inconsistent assertions — `_SAMPLE_GIT_LOG` hardcodes Feb-2026 commit dates, so `test_maps_files_to_correct_nodes` fails once "today" is >30 days later (`commits_30d` 3→0). Same class as the `test_hot_activity` flake fixed in commit a4c88fa. While investigating, the test also looks internally inconsistent (comment references "mno345 from Jan 10" absent from the sample; `core.commits_90d==3` with only 2 core-touching commits) — needs the 30d/90d semantics clarified, not a blind date swap. Found during BDL-036 Wave 1 assembly; pre-existing, unrelated to the wave's changes. Tracked as BDL-036 BEAD-10.
    > **Internal.** Beadloom test debt. Scoped as a follow-up bead within BDL-036 (blocks the test/exit-criterion bead).

---

## Closed Issues

### BDL-040 — F4: Living Knowledge Base + Visual Landscape (2026-06-02)

> F4 dogfooded (BEAD-05) by generating Beadloom's own VitePress site (`beadloom docs site --out site --federated <fed.json>`) — all three showcases: the honest-by-construction metrics dashboard, the 6-domain/4-service/14-feature architecture pages + diagrams, the 🌟 cross-repo landscape map (from a committed *anonymized* `federated.json` fixture — `catalog-service`/`storefront-web`/`commerce-platform`, NOT any private repo), and the published `docs/` with per-doc `doc_sync` validation badges. Dashboard numbers matched `beadloom ci` exactly (lint 0 / doctor 13 checks 0-err / sync-check fresh / federated repo_count 2, contract BREAKING 1).

- 113. ~~[MEDIUM] `docs site` publishes hidden/OS-junk files (e.g. `docs/.DS_Store`) into `site/docs/`~~ **FIXED (BEAD-05)** — `publish_docs`/`build_published_docs` (`application/site_published.py`) globbed `docs/**` and copied every non-`.md` file verbatim, sweeping up `docs/.DS_Store` (and any dotfile). That is non-deterministic per machine (breaks the byte-stable-regeneration guarantee) and pollutes the published site (57→56 files after the fix). Fix: skip any path whose parts start with `.`. RED→GREEN regression test `tests/test_site_published_docs.py::test_os_junk_files_not_published`.
- 115. ~~[INFO] F4 dogfood SUCCESS — `beadloom docs site` regenerates Beadloom's own 3-showcase site, deterministic + honest~~ **VERIFIED (BEAD-05)** — a single `beadloom docs site` run emits 57 files: `dashboard.md` + `dashboard.data.json`, `architecture.md`, one page per domain/service/feature with embedded Mermaid, `landscape.md` (anonymized `catalog-service`/`storefront-web` as clickable health-classed nodes), and the published `docs/` tree (with a generated `docs/index.md` landing page) carrying marker-delimited validation badges. Honest by construction: the dashboard JSON's lint/doctor/sync-check/federated numbers equal the live `beadloom ci` output (the same code path). Regeneration is byte-identical (determinism test). **Build now green:** `npm run docs:build` passed exit 0 after the dead-link fix (#116) — no `ignoreDeadLinks` suppression (honest source-of-truth).
- 116. ~~[MEDIUM] `docs site` node-page doc links + `/docs/` nav target are dead in the built VitePress site~~ **FIXED (BEAD-05 follow-up)** — the F4 dogfood `npm run docs:build` failed with 24 dead links. Root cause: node pages (`application/site_pages.py::_docs_section`) linked hand-written docs at `/<path>` (e.g. `/architecture.md`, `/domains/.../SPEC.md`), but Showcase C publishes the real `docs/` tree under `site/docs/<path>` — so the doc lives at `/docs/<path>`, not `/<path>`. The `docs` table stores paths relative to the source `docs/` dir, so a bare `/<path>` root was always wrong. Fix: `_published_doc_link` roots every node-page doc link at `/docs/` (normalising any stray `docs/` prefix to avoid `/docs/docs/…`). Separately, the `/docs/` Documentation nav target had no landing page (the source `docs/` has no root index), so `publish_docs` now emits a generated `site/docs/index.md` (sorted links to every published doc). No `ignoreDeadLinks` — the source of truth resolves honestly. RED→GREEN node-free guards: `tests/test_site_generator.py::test_generated_internal_links_resolve` (synthetic tree) + `::test_committed_site_tree_has_no_dead_links` (the real committed `site/` tree), both mirroring VitePress clean-URL / `.md`-optional / relative+absolute resolution so the regression is caught WITHOUT node.

### BDL-039 — F3: Tool-Agnostic Enforcement Everywhere (2026-06-02)

> F3 dogfooded (BEAD-06) with committed, anonymized, byte-stable fixtures under `tests/fixtures/f3_gate/` (synthetic role names — `catalog-service`/`storefront-web`/`commerce-platform`; NOT derived from any private repo; the real landscape stays in gitignored scratch). Three reproducible tests (`tests/test_f3_gate_dogfood.py`) prove the F3 success criterion: a CI gate blocks each break-class regardless of who wrote the code, with a non-zero exit AND agent-actionable output. This formalizes the live signal already seen in BEAD-04, where `beadloom ci`'s config-check caught a real stale auto-managed section in Beadloom's own AGENTS.md.

- 109. ~~[INFO] F3 dogfood SUCCESS — the gate BLOCKS a boundary violation, agent-actionable~~ **VERIFIED (BEAD-06)** — a fixture project whose `checkout` module imports `catalog` directly, breaching a committed `forbid_import` rule, runs through `run_ci_gate` (reindex → lint --strict). The gate's `lint` step → **FAIL**, `result.ok is False`, and the finding carries `rule: checkout-no-import-catalog` + a `remediation` hint ("remove the import …, or route it through an allowed intermediary"). `beadloom ci --format github` exits 1 and emits an inline `::error` annotation naming the rule — a violation an agent/CI can act on unaided (principle 4).
- 110. ~~[INFO] F3 dogfood SUCCESS — the gate BLOCKS a cross-service BREAKING, names the missing field~~ **VERIFIED (BEAD-06)** — two committed satellite `export` artifacts form a one-landscape break: producer `catalog-service` exposes GraphQL `{account, plan}`; consumer `storefront-web` references `{plan, subscriptionTier}`. `gate_failures(fed, {"breaking"})` → exactly one BREAKING contract failure whose `.missing == ("subscriptionTier",)`; the remediation hint names `subscriptionTier`. `beadloom ci --hub producer.json --hub consumer.json` exits 1, naming the `federate` step. Cross-language by NAME, no shared symbol.
- 111. ~~[INFO] F3 dogfood SUCCESS — the gate BLOCKS a drifted agent-config (AgentConfigAsCode)~~ **VERIFIED (BEAD-06)** — a project whose `.claude/CLAUDE.md` auto-managed section (between `beadloom:auto-start`/`auto-end`) is stale vs the graph. `check_config_drift` reports exactly one drift naming `.claude/CLAUDE.md` (which-file = agent-actionable); `run_ci_gate`'s `config-check` step → **FAIL**, `result.ok is False`; `beadloom ci --format json` exits 1 with the `config-check` step `status: FAIL`. Same class as the live BEAD-04 AGENTS.md catch — human prose outside the markers is never checked (no #73 false positive).

### BDL-038 — F2: Cross-Service Contract Graph (2026-06-01)

> F2 dogfooded (BEAD-08) on the real landscape via hand-curated, anonymized scratch slices (real repos NOT mutated; slices gitignored). Two parts: (A) live GraphQL contract between the web monolith and its web client; (B) a target-FSD round-trip for a second, separate mobile product. All names anonymized in this log; the real SDL was read read-only.

- 107. ~~[INFO] F2 dogfood SUCCESS — real GraphQL contract mismatch caught BEFORE it ships~~ **VERIFIED (BEAD-08)** — the F2 "what done looks like" criterion. `extract_surface` parsed the monolith's **real 3465-line `schema.graphql` → 266 surface names** (parser robust on production SDL). Modeled the monolith as the `graphql:WebAPI` **producer** (exposed = 266) and its web client as the **consumer** (references = a real subset). `federate` verdict = **CONFIRMED** while references ⊆ exposed. Then injected a realistic drift — the client still calls an operation the newer schema dropped — and `federate` flagged **`BREAKING: graphql:WebAPI — missing: <op>`**, naming the exact missing operation. Cross-language by NAME (TS client ↔ Python backend, no shared code symbol — G3). The 4 F1 AMQP contracts stayed **CONFIRMED** (no regression).
- 108. ~~[INFO] F2 dogfood SUCCESS — paradigm-agnostic FSD round-trip + external native modules + nested landscapes~~ **VERIFIED (BEAD-08)** — a second product (separate landscape) modeled on its **target FSD architecture** (`app→features→entities→shared`, kinds `page`/`feature`/`entity`/`repository`/`service`) round-tripped `export → federate` with **zero kind loss/rejection** (U1 — proves the BEAD-07 DB kind-CHECK drop on a real FSD shape). Its three **native bridge modules** (`lifecycle: external`, outside FSD) resolved to **EXTERNAL**, never DRIFT (U4). As a contract-less product in a **company-landscape** federate run alongside the web product, it produced **zero** mutual DRIFT/UNDECLARED (U5) — the report grouped satellites by landscape. Final company-landscape run: 5 contracts (4 AMQP + 1 GraphQL) CONFIRMED, 3 EXTERNAL edges, 37 OK, 0 false signals.

### BDL-037 — F1: Federation Foundation (2026-06-01)

> Cross-repo federation thin slice dogfooded on the real core-monolith ↔ integration-service RabbitMQ contract. The 4 findings below were raised during the dogfood (BEAD-05) and fixed in BEAD-09; #104 records the dogfood success.

- 100. ~~[HIGH] `beadloom export` silently drops cross-repo `@repo:` edges~~ **FIXED (BEAD-09, d48bfeb)** — new `foreign_edges` table (no FK) persists declared cross-repo edges; the loader writes them and `build_export` unions `edges` + `foreign_edges`, so intent-declared `@repo:` links reach the hub.
- 101. ~~[HIGH] Edge `kind` CHECK rejects `produces`/`consumes`~~ **FIXED (BEAD-09, d48bfeb)** — `produces`/`consumes` added to the `edges.kind` CHECK; the edges table is rebuilt (SQLite cannot `ALTER` a CHECK), additive and idempotent.
- 102. ~~[MEDIUM] UNIQUE `(src,dst,kind)` collapses multiple contracts on one node pair~~ **FIXED (BEAD-09, d48bfeb)** — `contract_key` (derived from `contract.message_type`) is now part of the edges primary key, so N contracts between one node pair survive instead of colliding.
- 103. ~~[LOW] `export` `commit_sha` leaks the host repo's HEAD for a nested project dir~~ **FIXED (BEAD-09, d48bfeb)** — `current_commit_sha` verifies `git --show-toplevel == project_root` and returns `null` (honest "unknown HEAD") for nested non-repo dirs.
- 104. ~~[INFO] Federation dogfood SUCCESS — both-sides confirmed on the real AMQP contract~~ **VERIFIED (BEAD-05, f2eaa94)** — end-to-end proof of F1: all 4 message types confirmed both-sides (`start_plan_version_upload` + `ensure_plans_folder_path` core→integration; `*_completed` integration→core), 16 edges all OK, `unresolved_refs: []`, per-satellite staleness reported. The reconciliation model (match by `message_type`; confirmed = produces ∧ consumes) maps cleanly onto the real contract.

### BDL-036 — Phase 0: Foundation / Honesty Gate (2026-05-30)

> The product now passes its own checks honestly. `lint --strict` exit 0 (rules at ERROR, 0 violations), `doctor` exit 0, 2608 tests pass, coverage 90.54%. Adversarial review (BEAD-08) = PASSED, no faked green.

- 91. ~~[CRITICAL] Beadloom violates its own architecture rules; lint --strict passes anyway~~ **FIXED (BEAD-03, 9c480d2)** — extracted orchestrators (reindex/doctor/debt_report/watcher) into a new `application/` DDD layer; `infrastructure/` is now domain-agnostic (zero domain imports); restored `no-dependency-cycles` + `architecture-layers` to `severity: error`; `lint --strict` genuinely clean.
- 88. ~~[HIGH] Incremental reindex returns 0 nodes~~ **FIXED (BEAD-02, 960f325)** — incremental path now reports true live-DB totals (was a display bug).
- 92. ~~[HIGH] doctor false version drift~~ **FIXED (BEAD-01, 960f325)** — reads in-tree `__version__`, not stale `importlib.metadata`.
- 93. ~~[LOW] AGENTS.md MCP tool count drift (13 vs 14)~~ **FIXED (BEAD-01, 960f325)** — single-source `mcp_tools` catalog pinned to live registry by a drift-guard test.
- 94. ~~[MEDIUM] Over-broad except Exception~~ **FIXED (BEAD-02, 960f325)** — narrowed to `sqlite3.OperationalError` (missing-table only).
- 86. ~~[HIGH] YAML edges silently produce 0 nodes~~ **FIXED (BEAD-04, 960f325)** — loader raises `GraphParseError` with file+line on malformed YAML; flow-style edges parse correctly.
- 89. ~~[MEDIUM] sync-check false untracked_files~~ **FIXED (BEAD-06, 960f325)** — file-level annotations on symbol-less modules now count as tracking signals; genuine 100% reachable (E2E test).
- 90. ~~[MEDIUM] beadloom:track markers inert~~ **FIXED (BEAD-06, 960f325)** — track markers now count as a doc→file binding signal.
- 71. ~~[MEDIUM] bootstrap generates rules that fail lint out-of-the-box~~ **FIXED (BEAD-07, b4d5e62)** — generated rule is `feature-needs-parent` (`has_edge_to: {}`); fresh bootstrap lints clean; regression test added.
- 98. ~~[LOW] test_git_activity date-relative flake~~ **FIXED (BEAD-10, b4d5e62)** — `_SAMPLE_GIT_LOG` uses relative dates; deterministic windows.

99. [2026-05-30] [MEDIUM] Repo-wide documentation drift — sync-check has ~30 pre-existing stale doc pairs

    **Severity:** medium
    **Command:** `beadloom sync-check`
    **Context:** Surfaced honestly during BDL-036 Phase 0. After fixing the sync-check *mechanism* (#89/#90) and restoring honest checks, `sync-check` still reports ~30-32 stale doc-code pairs (graph, tui, onboarding, doc-sync, etc.). Investigation showed the bulk is **accumulated content drift from prior releases**, largely unrelated to Phase 0 changes (e.g. `tui` docs, untouched by Phase 0 code).
    **Issue:** Beadloom's own docs have not kept pace with code; the doc *content* is stale even though the sync-check engine is now honest. Driving sync-check to zero is a repo-wide doc refresh, out of scope for the Phase 0 honesty gate.
    **Expected:** A dedicated doc-refresh epic: update each stale ref's prose to match current symbols, reach genuine `sync-check` exit 0, then keep it green via the BEAD-09 / CI tech-writer loop (ties to STRATEGY-3 F4). Also do the exact UX-log category recount here.
    > **Open — new epic.** The honest re-scope of BDL-036's exit criterion (lint + doctor green now; full sync-check green deferred to this epic).

### v1.9.0 — BDL-034 (UX Batch Fix)

> Phase 13. UX issues and improvements batch fix — rules DB, AGENTS.md regen, docs audit FP, two-phase sync.

65. ~~[2026-02-21] [MEDIUM] `docs audit` still has ~60% false positive rate on beadloom itself~~ **FIXED (BDL-034)** — 3-layer FP reduction pipeline: blocklist modifiers (skip numbers near `max`, `limit`, `%`, etc.), proximity scoring (closest keyword wins with distance ranking), file-type heuristics (SPEC.md/CONTRIBUTING.md suppressed). FP rate reduced from ~60% to ~11%.

66. ~~[2026-02-21] [LOW] `graph_snapshots` lacks diff/compare capability~~ **ALREADY RESOLVED** — Snapshot diffing was already implemented (`beadloom snapshot save`, `snapshot list`, `snapshot compare`) in prior work. No code changes needed.

67. ~~[2026-02-21] [MEDIUM] `_load_rules_into_db` silently drops v3 rule types~~ **FIXED (BDL-034)** — Added `_serialize_rule()` with generic isinstance branches for all 7 v3 rule types (DenyRule, RequireRule, CycleRule, LayerRule, CardinalityRule, ImportBoundaryRule, ForbidEdgeRule). Rules DB table now correctly stores all 9 rules.

68. ~~[2026-02-21] [LOW] `_build_rules_section` and `_read_rules_data` use simplistic rule type detection~~ **FIXED (BDL-034)** — New `_detect_rule_type()` function checks all 7 YAML keys (`require`, `deny`, `forbid_cycles`, `layers`, `check`, `forbid_import`, `forbid`) for accurate type labels in AGENTS.md and `beadloom prime`.

69. ~~[2026-02-21] [LOW] `generate_agents_md` Custom section preservation corrupts file on regeneration~~ **FIXED (BDL-034)** — Switched to HTML comment markers (`<!-- beadloom:custom-start -->` / `<!-- beadloom:custom-end -->`). Old `## Custom` format auto-migrated. No more duplication on regeneration.

70. ~~[2026-02-21] [MEDIUM] `sync-check` resets baseline on `reindex`, masking stale doc content~~ **FIXED (BDL-034)** — Two-phase sync via additive `doc_hash_at_last_edit` column in `sync_state`. Tracks doc content independently from reindex baseline. sync-check detects code drift that survives reindex.

### v1.8.0 — BDL-028 (TUI Bug Fixes)

> Phase 12.13. TUI stabilization round 3 — threading, Explorer dependencies, screen state.

58. ~~[2026-02-20] [MEDIUM] TUI: File watcher thread doesn't stop cleanly on exit~~ **FIXED (BDL-028 BEAD-01)** — Added `threading.Event` as `stop_event` passed to `watchfiles.watch(stop_event=...)`. On unmount, `stop_event.set()` is called, which makes `watchfiles.watch()` exit its blocking loop immediately.

59. ~~[2026-02-20] [MEDIUM] TUI: Domain nodes in graph tree not navigable to Explorer~~ **RECLASSIFIED (BDL-028 BEAD-02)** — UX navigation issue, not a code bug. Domain nodes (nodes with children) only expand/collapse on Enter — no way to open them in Explorer. Recognized as a feature request, now tracked as BEAD-01 in BDL-029 (see #61).

60. ~~[2026-02-20] [HIGH] TUI: Static widgets not updating after screen switch~~ **FIXED (BDL-028 BEAD-03)** — Changed `_push_content()` in `ContextPreviewWidget`, `NodeDetailPanel`, and `DependencyPathWidget` to use `update(self._build_text())` instead of `refresh()`. `Static.refresh()` only triggers a re-render of existing content, while `update()` actually replaces the widget's content with new Rich Text.

### v1.8.0 — BDL-029 (TUI UX Improvements)

> Phase 12.14. TUI usability improvements — domain navigation, tree icons, edge labels, screen switching.

61. ~~[2026-02-21] [MEDIUM] TUI: Explorer — no way to open domain nodes directly~~ **FIXED (BDL-029 BEAD-01)** — Domain nodes in graph tree only expand/collapse on Enter. Added `e` keybinding to Dashboard that opens Explorer for any highlighted node, including domain nodes with children.

62. ~~[2026-02-21] [MEDIUM] TUI: Triangle icon shown for childless nodes at cold start~~ **FIXED (BDL-029 BEAD-02)** — Some nodes (e.g. "tui") show expandable triangle icon but have no children at cold start. Root cause: `_build_tree` checked `ref_id in hierarchy` but hierarchy dict could contain entries with empty children lists `{"tui": []}`. Changed condition to `hierarchy.get(ref_id)` which is falsy for empty lists.

63. ~~[2026-02-21] [MEDIUM] TUI: Edge count `[N]` has no legend~~ **FIXED (BDL-029 BEAD-03)** — `[N]` numbers next to tree nodes have no explanation. Changed label format to `[N edges]` (plural), `[1 edge]` (singular), omit badge for 0.

64. ~~[2026-02-21] [HIGH] TUI: Esc (Back) from Explorer/DocStatus crashes with ScreenStackError~~ **FIXED (BDL-029 BEAD-04)** — Pressing Esc from Explorer or DocStatus after navigating via `switch_screen` (keys 1/2/3) crashes with `ScreenStackError: Can't pop screen`. Root cause: `action_go_back()` called `pop_screen()` but `switch_screen` navigation keeps only 1 screen on the stack. Fixed in both ExplorerScreen and DocStatusScreen by using `_safe_switch_screen("dashboard")`.

### v1.8.0 — BDL-025 (TUI), BDL-026 (Docs Audit), BDL-027 (UX Batch Fix)

> Phases 12.10–12.12. Dogfooding on beadloom itself and an external React Native + Expo project.

26. ~~[2026-02-16] [MEDIUM] Test mapping shows "0 tests in 0 files" for domains despite 1408+ tests~~ **FIXED (BDL-027 BEAD-05)** — `aggregate_parent_tests()` rolls up child node test counts to parent domain nodes.

29. ~~[2026-02-16] [HIGH] Route extraction false positives~~ **FIXED (BDL-027 BEAD-05)** — Self-exclusion added: files named `route_extractor` are skipped. Route aggregation scoped to source file ownership.

30. ~~[2026-02-16] [MEDIUM] Routes displayed with poor formatting in polish text~~ **FIXED (BDL-027 BEAD-05)** — `format_routes_for_display()` separates HTTP routes from GraphQL routes with wider columns.

32. ~~[2026-02-17] [HIGH] `beadloom init` scan_paths incomplete for React Native projects~~ **FIXED (BDL-027 BEAD-04)** — `detect_source_dirs()` now scans all top-level directories containing code files, not just manifest-adjacent ones.

33. ~~[2026-02-17] [MEDIUM] `beadloom init` is interactive-only — no CLI flags for automation~~ **FIXED (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

34. ~~[2026-02-17] [MEDIUM] Auto-generated `rules.yml` includes `service-needs-parent` that always fails on root~~ **FIXED (BDL-027 BEAD-04)** — Already resolved in prior work; verified during BDL-027.

38. ~~[2026-02-19] [MEDIUM] `beadloom doctor` shows `[info]` not `[warn]` for nodes without docs~~ **FIXED (BDL-027 BEAD-03)** — Promoted from `Severity.INFO` to `Severity.WARNING`, making it actionable for agents and CI.

39. ~~[2026-02-20] [MEDIUM] Debt report "untracked: 8" — no way to see which files~~ **FIXED (BDL-027 BEAD-03)** — `_count_untracked()` now returns `(count, ref_ids)` list in both human and JSON output.

40. ~~[2026-02-20] [MEDIUM] Oversized false positive on root and parent nodes~~ **FIXED (BDL-027 BEAD-03)** — `_count_oversized()` counts only direct files, excluding subdirectories claimed by child node source prefixes.

41. ~~[2026-02-20] [HIGH] C4 diagram: all elements render as `System()` — no Container/Component differentiation~~ **FIXED (BDL-027 BEAD-01)** — `_compute_depths()` filters self-referencing `part_of` edges. BFS correctly computes depths.

42. ~~[2026-02-20] [MEDIUM] C4 diagram: label and description are identical~~ **FIXED (BDL-027 BEAD-01)** — Label generated from ref_id via title-casing + hyphen-to-space; summary used as description only.

43. ~~[2026-02-20] [MEDIUM] C4 diagram: root node appears inside its own boundary~~ **FIXED (BDL-027 BEAD-01)** — `_load_edges()` skips self-referencing `part_of` entries.

44. ~~[2026-02-20] [LOW] C4 diagram: boundary ordering is non-semantic~~ **FIXED (BDL-027 BEAD-01)** — Orphan boundaries sorted by node kind/depth; root rendered first, then alphabetical.

45. ~~[2026-02-20] [LOW] C4 diagram: `!include` always uses `C4_Container.puml`~~ **FIXED (BDL-027 BEAD-01)** — PlantUML `!include` selects `C4_Context.puml` / `C4_Container.puml` / `C4_Component.puml` based on `--level` flag.

46. ~~[2026-02-20] [HIGH] TUI: Graph tree empty — only "Architecture" label visible~~ **FIXED (BDL-025)** — Self-referencing `part_of` edge caused `get_hierarchy()` infinite loop. Added `if child != parent` filter.

47. ~~[2026-02-20] [HIGH] TUI: Activity widget shows 0% for all domains~~ **FIXED (BDL-025)** — Wrong attribute name: `commit_count` → `commits_30d`. Normalization: `min(commits_30d * 2, 100)`.

48. ~~[2026-02-20] [MEDIUM] TUI: Enter on tree node only expands — doesn't navigate to Explorer~~ **FIXED (BDL-025)** — Leaf-node detection added: if `ref_id not in hierarchy`, opens Explorer screen.

49. ~~[2026-02-20] [HIGH] TUI: Doc Status screen shows "–" for all Doc Path and Reason~~ **FIXED (BDL-025)** — DB opened as `mode=ro` but `check_sync()` needs writes. Switched to WAL mode read-write.

50. ~~[2026-02-20] [MEDIUM] TUI: Explorer shows self-referencing edges as duplicates~~ **FIXED (BDL-025)** — Added `dst != ref_id` / `src != ref_id` filter to edge lists.

51. ~~[2026-02-20] [MEDIUM] TUI: Explorer defaults to "Downstream Dependents" — empty for leaf nodes~~ **FIXED (BDL-025)** — Default changed to `MODE_UPSTREAM`. User presses `d` to switch to downstream.

52. ~~[2026-02-20] [HIGH] `docs audit` high false positive rate (~86%) on real project~~ **FIXED (BDL-027 BEAD-02)** — Skip numbers <10 for count facts, percentage FP filter, SPEC.md/CONTRIBUTING.md excluded from scan.

53. ~~[2026-02-20] [MEDIUM] `docs audit` year "2026" matched as mcp_tool_count~~ **FIXED (BDL-027 BEAD-02)** — Standalone year regex `\b20[0-9]{2}\b` added to false positive filters.

54. ~~[2026-02-20] [MEDIUM] `docs audit` SPEC.md files dominate false positives~~ **FIXED (BDL-027 BEAD-02)** — `_graph/features/*/SPEC.md` excluded from default scan paths.

55. ~~[2026-02-20] [LOW] `docs audit` test_count ground truth seems inflated~~ **FIXED (BDL-027 BEAD-02)** — Labeled as symbol count in output; documented distinction between test symbols and test cases.

56. ~~[2026-02-20] [LOW] `docs audit` Rich output lacks file path context~~ **FIXED (BDL-027 BEAD-02)** — Stale mentions show full relative path from project root.

57. ~~[2026-02-20] [MEDIUM] `docs audit` version fact not collected for dynamic versioning~~ **FIXED (BDL-027 BEAD-02)** — Detects `dynamic = ["version"]` + `[tool.hatch.version]`; fallback to `importlib.metadata.version()`.

### v1.6.0 — BDL-017 (Context Oracle), BDL-019 (Docs Refresh)

16. ~~[2026-02-13] [MEDIUM] After BDL-012 bug-fixes, beadloom's own docs are outdated~~ **FIXED (BDL-019)** — All 13 domain/service docs refreshed. `symbols_changed` reduced from 35 to 0.

27. ~~[2026-02-16] [LOW] `docs polish` text format doesn't include routes/activity/tests data~~ **FIXED (BDL-017 BEAD-14)** — Smart `docs polish` now includes routes, activity level, test mappings, and deep config data.

28. ~~[2026-02-16] [INFO] `beadloom status` Context Metrics section working well~~ **CLOSED** — Confirmed working. No action needed.

### v1.5.0 — BDL-015 (Stabilization), BDL-016 (E2E Baseline)

15. ~~[2026-02-13] [HIGH] `doctor` 100% coverage + `Stale docs: 0` is misleading after major code changes~~ **FIXED (BDL-015 + BDL-016)** — Symbol-level drift detection via `_compute_symbols_hash()` + `_check_symbol_drift()`.

17. ~~[2026-02-14] [LOW] `setup-rules` auto-detect doesn't work for Windsurf and Cline~~ **FIXED (BDL-015 BEAD-12)** — Content-based detection instead of file presence.

18. ~~[2026-02-14] [HIGH] `sync-check` reports "31/31 OK" despite massive semantic drift~~ **FIXED (BDL-015 + BDL-016)** — Symbol-level drift detection works end-to-end.

19. ~~[2026-02-14] [MEDIUM] `.beadloom/AGENTS.md` not auto-generated during bootstrap~~ **FIXED (BDL-015 BEAD-06)**.

21. ~~[2026-02-14] [HIGH] Incremental reindex returns Nodes: 0 after YAML edit~~ **FIXED (BDL-015 BEAD-11)**.

22. ~~[2026-02-15] [HIGH] `.claude/CLAUDE.md` references obsolete project phases~~ **FIXED** — Updated phases, docs references.

23. ~~[2026-02-15] [HIGH] `/templates` has wrong project structure~~ **FIXED** — Fully rewritten with stabilized format.

24. ~~[2026-02-15] [HIGH] `/test` has wrong import paths~~ **FIXED** — Updated all paths and patterns.

25. ~~[2026-02-15] [MEDIUM] `/review` references old architecture layers~~ **FIXED** — Updated layer names.

### v1.0.0–v1.4.0 — BDL-012 (Bug Fixes), early fixes

1. ~~[2026-02-13] [MEDIUM] `doctor` warns about auto-generated skeleton docs as "unlinked from graph"~~ **FIXED** — `generate_skeletons()` writing to wrong paths. Fixed by using `docs:` paths from graph.

2. ~~[2026-02-13] [LOW] `lint` produces no output on success~~ **FIXED** — CLI now prints `"0 violations, N rules evaluated"` as confirmation.

3. ~~[2026-02-13] [LOW] `docs generate` creates skeleton files for services including the root~~ **FIXED** — Root detection changed from "empty source" to "no `part_of` edge as src".

4. ~~[2026-02-13] [INFO] MCP server description says "8 tools" / CLI "18 commands"~~ **FIXED** — services.yml updated to 20 commands, 9 tools.

5. ~~[2026-02-13] [HIGH] `doctor` shows 0% doc coverage on bootstrapped projects~~ **FIXED (BDL-012 BEAD-01)** — `generate_skeletons()` writes `docs:` field back to `services.yml` via `_patch_docs_field()`.

6. ~~[2026-02-13] [HIGH] `lint` false positives on hierarchical projects~~ **FIXED (BDL-012 BEAD-02)** — Rule engine accepts empty `has_edge_to: {}`. `service-needs-parent` removed.

7. ~~[2026-02-13] [MEDIUM] Dependencies empty in polish data~~ **FIXED (BDL-012 BEAD-03)** — `generate_polish_data()` reads `depends_on` edges from SQLite via `_enrich_edges_from_sqlite()`.

8. ~~[2026-02-13] [MEDIUM] `docs polish` text format = 1 line~~ **FIXED (BDL-012 BEAD-03)** — `format_polish_text()` renders multi-line output with node details, symbols, deps, doc status.

9. ~~[2026-02-13] [LOW] Generic summaries~~ **FIXED (BDL-012 BEAD-06)** — `_detect_framework_summary()` detects Django apps, React components, Python packages, Dockerized services.

10. ~~[2026-02-13] [LOW] Parenthesized ref_ids from Expo router~~ **FIXED (BDL-012 BEAD-06)** — `_sanitize_ref_id()` strips parentheses: `(tabs)` → `tabs`.

11. ~~[2026-02-13] [MEDIUM] Missing language parsers — 0 symbols with no warning~~ **FIXED (BDL-012 BEAD-05)** — `check_parser_availability()` + `_warn_missing_parsers()` in CLI.

12. ~~[2026-02-13] [LOW] `reindex` ignores new parser availability~~ **FIXED (BDL-012 BEAD-06)** — Parser fingerprint tracked in `file_index`. Extension changes trigger full reindex.

13. ~~[2026-02-13] [INFO] Bootstrap skeleton count includes pre-existing files~~ **FIXED (BDL-012 BEAD-06)** — CLI shows "N created, M skipped (pre-existing)".

14. ~~[2026-02-13] [MEDIUM] Preset misclassifies mobile apps as microservices~~ **FIXED (BDL-012 BEAD-04)** — `detect_preset()` checks for React Native/Expo and Flutter before `services/` heuristic.
