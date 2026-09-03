# CLI Reference

<!-- beadloom:watches=cli,graph,flow.yml -->

Beadloom CLI is built on Click and provides a set of commands for managing the knowledge index.

## Specification

### Global Options

```
beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND
```

- `--verbose` / `-v` -- verbose output
- `--quiet` / `-q` -- errors only
- `--version` -- show version

### beadloom init

Project initialization. Four entry points, and three modes for the two that let you
choose one:

```bash
# Generate graph from code structure (auto-detects architecture)
beadloom init --bootstrap [--preset {monolith,microservices,monorepo}] [--project DIR]

# Import existing documentation
beadloom init --import DOCS_DIR [--project DIR]

# Non-interactive mode (for CI/scripting)
beadloom init --yes [--mode {bootstrap,import,both}] [--force] [--project DIR]

# Interactive mode (default when no flags given)
beadloom init [--project DIR]
```

`--bootstrap` scans source directories (src, lib, app, services, packages), classifies subdirectories using architecture-aware preset rules, infers edges from directory nesting, and generates `.beadloom/_graph/services.yml` + `.beadloom/config.yml`.

`--preset` selects an architecture preset:
- `monolith` -- top dirs are domains; subdirs map to features, entities, services
- `microservices` -- top dirs are services; shared code becomes domains
- `monorepo` -- packages/apps are services; manifest deps become edges

When `--preset` is omitted, Beadloom auto-detects: `services/` or `cmd/` -> microservices, `packages/` or `apps/` -> monorepo, otherwise -> monolith.

`--import` classifies .md files (ADR, feature, architecture, other) and generates `.beadloom/_graph/imported.yml`.

`--yes` / `-y` enables non-interactive mode: no prompts, uses defaults. Combined with `--mode` to select the initialization strategy:
- `bootstrap` (default) -- generate graph from code
- `import` -- classify existing docs
- `both` -- bootstrap graph and import docs

`--force` overwrites an existing `.beadloom/` directory. Without it, non-interactive init skips if `.beadloom/` already exists.

#### Exit codes

`0` = a scaffold that passes the rules written beside it. `1` = a scaffold that does not.

**`init` takes a verdict on the graph it wrote.** Every entry point that writes a file
under `.beadloom/_graph/` — `--yes` in any mode, `--bootstrap`, `--import`, and the
interactive wizard — re-indexes and then runs the Gate's own lint step
(`application.gate.lint_step`, the same object `beadloom ci` runs) over the project. When
that step does not pass, `init` withdraws the completion it has already printed, reports
the failure on stderr and exits 1. The scaffold is left on disk either way: the exit code
reports the state, it does not withdraw the graph. The non-zero code is what makes a
scripted `init && ci` stop while the cause is still in view.

Before BDL-067 there was no verdict. A virgin `beadloom init --yes --mode bootstrap`
printed `Graph: 2 nodes, 0 edges`, exited 0, and the adopter's next command — `beadloom
ci` — was red on `domain-needs-parent`, a rule that same run had written one step earlier
(BDL-UX #192).

Two conditions decide whether a verdict is taken at all, and both are asked of the tree
rather than of the branch reporting:

- **Nothing under `.beadloom/_graph/` changed during the run** — no verdict. This is what
  keeps the wizard's re-init prompt, which is put before any writer runs, from reporting
  an existing tree's failures under a line saying a scaffold was written.
- **The wizard's `edit` review answer** — no verdict, deliberately. The wizard has just
  handed the graph over to be edited by hand and told you to run `beadloom reindex`
  afterwards, so there is nothing settled to judge.

**Two report shapes**, because a rule that failed and a rules file that would not load are
not the same news:

1. *Rules were evaluated and the graph fails them.* One line per error-severity rule,
   naming the rule, the node, and the graph file that node was written into. Under it, one
   sentence saying whose the failure is, chosen from two facts about the tree: did this run
   write the failing node, and did this run write `rules.yml`. Only the corner where both
   are this run's calls the result a defect in Beadloom's bootstrap and asks for a bug
   report. The other three name what was already in `.beadloom/_graph/` and ask for
   nothing.
2. *`.beadloom/_graph/rules.yml` could not be read.* The loader's complaint is printed
   instead of a rule name, and the report states that no rule was evaluated, so the graph
   is unchecked rather than wrong. `init` leaves an existing rules file alone, so this is
   usually a hand edit.

The closing line names the step `beadloom ci` will fail by the step's name and summary
rather than by quoting a rendered line: `ci` renders with `rich` on a TTY and with the
`github` renderer everywhere else, and the two print different text for the same failure —
which is exactly the scripted context `--yes` serves.

**Known limitation — a graph file `init` cannot read still ends in a traceback**
(BDL-UX #220, open). The readers under `onboarding/` share one skip policy, but the
readers `init` reaches in other domains do not: `application/reindex/indexing.py`'s
`read_declared_docs` and `graph/loader.py` walk `.beadloom/_graph/` with their own
answers. Measured over `init`'s eight (entry point x mode) cells crossed with three shapes
of a hand-edited `.beadloom/_graph/legacy.yml` — a file that does not parse, a file whose
top level is a list, and a file carrying an unquoted date (`added: 2026-09-02`) — 24 runs,
of which the 15 that reach the file end in a Python traceback: `--bootstrap`, `--import`
and all three wizard modes, on every shape.
`--yes` reaches none of them, and not because a guard works: non-interactive init returns
`skipped` when `.beadloom/` already exists, and `--force` deletes the directory, and the
unreadable file with it, before writing.

Projects without a `docs/` directory work fine -- Beadloom operates in zero-doc mode with code-only context (graph nodes, annotations, context oracle).

**`--bootstrap` also appends an ignore block to the project's `.gitignore`, once** (BDL-061.35). Before it, Beadloom wrote an ignore entry nowhere, so an adopter collected untracked churn from the very first `reindex`. The block names the derived state only — `.beadloom/**/*.db{,-wal,-shm}` and `.beadloom/guard-firings.jsonl` — and each pattern carries its reason in the file; the graph under `.beadloom/_graph/` and `flow.yml` are source and stay committable. It is **written once and never rewritten**: a run that finds the marker does nothing, so deleting a line is a real override rather than an edit the next run undoes (a team that wants the guard firing record committed removes that line, once). Nothing is written outside a git working tree, a pattern the project already declares is not duplicated, and the project's own lines are untouched. The write is reported (`✓ Ignored: N generated path(s) …`), because silently editing someone's `.gitignore` is its own surprise.

### beadloom reindex

Full reindex: drops all tables and reloads from scratch.

```bash
beadloom reindex [--full] [--docs-dir DIR] [--project DIR]
```

- `--full` -- force full rebuild (drop all tables and re-create)
- `--docs-dir` -- documentation directory (default: from config.yml or `docs/`)

Default mode is incremental (only changed files). Use `--full` to force complete rebuild.

Order: drop tables -> create schema -> load graph YAML -> index docs -> index code -> resolve imports -> load rules -> build sync state -> populate FTS5 -> take health snapshot.

When no changes are detected, displays current DB totals (nodes, edges, docs, symbols) instead of reindex counts. Warns about missing tree-sitter parsers when symbols == 0.

The incremental path re-extracts imports for the code files it touched, deletes the imports of files that disappeared, and rebuilds the derived `depends_on` edge set (marked `extra.derived='imports'`, so a graph-declared edge is never collateral damage). A boundary violation introduced between two incremental runs is therefore caught by `lint` without a full rebuild. Two counters in the summary do not describe that work: `Imports:` and `Rules:` are only populated on the `--full` path and print `0` on an incremental run that did refresh them.

**Reindex sets the freshness baseline.** `sync_state` is (re-)established from the tree being indexed, so a reindex into a fresh or deleted database makes every declared pair fresh by construction. That is why doc freshness must be checked after an *incremental* reindex on an existing index — see `beadloom sync-check`.

### beadloom ctx

Get a context bundle for the specified ref_id(s).

```bash
beadloom ctx REF_ID [REF_ID...] [--json|--markdown] [--depth N] [--max-nodes N] [--max-chunks N] [--intent|--no-intent] [--project DIR]
```

Outputs Markdown by default. `--json` for machine-readable format.

The bundle carries an **Intent (TO-BE)** section: the epics whose planning
documents declared this node, with the document and line to read the reason at.
So the one command an agent is told to run before touching an area answers what
the code IS and what it is FOR, rather than only the first.

It is on by default because a flag nobody passes protects nothing, and the cost
is small and measured: on this repository the section adds about 330 bytes to a
157 KB bundle, and reading the whole TO-BE space costs 25 ms on a cold bundle
and nothing on a cached one, since an edited planning document is now one of the
inputs the bundle cache is invalidated by. `--no-intent` skips the read; the
bundle then reports `not_checked`, which is not the same statement as *no epic
declares this node*.

A node no epic declared — 69 of this repository's 84 — prints the size of what
was searched instead of nothing:

```
## Intent (TO-BE)

No epic declares this node. 61 epic(s) read, 5 of them declare a node.
```

### beadloom graph

Architecture graph visualization. Supports Mermaid, C4-Mermaid, and C4-PlantUML output formats.

```bash
# Full graph in Mermaid format (default)
beadloom graph [--project DIR]

# Subgraph from specified nodes
beadloom graph REF_ID [REF_ID...] [--depth N] [--json]

# C4 architecture diagram (Mermaid C4 syntax)
beadloom graph --format c4 [--level {context,container,component}] [--project DIR]

# C4 architecture diagram (PlantUML C4 syntax)
beadloom graph --format c4-plantuml [--level container] [--project DIR]

# C4 component diagram scoped to a specific container
beadloom graph --format c4 --level component --scope graph [--project DIR]
```

- `--format` -- output format: `mermaid` (default), `c4` (Mermaid C4 syntax), or `c4-plantuml` (C4-PlantUML syntax).
- `--level` -- C4 diagram level (only used with `--format=c4` or `--format=c4-plantuml`):
  - `context` -- System-level nodes only (highest abstraction)
  - `container` (default) -- System and Container nodes
  - `component` -- Children of a specific container (requires `--scope`)
- `--scope` -- ref_id of the container to zoom into when `--level=component`. Required for component-level diagrams.

C4 level assignment uses `part_of` depth: root nodes become Systems, depth 1 becomes Containers, depth 2+ becomes Components. Nodes can override this by setting `c4_level` in their YAML `extra` field. Nodes tagged `external` render as `_Ext` variants; nodes tagged `database` or `storage` render as `Db` variants.

### beadloom status

Index statistics with health trends.

```bash
beadloom status [--json] [--project DIR]
```

Shows Rich-formatted dashboard with: node count (broken down by kind), edges, documents, symbols, per-kind documentation coverage, stale docs, isolated nodes, empty summaries. Includes trend indicators comparing current reindex with previous snapshot. Also displays context metrics: average bundle token size, largest bundle (ref_id + tokens), total indexed symbols.

`--json` -- structured JSON output.

#### status --debt-report

Architecture debt report mode. Aggregates health signals from lint, sync-check, doctor, git activity, and test mapper into a single 0-100 debt score with category breakdown and top offending nodes.

```bash
beadloom status --debt-report [--json] [--fail-if=EXPR] [--category=NAME] [--project DIR]
```

- `--debt-report` -- show architecture debt report instead of the standard status dashboard.
- `--json` -- output the debt report as structured JSON (with `--debt-report`).
- `--fail-if=EXPR` -- CI gate: exit 1 if condition is met. Requires `--debt-report`. Supported expressions:
  - `score>N` -- fail if overall debt score exceeds N.
  - `errors>N` -- fail if rule violation error count exceeds N.
- `--category=NAME` -- filter the debt report to a single category. Accepted names: `rules`, `docs`, `complexity`, `tests` (short names) or `rule_violations`, `doc_gaps`, `test_gaps` (internal names).

The debt score formula combines four categories:
- **Rule Violations** -- weighted count of lint rule errors and warnings.
- **Documentation Gaps** -- undocumented nodes, stale docs, untracked files.
- **Complexity** -- oversized domains (by symbol count), high fan-out nodes, dormant domains.
- **Test Gaps** -- untested domains/features.

Severity classification: `clean` (0), `low` (1-10), `medium` (11-25), `high` (26-50), `critical` (51-100).

Examples:

```bash
# Human-readable Rich output
beadloom status --debt-report

# Machine-readable JSON
beadloom status --debt-report --json

# CI gate: fail if score exceeds 30
beadloom status --debt-report --fail-if=score>30

# CI gate: fail if any lint errors
beadloom status --debt-report --fail-if=errors>0

# Filter to documentation gaps only
beadloom status --debt-report --category=docs
```

### beadloom doctor

Architecture graph validation.

```bash
beadloom doctor [--project DIR]
```

Checks:
- Nodes with empty summary
- Documents not linked to nodes
- Nodes without documentation
- Isolated nodes (no edges)

### beadloom sync-check

Check doc-code synchronization.

```bash
beadloom sync-check [--porcelain] [--json] [--report] [--ref REF_ID] [--staged]
                    [--since GIT_REF] [--record-surface] [--project DIR]
```

Exit codes: 0 = all OK, 1 = error, 2 = a pair is stale **or missing**.

- `--porcelain` -- TAB-separated output for scripts. Format: `status\tref_id\tdoc_path\tcode_path\treason`.
- `--json` -- structured JSON output with summary and pair details. Each pair includes `status`, `ref_id`, `doc_path`, `code_path`, `reason`, `baseline`, and optional `details`.
- `--report` -- ready-to-post Markdown report for CI (GitHub/GitLab).
- `--ref` -- filter results by ref_id.
- `--staged` -- judge only the pairs this commit stages either side of, and state how many were left to the push gate. For a pre-commit hook in a **shared working tree**, where a whole-tree check fails one agent's commit on a neighbour's in-progress file (BDL-UX #118). The narrowing is counted, never silent: `summary.not_checked_outside_commit` and `summary.commit_scope` in `--json` (present in this mode only), a `scope` record in `--porcelain`, and a leading line in the human shape. When git cannot say what is staged, nothing is narrowed and `commit_scope` reads `not_narrowed` -- an absent answer is not "nothing staged". The content compared is the WORKING-TREE content of the staged paths, not the staged blobs.
- `--record-surface` -- record the declared documentation surface (pair + declared-doc counts) to the committed `.beadloom/sync-surface.json`. A later run compares against it and says so when the surface SHRANK; no ordinary run rewrites it, because a check that silently re-records the number it checks against re-attests without evidence.
- `--since GIT_REF` -- compute drift against the code state at a **git ref** (e.g. the push's parent commit) instead of the stored `sync_state` baseline. Reports pairs whose code drifted since the ref while the doc was not correspondingly updated. This makes drift detection work on a **fresh CI checkout**: a clean clone reindexes from scratch and re-baselines `sync_state` to the just-pushed code, so without a ref baseline `sync-check` sees 0 stale even when the push left a doc behind. Mirrors `beadloom diff --since`. Used by the AI tech-writer harness (it passes the push parent — `github.event.before` / `$CI_COMMIT_BEFORE_SHA`, falling back to `HEAD~1`).

**What a green count covers.** A node that declares `docs:` contributes pairs from its `# beadloom:` annotations or, when those yield none, from the files its `source:` owns — the pairing is independent of node kind. Whatever is still uncovered is listed BY NAME with a reason, as an advisory line that never changes the exit code: `no_indexed_code` (no indexed code under the node's source), `files_owned_by_nested_nodes` (every file under it belongs to a more specific node) and `no_source` (the node declares no source path). `--json` carries the same list in `data.unchecked` with `summary.unchecked`; `--porcelain` prints one `unchecked` line per unchecked doc.

Measured on this repository, 2026-08-24: 330 declared pairs, all of them checked and 0 listed as unchecked.

**Six verdicts, because unverifiable is not clean.** `ok` and `stale` are outcomes of a comparison that happened. `missing` (the doc file, the code file, or a doc the graph DECLARES is not on disk) fails the check at exit 2 — the gate is not satisfied by having less to check. `unverified` (`reason=no_baseline`) means nothing could be compared; it is printed as `[not verified]`, counted separately, and never counted as fresh. `incomplete` (`missing_sections`, `section_not_in_use`, BDL-061 S4) is the only verdict about a document's STRUCTURE rather than its currency: the four content reasons all measure bytes changing, so none of them can see a README edited down to a title. It never blocks and is never written to `sync_state`. `exempt` (`working_space`, BDL-061 S5) means the document is in the WORKING space and a project's config declared that space exempt from freshness; the declared reason travels in `details`, and `missing` is decided BEFORE any exemption applies, so a deleted file is never made quieter by a declaration. Every pair also reports `baseline` — `index`, `git:HEAD` or `none` — so a green result says what it was green against.

**The verdicts sum to the total.** `incomplete` and `exempt` each had no summary counter, so `ok + stale + missing + unverified + unchecked` did not add up to `total` and a machine consumer reading only the summary saw neither. Both keys are in the summary now (stored-baseline mode; the `--since` shape is untouched), and the sum that holds is `ok + stale + missing + unverified + exempt + incomplete`. `unchecked` is deliberately outside it — it counts NODES that contribute no pair at all, a different population from the pairs the verdicts describe. Measured on this repository, 2026-08-24: `total 330 = 326 ok + 4 incomplete`, with `exempt 0` and `unchecked 0`.

**Where the baseline lives, and why a rebuild no longer blinds it.** `.beadloom/beadloom.db` is a cache, not the record: a database built from scratch used to store the current tree AS the baseline, so `sync-check` reported every pair fresh, including pairs whose doc was never updated (measured before the fix: incremental reindex → exit 2 with 6 stale; `rm .beadloom/beadloom.db*` + reindex → exit 0 with 0 stale, same tree). Each pair now records where its baseline came from, and a pair whose baseline was fabricated at index-build time is corroborated against **git `HEAD`** — the baseline a rebuild cannot destroy, because it is committed. Where git cannot answer (not a repository, no commit, no git binary), the pair reads `unverified` rather than fresh. `--since <ref>` remains the strongest form and is what the CI harness passes on a fresh checkout. A clean database is still the right instrument for `lint`, and it is no longer a way to get a green `sync-check` for free.

**The count is part of the contract.** `--record-surface` writes `.beadloom/sync-surface.json` (committed, so a rebuild cannot lose it). A later run whose declared surface FELL says so by name — `declared surface SHRANK since it was recorded: 275 → 269 pair(s)` — instead of quietly printing the smaller number. It is a warning, not a verdict: the cause that matters (a declared doc that is gone) fails on its own.

Human-readable output includes reason-aware formatting:
- `missing` status: `[missing]` with which side is gone (`the linked doc file is gone`, `the paired code file is gone`, `declared in the graph, not on disk`).
- `unverified` status: `[not verified]` with the reason it was not verified — either there was no baseline, or this pair's own file did not move while a named sibling of the same node did (`sibling_symbols_changed`).
- `incomplete` status: `[warn]` naming either the document and its missing sections, or the node KIND and the ratio behind a section its documents do not use (`Source (5/39)`).
- `untracked_files` reason: displays list of untracked files in `details`.
- `missing_modules` reason: displays list of missing modules in `details`.
- Other stale reasons (e.g. `symbols_changed`, `content_changed`): displays `reason` next to the code path.

**Reference surface drift (advisory).** A high-traffic overview doc can opt in to
freshness against a coarse interface surface with an in-doc annotation near its
top:

```markdown
<!-- beadloom:watches=cli,graph,flow.yml -->
```

The watched surfaces are `cli` (the Click command + flag tree), `graph` (the
node + edge identity set), and `flow.yml` (the normalized `.beadloom/flow.yml`).
`reindex` baselines the aggregate hash of the declared surfaces; `sync-check`
recomputes it and, when the surface changed, emits a pair with `reason =
surface_drift` and **severity warning**. In `--json`, `summary.surface_drift`
and a `references[]` array carry these pairs (stored-baseline mode only; the
`--since` shape is unchanged). Surface drift is advisory — it never changes the
exit code or fails `beadloom ci`; it asks a human to re-read the overview and
clear it with `sync-update`.

### beadloom sync-update

Review and update stale documentation.

```bash
# Show sync status for a ref_id
beadloom sync-update REF_ID --check [--project DIR]

# Interactive: open stale docs in $EDITOR, mark synced after editing
beadloom sync-update REF_ID [--project DIR]

# Non-interactive: re-baseline freshness without an editor or prompt
beadloom sync-update REF_ID --yes [--project DIR]

# Non-interactive, fixpoint loop: re-baseline every currently-stale ref
beadloom sync-update --all --yes [--project DIR]
```

`--yes` (`-y`) records that the doc(s) for the ref match the code now (recomputes
file hashes + symbols hash, sets `status='ok'`), prints a concise summary, and
exits 0 — no editor, no prompt. This is the primitive a CI/script fixpoint loop
uses to re-baseline freshness after a doc is rewritten; it is the same operation
the interactive path performs after an edit. `--all` re-baselines every ref
`sync-check` currently flags stale (deterministic; requires `--yes`).

`REF_ID` also accepts the **path of a reference doc** (one carrying a
`watches:` annotation). In that case `sync-update` recomputes and stores the
doc's aggregate surface hash, clearing a `surface_drift` warning — the same
re-attestation as a symbol pair.

**`--check` never writes**, on either kind of argument:

```bash
$ beadloom sync-update docs/architecture.md --check
  [surface drift] docs/architecture.md watches cli, graph
```

It did until BDL-061 S3b. The reference-doc branch was reached *before* the
`--check` guard, so the flag whose whole contract is "tell me, do not change
anything" re-baselined the doc and printed `Re-baselined reference doc <path>`;
measured on this repository, the drift count fell from 7 to 6 on a run that asked
for a report, and the next `sync-check` read clean for a reason nobody recorded.
That is BDL-UX #147 (`lint` mutating its index) in another command, and #163
(re-attesting without evidence) reached by accident rather than by choice
(BDL-UX #189).

For automated doc updates, use your AI agent (Claude Code, Cursor, etc.) with Beadloom's MCP tools. See `.beadloom/AGENTS.md` for agent instructions.

### beadloom install-hooks

Install (or remove) Beadloom's git hooks: a **pre-commit** hook (the lighter
synchronization check) and a **pre-push** hook (the authoritative blocking
**Beadloom Gate**). By default both are installed.

```bash
# Install BOTH hooks (pre-commit warn mode + pre-push Gate)
beadloom install-hooks [--mode warn|block] [--project DIR]

# Install only one
beadloom install-hooks --pre-commit [--mode warn|block] [--project DIR]
beadloom install-hooks --pre-push [--project DIR]

# Remove (both, or the selected one)
beadloom install-hooks --remove [--pre-commit|--pre-push] [--project DIR]
```

**Pre-commit hook** runs, in order: ruff lint, mypy, `beadloom sync-check`
(`--mode warn` reports stale docs; `--mode block` fails the commit on stale docs),
and finally the **ACTIVE / tracker coherence** step. That last step is a guarded
auto-fix: it runs only when BOTH `bd` and `beadloom` are on `PATH`, calls
`beadloom active-sync` to reconcile each epic's ACTIVE.md bead-status table from
`bd` and re-export `.beads/issues.jsonl`, then restages the touched
`.claude/development/docs/features/**` files and `.beads/issues.jsonl` so the
commit is coherent **by construction**. It never blocks the commit (it runs even
in `block` mode without affecting the exit code), and in any repo without `bd` —
or without ACTIVE tables — the block is a complete no-op (see
[`active-sync`](#beadloom-active-sync)).

**Pre-push hook (Beadloom Gate)** is the authoritative blocking enforcement of
the hard invariant *"no code in `main` without current docs."* On every push it
runs the full Gate (`beadloom ci` — incremental reindex → `lint --strict`
(module-coverage included) → sync-check → docs-audit → docs-quality → config-check →
doctor) and **exits
non-zero to block the push** on red, printing an
actionable message ("Beadloom Gate failed … run the tech-writer (or
`/coordinator`) then re-push; `git push --no-verify` to override"). It is
**fail-safe**: in any repo without `beadloom` on `PATH` the hook is a safe no-op
and never blocks. The full Gate lives in pre-push (not duplicated on every commit)
because pushes are less frequent than commits; the pre-commit hook stays the
lighter warn/block check. `--no-verify` is the documented (discouraged) escape
hatch.

Both hooks are idempotent — re-running `install-hooks` overwrites cleanly.

### beadloom active-sync

Reconcile each epic's `ACTIVE.md` bead-status table from `bd` — the source of
truth — and re-export the tracked `.beads/issues.jsonl`.

```bash
# Fix mode (default): rewrite drifted Status cells + bd export the jsonl
beadloom active-sync [--epic KEY] [--no-export] [--project DIR]

# Check mode: report drift without writing; exit 1 if any drift, 0 if clean
beadloom active-sync --check [--epic KEY] [--project DIR]

# Machine-readable JSON (works with --check or fix mode)
beadloom active-sync --json [--check] [--epic KEY] [--project DIR]
```

For every epic's `ACTIVE.md`, it finds the bead-status table and rewrites each
Status cell to match the bead's current `bd` status (`closed → ✓ done`,
`in_progress → in progress`, `open`/`ready → ready`, and `blocked` for an `open`
bead with an open blocker). A richer coordinator note is preserved when its state
already agrees (e.g. `✓ done (PASS-WITH-FIXES)` is left intact for a `closed`
bead). Only Status cells change — prose, the Progress Log, and other columns are
byte-preserved. The reconcile core (`application/active_table.py`,
`reconcile_active_tables` / `bd_status_to_cell`) is the same one the MCP S4
process-tools (`checkpoint` / `complete_bead`) use.

This is the mechanism that keeps `ACTIVE.md` honest **by construction** — wired
into the pre-commit hook (above), the coordinator no longer hand-edits
bead-status rows; the table is reconciled from `bd` on every commit.

- `--epic KEY` — reconcile only `features/<KEY>/ACTIVE.md` (default: every
  `features/*/ACTIVE.md`).
- `--check` — report drift on a throwaway copy without writing; **exit 1** if any
  row would change, **exit 0** when clean. Never writes and never exports.
- `--json` — machine-readable output: `{ "changed_files": [...], "drifted_rows":
  [ { "path", "bead_id", "old", "new" }, ... ] }`.
- `--no-export` — skip the `bd export` jsonl sync (fix mode only).
- `--project DIR` — project root (default: current directory).

In fix mode (no `--check`), after rewriting it best-effort runs
`bd export -o .beads/issues.jsonl` — but only when that file is already
git-tracked — so the tracked tracker artifact stays honest across
branch/squash-merge. `--no-export` skips that step.

**No-op contract.** `active-sync` exits **0 and writes nothing** when there is no
`ACTIVE.md` with a bead-status table, OR when `bd` is unavailable, OR when
`.beads/issues.jsonl` is not tracked (the export is skipped). So a non-flow repo —
or any adopter without the agentic flow — is never affected; the command (and the
hook step that calls it) is a safe out-of-the-box no-op.

### beadloom link

Manage external tracker links on graph nodes.

```bash
# Add a link (label auto-detected from URL)
beadloom link REF_ID URL [--label LABEL] [--project DIR]

# List links for a node
beadloom link REF_ID [--project DIR]

# Remove a link
beadloom link REF_ID --remove URL [--project DIR]
```

Auto-detected labels: `github`, `github-pr`, `jira`, `linear`, `link` (fallback).

### beadloom diff

Show graph changes since a git ref.

```bash
beadloom diff [--since REF] [--json] [--project DIR]
```

Compares current graph YAML with state at the given ref (default: HEAD). Exit code 0 = no changes, 1 = changes detected.

### beadloom export

Export the indexed graph as a deterministic cross-repo federation artifact (JSON).

```bash
beadloom export [--out FILE] [--project DIR]
```

Reads the indexed graph from SQLite (read-only) and emits a self-describing JSON artifact (schema v1): `repo`, `commit_sha`, `exported_at`, `generator`, and the `nodes` / `edges` arrays (each carrying `lifecycle`; edges may carry AMQP `contract` meta). The `edges` array unions the local `edges` table and the cross-repo `foreign_edges` table so declared `@repo:` links survive. Output is byte-deterministic (sorted nodes/edges + sorted keys). `--out` writes to a file; otherwise prints to stdout. Exits 1 if the database is missing (run `beadloom reindex` first). See the [federation SPEC](../domains/graph/features/federation/SPEC.md).

### beadloom federate

Aggregate ≥2 satellite export artifacts into one federated graph (hub).

```bash
beadloom federate EXPORT1.json EXPORT2.json [...] [--project DIR]
```

Composes the namespaced node/edge union (`@repo:ref_id` identity), resolves `@repo:` foreign refs, assigns a three-valued intent-vs-reality verdict per edge (`OK` / `DRIFT` / `EXPECTED` / `CLEANUP_CANDIDATE` / `UNDECLARED` / `DEAD`), reconciles AMQP contracts (confirmed both-sides vs one-sided), and reports per-satellite staleness (commit_sha + age). Writes `.beadloom/federated.json` + `.beadloom/federated.txt` in the hub project root and echoes the report (with any DRIFT) to stdout. Requires at least two artifacts; exits 1 otherwise or if a file is not a JSON object. The `--fail-on <csv>` landscape gate (writes artifacts first, then exits 1 on matching verdicts) prints an agent-actionable `fix:` hint per failing verdict (BREAKING / ORPHANED_CONSUMER / UNDECLARED_PRODUCER / DRIFT). See the [federation SPEC](../domains/graph/features/federation/SPEC.md).

### beadloom snapshot

Architecture snapshot management. Snapshots capture the current graph state (nodes, edges, symbols) for later comparison.

#### beadloom snapshot save

Save the current graph state as a snapshot.

```bash
beadloom snapshot save [--label LABEL] [--project DIR]
```

- `--label` -- optional label for the snapshot (e.g. `pre-refactor`).

#### beadloom snapshot list

List all saved architecture snapshots.

```bash
beadloom snapshot list [--json] [--project DIR]
```

Shows snapshot ID, label, creation time, and counts (nodes, edges, symbols). `--json` for structured output.

#### beadloom snapshot compare

Compare two architecture snapshots to see what changed.

```bash
beadloom snapshot compare OLD_ID NEW_ID [--json] [--project DIR]
```

Displays added/removed/changed nodes and added/removed edges between the two snapshots. Both `OLD_ID` and `NEW_ID` are required integer snapshot IDs.

### beadloom search

Search nodes and documentation by keyword.

```bash
beadloom search QUERY [--kind {domain,feature,service,entity,adr,to_be,as_is,working}] [--limit N] [--json] [--project DIR]
```

Uses FTS5 full-text search when available, falls back to SQL LIKE. Run `beadloom reindex` first to populate the search index.

`--kind` takes a node kind, or one of the three documentation SPACES. A document
bound to no node — every planning document in the TO-BE space — is indexed under
its space and keyed by its path, so `--kind to_be` narrows a search to recorded
intent:

```bash
beadloom search "sequencing principles" --kind to_be
```

### beadloom why

Show impact analysis for a node -- upstream dependencies and downstream dependents.

```bash
beadloom why REF_ID [--depth N] [--json] [--reverse] [--format {panel,tree}] [--project DIR]
```

- `--reverse` -- focus on what this node depends on (upstream only) instead of the default full analysis.
- `--format` -- output format: `panel` (Rich panels, default) or `tree` (plain text for CI/scripting).

### beadloom lint

Run architecture lint rules against the project.

```bash
beadloom lint [--format {rich,json,porcelain,github}] [--strict] [--fail-on-warn] [--no-reindex] [--project DIR]
```

Checks cross-boundary imports against rules defined in `rules.yml`. Format auto-detects: `rich` if TTY, `porcelain` if piped.

`--format` options:
- `rich` -- human-readable text (default on a TTY).
- `json` -- structured output: a backward-compatible `violations` array (now with an additive `remediation` key), a stable agent-actionable `findings` array (`{kind, rule, severity, node, locations, why, remediation}`), a `suppressed` array naming every crossing a `forbid_import` exemption excused, and a `summary` object (whose `violations_suppressed` is that array's length). Deterministic (violations are pre-sorted).
- `porcelain` -- one colon-separated line per violation (default when piped).
- `github` -- GitHub Actions workflow commands (`::error file=…,line=…::<rule>: <message> — <remediation>`) so violations surface as inline PR annotations; warnings use `::warning`.

Each violation carries an agent-actionable `remediation` hint derived per rule kind (deny/forbid → remove/reroute the import or edge; cycle → break the cycle at a named edge; layer → invert the dependency or extract a shared abstraction; cardinality → split the node; require → add the required edge).

Exit codes: 0 = clean (or violations without `--strict`/`--fail-on-warn`), 1 = violations with `--strict` (errors only) or `--fail-on-warn` (any violation), 2 = configuration error or missing index.

**A deny rule can only check a file it can place.** An import's source end is attributed to a node by annotation OR by ownership — the same most-specific-`source` rule that derives the `depends_on` edges — so a file with no annotation, or one written where the extractor could not read it, is no longer invisible to every deny rule (measured before the fix on this repository: 22 of 128 import-source files, BDL-061.50). What still belongs to no node is counted rather than skipped: `Files: N scanned, M imports resolved, K attributable to no node` on the rich header, `summary.files_unattributed` in `--format json`, and the same clause on the no-violations summary line. The clause is absent when K is zero. A deny rule that never saw a file did not clear it.

**A rule that cannot check anything reports itself.** All 12 authoring keys the loader dispatches are covered: a matcher that selects no node, a `has_edge_to` naming a node the graph does not contain, an edge kind that never runs between two layered nodes, a `check` with no threshold set, a `from:`/`to:` glob matching zero candidates anywhere in the index, a `source_root` with no module under it. Each is a `rule_liveness` finding. A partial inertness is `warn` — it describes the configuration rather than the code, so one mistyped glob cannot turn an adopter's green project red — while a rule that could check NONE of its population reports at the severity the project declared, because at that point a pass and a no-op are the same output (BDL-062 `.9`; `doc_area_coherence` only, so far — BDL-UX #197). Either way it is printed by default, typed in `--format json` as `kind: rule_liveness`, and counted in `summary.rules_inert`. The rich summary line carries the count only when it is non-zero (`N rules evaluated, M of them unable to check anything`), so the advertised rule count cannot over-claim while the everyday line keeps its shape (BDL-061.48). Two silences are deliberate and are properties of the INDEX rather than of any rule: an index with zero resolved imports makes every `deny` rule inert, which the header's `0 imports resolved` already says, and an empty graph silences the pass entirely so a fresh clone does not light up one warning per rule. Two rule types state their own diagnosis instead of the generic one, because a generic "cannot fire" cannot name which glob or which leg did it: `forbid_import` reports from the import scan it already runs, and `scenario_coverage` reports per leg. `scenario_coverage` is still COUNTED in `summary.rules_inert` — the report and the count are two questions, and one predicate answers both so they cannot disagree (BDL-061.66).

**Behaviour bound to an executable claim (BDL-061 S4).** `lint` also evaluates the
`scenario_coverage` rule: a behaviour-bearing node with no scenario, a scenario naming no bead,
a scenario naming a `@node:` the graph does not contain, and a scenario a PRD or BRIEF
references and the acceptance suite does not contain. All `warn`, each carrying the population
it is a fraction of (`none of 92 scenarios in 20 files carries @node:agent-prime`). Measured on
this repository, 2026-08-26: 59 findings. 32 of them, each naming a `feature` node that no
scenario in the suite binds to; 26, each naming a scenario a document references and the suite
does not contain; and one stating the rule's own reach: the `feature` nodes it selects, of the whole graph. See the [BDD guide](../guides/bdd-scenarios.md).

**What an exemption excused is part of the answer.** A `forbid_import` rule may carry `exempt:` entries that baseline a pre-existing crossing (see the [rule-engine SPEC](../domains/graph/features/rule-engine/SPEC.md)). Every run says how many crossings they suppressed — `", N crossings suppressed by an exemption"` on the summary line, `violations_suppressed` plus the `suppressed` array under `--format json`, and the same clause on the `0 violations, N rules evaluated` line printed when a piped run has nothing to report. Without it, `0 violations` reads as "nothing crossed" when it means "what crossed was excused" (BDL-061.49). An entry whose `until:` leads with an ISO date that has passed, and which is still suppressing something, is reported as a `rule_liveness` finding (`warn`); it keeps suppressing, so no build reddens because a day passed. `--fail-on-warn` is the lever for a project that wants that deadline enforced.

Without `--strict` the exit code stays 0 even when error-severity violations were printed. That is deliberate — changing it would turn an adopter's green pipeline red on upgrade — so `lint` names the omission on stderr instead (`warning: N error-severity violation(s) found, but the exit code stays 0 without --strict`).

**Which form writes the index.** Plain `beadloom lint` reindexes first and therefore WRITES `.beadloom/beadloom.db` (measured: its sha256 changes). This is by design: the default must never lint a stale graph. `--no-reindex` is the read-only form — it leaves `beadloom.db` byte-identical (measured under both `journal_mode=wal` and `journal_mode=delete`) and refuses a missing index at exit 2 with `index not found … Run 'beadloom reindex' first` rather than creating one and reporting `0 violations` against it. Two qualifications, both measured: on a WAL index the read-only form still creates and leaves the `beadloom.db-wal` / `beadloom.db-shm` sidecars, so byte-identity is a property of the FILE and not of `.beadloom/`; and `--no-reindex` answers about the INDEX rather than about the working tree, so with a stale index it reports `0 violations` over a boundary violation that plain `lint --strict` catches on the same tree (BDL-UX, `beadloom-mr2l`). Use it when you have just reindexed, or when the read-only property is what you need.

### beadloom tui

Launch interactive terminal dashboard (primary command).

```bash
beadloom tui [--project DIR] [--no-watch]
```

Multi-screen architecture workstation with graph explorer, debt gauge, lint panel, doc status, and keyboard actions. Requires: `pip install beadloom[tui]`.

- `--no-watch` -- disable file watcher (for CI/testing)

### beadloom ui

Launch interactive terminal dashboard (alias for `tui`).

```bash
beadloom ui [--project DIR] [--no-watch]
```

Backward-compatible alias for `beadloom tui`. Requires: `pip install beadloom[tui]`.

### beadloom watch

Watch files and auto-reindex on changes.

```bash
beadloom watch [--debounce MS] [--project DIR]
```

Monitors graph YAML, documentation, and source files. Graph changes trigger full reindex; other changes trigger incremental. Requires: `pip install beadloom[watch]`.

### beadloom docs generate

Generate documentation skeletons from the architecture graph.

```bash
beadloom docs generate [--project DIR]
```

Creates `docs/` tree: `architecture.md`, domain READMEs, service pages, feature SPECs. Never overwrites existing files. All generated files include `<!-- enrich with: beadloom docs polish -->` markers.

### beadloom docs site

Generate a VitePress content tree from the architecture graph.

```bash
beadloom docs site [--out DIR] [--federated FILE] [--project DIR]
```

Reads the indexed graph read-only and emits, under `--out` (default `site/`):

- `index.md` -- architecture overview: domain/service/feature counts, the top-level C4/Mermaid diagram, and a health summary line (nodes/edges/docs/coverage/stale).
- per-node pages (`domains/<ref>.md`, `services/<ref>.md`, `features/<ref>.md`) -- each with summary, source, public symbols, `part_of`/`depends_on`/`uses` edges rendered as Markdown links to the other node pages, linked hand-written docs, and an embedded scoped C4/Mermaid diagram.
- `dashboard.md` + `dashboard.data.json` -- **Showcase A**, the AaC/DocAsCode metrics dashboard (lint count + severity, debt score + trend, doc coverage / sync-check freshness / stale count, doctor pass-fail, and an optional federated rollup). Every number comes from the SAME code path as its gate (`lint` / `debt-report` / `sync-check` / `doctor` / `federate`) -- honest by construction.
- `landscape.md` -- **Showcase B**, the 🌟 cross-repo landscape map: a Mermaid diagram of the federated contract graph (with `--federated`) or the local graph (without), edges labelled by their verdict, a `classDef` health overlay, and clickable nodes linking to their intra-repo page.
- `docs/**` + `docs/index.md` -- **Showcase C**, the published validated documentation: the REAL `docs/**` tree copied verbatim (the source of truth, rendered as-is) with a per-doc `doc_sync` freshness badge injected into the COPY only. The source `docs/` is NEVER mutated.
- `.vitepress/config.generated.mjs` -- the nav/sidebar config imported by the committed VitePress scaffold (`site/.vitepress/config.mjs`); sections: Dashboard / Architecture / Landscape / Documentation.

Beadloom produces, VitePress renders. Output is deterministic (sorted, stable frontmatter, no wall-clock in the diffed output) and is NEVER written into the source `docs/` tree -- only under `--out`. `--federated` takes a `federate` hub artifact (`federated.json`) and drives the Showcase B landscape map. To render: `cd site && npm install && npm run docs:build` (preview with `npm run docs:preview`). See the [VitePress Site guide](../guides/vitepress-site.md).

### beadloom docs audit

Detect stale numeric facts in project documentation.

```bash
beadloom docs audit [--json] [--fail-if EXPR] [--stale-only] [--verbose] [--path GLOB]... [--project DIR]
```

Scans markdown documentation for numeric mentions (version strings, counts) and compares them against ground-truth facts collected from the project infrastructure (manifest files, graph DB, MCP tools, CLI commands). The audit is stable and runs as the **docs-audit step inside `beadloom ci`**, where it blocks the gate on `stale>0`.

- `--json` -- structured JSON output with facts, findings, unmatched mentions, per-fact `coverage`, `unverified_facts` and the `scan_surface`.
- `--fail-if` -- CI gate expression. Supported formats: `stale>N` / `stale>=N` (mentions that disagree with ground truth) and `unverified>N` / `unverified>=N` (declared facts the run checked nothing for). Exits with code 1 when the condition is met.
- `--stale-only` -- show only stale findings (omit fresh matches).
- `--verbose` -- include extra detail: unmatched mentions, the documents that were not read (with the reason each was skipped), and the ones scanned for versions only.
- `--path` -- override default scan paths with custom glob patterns (can be specified multiple times).

Exit codes: 0 = no issues (or below threshold), 1 = `--fail-if` condition met.

**What a green audit covers.** `N mention(s) fresh` counts what the audit FOUND, not what it
CHECKED, and the two were measured nine-fold apart on this repo: nine declared facts, thirteen
verifications, all thirteen of the same fact (BDL-UX #173). Every declared fact therefore
carries its own coverage — `verified` (something was compared), `not_covered` (no document
states it) or `unreadable` (the extractor cannot read a claim of that value at all, with the
reason) — printed against the fact in the `Ground Truth` block and summarised on one line:

```
2 of 9 declared fact(s) verified; NOT VERIFIED: cli_command_count, edge_count, ...
46 document(s) scanned, 33 not read, 1 scanned for versions only (file-type heuristic)
```

A fact nothing was found for is never counted as passing. Coverage does not fail the gate —
documentation is not required to state every fact — but `--fail-if unverified>N` makes it
enforceable for a project that wants it.

**What counts as a claim.** A line is split on whitespace and only a token whose whole core is a number is a candidate — all digits, or digits in thousands groups (`6,390`, read whole as `6390`). A number inside a larger token is an identifier rather than a claim (`BDL-061.33`, `v2.2.0`, `utf-8`) and is never extracted; markdown emphasis, brackets and trailing punctuation around the token are stripped first. A claim also reaches only to the end of its own clause: a modifier or a noun on the far side of `,` `;` `:` or a dash belongs to the rest of the sentence, so `The graph holds 316 edges, one per import.` is read (the `per` is not modifying the count) while the `14` in `exposes 18 tools: 14 over the graph` is not (it is a breakdown, not the total). See `docs/domains/doc-sync/features/docs-audit/SPEC.md` for the layer model and the declared blind spots.

**Tuning false positives.** The audit masks dates, hex, issue IDs, line refs, and version pins, and applies per-fact tolerances. Two `.beadloom/config.yml` keys handle the rest:

```yaml
docs_audit:
  tolerances:
    node_count: 0.1          # accept counts within 10% of ground truth
  ignore:                    # suppress one {path, fact, value} false match each
    - path: docs/guides/vitepress-site.md
      fact: cli_command_count
      value: 404
```

`docs_audit.ignore` is a list of `{path, fact, value}` triples. Each suppresses exactly one keyword-proximity false positive — for example a subset count stated next to the correct total, or an HTTP status code matched as a command count — **without** rewording correct prose and **without** masking a genuine stale fact of the same type elsewhere. Use it only for confirmed false positives; genuine stale facts must be corrected in the doc.

Examples:

```bash
# Human-readable Rich output
beadloom docs audit

# CI gate: fail if any stale docs
beadloom docs audit --fail-if=stale>0

# Stricter: also fail when a declared fact is stated by no document at all
beadloom docs audit --fail-if=unverified>0

# JSON output for scripting
beadloom docs audit --json --stale-only

# Scan only specific paths
beadloom docs audit --path "docs/**/*.md" --path "README.md"
```

### beadloom docs quality

Check the project's planning documents against the shipped writing standard
(BDL-061 S4b).

```bash
beadloom docs quality [--json] [--check NAME]... [--strict] [--project DIR]
```

Eleven checks, all `warn`:

| Check | Reports | Where it looks |
|-------|---------|----------------|
| `measurable-goal` | a goal statement with no number in it | the `## Goal` / `## Goals` section |
| `decision-reason` | a decision row whose reason cell is empty | any table with a Reason / Rationale / Why column |
| `risk-mitigation` | a risk row with no mitigation, or one that names no action (`monitor it`) | any table with a Mitigation column |
| `pending-in-approved` | a question still answered `Pending` | `## Open Questions`, in a document whose status is `Approved` or `Accepted` |
| `unfilled-placeholder` | a shipped template token nobody replaced | the whole document, outside fenced blocks and inline code |
| `missing-section` | a section this document's kind carries in its template AND a majority of its peers keep | every document of a kind the `/templates` command describes |
| `empty-section` | a required section whose heading is there with nothing under it | the same, and not peer-relative: a heading answering nothing is a defect whatever the peers do |
| `axes-without-a-seed` | an `## Axes` section stating axes without naming the seed they were derived from | the `## Axes` section |
| `axis-without-a-scope-decision` | an axis row carrying the derivation's output and no decision | the same |
| `routed-without-axes` | a work item on the simplified route (`bug`, `task`, `chore`) carrying no `## Axes` section in any of its documents | the work-item FOLDER, which is the unit that has a type |
| `route-not-supported-by-the-axes` | a work item on the simplified route whose kept axes name more than one graph node | the same |

The middle four arrived with BDL-068 S1.4 and the last two with S1.5. The last
two take the work-item FOLDER as their unit, because a route is a property of the
item rather than of any one document it holds, and they are absolute rather than
peer-relative: `missing-section` reported `BRIEF documents do not carry Axes
(0/12)` against the KIND and nothing against any document, which is right for a
convention an archive never adopted and wrong for the input to a decision. Only
the simplified route is judged — the full route writes a PRD and an RFC and each
passes an approval gate, so a mis-route there meets a person.

The section requirements are DERIVED
from the composed `/templates` command, so a project that appends a section to
its own template layer makes it required by the same act. A required section no
MAJORITY of a kind carries is reported once against the KIND, with its ratio
(`BRIEF documents do not carry Axes (0/12)`) — the fix is in the template, not
in every document.

The exit code is **0 even with findings** — no adopter's green project turns red
on upgrade. `--strict` exits 1 when anything is reported, for a project that
wants to enforce it.

**`measurable-goal` decides one named form, not measurability in general.** A
goal is reported only when its predicate is an unbounded improvement (`improve`,
`establish`, `clean up`, `make` something *better*) AND it names no witness — no
quantity, no named artifact, no observable outcome. It shipped as a numeral
detector and reported 154 of 235 goal statements here, against **4 of 232** after
`beadloom-mr2l.70` re-scoped it; all four are in closed epics, which is why the
remaining debt is a historical exclusion (`beadloom-mr2l.71`) rather than a
rewrite. The stated limit: 27 of the 150 newly-accepted statements name no
witness either, so this check now decides nothing about them — precision was
bought with recall, deliberately. That number is not on the gate line; it is in
the [doc-quality SPEC](../domains/doc-sync/features/doc-quality/SPEC.md), which
also states the other four checks' limits.

The report ends with a per-check line stating how much there was to READ, and
names any check that found nothing at all: a green count over documents that
state no risks is not a statement about risks.

**And per document KIND**, because the line above is an OR over the whole corpus
and goes silent the moment one document carries one row — so it can see a check
that is blind everywhere and not one that is blind on an entire document kind.
`NO CHECK READS: <kind>` names each kind no *content* check enters, with its
document count. The judgement is made over the four checks that read items;
`unfilled-placeholder` counts documents OPENED and would report every kind as
read. Measured on this repository, 2026-08-24: `measurable-goal` 4 over 232,
`pending-in-approved` 2 over 69, 0 over 272 / 138 / 243 for the other three, and
`NO CHECK READS: BRIEF, PLAN, SUMMARY` — 56 of 243 documents (23%).

**A document nobody could read is named, not dropped.** A planning document is a
UTF-8 contract; one that does not decode is counted, printed as
`UNREADABLE: <path> — <reason>; judged by nothing`, and left out of its kind's
denominators. Counting a file nobody read as a file carrying nothing would turn
an encoding accident into evidence about a project's templates.

`--check` accepts the eleven check names above and nothing else; an unknown name
is an error and exits 1. `--json` carries `checks`, `read_nothing`, `kinds`,
`kinds_read_by_nothing`, `unreadable` and `findings`.

Documents are found under `.claude/development/docs/features/*/*.md` by default;
a project with another layout declares its own globs:

```yaml
# .beadloom/config.yml
doc_quality:
  paths:
    - docs/rfcs/*.md
```

A run that matches no document says so and names the globs it looked under,
rather than printing a clean bill of health over nothing.

```bash
# Everything, as a warning report
beadloom docs quality

# One check, machine-readable
beadloom docs quality --check pending-in-approved --json

# Enforce it
beadloom docs quality --strict
```

### beadloom impact

Who else writes this, who else calls it, and how many branches it has — derived
from the source over a seed the command finds for itself (BDL-068 S1.2).

```bash
beadloom impact TARGET [--project DIR] [--root DIR] [--json] [--section]
```

TARGET is a path or a symbol name. The seed the answer is computed over is
DERIVED from the target and named in the output together with the rule that found
it, because the same derivation reports two writers under one seed and none under
another — an answer that does not say what it was seeded with cannot be checked.
A target no rule finds a sink for is reported as unresolved rather than answered
over an empty set. Exits 1 when no file and no symbol matches TARGET.

- `--root` — sweep this tree instead of the one derived from the target.
- `--section` — render the answer as the `## Axes` section a work item's document
  carries, with the `In scope` column left undecided.
- `--json` — the whole answer as data: `seeds`, `co_writers`, `callers`,
  `commands`, `boundary` and `unresolved`.

**A branch count names the seat it was taken from.** Run on this repository:

```
$ beadloom impact src/beadloom/onboarding/scanner/bootstrap.py
root swept: src/beadloom
...
- bootstrap_project (src/beadloom/onboarding/scanner/bootstrap.py:36): 3 branch(es), reaching a seed
- init (src/beadloom/services/commands/setup.py:1255): 4 branch(es), reaching a seed, read from a caller's seat
```

Both numbers are right and they answer different questions. Three is the count of
`bootstrap_project`, the function the target names, and it is the number BDL-067
carried through nine review passes while the fourth branch it needed lived in
`init` — a caller, one hop out. So the count alone is not the answer: the seat is
part of it, and `--section` spells the same distinction in its rows
(`init: 4 branch(es), 1 exit form(s), from a caller's seat`).

`co_writers` and `callers` each carry `resolved` as well as their sites, because
*no population* and *an empty population* are different statements. The swept
root is printed as `root swept:` in every rendering and withdrawn as a claim when
it is narrower than the project's source root
(`sweep-narrower-than-the-project`). What that withdrawal does not yet reach is
in the [Impact SPEC](../domains/application/features/impact/SPEC.md) under
"Known ceilings". Read it before treating an empty axis as an absence.

### beadloom scope-check

Judge the paths a commit stages against the axes its work item declared
(BDL-068 S1.6).

```bash
beadloom scope-check [--project DIR] [--since REF] [--branch NAME] [--porcelain] [--json]
```

The work item is the one the checked-out branch names, and its `## Axes` section
is the scope a person approved. A bead may narrow freely inside that scope. A
path that falls OUTSIDE it means the approval no longer covers the change, which
is the re-plan trigger. Exit `2` when a path falls outside, `0` otherwise.

**This reports. It does not prevent.** An agent with a shell can commit anything
the file system allows. What the check raises is detectability — the crossing is
named, with the axis it fell outside, at the moment it is made rather than at
review.

- `--since REF` — judge every path the branch changes against REF (`REF...HEAD`),
  which is what a pull request contains, instead of only the staged ones.
- `--branch NAME` — name the work item's branch instead of reading the
  checked-out one.
- `--porcelain` — the verdict first as a `# `-marked line, then one finding per
  line (`path:line`, check, excerpt). A hook splits the two on the marker: a
  finding line opens with a project-relative path and no path opens with `# `.
- `--json` — the verdict plus `checked`, `reason`, `work_item`, `document`,
  `scope`, `judged`, `unowned` and `undecided`.

**The verdict is printed whatever it says, on standard output, in both forms.**
Until BDL-068 S4 (`beadloom-0mdo.32`) the reason for having compared nothing
went to standard error alone, and the pre-commit hook read this command as
`2>/dev/null`: a run that found nothing outside and a run that could attribute
no work item were both the empty string there, so the gate printed the same
nothing for both and an unattributable commit read as clean.

A clean run states its population rather than only its verdict. Measured on this
branch, 2026-09-04:

```
$ beadloom scope-check --since origin/main
Declared axes (BDL-068, against origin/main): 11 staged path(s) a node owns, 28 no node owns.
```

The 28 are counted and stated, never reported: a path no node owns — a document,
a test, a graph YAML — is not a call site and has no axis to be outside of.
Counting them as checked would be the false green the check exists to remove.
They are also the larger half: measured over the eleven commits of this branch,
52 paths carried 11 with an owner in the graph against 41 with none, so four paths in five
were never compared and the count is the only thing that says so.

There are five ways to have checked nothing — no branch, no work item, no graph
index, no `## Axes` section and no answer from git — and each is reported as
itself. A run that reports no findings and states no reason really did compare
the paths.

The rule, the two candidates measured against this repository's own history
before either was written, and what an undecided row does are in the
[Scope Check SPEC](../domains/doc-sync/features/scope-check/SPEC.md).

### beadloom axes

Read a work item's `## Axes` section back: what it declares, and the `refs:` line
generated from it (BDL-068 S1.4).

```bash
beadloom axes DOCUMENT [--refs] [--json]
```

DOCUMENT is a BRIEF or an RFC. The section records the derivation's output and
the person's scope decision; this reads it back, so a bead's `refs:` is
GENERATED from the document rather than written beside it — two authored homes
for one fact are two things that can disagree.

`beadloom impact <path|symbol> --section` writes the other direction: the same
answer, rendered as the section to paste into the document, with every row left
undecided until a person rules on it.

```
$ beadloom axes .claude/development/docs/features/KEY-1/BRIEF.md --refs
refs: doc-quality, flow-composer
```

Exits 1 when the document carries no `## Axes` section, naming the command that
produces one.

### beadloom docs spaces

Report the three documentation spaces, and where recorded intent never reached
the documentation of reality.

```bash
beadloom docs spaces [--json] [--strict] [--project DIR]
```

- **TO-BE** — `PRD`, `RFC`, `BRIEF`, `CONTEXT`, `PLAN`. What the system is to
  become.
- **AS-IS** — `SPEC`, `DOC`, `README`. What it is; the space `sync-check` holds
  against the code.
- **WORKING** — `ACTIVE`. Ephemeral, exempt from freshness by declaration.

The names are deliberately not TODO/DONE. Nothing changes status: a planning
document stays the record of what was intended, and a *different* artifact is
what gets updated — so the checkable claim is a relation between two artifacts.

An epic with at least one closed bead that declared a graph node with no AS-IS
document is reported: intent was recorded, the work finished, and reality was
never written down. The node list is read only from the epic's *Related Files*
section, because that list is a declaration; an epic that declares nothing is
counted as unresolved and named, never counted as clean.

Roots, kinds and the intent documents an epic declares its nodes in are
configurable under `doc_roots` in `.beadloom/config.yml`; the documentation
directory itself comes from `docs_dir`. See the
[Doc Roots component](../domains/infrastructure/components/doc-roots/DOC.md) for
the keys and the [Document Kinds guide](../guides/document-kinds.md) for the
decision behind the three spaces.

**Every document a declared root matched is in exactly one population.** When a
document's kind sends it to a space whose declared roots do not reach it, it is
counted in the space its kind chose and reported as `document_outside_declared_root`
— once per kind, with the count, up to five example paths and the roots that
failed to reach them. It used to fall out of every count instead.

**What is not checked is named, never folded into a green count.** An epic that
declares no node, one whose intent document nothing could decode, and one a
readable tracker does not name are three different ways of knowing nothing, and
each is reported under its own reason.

Exits 0 with findings unless `--strict` is given, so no adopter's green project
turns red on upgrade. The same check runs as the `doc-spaces` step of
`beadloom ci`, where it reports and never blocks.

```bash
# The report, with every denominator beside every count
beadloom docs spaces

# Machine-readable
beadloom docs spaces --json

# Enforce it
beadloom docs spaces --strict
```

`--json` carries the populations and every denominator behind the human report:

| Key | What it holds |
|-----|---------------|
| `populations` | `{to_be, as_is, working}` document counts |
| `epics`, `epics_with_closed_beads`, `epics_declaring_nodes`, `epics_declaring_nothing` | the relation's denominators |
| `refs_checked` | node declarations actually held against the AS-IS space |
| `relation_checked` | `false` when nothing was related — reported as NOT CHECKED, never as clean |
| `unresolved_epics`, `unresolved_reasons` | every epic the relation could not decide, with `no_node_declared` / `no_intent_document` / `unreadable_intent_document` |
| `tracker_read`, `tracker_source`, `epics_unknown_to_tracker` | which tracker answered, and the epics it has no record of |
| `documents_outside_declared_root` | documents whose kind and root disagree |
| `working` | `{documents, exempt_from_freshness, reason, reach, pairs_excused}` |
| `findings` | `{rule, path, line, why, remediation}` per finding |

`working.reach` names each **declared** kind and each declared root with how many
documents it excused, so a declaration whose halves are half inert says which
half. `working.pairs_excused` is **`null`** from this command rather than `0`:
`docs spaces` runs no freshness check, so it did not measure that number and does
not print one. The `beadloom ci` doc-spaces line does carry it, because the
sync-check step in the same run measured it and hands it over.

Measured on this repository, 2026-08-26: `to_be 194`, `as_is 100`, `working 56`;
`epics 62`, `epics_with_closed_beads 38`, `epics_declaring_nodes 5`,
`refs_checked 17`; `epics_declaring_nothing 57` and
`epics_unknown_to_tracker 24`, every one of them named rather than folded into a
green count; and one `epic_not_in_tracker` finding. Every number here moves with
the repository's own planning tree, so read them as a shape and re-run the command
for a current value.

### beadloom docs polish

Generate structured data for AI-driven documentation enrichment.

```bash
beadloom docs polish [--format {text,json}] [--ref-id REF_ID] [--project DIR]
```

- `text` (default) -- human-readable summary with enrichment instructions
- `json` -- structured JSON with nodes (symbols, dependencies, existing docs), Mermaid diagram, and AI prompt
- `--ref-id` -- filter to a single node

### beadloom prime

Output compact project context for AI agent injection.

```bash
beadloom prime [--json] [--update] [--project DIR]
```

- `--json` -- structured JSON output
- `--update` -- regenerate `.beadloom/AGENTS.md` before outputting context

Returns architecture summary, health status (stale docs, lint violations), architecture rules, domain list, and agent instructions.

### beadloom setup-rules

Create IDE rules files that reference `.beadloom/AGENTS.md`.

```bash
# Auto-detect installed IDEs
beadloom setup-rules [--project DIR]

# Target a specific IDE
beadloom setup-rules --tool {cursor,windsurf,cline} [--project DIR]
```

Creates thin adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) that instruct agents to read AGENTS.md.

### beadloom config-check

AgentConfigAsCode freshness gate: verify that generated agent-config is in sync with the graph.

```bash
beadloom config-check [--project DIR]   # exit 1 on BLOCKING drift, 0 otherwise
beadloom config-check --fix [--project DIR]  # regenerate drifted artifacts, then re-check
```

Since **BDL-061 S3** a drift carries a severity. `error` exits 1; `warn` is
printed (`! <file>: <reason>` plus a `-> <remediation>` line) and exits 0, so an
adopter upgrading into this release does not go red for a file scaffolded before
the flow manifest existed. The clean line says which case it is —
`Agent-config in sync — no blocking drift (N warning(s) — see above).`

Re-runs the same `setup-rules --refresh` generator in memory and diffs its output against on-disk content for `.beadloom/AGENTS.md`, the auto-managed sections of `.claude/CLAUDE.md`, and present IDE adapter files. For those three, only the auto-managed regions are compared — editing user-authored prose (the AGENTS.md `custom` block, CLAUDE.md content outside the `auto-start`/`auto-end` markers) never trips them. The composed artifacts are a separate check with its own rules, described below. Prints which file drifted, why, and the remediation; an absent target file is skipped unless the project adopted the flow, in which case it is `missing`. `--fix` regenerates via the refresh path (`config_sync.apply_config_fixes`), names every file it changed, declines any body Beadloom cannot prove it wrote, and re-checks. Delegates to `onboarding/config_sync.py:check_config_drift()`.

As of BDL-048, when a repo has the agentic flow scaffolded (`beadloom setup-agentic-flow`), `config-check` also drift-checks the **scaffolded flow files**. As of **BDL-061 S3** it checks them against their **composition result** rather than against fixed bytes: `.claude/CLAUDE.md`, each `.claude/commands/*` and each `.claude/agents/*` must equal `CORE + the flow.yml overlays + the project layer in .beadloom/flow/`. That is what makes a project extension legal — it is part of the expected output — while a change to a shipped fragment still differs from it and is reported.

Two things this closed, both measured:

- **The `CLAUDE.md` body was checked by nothing.** `config-check` diffed only the marker-bounded auto-regions, so on a freshly scaffolded project, appending a project-local paragraph, deleting the whole of section 7, and replacing the entire file with the single line `# gone` all returned zero drifts — and `beadloom ci` printed `config-check PASS: agent-config in sync` over it (BDL-UX #177).
- **`--fix` used to delete hand edits.** It restored every divergent file byte-identical, with no diff and no confirmation, which is why a team's standing engineering practice could not live in a role adapter at all (BDL-UX #139, #152). For the slash commands and `CLAUDE.md` it no longer does: it runs the scaffold's non-forcing path, names `.beadloom/flow/<kind>/<name>.md` and leaves the edit where it is.

**`--fix` may only rewrite what Beadloom wrote (BDL-UX #186, closed in BDL-061 `.59`).** The role adapters were the one kind left out: `refresh_composed_adapters` rewrote `.claude/agents/<role>.md` unconditionally, so doing what the closing line said (*Run `beadloom setup-rules --refresh` (or `config-check --fix`) to fix.*) undid what the line above it promised — and the re-check then printed `Agent-config in sync — no blocking drift` at exit 0 over the deletion. Verified by sha256 on a clean repository. Now:

- an adapter classified `hand_edited` or `unverified` is **declined**: left byte-identical, named in the output, and its finding keeps the exit code honest;
- everything else is recomposed as before, and the run **names every file it created or rewrote**, measured by digesting the artifact surface before and after rather than by trusting each writer's self-report;
- the closing advice stops offering `config-check --fix` for a finding `--fix` will decline (`ConfigDrift.fixable`).

The remedy is unchanged and now actually terminates: move the additions into `.beadloom/flow/roles/<role>.md`, then re-run `beadloom setup-agentic-flow`.

Which of the two a divergence *is*, is decided by the flow manifest (`.beadloom/flow-manifest.json`): every write records the body's sha256, so `stale` (Beadloom wrote it, the composition moved — `error`, recompose), `hand_edited` (`error`, never rewritten) `missing` (we wrote it and it is gone — `error`) and `unverified` (nothing accounts for it, so the two cannot be told apart — `warn`) are separate findings and not one word. The `CLAUDE.md` body is JUDGED only when the file is Beadloom's: a manifest entry, or the `<!-- beadloom:composed` stamp the shipped core begins with — a project's own hand-written `CLAUDE.md` is never policed. Not judged is not the same as not mentioned: in a project that adopted the flow, a `CLAUDE.md` with neither signal is named at `unverified`/`warn` rather than passed over. Those two signals are independent on purpose: deleting the generated manifest used to downgrade a hand edit to `warn` and the command to exit 0, and deleting one scaffolded file used to switch the checks off for every other one. Neither does now — the deletions are themselves reported (BDL-061 `.57`). `config-check` also names, at `warn`, a project layer in effect (its prose is composed but not judged) and an `overlays.suppress` entry that has expired or that names no rule in the composed flow.

**A downgrade across an upgrade is itself a finding (BDL-061 S3b).** The
constraint this project has always stated runs one way — *no adopter's green
project turns red on upgrade* — and review `.11` measured the other direction: a
repo that hand-edited a role file before the flow manifest existed used to block
at `error` and, after the manifest shipped, has no entry for that file, reads
`unverified`, and warns at exit 0. A downgrade is the worse of the two, because a
red is loud and correlates with the release while a downgrade is silent: the
project was correctly failing, now passes, and the evidence it ever failed is
gone. So every severity Beadloom reduced *for want of evidence* carries
`ConfigDrift.weakened_from`, and the command says so — on the passing path as
well as the blocking one:

```
Agent-config in sync — no blocking drift (5 warning(s) — see above).
  This pass is WEAKER than it would be: 5 finding(s) are `warn` only because
  Beadloom cannot prove what it wrote — each would be an `error` with the
  evidence. A verdict that got quieter across an upgrade is a finding, not a pass.
    -> restore `.beadloom/flow-manifest.json` (re-run `beadloom setup-agentic-flow`)
       to get the blocking verdict back.
```

The exit code deliberately does **not** change: a `warn` must not block, or
fixing the silence would itself be the red-on-upgrade the rule exists to prevent.
And nothing is recorded to compute it — the downgrade follows from the finding's
own state, because `config-check` writing on every run to keep a verdict history
would be BDL-UX #147/#189 in the one command whose job is to look without
touching.

As of **BDL-052 S3**, when a valid `.beadloom/flow.yml` is present `config-check` also: (a) validates `flow.yml` itself (an invalid config is reported as drift; an absent one is not); and (b) byte-compares each **composed role adapter** (`<tool>/agents/<role>.md` for every tool the config names) against the freshly recomposed body (`compose_role(...)` for the configured architecture + stack overlays) — `config_sync._composed_adapter_drifts`. When a `flow.yml` is present the role agents are composer-owned, so the byte-vendor compare is skipped for `agents` (it would false-positive on a non-Python stack). `--fix` recomposes the per-tool adapter sets except the ones it declines (`config_sync.refresh_composed_adapters`, which returns an `AdapterRefresh` of `rewritten` + `declined`). **Known limitation:** the composed-adapter check iterates only the tools named in `flow.yml`, so adapters left behind by a tool dropped from a narrowed `flow.yml` (e.g. orphaned `.cursor/agents/*`) are neither flagged nor recomposed; a follow-up bead tracks an orphaned-adapter lint.

### beadloom guard

Evaluate one flow guard — the enforcement primitive the agentic flow binds to (BDL-061 S1).

```bash
beadloom guard NAME [--context KEY=VALUE ...] [--json] [--project DIR]
beadloom guard NAME --hook claude-code            # harness event as JSON on stdin
beadloom guard --liveness [--json] [--project DIR]
```

Returns a verdict `{guard, outcome, why, not_covered[], remediation, context}` — plus `recorded` and `not_recorded_because` under `--json` — where `outcome` is `pass` / `warn` / `block` / `skip` / `error`. **Exit codes carry the outcome** so a shell adapter needs no parsing: `0` for `pass`/`skip`, `1` for `warn` (shown, never blocking), `2` for `block`, and `3` for a usage or configuration error reported to a **shell** caller — deliberately not `2`, which is Click's own usage code and would otherwise be indistinguishable from a genuine block. That distinction is answered only to the caller it means something to: reached through `--hook`, the same class exits `2` (BDL-061.33). It exited `3` there until S2, and `3` stops no tool call — so a `.beadloom/flow.yml` that would not parse left every bound guard announcing that it could not answer while every edit went through. The mapping lives in the CLI, keyed on the harness the adapter already declares, rather than in the generated script: a script that maps codes carries logic, and the next harness would have to re-implement it. `warn`, `block` and `error` are written to **stderr** (the stream a hook harness shows the agent); `pass` and `skip` go to stdout, as does `--json` in every case.

`3` is for a defect in the project's *declared configuration* (an unparseable `guards:` block, an exclusion with no reason, a guard name nobody registered) and for a command line that could not be used at all (no guard named, `--liveness` with a name, a malformed `--context` pair, an unsupported `--hook` harness) — stable defects that fail the same way on every invocation. Anything that goes wrong while answering about *this* edit — a hook payload that cannot be decoded or parsed, a project that cannot be located, an exception anywhere — is an `error` verdict at `2`, the one code the shipped adapter blocks on.

**`3` is not what a hook sees, and that is the point (BDL-061.33).** The harness stops the tool call on `2` and on nothing else, so while the class exited `3` unconditionally, all five cases above were an `error` verdict — loud on stderr, and letting the edit through. The reachable one is a `.beadloom/flow.yml` that will not parse, the one file of this feature an adopter edits by hand: while it will not parse, every bound guard answered "could not tell" and nothing was enforced. The distinction `3` draws is worth keeping, so it is kept for the caller that can act on it and dropped for the one that cannot: `beadloom guard` run by a person or by CI still exits `3`, and the same defect reached through `--hook` exits `2` and stops the edit. Mapping the whole class to `2` would have spent the distinction on a caller with no use for it; mapping it in the emitted script would have put logic in an adapter and left the next harness to re-derive it. An unsupported `--hook` harness blocks for the same reason, since Beadloom cannot know the exit vocabulary of a tool it does not support.

`error` means **the guard could not answer** — a refused path (see below), a `guards:` block that will not parse, a project that cannot be located, or any failure inside the evaluation. It exits `2`, because the adapter's harness blocks on 2 and on nothing else, and because `1` is the `warn` code a harness reads as "carry on". Every invocation runs inside one boundary: argument parsing, the stdin read and the evaluation all come back through it, so a failure anywhere is a recorded verdict rather than a traceback — including a **`KeyboardInterrupt`**, which since BDL-061.31 is a recorded `error` at exit 2 rather than an escape to Click's exit 1. That means Ctrl-C during a guarded edit *blocks* that edit: an interrupted guard checked nothing, and "could not answer" must never read as "passed". Rendering the verdict happens after the boundary and is wrapped, so a failure while printing is reported on stderr and the exit code stays the verdict's. Every invocation that names a registered guard in a located project is recorded, `error` included — an evaluation missing from `guard-firings.jsonl` is invisible to `--liveness`. The four invocations that leave no record say so (`not recorded: <reason>` on stderr): a successful `--liveness` report evaluated nothing, an unlocatable project has nowhere to write, an invocation that named no guard asked about nothing, and an unregistered name has nothing to attribute the row to. The last two were one reason until BDL-061.34, which is why `beadloom guard` with no name used to report `'(no guard named)' is not a registered guard` — a placeholder quoted as though it had been typed, and identical to what a caller who really typed it got.

Shipped guards: `bead-claimed` (an edit happens under a claimed work item) and `working-branch` (work happens off the protected trunk; `options.trunk`, default `main`). Both skip — with a stated reason — when their evidence is unavailable (`bd` not present, no branch checked out), because a guard that silently does not apply is indistinguishable from one that passed.

Guards are declared in `.beadloom/flow.yml`; an absent `guards:` block means every guard runs at the shipped default (`warn`), so an upgrade never turns a green project red:

```yaml
guards:
  bead-claimed:
    strictness: { default: warn, epic: block, chore: off }
    exclusions:
      - path: "scripts/**"
        reason: "operational scripts are not bead-scoped"
        until: "BDL-0xx introduces a scripts node"
```

Strictness resolves per work kind (`--context work_kind=epic`) with a `default` fallback. **An exclusion must carry both `reason` and `until`** — one without either is a configuration error (exit 3 from a shell, exit 2 through a hook), because an unnamed, undated exclusion disables a gate permanently by accident. `until` may name a **deadline** (it LEADS with an ISO `YYYY-MM-DD`, optionally followed by the prose that explains it) or an **event** (anything else, as above — what retires a real exclusion is usually a landed change, not a day). A deadline is parsed by the same function the `forbid_import` exemptions of `rules.yml` use, so the two surfaces cannot promise different things; once it passes, the exclusion says so in its own skip reason (`… (until 2024-01-01 — EXPIRED)`) and `--liveness` flags it as `exit condition has passed: '<pattern>'`. It is never enforced — the exclusion keeps applying, because a guard that starts blocking with no commit behind it is worse than the silence being reported (BDL-061.49). A `guards:` key naming an unregistered guard is likewise an error, not a no-op, and so is **a key the loader does not read** — a guard body carries `strictness` / `exclusions` / `options`, an exclusion carries `path` / `reason` / `until` (BDL-061.34): `option:` for `options:` used to drop the declared `trunk` and leave `working-branch` comparing against `main`, which passes an edit made on the project's real trunk at exit 0. There is **no `on:` key**: which tool invocations count as an edit, and which guards run on them, is decided by the harness adapter (in Claude Code, the matcher and the per-guard entries in `.claude/settings.json`), not by Beadloom. An `on:` key shipped in the S1 schema with no consumer and was deleted rather than quoted; it returns wired in S3.

**That matcher is the enforcement surface, and it is narrower than "every edit".** The emitted adapter is registered on `PreToolUse` for `Edit|Write|MultiEdit|NotebookEdit`, so a file written through `Bash` — `sed -i`, a heredoc, `python3 - <<EOF` — invokes no guard, produces no verdict and writes no firing. `--liveness` therefore cannot distinguish a session that edited entirely outside the matcher from one that complied: both leave the same record. This is a property of the binding rather than of a verdict, so no `not_covered` note can carry it (there is no evaluation to attach one to) — see BDL-UX #170 and the [flow-guards SPEC](../domains/application/features/flow-guards/SPEC.md#the-enforcement-surface).

With no `--project`, the **project root is discovered** by walking up from the working directory to the nearest ancestor containing `.beadloom/`; with `--project`, that directory is used verbatim and **must carry `.beadloom/` itself** — the flag names a project, not a directory. A missing path, a file, and an ordinary directory with no marker are one refusal: a guard that cannot locate a project answers `error` (exit 2) and creates nothing, by any route. Until BDL-061.31 any existing directory was honoured, so `--project <an ordinary directory>` found no `flow.yml`, silently traded the project's declared `block` for the shipped default `warn` (a non-blocking exit 1), and manufactured `.beadloom/` there when the firing was written — the record belongs to the project, not to wherever the process was pointed, and a firing written where `--liveness` does not read it is indistinguishable from no firing. A directory this process **may not read** is the same refusal since BDL-061.32: `click.Path` defaults `readable=True`, and that check runs in Click, so `--project <an unreadable directory>` used to be a usage error at exit 2 with no verdict, no record and nothing on stdout for `--json` to parse. No parameter of `beadloom guard` declares a conversion Click can refuse — every reason an argument cannot be used is answered by the guard, not by the argument parser.

`--context KEY=VALUE` is repeatable, and where a key is given twice **the last occurrence wins**. `--context path=...` is resolved against the project root before any exclusion is matched — `..` collapsed, symlinks followed — so a declared exclusion cannot be turned into an opt-out by respelling the path (`scripts/../src/app.py` is guarded, not skipped). A path resolving outside the project root is matched against no exclusion at all, and the verdict names it in `not_covered`.

The path is model-supplied, so its **shape is narrowed rather than repaired**: a well-formed target carries no C0 control character or `DEL`, no backslash, no leading `~`, and is encodable for the filesystem, and it is judged exactly as supplied — nothing is stripped first, because `str.strip()` also removes nine C0 characters the same rule refuses, which turned a `block` into a `skip` quoting a pattern that does not cover the file. Anything else is refused with an `error` verdict naming the offending rule — never normalised into a guess, and never a traceback. Each rule removes a spelling that means one file to the guard and another to the writer (`src\app.py` skipped a `*.py` exclusion while the write landed on `src/app.py`; a NUL crashed the process out on exit 1, the non-blocking code, leaving no record at all).

`--hook HARNESS` reads the harness's own hook event as JSON on stdin and derives the context from it (`claude-code`: `tool_input.file_path`, `tool_name`, `hook_event_name`). The event is read as **bytes** and decoded as UTF-8 strictly, so a payload the harness could not encode is refused (`error`, exit 2) identically under every locale — reading it as text left the decode to `sys.stdin`, whose error handler is `surrogateescape` under `LC_ALL=C`/`PYTHONUTF8=1` (the default in most containers), and there the undecodable bytes silently became a file name the guard then evaluated (BDL-061.36). The emitted adapter (`.claude/hooks/beadloom-guard.sh`, written by `beadloom setup-agentic-flow`) contains no logic — it is one `exec beadloom guard "$1" --hook claude-code` — so a hook and a shell cannot produce different verdicts.

`--liveness` reports, per guard, its effective strictness, how many times it fired, its last outcome, and four ways a gate stops protecting anything: `never-fired` (no firing that reached a verdict — an `error` is counted and shown, but does not clear the flag, because a guard that ran three times and answered none of them is not a live gate), `excluded-everywhere` (every strictness `off`, or nothing escapes the exclusion **list** — decided by matching the patterns against representative paths, not by comparing spellings, and asked of the list because `*` and `*/**` are each narrow and together exempt everything), `matches no file in the project: '<pattern>'` (a declared exclusion that exempts nothing that currently exists — a typo'd `scrpits/**` is safe but was silent), and `exit condition has passed: '<pattern>'` (its `until:` names a date that is behind us). A gate that cannot demonstrate it ran is treated as not having run. Every CLI evaluation appends one line to `.beadloom/guard-firings.jsonl`, which is the only file guards write — never the index they inspect. Decision logic lives in `application/guards/evaluation.py`; the CLI only renders it.

### beadloom waves

Decide which of these beads may run at the same time.

```bash
beadloom waves BEAD [BEAD ...] [--json] [--project DIR]
```

Exit codes: `0` = a shape was decided and rests on nothing unstated; `1` = a
shape was decided and carries findings (a bead whose declared scope could not be
read, an override past its exit condition, an override that changed nothing, a
shared medium that failed its check or that nobody measured) -- visible, never
blocking; `2` = no shape could be decided (no index, no answer from the
tracker, a bead the tracker does not have, a `waves:` block that would not parse).

It **decides**, it does not advise. Parallelism follows from the code-level
independence of the beads' node scopes, which only the architecture graph holds:
a tracker knows which beads block which, and nothing else knows which code they
occupy.

A bead says what it occupies in the tracker, in its own words -- `refs: billing,
shipping` (also `ref:`, also `area:`). The declaration **opens a line** and its
list runs to the end of that line, separated by commas or semicolons; a `refs:`
written inside a sentence is prose. A scope expands downward through `part_of`,
so a bead scoped to a domain and a bead scoped to one of its components do not
compare independent while editing the same package. A pair is serialised for
exactly one named reason: `blocked_by_bead`, `unresolved_scope`, `shared_node`,
`shared_file`, `dependency_edge` or `override_serial`.

**A bead whose declaration cannot be read is serialised against every bead.** An
unknown scope is not an empty scope -- an empty one compares independent of
everything, which would make the command's whole claim rest on silence. Four
things count as unreadable, each printed with its own remedy: no declaration
(`no_declared_refs`), a name the graph does not have (`ref_not_in_graph`), a
`refs:` written inside a sentence (`declaration_not_at_a_line_start`), and a
second ref written without a comma that the graph confirms is a node
(`declaration_dropped_a_node`). The parser fails toward serialisation on purpose:
a wave shape is acted on, so a parser whose errors widen a wave is worse than no
parser.

Every wave of more than one bead also prints the four media it shares no matter
what shape is chosen, each with the evidence it comes from: the working tree
(#181), the commit gate (#118), the doc baseline (#182, #133) and the tracker's
id space (#171). Each wave names one bead as its `gate_owner` -- the bead that
measures the combined tree once the wave has landed. It is assigned
deterministically rather than wisely; the point is that the step belongs to a
named bead instead of to a coordinator's habit.

**Each of those media is also checked, and each check can fail.** The command
measures a precondition per medium before the wave runs: that no path differs
from `HEAD` which no bead in the plan owns (`git status`), that the installed
pre-commit hook judges the paths a commit stages (`.git/hooks/pre-commit`), that
no doc pair is stale already (the doc index), and that no bead's title numbers it
differently from the id the tracker allocated (the bead records). A medium that
could not be observed is reported `unmeasured`, which is a finding: a concurrent
wave nobody measured is not a clean plan, it is an unmeasured one. What is NOT
checked is the wave's conduct afterwards -- nothing here can know whether the
gate owner ran the combined tree.

The `tracker-ids` check runs even when the plan is fully serial, because a
concurrent `bd create` shifts an id out from under the number an author already
wrote into the title, and that happens before any wave runs (#171).

A human outranks the decision by declaring it in `.beadloom/flow.yml`, with a
reason and an exit condition like every other stand-down in this tool:

```yaml
waves:
  overrides:
  - beads: [proj-1, proj-2]
    decision: parallel        # or: serial
    reason: "the two touch one vocabulary module and nothing else"
    until: "2026-09-01"
```

Every key is required, and required by its **content**: a key present but blank
is a configuration error too, because an override with no reason and no deadline
outranks the graph permanently by accident. Each override is reported with the
number of decisions it changed -- the number of its pairs the shape decides
differently when that entry is removed -- and one that changed **none** is a
finding, because an override nobody can see doing anything is how a check gets
switched off without anybody saying so.

```
$ beadloom waves proj-1 proj-2
2 wave(s) for 2 bead(s), 1 serialisation(s), 0 finding(s).

Wave 1: proj-1
Wave 2: proj-2

Serialised because:
  proj-1 | proj-2 - shared_node: billing

0 declared override(s).

No wave runs more than one bead, so nothing is shared concurrently.

Plan-time precondition of each shared medium:
  working-tree: not_applicable - no wave runs more than one bead, so nothing is carried between beads through this medium
  commit-gate: not_applicable - no wave runs more than one bead, so nothing is carried between beads through this medium
  doc-baseline: not_applicable - no wave runs more than one bead, so nothing is carried between beads through this medium
  tracker-ids: passed - every bead's title agrees with the number the tracker allocated
```

Every plan prints that block, a fully serial one included: three media are
`not_applicable` because nothing runs concurrently, and `tracker-ids` is checked
regardless.

`--json` carries the same facts: `waves[]` (with `gate_owner`), `scopes[]`,
`conflicts[]`, `overrides[]`, `shared_media[]`, `media_checks[]` (`medium`,
`status`, `detail`), `findings[]` and `exit_code`.

### beadloom review-brief

Hand a reviewer the change and the specification, and not the author's account of
either.

```bash
beadloom review-brief BEAD [--since REF] [--release] [--json] [--project DIR]
```

Exit codes: `0` = the brief rests on nothing unstated, or `--release` released the
account; `1` = the brief carries findings (an undeclared scope, an ambiguous one,
an unknown ref, a change nobody could measure, a change outside the declared
scope, no bound scenario -- or, under `--release`, a verdict whose independence
the tracker could not confirm); `2` = no brief could be assembled (no index, no
answer from the tracker, no such bead); `3` = `--release` was refused because no
verdict is recorded. `3` is distinct from `2` on purpose: nothing failed, the
account is simply still withheld, and a caller that could not tell those apart
would retry the wrong one.

The brief carries the **assignment** (the bead's title and description), the
**declared scope**, the **specification** (the graph's documents for those nodes
and every scenario whose `@bead:` tag names the bead) and the **change**
(`git diff <base>...HEAD`, the working tree, and the untracked files, each path
carrying the node that owns it). It does not carry the bead's comments.

The measurement behind that ordering: in hidden-profile tasks a group that hears
one member's conclusion first scores 17-36% where a single holder of all the
facts scores ~100%. So the account is released after the reviewer's own judgement
is recorded rather than never.

#### The reachability block

The brief closes with a statement of what can reach the reviewer, **per
channel** -- not with a count of what this command holds back. Four channels, each
either inspected or named as one nothing here can inspect (the output is wrapped
for this page):

```
REACHABLE — what can reach you about this change, per channel. This command withholds one
of them and closes none of the others; declaring what actually reached you is still yours
to do.
  bead comments: 0 item(s) — counted on <bead> and on no other bead — the beads that made
    this change are neither read nor counted here; withheld by this command until a verdict
    recorded on the bead; then `beadloom review-brief <bead> --release`; the author's account
    of the change converges the reviewer on the author's framing before the reviewer has
    looked at the code
  the work item's documents: 5 item(s) — the folder
    .claude/development/docs/features/BDL-068, against the 9 document name(s) this
    project's composed prompts mention
    .claude/development/docs/features/BDL-068/ACTIVE.md — named by roles/dev,
      commands/checkpoint, commands/coordinator, commands/task-init, commands/templates
  the commit bodies of the reviewed range: 19 item(s) — read over the range since main;
    19 of 19 carry a body, and your protocol sends you to this diff
    ab7e9fa9 [BDL-068] feat: review-brief states what is reachable — 24 body line(s)
  the launch prompt: NOT INSPECTED — nothing in this process can see one, so: if your launch
    prompt carried anything about this change that you did not derive yourself — the author's
    summary, or the coordinator's own observation of it — this withholding was defeated
    before it ran; say so in your verdict, you are the only party that can see it
```

The count that was printed before S2 said `4 author comment(s) withheld` and
nothing else, and a reviewer read it as a statement about its own knowledge. It
is not one: all three defeats of the withholding measured so far reached the
reviewer through a channel that count never mentioned -- `ACTIVE.md`
(BDL-UX #212), the commit bodies of the reviewed range (BDL-UX #219), and the
launch prompt (BDL-UX #204). Each was known only because a reviewer declared it
unprompted.

**This raises detectability and closes nothing.** The review protocol itself
sends the reviewer to the diff, and the commit bodies come with it; no report
changes that. What changed is that a reviewer can now see what it could reach and
say so, which is how all three defeats were found in the first place.

**A channel found empty never reads like one nobody could inspect.**
`0 item(s)` and `NOT INSPECTED — <reason>` are different sentences. A `flow.yml`
that will not parse costs the documents channel and not the brief: the channel
reports `NOT INSPECTED — the project's flow.yml will not parse, so no prompt
could be composed`, where before S2 the malformed file raised out of the command
and no brief was produced at all.

**A commit body is counted, never quoted** -- subject and non-empty body-line
count only, so a report about a leak is not itself one.

The documents channel is derived rather than listed: the names come from the
composed role and command prompts for this project's `flow.yml`, project layer
included, matched by shape (an upper-case name ending in `.md`). A team that names
`DECISIONS.md` in `.beadloom/flow/roles/review.md` moves this report by that act.

#### Two channels the block does not name

Both are measured, filed, and open. A reader of this section should not take the
four channels as the whole list.

- **The tracker export inside the reviewed diff** (BDL-UX #229). Where the project
  commits its tracker, the diff under review carries the author's comments as
  data. Measured on this feature's own S2 review: 16 added record lines, 30 author
  comments, 81,270 characters of comment text. The brief's own change inventory
  lists that file and prints `read it: git diff <base>...HEAD -- <path>` beneath
  it, so the report sends the reviewer to a channel it does not count -- BDL-UX
  #219's mechanism one step further along. Widening the count to that export and
  to the slice's sibling beads is filed, not done.
- **The work item's documents on a branch whose name carries a suffix**
  (BDL-UX #230). `work_item_of_branch` matches a `/`-separated segment that
  *equals* a work-item key, so `features/BDL-068` names the work item and
  `features/BDL-068-S2S3` names none. Measured on this feature's own development
  branch: the channel read `NOT INSPECTED — the branch 'features/BDL-068-S2S3'
  names no work item among the project's planning documents` while the reviewer
  was reading `RFC.md` and `CONTEXT.md` out of exactly that folder. The fix belongs
  in `application/declared_scope.py`, its one home, and is filed there.

#### The release half

`--release` prints the account once a verdict comment is on the bead, so the
deferrals, sabotage tables and measured numbers stay available to a reviewer who
would otherwise re-derive them. A verdict is a comment whose **first non-blank
line opens with** `REVIEW PASSED:`, `REVIEW ISSUES:` or `REVIEW FINDINGS:`, the
colon included -- the exact openings the review role is instructed to write.

A refusal names the bead its count was taken over, in the same vocabulary the
reachability block uses:

```
$ beadloom review-brief <bead> --release
WITHHELD — bead comments on <bead>: 0 item(s) stay withheld: no verdict is recorded on
this bead — the author's account stays withheld until one is. Record it with
`bd comments add <bead> "REVIEW PASSED: ..."` or a findings comment opening `REVIEW ISSUES:`
```

`0 item(s)` there says this bead carries no account. It says nothing about the
beads that made the change, and on a wave-structured slice — where the brief is
for a review bead — that is the ordinary case: the S2 review of this feature read
`0 item(s)` while 31,544 characters of the author's account sat on the two beads
that made the change.

The verdict comment's author is compared with the bead's assignee, and the answer
is **reported, not enforced**. A self-recorded verdict still releases, prints why
its independence cannot be established before the account rather than after it,
and exits `1`:

```
$ beadloom review-brief <bead> --release
FINDING: the verdict was recorded under the same tracker identity as the bead's own
author (v.zoologov), so this gate cannot tell an independent verdict from the author's
own — say which it was in your review
RELEASED — 5 author comment(s), on the verdict 'REVIEW ISSUES' already recorded.
```

A tracker that names no author for the verdict comment gets its own note rather
than that one — `the tracker named no author for the verdict comment, so this gate
could not tell whether the account was released by its own author`. Two different
facts, so two sentences: a shared identity and an absent author field are not the
same finding, and the S2 review of this feature met the second where it predicted
the first.

Refusing was rejected on a measurement: where every role writes under one tracker
identity, a refusal refuses every release, and a gate nobody can pass is bypassed
rather than obeyed. What this command withholds is an **input**, not a door -- a
reviewer with a shell can read the comments directly, and the value is in the
default and in the reachability statement being printed where the reviewer will
read it.

The change is measured over the **branch**, not over the bead, because no
per-bead attribution exists in the commits. On a branch carrying five beads all
five briefs report the same files, so the `changed-outside-scope` finding names
its window (`measured over the branch since <ref>`). `--since <ref>` narrows it.

`--json` carries `bead`, `title`, `assignment`, `refs`, `unknown_refs`, `docs`,
`base_ref`, `change_measured`, `changed`, `scenarios`, `reachability`, `findings`
and `exit_code`. `reachability` is an array of objects carrying `channel`,
`inspected`, `carries`, `reason` and `items` — it replaced the `withheld` object
in S2, a declared break. Under `--release` it carries `withheld_count`,
`verdict_marker`, `verdict_author`, `independence_note`, `refused_reason`,
`released` and `exit_code`; `withheld_count` is unchanged, because the break was
declared for the before half only. The account never appears in the non-release
`--json`.

### beadloom mutation

The score a run produced, held against the mutation scope the project declared
(BDL-068 S3.1). It reports a mutation run. It does not perform one.

```bash
beadloom mutation [--project DIR] [--stats FILE] [--target PATH]... [--only PATH]...
                  [--tool NAME] [--min-score FRACTION] [--json]
```

**Beadloom ships no mutation runner, and this command needs none installed.** The tool
is the project's choice, because owning one would tie the flow to a language (BDL-061
CONTEXT Q5) — which is why BDL-061 S4 shipped the mutation duty with no score behind it.
What ships here is the seam the project's own runner meets: `--stats` names a JSON object
of counters that *whatever* tool the project ran wrote, and this command reads them **by
name**. `killed` and `survived` are required; `timeout`, `no_tests`, `skipped` and
`suspicious` are optional; `total` is accepted as a second spelling of `mutants`. Nothing
under `src/` imports a runner, and a test asserts it.

**A counter it did not find is reported, never read as zero**
(`mutation-counters-missing`). A missing `killed` read as zero produces "0%", and a number
is what gets pasted into a bead comment. The same refusal covers a non-integer, a negative
value, and a stats file that is absent or is not a JSON object.

**Timeouts count as killed; mutants no test covers do not.** A mutant that hung was
detected. A mutant nothing executed was not, and leaving that class out of the denominator
is how a slice with no tests scores 100%.

- `--stats FILE` — the counters a run wrote. Without it the command still reports: every
  declared target is then measured by no run, which is a finding rather than silence.
- `--target PATH` — a path the run covered. Repeatable, and **required whenever `--stats`
  is given**: a run that does not say what it covered exits `2` rather than being assumed
  to cover the declared scope.
- `--only PATH` — judge only these declared targets; the rest print as `Not judged by this
  run`. A first slice measures one target of several, and both obvious alternatives are
  wrong. Reporting the rest as findings makes a scheduled job permanently red, which is how
  a check stops being read; dropping them from `mutation.targets` deletes a duty to make a
  job green.
- `--tool NAME` — the runner that produced the counters. Omitted, the report says `an
  unnamed runner`: a score whose producer is unnamed is a weaker claim and should look like
  one.
- `--min-score FRACTION` — the floor the score must clear (`0.95` is 95%). A floor declared
  against a score that does not exist is **missed**, not passed.
- `--json` — the same facts as the human report: `declared`, `not_judged`, `covered`,
  `tool`, `room`, `score`, `counters`, `missing_counters`, `min_score`, `below_floor` and
  `findings`.

Exit `0` when every judged target was measured by a run that produced mutants and the score
clears the floor — and also when the project declares no mutation scope at all, because not
opting in is not a violation. Exit `1` on findings or a missed floor. Exit `2` when the
invocation cannot be answered (`--stats` without `--target`).

**Every report names its room, including one carrying no run.** A report over declared
targets nothing covered exits 1, so it is a verdict, and until BDL-068 S3.3 it printed no
room at all. The room is a property of the process rather than of the run.

**An empty population is a finding, not a 100%** (BDL-068 S3.3). Before that slice this
command never asked the scope half anything, and each of these scored `100.0% of 10 scored
mutants` at exit 0: a declared target not on disk, a target outside the configured
`scan_paths`, and a target inside them holding no source file. The score is now folded with
`check_mutation_scope` over the targets the run is answerable for, so the same invocation
still prints the number the counters state and no longer prints it alone. Measured on a
temporary project whose only declared target is absent:

```
$ beadloom mutation --stats counters.json --target src/gone/
Room: Darwin arm64 · CPython 3.13.7 · 10 cores
Declared scope: src/gone/
Measured: src/gone/
Tool: an unnamed runner
Counters: killed 10, survived 0
Score: 100.0% of 10 scored mutants
WARN [mutation-target-missing] src/gone/: the mutation target 'src/gone/' is not on disk — the run produces zero mutants and a mutation score computed over nothing
  fix: update `mutation.targets` in .beadloom/flow.yml to the path the code moved to, or drop the target
$ echo $?
1
```

Two more populations are refused the same way. A run whose counters produce no mutants, and
a run that produced mutants and reached a verdict on none of them, both raise
`mutation-run-zero-mutants`: a suite that cannot start in the runner's copied tree skips
every mutant and leaves counters that look like a clean sheet.

The findings, all at `warn` severity: `mutation-target-unmeasured`,
`mutation-run-zero-mutants` and `mutation-counters-missing` from the score half, plus the
three scope checks `config-check` has raised since BDL-061 S4b —
`mutation-target-missing`, `mutation-outside-source` and `mutation-zero-mutants`.

**A measured report.** The counters below are the ones a `mutmut` run over
`src/beadloom/graph/rules/` wrote — 3 989 mutants, 54 min 55 s, in the room the output's
first line names. The runner's own release is whatever `--tool` was handed and is printed
back verbatim: this document does not restate it, because a third-party version quoted here
goes stale in a way that says nothing about the command.

```
$ beadloom mutation --stats mutants/mutmut-cicd-stats.json \
    --target src/beadloom/graph/rules/ --only src/beadloom/graph/rules/ \
    --tool 'mutmut 3.7.0' --min-score 0.95
Room: Darwin arm64 · CPython 3.13.7 · 10 cores
Declared scope: src/beadloom/doc_sync/doc_quality.py, src/beadloom/doc_sync/doc_shape.py, src/beadloom/graph/rules/
Not judged by this run: src/beadloom/doc_sync/doc_quality.py, src/beadloom/doc_sync/doc_shape.py
Measured: src/beadloom/graph/rules/
Tool: mutmut 3.7.0
Counters: killed 3836, mutants 3989, no_tests 0, skipped 0, survived 152, suspicious 0, timeout 1
Score: 96.2% of 3989 scored mutants
Floor: 0.95 — the score is at or over it.
```

That 96.2% is one room's figure and was not taken on a CI runner.
`.github/workflows/mutation.yml` runs the same command nightly under the same floor and is
deliberately NOT a required status check: the run is two to three times the ~16-28
runner-minute budget that withdrew this project's Windows leg, and a scheduled workflow
produces no check-run on a pull request, so requiring its context would make `main`
unmergeable.

The three findings, the counter vocabulary and the report's own invariants are in the
[Mutation Scope DOC](../domains/application/components/mutation-scope/DOC.md).

### beadloom rooms

The room this run is in, the rooms the project declares, and which of them the run did not
enter (BDL-068 S3.2).

```bash
beadloom rooms [--project DIR] [--dimension AXIS] [--json]
```

**The census is derived, never listed.** The supported interpreters come from the
`Programming Language :: Python :: X.Y` classifiers in the packaging metadata; the legs come
from every job of every `.github/workflows/*.y*ml`, each matrix expanded as a product and a
`matrix.<axis>` expression in `runs-on` resolved through it. The module owns a runner-label
vocabulary (`ubuntu` / `macos` / `windows`) and no room list, so a leg added to a workflow is
covered by the same act that adds it. A hand-written list satisfies every test beside it and
goes stale the first time a leg moves: this repository's own
`DEFAULT_STATUS_CHECK_CONTEXTS` has drifted from what CI reports three times, and a required
check that never reports makes `main` unmergeable.

**Naming the room does not make a verdict stronger. It makes it answerable** — a reader can
see which declared rooms the run covers and which it does not. It is not a step and carries
no status.

Measured on this repository, 2026-09-03, with rows elided:

```
$ beadloom rooms
Rooms — derived from this project's declaration, never from a list

  This run is in: Darwin arm64 · CPython 3.13.7 · 10 cores

  Declared rooms: 21, entered by this run: 0
    [  ] os=ubuntu-latest python=3.13    .github/workflows/ci.yml: tests
         os: the leg is ubuntu-latest (Linux) and this run is Darwin
    [  ] locale=C os=ubuntu-latest    .github/workflows/ci.yml: tests-locale
         locale: this run cannot describe the dimension `locale`, which the leg declares as C; os: ...
    [  ] os=ubuntu-latest    .github/workflows/mutation.yml: mutation
         os: the leg is ubuntu-latest (Linux) and this run is Darwin
    ... and 9 more

  Interpreters this project supports: 3.10, 3.11, 3.12, 3.13 (floor >=3.10)

  Unresolved (1):
    .github/workflows/ci.yml: ai-techwriter — the runner label `self-hosted+ai-techwriter` names no platform this report knows, so no run can be said to have entered it
```

A local run is in **0 of the 21 rooms this project declares**, and that is the point rather
than a caveat: nine "green on the tree" reports across BDL-067 were taken in exactly this
room. The `mutation` leg above was added by the slice that added it and appeared in the
census with no edit to the census's own code, which is the property the required-contexts
tuple lacks.

A run enters a declared room only when every dimension is comparable and equal. A runner
label naming no platform (`self-hosted`) and a dimension this run cannot describe (the two
`locale` legs) both resolve to NOT ENTERED with the deciding dimension named, and an
unresolved job is listed rather than dropped: a comparison that cannot be made must never
manufacture coverage.

- `--dimension AXIS` — the distinct values of one axis, one per line: the form a checklist
  loops over instead of spelling out a set that goes stale. The Python overlay's type-check
  step is `for v in $(beadloom rooms --dimension python)`, and the honest limit of that local
  form is that it varies the TARGET version only — the interpreter the checker runs under is
  still one, which is a difference only CI measures.
- `--json` — `current`, `declared` (each with `dimensions`, `source`, `entered` and `why`),
  `supported`, `floor`, `supported_without_a_leg` and `unresolved`.

Exit `0` when the census was taken; a project declaring no leg also exits `0`, because this
command grades nothing. Exit `2` when `--dimension` names an axis no declared room carries,
and the refusal names the axes that exist (`no declared room carries a 'nonesuch' axis; the
axes declared are: locale, os, python`). An empty answer would read as "this project has no
such axis", which is the clean list an agent trusts and stops at.

The derivation, the floor-is-not-a-set rule and why the packaging metadata is read without a
TOML parser are in the
[Verdict Room DOC](../domains/application/components/verdict-room/DOC.md).

### beadloom ci

The unified enforcement gate — the single CI convergence point (principle 7: identical for Cursor / Claude Code / human authors).

```bash
beadloom ci [--hub EXPORT.json ...] [--fail-on CSV] [--format {rich,json,github}] [--no-reindex] [--project DIR]
```

Composes the existing checkers, in order, into ONE verdict with a single exit code (0 = all steps passed, 1 = any step failed):

1. `reindex` (incremental) — unless `--no-reindex`.
2. `lint --strict` — architecture boundary rules at error severity.
3. `sync-check` — doc↔code freshness (stale pairs fail).
4. `docs audit` — stale numeric facts in documentation (`stale>0` fails). The step line also states its coverage — `M/N declared fact(s) verified` plus the names of the facts it checked nothing for — because a count of findings says nothing about the facts nobody stated.
5. `docs-quality` — the eleven planning-document checks (the five writing-standard ones, the four shape ones and the two route ones) over the project's planning documents. Warn only: it never fails the gate, and a project with no planning document is a NAMED skip stating the globs. Three states set the step to `WARN` rather than `PASS`: a check that read nothing anywhere (`NOT CHECKED`), a document KIND no content check enters (`NO CHECK READS`), and a document nothing could decode (`UNREADABLE: N`). Measured on this repository, 2026-09-03: `WARN | 259 document(s) read; measurable-goal 4, pending-in-approved 7, missing-section 102, routed-without-axes 12; NO CHECK READS: BRIEF, PLAN, SUMMARY`. The line prints the finding count and not the 27 accepted-without-witness statements the re-scope stopped deciding about; that limit is stated in the doc-quality SPEC.
6. `doc-spaces` — the TO-BE → AS-IS relation over the project's documentation spaces (BDL-061 S5). Warn only, on the same terms as the step above, and a project with no TO-BE document is a NAMED skip stating the roots it looked under. FOUR states set `not_verified` and the step then reports `WARN`: no tracker was readable, no epic with closed beads declared a node, some epics declare none, and some epics the tracker does not name. The line states both WORKING populations apart — `N WORKING document(s) in the exempt space, M sync pair(s) excused` — because one word for two populations is how a reader takes the document count as the excused-pair count; the pair count is carried from the sync-check step that measured it, never recomputed here.
7. `scope-check` — did this branch leave the axes its work item declared? Branch-scoped (`<trunk>...HEAD`, what the pull request contains) rather than tree-scoped, because the tree is shared by several agents and judging it would fail one agent's push on a neighbour's edit. Warn only, and `passed=True` unconditionally: one work item in 64 on this repository carries an `## Axes` section, so a check that blocked would meet a repository that cannot satisfy it. A run with no branch, no work item, no index or no section is SKIPPED with its reason, and a run over a branch whose changed paths no node owns is SKIPPED too, because a comparison over an empty population is not a pass. The report names each path and the axis it fell outside. It does not prevent the commit that made it.
8. `config-check` — AgentConfigAsCode drift, plus the mutation-SCOPE findings (a declared `mutation.targets` entry outside `scan_paths`, absent from disk, or holding no source a runner could mutate). All `warn`. The SCORE half is not a gate step: it needs counters a runner wrote, and [`beadloom mutation`](#beadloom-mutation) is where they are read.
9. `doctor` — graph/data integrity; ONLY `ERROR`-severity checks fail the gate (WARNING/INFO advisories never block — no false gate).
10. `federate --fail-on` — the cross-service landscape gate, only when `--hub` export(s) are given (safe-default fail-set `breaking,drift,orphaned_consumer,undeclared_producer`; no-false-gate verdicts rejected).

**What `--no-reindex` changes about the verdict.** It skips step 1, so every later step describes the INDEX rather than the working tree. With an index older than the tree, the `lint` step reports `PASS` over a live error-severity violation that the same gate catches after a reindex (measured), and the `sync-check` step compares against whatever baseline the index holds. Use it only where something else has just reindexed.

**Honest gate (the Phase-0 lesson):** the report names every step that ran and its outcome — `PASS` / `WARN` / `FAIL` / `SKIP` — never a green that silently skipped a step, and never a `PASS` over something the step could not check (`WARN`: it ran, found nothing wrong, and part of what it reports on was not verifiable — see `sync-check` above). **No short-circuit:** all steps run and ALL findings are collected even after an earlier failure, so one run surfaces every problem. `--format` applies uniformly across every step; findings share the agent-actionable `{kind, rule, severity, node, locations, why, remediation}` shape (`github` emits valid `::error file=<path>,line=<n>::<msg>` workflow-command annotations, matching `lint --format github`; `json` emits `{ok, steps[]}`). The per-repo `beadloom-aac-lint.yml` reindex+lint+sync steps collapse into one `beadloom ci` call. Orchestration lives in `application/gate.py:run_ci_gate()`; the CLI only parses options and renders.

**The verdict names the room it was taken in (BDL-068 S3.2), and does not change because of it.** `GateResult` carries a `RoomCensus` populated by `run_ci_gate()`, and all three output shapes print it: a `Room:` block under the rich verdict (the current room, then `N of M declared room(s) not entered by this run:` with the first three named, or `every declared room entered (M)`); a `room` object in `--format json` with `current`, `entered`, `not_entered` and `unresolved`; and one `::notice::room <room> — N of M declared room(s) entered by this run` line in `--format github`. It is printed UNDER the verdict rather than beside it, because it is not a step and has no status — a passing gate still passes with zero findings and a failing gate still exits 1. Measured on this repository, 2026-09-03: a local macOS run reports `0 of 21 declared room(s) not entered by this run`, which is the verdict's address rather than a caveat on it. The census itself is [`beadloom rooms`](#beadloom-rooms).

### beadloom setup-mcp

Configure MCP server for your editor.

```bash
beadloom setup-mcp [--tool {claude-code,cursor,windsurf}] [--project DIR]
beadloom setup-mcp --remove [--tool {claude-code,cursor,windsurf}] [--project DIR]
```

- `claude-code` (default) -- `.mcp.json` in project root
- `cursor` -- `.cursor/mcp.json` in project root
- `windsurf` -- `~/.codeium/windsurf/mcp_config.json` (global)

### beadloom setup-ai-techwriter

Scaffold the AI tech-writer (BDL-047 / F4.1; harness packaged in BDL-051 / S2)
into this repo for one-command, 3-step opt-in. In the `setup-*` family alongside
`setup-mcp` / `setup-rules`.

```bash
beadloom setup-ai-techwriter --platform {github,gitlab} [--project DIR]
```

Idempotently scaffolds (clean overwrite on re-run):

- **No Python vendoring.** As of BDL-051 / S2 the harness ships **inside** the
  installed `beadloom` package as the `beadloom.ai_agents.ai_techwriter` domain,
  so adopters depend on `beadloom` and invoke it directly via
  `python -m beadloom.ai_agents.ai_techwriter` (the BDL-047/048 `tools/` Python
  vendoring + drift-guard machinery is retired). Only the operator artifacts —
  the Goose `recipe.yaml` (a readable reference of the agent's blast radius) and
  `provision-runner.sh` — are copied (from package data via
  `importlib.resources`) into `tools/ai_techwriter/` for operator convenience.
- The chosen platform's CI wrapper: `.github/workflows/ai-techwriter.yml`
  (GitHub) **or** an `ai-techwriter` job in `.gitlab-ci.yml` (GitLab). As of
  BDL-049 both trigger on a **PR to main/master** — GitHub `on: pull_request`
  (`opened`/`synchronize`/`reopened`), GitLab `merge_request_event` — plus a
  manual fallback (`workflow_dispatch`). They call the same
  `python -m beadloom.ai_agents.ai_techwriter` entrypoint; the PR path passes
  `--target pr-branch` and `--since $(git merge-base origin/<base> HEAD)` so the
  agent commits its refresh into the PR branch; the manual path uses
  `--target branch-pr`. A loop-guard skips the agent's own
  `[skip ai-techwriter]` commit, and `cancel-in-progress: true` supersedes older
  runs. Only the trigger, the secret naming (`QWEN_API_KEY` repo secret vs CI/CD
  variable), and `--platform` differ. An existing `.gitlab-ci.yml` is appended to
  (job-only, stripping the standalone `stages:` header) — never blindly
  clobbered; an already-wired file is left as-is.
- `tools/ai_techwriter/provision-runner.sh` — a hardened, idempotent,
  executable (`0o755`) self-hosted-runner provisioner (`--platform/--repo/--token`):
  guarantees swap **before** any apt/build (the OOM lesson), RAM (~2 GB min,
  ~4 GB recommended) + disk (~5 GB) prechecks, fail-hard on the critical
  steps (toolchain + runner register/start), and best-effort + verified
  Goose/beadloom/bd installs reported at the end.
- `docs/guides/ai-techwriter.md` — the 3-step getting-started guide.

Delegates to `onboarding/ai_techwriter_setup.py:scaffold()`.

### beadloom setup-agentic-flow

Scaffold Beadloom's proven multi-agent dev flow into this repo (BDL-048 / 052).
In the `setup-*` family alongside `setup-rules` / `setup-mcp` /
`setup-ai-techwriter`.

```bash
beadloom setup-agentic-flow [--project DIR] [--force] \
    [--tool claude|cursor]...        # repeatable; default: flow.yml or claude
    [--architecture ddd|fsd]         # default: flow.yml or ddd
    [--stack python,fastapi,javascript,typescript,vuejs]  # CSV; default: flow.yml or auto-detected
```

Since **BDL-061 S3** every flow artifact is **composed** from four layers in a
fixed order — the shipped stack-neutral CORE, one architecture overlay
(`ddd`/`fsd`), each selected stack overlay **sorted**, and the project fragment
under `.beadloom/flow/` — for all three kinds:

| kind | written to | project fragment |
|------|-----------|------------------|
| `roles` | `.claude/agents/<role>.md`, `.cursor/agents/<role>.md` | `.beadloom/flow/roles/<role>.md` |
| `commands` | `.claude/commands/<cmd>.md` | `.beadloom/flow/commands/<cmd>.md` |
| `claude` | `.claude/CLAUDE.md` | `.beadloom/flow/claude/CLAUDE.md` |

`cursor` additionally gets a `.cursor/rules/beadloom-flow.md` orchestrator
pointer. Selection comes from `.beadloom/flow.yml`, overridden by the
`--tool`/`--architecture`/`--stack` flags (defaults `claude` / `ddd` /
auto-detected stack — **flag → flow.yml → default** precedence). An invalid
selection raises a `FlowConfigError` naming the bad value + the allowed set.
`config-check` compares each artifact against its composition, so a project
fragment is part of the expected output while a change to a shipped fragment is
not. See the [Project Overlays guide](../guides/project-overlays.md).

`.claude/CLAUDE.md` keeps two auto-regions generated for THIS project via the
same `refresh_claude_md` machinery `setup-rules --refresh` uses: `project-info`
and `doc-language` (rendered from `language:` in `flow.yml`). Every bullet in
`project-info` is read from **the target project** — its declared version
(`pyproject.toml` including a `dynamic` one, `package.json`, `Cargo.toml`), its
`requires-python` verbatim, its declared dependencies, its own `src/` packages
and the architecture its `flow.yml` names. A fact that cannot be read is
**omitted, never substituted**.

> Until **BDL-061 S3b** it was not. The version bullet rendered Beadloom's own
> `__version__` (a JavaScript project a major version behind was told ours), the
> architecture line said `DDD packages` whatever the project declared, the stack
> line matched the project's manifest against *Beadloom's* dependency names and
> printed our Python floor as theirs, and the package scan fell back to looking
> for `src/beadloom/` inside the adopter's tree. Each read correct on this one
> repository by coincidence, which is why four slices of scrutiny passed over it
> (BDL-UX #183). The same coincidence covered `beadloom doctor`, which audited
> those four claims in an adopter's file against *our* state; it now reads
> theirs, and reports `not verified` for a fact the project does not declare.

**The command records the selection it composed from.** A first run writes
`.beadloom/flow.yml` — and never writes over an existing one, since that file is
the adopter's policy (`language` and `overlays.suppress` have no flag and live
only there). Before BDL-061 S3b it resolved the selection in memory and never
wrote it down, so a virgin scaffold on a fresh TypeScript project left
`beadloom config-check` — the command this one's own closing advice recommends —
at **exit 1 with four errors**, remediated by advice to add a `flow.yml` by
running the command just run (BDL-UX #187). The same fix closed a divergence
found alongside it: `scaffold()` re-resolved from disk *without* the flags, so
`--architecture fsd` composed the role adapters as `fsd` and the commands and
`CLAUDE.md` as `ddd`.

It also writes the **flow-guard binding** (BDL-061 S1): `.claude/hooks/beadloom-guard.sh`
— one `exec beadloom guard "$1" --hook claude-code` — and one `PreToolUse` entry per
registered guard in `.claude/settings.json`, matched on
`Edit|Write|MultiEdit|NotebookEdit|Bash`.
The guard names come from the registry, so a guard added in a later release is wired by
re-running this command. Registration is a **merge**: existing hooks survive, re-running adds
only the missing entries, and a `settings.json` that cannot be parsed is reported and left
untouched. The merge is on the command string, so a project scaffolded before `Bash` joined the
matcher (BDL-068 S4, BDL-UX #170) keeps the narrower one across the upgrade; `beadloom guard
--liveness` reports that gap rather than leaving it silent (see
[`beadloom guard`](#beadloom-guard)).

The command makes the same whole-working-set `.gitignore` call `init` makes (see
[`beadloom init`](#beadloom-init)), for a project initialised by a Beadloom older than
the block: the guards' firing record is one entry in that set, not a special case owned
by the guard scaffolder.

A composed command or `CLAUDE.md` that already matches is left alone; a
hand-edited one is **skipped** (reported as such) so user edits are not silently
clobbered; `--force` overwrites it. Composed role adapters are owned by the
configurator (re-running recomposes them). Delegates to
`onboarding/role_adapters.py:generate_adapters()` (the adapters) +
`onboarding/agentic_flow_setup.py:scaffold()` (the commands + CLAUDE.md).

The command **prints what it found**, not only what it wrote: the files an older
layout left behind, each with the exact `rm -f` command (BDL-UX #137), and a
migration note naming the project-layer path a hand edit belongs in.

```
Left alone (1) — your edits are the only copy of an intent, so Beadloom did not
recompose over them:
  = .claude/commands/coordinator.md: hand-edited … move the additions to
    .beadloom/flow/commands/coordinator.md

Left by an older flow layout (5) — reported, never deleted:
  ? .claude/commands/dev.md: left by an older flow layout (the role moved to
    .claude/agents/dev.md) — remove with `rm -f .claude/commands/dev.md`
```

Until BDL-061 S3b both lists were computed on every run and read by **nothing**
outside the library, so BDL-UX #137's closure and S3's migration-guidance
criterion were true of `scaffold()` and false of the command anybody runs. What
the user saw instead was `Skipped .claude/commands/coordinator.md (hand-edited;
use --force)` — advice to run the destructive flag, naming nowhere the edit could
safely go (BDL-UX #188). NO CALLER, NO CAPABILITY.

The command prints the **honest boundary**: the coordinator + `Agent`-spawn are
Claude-Code-native (orchestration stays in the harness); the Beadloom MCP
process-tools are the deterministic, tool-agnostic substrate the flow calls; and
the single source of TRUE enforcement remains `beadloom ci` in CI (the in-flow
gates are advisory-strong, not a substitute for CI). See the
[Agentic Dev Flow guide](../guides/agentic-flow.md).

### beadloom setup-branch-protection

Configure trunk-based branch protection on `main` via `gh api` (BDL-049), so the
CI gate becomes **true enforcement** rather than advisory. GitHub only.

```bash
beadloom setup-branch-protection --repo OWNER/NAME [--branch main] [--check CONTEXT]... [--dry-run]
```

Idempotently sets `main` (or `--branch`) protection with a declarative
`PUT repos/{owner}/{repo}/branches/{branch}/protection`: a **PR is required** (no
direct push), the scaffolded default set of `ci.yml` checks — `gate`, `tests (3.10)`,
`tests (3.11)`, `tests (3.12)`, `tests (3.13)`, `tests-locale (C)`,
`tests-locale (en_US.ISO-8859-1)`, `site-build`, `ai-techwriter`
(ci.yml's job names + matrix legs) — are **required status checks**
(`strict: true`), and `enforce_admins: true` + 0 required reviews so the
**solo owner is never locked out** (can self-merge). `PUT .../protection` is
declarative, so re-running re-settles the same state.

- `--repo OWNER/NAME` (required) — the GitHub repository (e.g. `acme/widget`).
- `--branch` (default `main`) — the trunk to protect.
- `--check CONTEXT` (repeatable) — overrides the default required-check contexts
  (the consolidated `ci.yml` job check-runs listed above) **entirely**. A context
  MUST match a real GitHub check-run name EXACTLY and must NOT be a
  **path-filtered** workflow's check: such a check does not run on PRs that miss
  the filter, so under `strict: true` the PR — and therefore `main` — would never
  become mergeable. BDL-050 dropped the `tests` `paths:` filter precisely so each
  matrix leg runs on every PR and is a reliable required check.
- `--dry-run` — print the exact `gh api` call + JSON payload without touching
  GitHub.

**A required context must be a check that can go green.** `PUT .../protection` is
declarative and re-running it is harmless in itself, but the payload is the
DEFAULT set above, and `strict: true` means every context in it must pass before
a pull request can merge. Requiring a check-run that is red — or that does not
exist in your pipeline at all — makes the branch permanently unmergeable until it
is green or the context is removed. **On this repository today that is a live
constraint, and the gap is now small enough to close deliberately:** the two
`tests-locale` legs added in BDL-061.38 were knowingly red (108 ASCII / 83 8-bit
locale-attributable failures, measured) and BDL-061.42 turned both **green**. A
`tests-windows` leg (BDL-061.39) briefly made the declared set ten and was the
red one; the owner withdrew it in `beadloom-mr2l.64` on a measured cost — ~16-28
runner-minutes per PR and the pipeline's critical path, roughly tripling
PR-to-merge latency, for a platform outside this project's target audience — so
the declared set is nine again. `main` still carries the seven pre-BDL-061.38
contexts, and the two it lacks have both been observed green.
**Sequencing:** before re-running `beadloom setup-branch-protection` here,
compare the declared contexts against what actually reports green on an open PR
(`gh pr checks`), because the payload is the whole default set. Alternatively
pass `--check` explicitly for the set your pipeline can satisfy.

Delegates to `onboarding/branch_protection.py:apply_branch_protection()` (the
`gh` invocation is injected via a `GhRunner` seam for mockable tests).

### beadloom mcp-serve

Launch MCP stdio server.

```bash
beadloom mcp-serve [--project DIR]
```

## API

As of BDL-059 S4, `src/beadloom/services/cli.py` is a thin registration shell:
it imports each command module for its registration side effects and
re-exports `main` (plus the private helpers tests import) so
`beadloom.services.cli.main` stays the stable entry point. The command
implementations live in the `src/beadloom/services/commands/` package — one
cohesive module per command group: `_root` (the `main` group + global options),
`query` (`ctx`/`search`/`why`/`graph`/`diff`), `index_ops` (`reindex`/`link`),
`status` (`status` + `--debt-report` rendering), `docsync`
(`sync-check`/`sync-update`/`install-hooks`/`active-sync`/`ci`), `federation`
(`export`/`federate`), `docs` (the `docs` group: `generate`/`site`/`audit`/`polish`),
`setup` (the `init`/`setup-*`/`mcp` commands), `dashboard` (`tui`/`ui`/`watch`),
`snapshot` (the `snapshot` group), `waves` (`waves`), `review_brief`
(`review-brief`), `mutation` (`mutation`) and `rooms` (`rooms`). The `status`
command's data-gathering was
moved DOWN to the application layer (`application/status.py`:
`gather_status`/`compute_context_metrics`/`StatusData`); the command keeps only
the Rich/JSON presentation. The CLI surface (every command, option, help text,
output, and exit code) is unchanged by the split.

Commands (re-exported from the package via the registration shell):

- `main` -- Click group: `beadloom [--verbose|-v] [--quiet|-q] [--version] COMMAND`
- `reindex` -- rebuild SQLite index (incremental by default, `--full` for complete rebuild)
- `ctx` -- get context bundle for ref_id(s)
- `graph` -- show architecture graph (Mermaid, C4-Mermaid, C4-PlantUML, or JSON) with `--format`, `--level`, `--scope` options
- `export` -- export the indexed graph as a deterministic federation artifact (JSON, schema v1) with `--out`
- `federate` -- aggregate >=2 satellite export artifacts into one federated graph (drift verdicts + staleness)
- `doctor` -- run validation checks
- `status` -- show index statistics with health trends and context metrics (data gathered by `application/status.py:gather_status`); `--debt-report` mode with `--fail-if`, `--category` flags
- `sync_check` -- check doc-code sync with reason/details (reason-aware output for `untracked_files`, `missing_modules`, `symbols_changed`); `--since GIT_REF` measures drift against a git ref instead of the stored baseline (fresh-checkout / per-push drift detection)
- `sync_update` -- review and update stale docs interactively; `--check` for status-only; `--yes`/`-y` for a non-interactive re-baseline; `--all` (with `--yes`) re-baselines every stale ref
- `install_hooks` -- install/remove the pre-commit hook (lint -> mypy -> sync-check -> guarded ACTIVE/tracker-coherence auto-fix step) AND/OR the pre-push Beadloom Gate hook (`beadloom ci`, blocks the push on red; `command -v beadloom` guard -> safe no-op outside a flow repo); `--pre-commit`/`--pre-push` selectors (default both), `--remove`, idempotent
- `active_sync` -- reconcile each epic's ACTIVE.md bead-status table from `bd` (`--epic`/`--check`/`--json`/`--no-export`); fix mode also `bd export`s the tracked `.beads/issues.jsonl`; safe no-op when no ACTIVE table or no `bd`; delegates to `application/active_table.py:reconcile_active_tables()`
- `link` -- manage external tracker links
- `search` -- FTS5 search with LIKE fallback
- `why` -- impact analysis (upstream + downstream) with `--reverse` and `--format {panel,tree}`
- `diff_cmd` -- graph changes since a git ref
- `snapshot` -- Click group for snapshot commands (`save`, `list`, `compare`)
- `snapshot_save` -- save current graph state as a snapshot
- `snapshot_list` -- list all saved snapshots
- `snapshot_compare` -- compare two snapshots (added/removed/changed nodes and edges)
- `lint` -- architecture lint with `--strict`, `--fail-on-warn`, auto-format detection, agent-actionable `remediation`, and `--format {rich,json,porcelain,github}` (GitHub annotations)
- `prime` -- compact project context for AI agents
- `setup_mcp` -- configure MCP server for editor
- `setup_rules` -- create IDE rules files
- `setup_ai_techwriter` -- scaffold the AI tech-writer (vendored harness + recipe + chosen platform CI wrapper + getting-started guide) for one-command opt-in; delegates to `onboarding/ai_techwriter_setup.py:scaffold()`
- `setup_agentic_flow` -- scaffold the packaged multi-agent dev flow (`.claude/agents/*` + `commands/*` vendored byte-identical + CLAUDE.md auto-regions per-project); idempotent, `--force` overwrites hand-edited flow files; delegates to `onboarding/agentic_flow_setup.py:scaffold()`
- `config_check` -- AgentConfigAsCode drift gate (`--fix` regenerates); reuses the `setup-rules --refresh` generator; also drift-checks/restores the scaffolded agentic-flow files when the flow is present
- `ci` -- unified enforcement gate composing reindex -> lint -> sync-check -> docs-audit -> docs-quality -> doc-spaces -> scope-check -> config-check -> doctor -> (optional `--hub`) federate into one exit code; the verdict carries the room it was taken in (`GateResult.room`), printed in all three formats and changing no step's status; the docs-audit step blocks on stale facts (`stale>0`); honest per-step PASS/WARN/FAIL/SKIP; uniform `--format {rich,json,github}` (github = valid `::error file=,line=` annotations); delegates to `application/gate.py:run_ci_gate()`
- `waves` -- decide which of the named beads may run at the same time, from the code-level independence of their declared node scopes; prints one named reason per serialised pair, the media a concurrent wave shares, one plan-time verdict per medium and each wave's `gate_owner` (`--json`; exit 0 clean / 1 findings / 2 undecidable); delegates to `application/waves/planner.py:plan_waves()`
- `review_brief` -- assemble a reviewer's input (assignment, declared scope, specification documents, bound scenarios, changed files) while withholding the bead's own comments, and state what is REACHABLE per channel: bead comments (counted on that bead and on no other), the documents of the work item the branch names, the commit bodies of the reviewed range, and the launch prompt, which is named as a channel nothing here can inspect; `--release` prints the account once a verdict is recorded and reports whether that verdict's independence can be established (`--since`, `--json`; exit 0 clean / 1 findings / 2 unassemblable / 3 release refused); delegates to `application/review_brief/`
- `mutation` -- the score a run produced over the declared `mutation.targets`, from the counters the project's own runner wrote (`--stats`/`--target`/`--only`/`--tool`/`--min-score`/`--json`); reads counters by NAME and reports one it did not find rather than as zero; folds the scope check in, so an empty population is a finding and not a 100%; exit 0 clean or nothing declared / 1 findings or under the floor / 2 counters named without the scope they cover; delegates to `application/mutation_scope/score.py:report_mutation_score()`
- `rooms` -- the room this run is in and the rooms the project declares, derived from the packaging classifiers and every CI workflow rather than from a list (`--dimension` prints one axis, one value per line, for a checklist to loop over; `--json`); exit 0 census taken / 2 `--dimension` names an axis no declared room carries; delegates to `application/rooms.py:take_census()`
- `mcp_serve` -- run MCP stdio server
- `docs` -- Click group for doc commands (`generate`, `polish`, `audit`)
- `tui` -- launch TUI dashboard (primary command, multi-screen with `--no-watch`)
- `ui` -- launch TUI dashboard (alias for `tui`)
- `watch_cmd` -- watch files and auto-reindex
- `init` -- project initialization (bootstrap, import, interactive, non-interactive with `--yes`/`--mode`/`--force`)

All commands accept `--project DIR` to specify the project root. The current directory is used by default.

## Testing

CLI is tested via `click.testing.CliRunner`. Each command has a corresponding test file in `tests/test_cli_*.py`: `test_cli_reindex.py`, `test_cli_ctx.py`, `test_cli_graph.py`, `test_cli_status.py`, `test_cli_sync_check.py`, `test_cli_sync_update.py`, `test_cli_hooks.py`, `test_cli_link.py`, `test_cli_docs.py`, `test_cli_mcp.py`, `test_cli_watch.py`, `test_cli_diff.py`, `test_cli_why.py`, `test_cli_lint.py`, `test_cli_init.py`, `test_cli_snapshot.py`, `test_cli_config_check.py`, `test_cli_setup_agentic_flow.py`, `test_cli_active_sync.py` (+ `test_cli_active_sync_hardening.py`), `test_cli_waves.py`, `test_cli_review_brief.py`. Two commands carry their command-level tests outside that naming, beside the application tests they render: `test_mutation_command.py` (with `test_mutation_score.py`, `test_mutation_phantom_gate.py`, `test_mutation_runner_scope.py` and `test_mutation_ci_job.py`) and `test_rooms_command.py` (with `test_verdict_room_derivation.py`, `test_verdict_room_census.py`, `test_verdict_room_population.py` and `test_gate_verdict_room.py`).
