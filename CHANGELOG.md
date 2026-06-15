# Changelog

All notable changes to Beadloom are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-06-15

**Reference-documentation freshness + positioning refresh.** A minor, backward-compatible
release: Beadloom now guards the freshness of overview/reference docs (READMEs, guides)
that aren't paired to a code symbol, and the public docs lead with the data-core positioning.

### Added
- **`docs audit` in the Gate (BDL-057).** `beadloom docs audit` is promoted out of
  `[experimental]` and runs inside `beadloom ci` as a blocking step (fails on `stale>0`):
  stale numeric/version facts in prose (version, node/edge counts, MCP-tool/CLI-command
  counts) are caught before merge.
- **`reference` doc kind with `watches:` (BDL-057).** A doc opts in with
  `<!-- beadloom:watches=cli,graph,flow.yml -->`; `sync-check` computes a coarse aggregate
  hash over the watched surface and reports an advisory `surface_drift` (warn-only — never
  blocks), cleared by `sync-update`. New `reference_state` table; the symbol-pair
  `sync_state` logic and the reason-masking/fixpoint invariant are untouched.
- **`docs_audit.ignore` config key (BDL-057).** Targeted suppression of false-positive fact
  matches in `.beadloom/config.yml` (`{path, fact, value}` triples) plus per-fact tolerances.
- The multi-agent development process is now documented bilingually at
  `docs/guides/multi-agent-development.md` (+ `.ru`), on the VitePress portal.

### Changed
- **Positioning (BDL-056).** README (en/ru) rewritten to "the source of truth about your
  code — its architecture, contracts, and documentation," with a single Gate enforcing it
  the same way for people and agents.
- **Writing-quality standard** added to the CORE tech-writer role, so documentation quality
  is reproducible by the agent rather than ad hoc.
- The 11 remaining skeleton SPECs are filled with code-accurate prose.
- Doc fixes: `getting-started` drops the non-existent `--non-interactive` flag; the
  architecture domain count is corrected; `CONTRIBUTING` gains a release-process section.

### Removed
- The generated VitePress `site/` content tree is **no longer committed** — it is regenerated
  by CI and the deploy workflow (`beadloom docs site`). Only the hand-authored shell
  (`.vitepress/config.mjs`, `.vitepress/theme/**`, `package*.json`) stays tracked.
- The accidentally-committed team presentation deck (`docs/presentations/`).

Backward-compatible (MINOR): repositories without `watches` annotations and with
audit-clean docs are unaffected; `reference_state` ships with a migration guard.

## [2.0.0] - 2026-06-14

**Beadloom 2.0 — the self-governing, configurable, tool-agnostic agentic dev loop.**
A major release consolidating BDL-049/050/051/053/052. Headline: Beadloom now
applies its own architecture-as-code thesis to itself (no shadow code, no stale
docs — enforced by deterministic gates), and the packaged multi-agent flow is
configurable per stack/architecture/tool (Claude Code + Cursor).

**Breaking changes (why MAJOR):**
- The AI tech-writer harness moved `tools.ai_techwriter` → `beadloom.ai_agents.ai_techwriter`
  (invoke `python -m beadloom.ai_agents.ai_techwriter`); the BDL-047/048 Python
  vendoring in `setup-ai-techwriter` is retired (harness ships in the wheel).
- `module-coverage` lint promoted to `severity: error` — a repo with an
  unclassified `src` module now fails `beadloom ci` (previously a warning).
- `setup-agentic-flow` role files are now composer-owned (generated from
  `.beadloom/flow.yml`); hand-edits are recomposed.

Phase "Usable doc-flow + role configurator" (BDL-052): makes the packaged
multi-agent flow **tool- and stack-agnostic** and adds a **local-primary**
enforcement layer. (S1) a blocking **pre-push Beadloom Gate** hook runs the full
`beadloom ci` on every push and blocks on red (`git push --no-verify` is the
documented escape hatch), with the coordinator Gate-loop + explicit parallelism.
(S2) restored + modernized the CORE `dev`/`test`/`review`/`tech-writer` role
protocols. (S3) the **role configurator**: a repo declares `.beadloom/flow.yml`
(`architecture: ddd|fsd` + `stack` + `tools` + `quality`) and Beadloom **composes**
each role from CORE + the selected architecture overlay + stack overlays, then
writes a per-tool **adapter set** — `.claude/agents/*` for Claude Code and
`.cursor/agents/*` (+ a Cursor orchestrator pointer) for Cursor — at parity;
`config-check` byte-guards every composed adapter against `compose_role(...)`.
(S4) **symbol-level scope** for the AI tech-writer: a changed file no longer
fans out to every linked doc — a doc is rewritten only when it references a
symbol whose body changed (unioning new-side edits AND old-side removed/renamed
defs so a doc naming a deleted symbol is still KEPT), conservative when
attribution is unavailable. (S5) the CI `ai-techwriter` job runs per-doc repair
in a **bounded parallel session pool** (`HarnessConfig.max_parallel`, default 3)
with per-session 429/5xx **exponential back-off** and a uv-dependency + Beadloom-
index **cache** (behaviour unchanged vs sequential; folded in stale order so the
verdict is identical). (S6) `beadloom active-sync --stage` (restage the touched
files). Result: local authoring is tool-agnostic and Gate-enforced, CI is the
fallback/true enforcement, and the same canonical flow runs on Claude Code +
Cursor.

### Added (BDL-052)
- **Pre-push Beadloom Gate** — `beadloom install-hooks --pre-push` installs a hook that runs `beadloom ci` (reindex → `lint --strict` → sync-check → config-check → doctor) and blocks the push on red; fail-safe (no-op without `beadloom` on `PATH`); `git push --no-verify` overrides
- **`.beadloom/flow.yml` + `flow_config.py`** — `FlowConfig` (frozen) + `build_flow_config` / `load_flow_config` / `load_flow_config_or_default` / `resolve_flow_config` (flag → flow.yml → default) + `detect_stack`; strict validation naming the bad value + allowed set (`FlowConfigError`). Supported: tools `claude`/`cursor`; architecture `ddd`/`fsd` (exactly one); stack `python`/`fastapi`/`javascript`/`typescript`/`vuejs`
- **`role_composer.py`** — `compose_role(role, *, architecture, stack)` = CORE + one architecture overlay + sorted stack overlays (byte-deterministic); `compose_all_roles`; FSD at parity with DDD
- **`role_adapters.py`** — `generate_adapters(config, project_root)` writes the per-tool adapter set(s) (`claude` → `.claude/agents/*`; `cursor` → `.cursor/agents/*` + `.cursor/rules/beadloom-flow.md`); the single writer the drift-guard verifies against
- **`beadloom setup-agentic-flow --tool/--architecture/--stack`** — compose + write the configured adapters (defaults `claude`/`ddd`/auto-detected); `config-check`/`--fix` validate `flow.yml` and recompose drifted adapters (`_composed_adapter_drifts` / `refresh_composed_adapters`)
- **AI tech-writer symbol scope** (`ai_techwriter/symbol_scope.py`) — narrows the stale set to docs that reference a changed symbol (git hunks ∩ Python `def`/`class` ranges, both diff sides); an empty intersection drops AND baselines the pair so `sync-check` still reaches 0
- **AI tech-writer bounded parallel + back-off** (`ai_techwriter/runner.py` pool keyed on `HarnessConfig.max_parallel` default 3; `ai_techwriter/backoff.py` `RateLimitError`/`retry_with_backoff`) + CI uv-dep + index caches
- **`beadloom active-sync --stage`** — restage the touched `ACTIVE.md` + `.beads/issues.jsonl`

### Known limitations (BDL-052)
- **Orphaned adapters not drift-guarded.** `config-check`'s composed-adapter check iterates only the tools named in `.beadloom/flow.yml`. If a tool is dropped from a narrowed `flow.yml`, the previously-scaffolded adapter set (e.g. `.cursor/agents/*`) is left un-checked and un-recomposed. A follow-up bead tracks an orphaned-adapter lint; until then, remove a dropped tool's adapter directory by hand.

Phase "Tracker / ACTIVE coherence hook" (BDL-053): makes each epic's `ACTIVE.md`
bead-status table **correct by construction** instead of by coordinator
discipline. New `beadloom active-sync` reconciles every epic's table FROM `bd`
(the source of truth) — rewriting each Status cell to match the bead's `bd`
status while preserving a richer coordinator note when its state agrees — and
re-exports the tracked `.beads/issues.jsonl`. It is wired into the pre-commit hook
(both `warn` and `block` templates) as a **guarded auto-fix step** that restages
the touched `ACTIVE.md` + jsonl so every commit is coherent. The reconcile core
(`application/active_table.py`) is the SAME tolerant, fail-safe parser the MCP S4
`checkpoint` / `complete_bead` tools use for single-row updates. **Safe no-op by
construction:** with no `ACTIVE.md` table, no `bd`, or an untracked jsonl, the
command (and the hook step) exits 0 and changes nothing — so it works
out-of-the-box for every adopter and never blocks a commit.

### Added (BDL-053)
- **`beadloom active-sync`** (`services/cli.py`) — reconcile each epic's ACTIVE.md bead-status table from `bd`. `--epic KEY` scopes to one epic; `--check` reports drift on a throwaway copy without writing (exit 1 on drift, 0 clean); `--json` emits `{changed_files, drifted_rows[{path,bead_id,old,new}]}`; `--no-export` skips the jsonl sync. Default (fix) mode rewrites drifted Status cells and best-effort runs `bd export -o .beads/issues.jsonl` (only when that file is git-tracked). No-op contract: no ACTIVE table / no `bd` / untracked jsonl → exit 0, zero behavior change
- **`application/active_table.py` reconcile core** — `reconcile_active_tables(project_root, bd_statuses, *, epic=None)` (pure with respect to `bd`: the caller injects the status map) returns a `ReconcileResult` (`changed_files`, `drifted_rows`); `bd_status_to_cell` documents the `bd`-status → Status-cell map (`closed → ✓ done`, `in_progress → in progress`, `blocked → blocked`, `open`/`ready → ready`; unknown → `None`). Classified as the new `active-table` **component** node with its own DOC.md
- **Pre-commit hook ACTIVE / tracker coherence step** — both `install-hooks` templates (`warn` and `block`) gained a guarded final step that runs `beadloom active-sync` and restages `.claude/development/docs/features/**` + `.beads/issues.jsonl` only when both `bd` and `beadloom` are installed. Never blocks the commit; a complete no-op in any repo without `bd`/ACTIVE

Phase "Beadloom governs itself" (BDL-051): closes the graph-discipline gap so
Beadloom's own architecture is **honest-by-construction**. Three threads land
together: (1) a new **`component` node kind** — an internal/infra building block
that earns a node + a `DOC.md` (the mirror of a `feature`'s `SPEC.md`), attributed
in code with `# beadloom:component=<id>`; (2) a **`module-coverage` lint** promoted
to **`severity: error`** (it supersedes the advisory `unregistered-feature-candidate`
sprawl-lint): every `src/beadloom/**.py` module with ≥1 symbol is either a tracked
node (feature/component, or under a node's `source` — incl. a **directory** source
like `tui/`) or named on a minimal, **visible** `exempt:` list in `rules.yml` —
**no shadow code**, and a new untracked module now **fails `beadloom ci`**; (3) the
AI tech-writer harness moved out of `tools/` into a first-class
**`ai_agents/ai_techwriter` domain** shipped inside the wheel (adopters run
`python -m beadloom.ai_agents.ai_techwriter` — **no Python vendoring**). ALL src
modules were classified (**21 new feature/component nodes** + the seeded exempt
list). The MCP `checkpoint` / `complete_bead` process-tools now **maintain the
`ACTIVE.md` status table** correct-by-construction. **Honest framing:** the lint is
the enforcement; this epic dogfooded the whole model on Beadloom itself.

### Added (BDL-051)
- **`component` node kind** — a tracked internal/infra building block with a `part_of` edge to its domain, a `source: <file>`, and a `docs: <DOC.md>`; attributed via `# beadloom:component=<id>` (the mirror of `# beadloom:feature=`). 10 component nodes: `graph/{loader,contracts,sdl}`, `context-oracle/context-builder`, `doc-sync/doc-indexer`, `infrastructure/{db,health,git-activity,mcp-tools}`, `services/bd-seam` (BDL-051 / S3a/S3b)
- **`ai_agents/ai_techwriter` domain** — the deterministic, seam-isolated PR-triggered doc-refresh harness, moved from the retired `tools/ai_techwriter` repo-tooling package INTO the installed `beadloom` package (graph-tracked, lint-governed, shipped in the wheel). Behaviour is the BDL-049/050 model byte-unchanged; adopters invoke `python -m beadloom.ai_agents.ai_techwriter`. A `core-no-import-ai-agents` / `application-no-import-ai-agents` `forbid_import` pair keeps it a **leaf consumer** (BDL-051 / S2)
- **11 feature `SPEC.md` + 10 component `DOC.md`** filled — the newly-classified capabilities (`site-generation`, `ci-gate`, `code-indexer`, `route-extraction`, `test-mapping`, `sync-check`, `snapshot`, `config-check`, `branch-protection`, `agentic-flow-setup`, `ai-techwriter-setup`, `ai-techwriter`) and the component docs (BDL-051 / S3b + the docs wave)

### Changed (BDL-051)
- **`module-coverage` lint is now `severity: error`** (was `warn`) — with every src module classified, a new untracked module fails `beadloom lint --strict` / `beadloom ci`. It supersedes the older `unregistered-feature-candidate` advisory sprawl-lint with a whole-tree check; a node's `source` may be a **directory** (dir-source coverage — the `tui` service covers all of `src/beadloom/tui/`) (BDL-051 / S3a)
- **No Python vendoring in `setup-ai-techwriter`** — the scaffold no longer copies harness Python into a target repo (the BDL-047/048 `HARNESS_MODULES` / `vendor_harness` / `sync_vendored_harness` drift-guard machinery is retired); it emits only the CI wrapper (invoking the packaged module) + the operator artifacts (`recipe.yaml` / `provision-runner.sh`, copied from package data) (BDL-051 / S2)
- **MCP `checkpoint` / `complete_bead` maintain the `ACTIVE.md` status table** — the process-tools update the bead-status table + progress log in `ACTIVE.md` correct-by-construction, not just `bd` comments (BDL-051 / S4)
- **Docs** — the architecture-model guide gained the directory-`source` coverage note + the corrected feature/component example (`code-indexer` is a feature); domain READMEs now index their features + components; the AI tech-writer guide + `services/cli.md` reference the packaged `beadloom.ai_agents.ai_techwriter` module (no `tools.ai_techwriter`) (BDL-051 docs wave)

Phase "CI consolidation" (BDL-050): replaces the three independent PR workflows
(`beadloom-gate.yml` / `tests.yml` / `ai-techwriter.yml`) with **one
`.github/workflows/ci.yml`** on `pull_request → main`. Jobs `gate` ∥ `tests`
(3.10–3.13 matrix) ∥ `site-build` (VitePress build) run in parallel; `ai-techwriter`
has **`needs: [gate, tests, site-build]`** so it runs only when all three are green —
**a broken PR never spends Qwen tokens**. The AI tech-writer harness now classifies
each run into a **verdict** `{ok, flagged, infra}` (discriminator: `tokens > 0`): a
genuine unresolved doc drift (`flagged`) blocks the PR (exit 1), but an **infra
failure** (`infra` — a dead self-hosted runner, an exhausted `$30` quota, a provider
5xx; `tokens == 0`) PASSES (exit 0) with a loud `::warning::` + a best-effort PR
comment, so dead infra never freezes merges. `tests` dropped its `paths:` filter (so
every leg runs on every PR and is a reliable required check); `site-build` is now a PR
check (a VitePress/mermaid/interpolation break is caught **before** it lands on
`main`); the redundant `push: main` gate/tests runs were removed (`main` is green by
construction under strict trunk-based — `deploy-site.yml` is the only `push: main`
job). All workflow actions are Node24-compatible. Branch protection now requires the
**7 consolidated check-runs**. GitLab mirrors the structure via stages
`verify → docs` with the same `needs`. **Honest framing:** still no auto-merge — a
human merges; CI on the PR is the true enforcement; the agent's refresh is a proposal.

### Added (BDL-050)
- **Consolidated `.github/workflows/ci.yml`** — one `on: pull_request → [main, master]` (+ `workflow_dispatch`) pipeline with jobs `gate` (the `beadloom-gate` composite Action) ∥ `tests` (3.10–3.13 matrix) ∥ `site-build` (`beadloom docs site` + `npm run docs:build`) → `ai-techwriter` (`needs: [gate, tests, site-build]`, self-hosted). `concurrency: ci-${{ github.event.pull_request.number || github.ref }}` with `cancel-in-progress: true`. The `ai-techwriter` job body is the BDL-049 model verbatim (loop-guard, `--since merge-base`, `--target pr-branch`, `AI_TW_PAT` push, PR comment) — only the trigger moved into `ci.yml` and the exit code is now verdict-driven (BDL-050 G1/G7)
- **AI tech-writer verdict `{ok, flagged, infra}`** (`tools/ai_techwriter/runner.py::classify_verdict` + `cli.py::_report`) — the discriminator between a doc problem and an infra failure is whether the model produced output (`input_tokens + output_tokens > 0`). `ok` (no-op / clean) and `infra` (`tokens == 0` — process/provider error, 5xx, exhausted quota) → exit 0; `flagged` (`tokens > 0` but docs still dirty: post-refresh `beadloom ci` red / fixpoint not reached / budget exceeded) → exit 1 (the required check goes red). On `infra` the entrypoint also emits a GitHub `::warning::` annotation + a best-effort PR/MR comment so a skipped check is visible. A dead runner / exhausted `$30` quota never freezes merges; a real unresolved doc drift does (BDL-050 G1 / RFC Q1)

### Changed (BDL-050)
- **Required status checks = the 7 consolidated `ci.yml` check-runs.** `onboarding/branch_protection.py::DEFAULT_STATUS_CHECK_CONTEXTS` is now `("gate", "tests (3.10)", "tests (3.11)", "tests (3.12)", "tests (3.13)", "site-build", "ai-techwriter")` (was the single `beadloom-gate`). `enforce_admins: true` + 0 required reviews kept (strict trunk-based; owner self-merges). Re-apply with `beadloom setup-branch-protection` (BDL-050 G2/G4)
- **`tests` un-filtered + required.** The 3.10–3.13 matrix lost its `paths:` filter and runs on every PR, so each leg can be a strict required check without stalling. `push: main` gate/tests runs were removed — `deploy-site.yml` is the ONLY `push: main` job (BDL-050 G2/G5)
- **`site-build` is a PR check** (closes `beadloom-wozp`) — the VitePress build (the BUILD half of `deploy-site`, no Pages deploy) runs on every PR, catching VitePress/mermaid/dead-link/interpolation breaks before they reach `main` (BDL-050 G3)
- **Node24-compatible actions** (closes `beadloom-t7vn`) — `actions/checkout@v5`, `astral-sh/setup-uv@v6`, `actions/setup-node@v5`, `node-version: 22` across the workflows; `deploy-site.yml` opts the whole workflow into the Node24 runtime via `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` as a documented stopgap until `configure-pages` / `upload-pages-artifact` / `deploy-pages` publish Node24 majors — avoids the 2026-06-16 Node20 deprecation (BDL-050 G6)
- **GitLab mirror** — `.gitlab-ci.yml` now consolidates into stages `verify` (`gate` ∥ `tests` ∥ `site-build`) → `docs` (`ai-techwriter` with `needs: [gate, tests, site-build]`), gated on `$CI_PIPELINE_SOURCE == "merge_request_event"`, with the same `AI_TW_PAT` push + verdict exit handling (no `allow_failure` — the verdict IS the gate). Vendored CI templates re-vendored to match (drift-guard green) (BDL-050 G7)
- **Docs** — the AI tech-writer guide (`docs/guides/ai-techwriter.md`) and the agentic-flow guide (`docs/guides/agentic-flow.md`) now describe the consolidated `ci.yml` (needs-ordering), the verdict semantics, and the 7-check branch protection; the team-facing `BDL-AI-AGENTS-ARCHITECTURE.md` was refreshed end-to-end (PR-triggered consolidated model + diagrams) (BDL-050 G8)

Phase "Trunk-based + PR-triggered AI tech-writer" (BDL-049): moves the AI
tech-writer from an `on: push` to `main` trigger to **`on: pull_request` → `main`**,
and the whole dev flow to **trunk-based development**. The agent now runs **once per
PR** against a clean `--since $(git merge-base origin/<base> HEAD)` baseline and
**commits its doc refresh back onto the PR head branch** (`--target pr-branch`,
message `[skip ai-techwriter] …`) + posts a PR comment — code and its doc updates
review and merge in one PR; no orphan doc-PRs. A **loop-guard** (bot author /
`[skip ai-techwriter]` subject → the workflow's `AI_TW_SKIP` early-skip step) stops
the agent's own push from re-triggering the `synchronize` event, and
`cancel-in-progress: true` cancels a superseded in-flight run. GitLab mirrors the
model via `merge_request_event`. This fixes the redundant 1h/768K-token re-refreshes,
the red-`main` window, and the orphan-doc-PR pile-up seen during BDL-047/048.
**Honest framing (not overclaimed):** no auto-merge — a human merges the PR; CI on
the PR (`beadloom-gate` as a **required check** via the new
`beadloom setup-branch-protection`) is the true enforcement; the agent's refresh is a
proposal in the PR.

### Added (BDL-049)
- **`beadloom setup-branch-protection --repo OWNER/NAME [--branch] [--check] [--dry-run]`** — idempotent `main` (or `--branch`) branch protection via `gh api` (declarative `PUT .../protection`): a PR is required (no direct push), the always-on `beadloom-gate` check is a **required status check** (`strict: true`), `enforce_admins: false` + 0 required reviews + `restrictions: null` so the solo owner is never locked out (can self-merge). `--check` (repeatable) overrides the default required-check context entirely; it must match a **real** GitHub check-run name and must NOT be a path-filtered workflow's check (it would not run on every PR → stuck PRs under `strict`). `--dry-run` prints the exact `gh api` call + JSON payload without touching GitHub. New module `onboarding/branch_protection.py` (`build_protection_payload`, `BranchProtectionRequest`, `apply_branch_protection`; injectable `GhRunner` seam for mockable tests) (BDL-049 G6)
- **`--target {branch-pr,pr-branch}` on the AI tech-writer harness** (`tools/ai_techwriter`) — `pr-branch` (the `on: pull_request` path) commits the refresh **onto the existing PR head branch** + posts a PR/MR comment (`GitHubPRBranchPublisher` / `GitLabPRBranchPublisher`), resolving the PR/MR from the CI env; `branch-pr` (the default, for manual `workflow_dispatch` with no PR context) keeps the original branch-cutting + open-PR behaviour (BDL-049 G4)

### Changed (BDL-049)
- **AI tech-writer triggers on `pull_request` to `main`/`master`, not `push`.** `.github/workflows/ai-techwriter.yml` now fires on `pull_request` (`opened`, `synchronize`, `reopened`); the `push: branches:[main]` trigger is removed. `--since` is `git merge-base origin/$BASE_REF HEAD` (fallback: the PR base SHA) — exactly "what this PR changed" — replacing `--since github.event.before`. A **loop-guard** step skips the run (`AI_TW_SKIP=1`) when the PR head commit's author is `beadloom-ai-techwriter` OR its subject contains `[skip ai-techwriter]`. `concurrency` now sets `cancel-in-progress: true` (a new commit cancels the older in-flight run for that PR). `workflow_dispatch` is kept as a manual fallback and uses the `--target branch-pr` path (BDL-049 G2/G3/G5/G8)
- **GitLab CI mirrors the model** — the `ai-techwriter` job in `.gitlab-ci.yml` now runs on `rules: $CI_PIPELINE_SOURCE == "merge_request_event"`, computes `--since` from `git merge-base origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME HEAD` (fallback `$CI_MERGE_REQUEST_DIFF_BASE_SHA`), publishes `--target pr-branch` onto `$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME`, and applies the same loop-guard. The vendored CI templates (`onboarding/templates/ai_techwriter/{github-workflow,gitlab-ci-job}.yml`) mirror both platforms (BDL-049 G7)
- **Vendored coordinator flow is now trunk-based** — `CLAUDE.md` §6 (Git) and the vendored `.claude/commands/coordinator.md` describe feature-branch + one PR to `main` + merge-when-green, re-vendored so the BDL-048 drift-guard stays green and `setup-agentic-flow` scaffolds the trunk-based flow into any repo (BDL-049 G1)
- **Docs** — the AI tech-writer guide (`docs/guides/ai-techwriter.md`) and the agentic-flow guide (`docs/guides/agentic-flow.md`) now describe the PR-triggered / trunk-based model (merge-base `--since`, `--target pr-branch`, loop-guard, `cancel-in-progress`, `workflow_dispatch` fallback, GitLab MR mirror, `setup-branch-protection`) (BDL-049 G10)

Phase "Agentic-flow packaging" (BDL-048): packages Beadloom's proven solo
multi-agent dev flow into the product. One command (`beadloom setup-agentic-flow`)
scaffolds the flow into any repo — the role subagents + slash skills vendored
**byte-identical** to Beadloom's own live `.claude/` (drift-guarded), with the
`CLAUDE.md` auto-regions generated per-project — and `config-check` now
drift-checks (and `--fix` restores) those scaffolded flow files. Four MCP
**process-tools** (`task_init` / `bead_context` / `complete_bead` / `checkpoint`)
make the flow's deterministic steps callable from ANY MCP client; the MCP catalog
is now **18 tools**. **Honest boundary (not overclaimed):** MCP serves
deterministic process-tools, NOT orchestration — the coordinator + Agent-spawn
stay Claude-Code-native/harness; `complete_bead` is advisory-strong; the single
source of TRUE enforcement remains `beadloom ci` in CI. Additive — no schema bump.

### Added (BDL-048)
- **`beadloom setup-agentic-flow [--project DIR] [--force]`** — one-command, idempotent scaffold of the packaged multi-agent dev flow into a repo (in the `setup-*` family). Drops `.claude/agents/{dev,test,review,tech-writer}.md` + `.claude/commands/{coordinator,task-init,checkpoint,templates}.md` **vendored byte-identical** from package-data assets (drift-guarded against the live `.claude/`), plus a `.claude/CLAUDE.md` whose auto-regions are generated for THIS project (name / stack / version — version from Beadloom's `__version__`) via the existing `refresh_claude_md` machinery. A matching file is left alone, a hand-edited file is skipped (reported as such) unless `--force`; user prose outside the CLAUDE.md auto-regions is never touched. New module `onboarding/agentic_flow_setup.py` (`scaffold()` + `sync_agentic_flow()` drift guard) (BDL-048 G1)
- **`config-check` covers the scaffolded flow** — when a repo has the agentic flow scaffolded, `config-check` byte-compares each vendored `agents/*` + `commands/*` file against the shipped template, and `--fix` re-drops them (`config_sync.refresh_agentic_flow_files`, gated on the flow already being present — never forced onto a repo that did not adopt it) alongside refreshing the CLAUDE.md auto-regions (BDL-048 G1)
- **Four MCP process-tools** on `services/mcp_server.py` (catalog 14 → 18) — deterministic, refusable operations over the substrate, callable from any MCP client (tool-agnostic via `setup-mcp`). They do NOT orchestrate or spawn sub-agents:
  - **`task_init(type, key)`** — scaffold the docs folder + per-type skeletons (PRD/RFC/CONTEXT/PLAN/ACTIVE or BRIEF/ACTIVE) + a valid 4-role bead DAG (dev → test → review → tech-writer) via `bd`.
  - **`bead_context(bead)`** — ONE payload: `ctx` + `why` + a CONTEXT.md/ACTIVE.md excerpt + the active architecture rules for the bead's area (resolves the bead's graph ref from `bd show`); read-only.
  - **`complete_bead(bead, run_tests=true)`** — the **refusing gate**: runs `beadloom ci` (reindex → lint → sync-check → config-check → doctor, via `application/gate.run_ci_gate`) + the test suite; **on PASS** closes the bead (`bd close --suggest-next`), **on FAIL REFUSES to close** and returns the findings. Advisory-strong, not the true enforcement point.
  - **`checkpoint(bead, text)`** — `bd comments add` + a best-effort timestamped ACTIVE.md note.
- **`services/bd_seam.py`** — a thin, mockable wrapper over the `bd` (beads) CLI (`run_bd()` → `BdResult`; `BdUnavailableError` with a clear message when `bd` is absent), so the bead-touching process-tools are testable without a real `bd` binary (BDL-048)
- **Getting-started guide** `docs/guides/agentic-flow.md` — the packaged flow, `setup-agentic-flow` (scaffold / idempotency / `config-check --fix`), the four process-tools (and that `complete_bead` refuses red), the tool-agnostic angle, and the honest boundary (orchestration stays in the harness; CI is the true enforcement) (BDL-048 G7)

Phase F4.1 "AI tech-writer in CI" (BDL-047): closes the DocAsCode loop at the *fix*
step. Beadloom already detects doc drift honestly; F4.1 adds automated remediation —
on push to `main`/`master`, a deterministic, platform-agnostic harness
(`tools/ai_techwriter/`) drives a **Goose** agent + **Qwen3.7-Plus** (external API)
to rewrite ONLY the drifted docs, verifies freshness to a fixpoint, runs
`beadloom ci`, and opens a **PR/MR for human review** (never auto-merges; flagged
"⚠ needs human" if the gate is not green). Runs on a self-hosted VPS runner where
the API key + Goose live; dual-platform (GitHub Actions + GitLab CI), first-class.
Dogfood-proven on the real VPS runner (refresh PR merged). Honesty preserved:
`sync-check → 0` proves *freshness*, the human PR review proves *correctness*. Only
two additive core changes (a non-interactive `sync-update` and a `sync-check --since`
primitive) + one new `setup-*` command; no schema bump.

### Added (BDL-047 / F4.1)
- **`beadloom sync-check --since <git-ref>`** — measures doc-code drift against the code state at a **git ref** (e.g. the push's parent) instead of the stored `sync_state` baseline. Reports pairs whose code drifted since the ref while the doc was not correspondingly updated. Makes drift detection survive a **fresh CI checkout** (a clean clone re-baselines `sync_state` to the just-pushed code, masking per-push drift). Mirrors `diff --since`; rejects invalid/all-zero refs. New engine fn `doc_sync/engine.check_sync_since` (reads `git show <ref>:<path>` + disk only; mutates nothing) (BDL-047 G12)
- **`beadloom sync-update [REF] --yes [--all]`** — a **non-interactive** re-baseline (no editor/prompt): records that the doc(s) match the code now (recompute hashes/symbols, `status='ok'`). `--all` (with `--yes`) re-baselines every currently-stale ref in one call — the primitive a CI fixpoint loop needs. Wraps the existing `mark_synced_by_ref`. Closes UX #106 (BDL-047 W1)
- **`beadloom setup-ai-techwriter --platform {github,gitlab}`** — one-command, idempotent opt-in (in the `setup-*` family). **Vendors** the deterministic harness package + Goose recipe into `tools/ai_techwriter/` (self-contained — the runner needs only `beadloom` + `goose` + python), drops the chosen platform's CI wrapper, a hardened `provision-runner.sh`, and the getting-started guide `docs/guides/ai-techwriter.md`. The harness is shipped as drift-guarded package data (inert `.py.txt` assets kept byte-identical to the live source) (BDL-047 G8/G11)
- **The deterministic harness** (`tools/ai_techwriter/`, repo tooling, not the wheel): discover scope from `sync-check --json --since` → per-doc context packet (`docs polish --format json` + `ctx`/`why`) → Goose rewrite → `sync-update --yes` → fixpoint re-check (per-doc retry ≤2, fixpoint rounds ≤10, hard caps 50 turns / 2M tokens) → `beadloom ci` gate → branch + PR/MR via a per-platform adapter (`gh` / `glab`). Entrypoint `python -m tools.ai_techwriter --platform {github,gitlab} --since <ref> [--dry-run]`. Goose never decides scope, marks synced, or merges (BDL-047 W2/W3)
- **Both CI wrappers trigger on push to main/master** (+ manual dispatch): `.github/workflows/ai-techwriter.yml` and the `ai-techwriter` job in `.gitlab-ci.yml` call the SAME entrypoint; only the trigger, secret naming (`QWEN_API_KEY` repo secret / CI/CD variable; optional `QWEN_BASE_URL`), and `--platform` differ. The push parent (`github.event.before` / `$CI_COMMIT_BEFORE_SHA`, fallback `HEAD~1`) feeds `--since`. Loop-safe: a human-merged refresh PR triggers a 0-stale no-op; `concurrency` serializes (BDL-047 G10)
- **`provision-runner.sh`** — a hardened, idempotent, executable self-hosted-runner provisioner (`--platform/--repo/--token`): guarantees swap **before** apt/build (the OOM lesson), RAM (~2 GB min, ~4 GB recommended) + disk (~5 GB) prechecks, fail-hard on the critical steps (toolchain + runner register/start), best-effort + verified Goose/beadloom/bd installs reported at the end (BDL-047 G11)
- **G9 dashboard widget "AI tech-writer activity"** — the harness appends an honest **run-record** per run to `.beadloom/ai_techwriter_runs.json` (`ts` stored not `now()`, platform, docs_refreshed, input/output tokens, model, gate, pr_url); the VitePress dashboard renders an `AiTechwriterActivity` widget (`site_dashboard.build_dashboard_data` `ai_techwriter` section): docs-refreshed + token spend per-run and cumulative, ONLY real recorded runs (no interpolation). **Tokens are fact** (from the API `usage`); the **dollar figure is a clearly-labeled estimate** ("est. @ $X/1M tokens"), never a hard cost. Absent/empty/corrupt store → empty-but-present section (BDL-047 G9)
- **Getting-started guide** `docs/guides/ai-techwriter.md` — the loop, the 3-step setup, both platforms, the on-push trigger, the honesty model, and the G9 widget (BDL-047 G7)

## [1.10.0] - 2026-06-02

**Federation + a living, navigable public portal.** This release adds cross-repo contract federation and a tool-agnostic CI gate (F1–F3), a generated VitePress knowledge-base portal with an interactive metrics dashboard, interactive architecture + cross-repo landscape map, and the published validated docs (F4/F4.4), and reshapes that portal into a navigable, bilingual (EN/RU) front door with the README as its landing page (BDL-046). Everything is additive — no breaking changes to the CLI/API or the graph schema.

Phase 0 "Foundation / Honesty Gate" (BDL-036): Beadloom now passes its own checks honestly.
Phase F1 "Federation Foundation" (BDL-037): cross-repo federation thin slice — `@repo:ref_id` identity, the `lifecycle` field, `beadloom export`, and `beadloom federate`, dogfooded on the real core-monolith ↔ integration-service RabbitMQ contract.
Phase F2 "Cross-Service Contract Graph" (BDL-038): a first-class cross-service contract graph — AMQP exchange identity + GraphQL SDL contracts, contract-level intent-vs-reality verdicts (incl. presence-based `BREAKING`), the `external`/`unmapped` lifecycle, nested product-vs-company landscapes, and paradigm-agnostic node/edge kinds.
Phase F3 "Tool-Agnostic Enforcement Everywhere" (BDL-039): the detection from F1/F2 gains teeth — a federated landscape gate (`federate --fail-on`), agent-actionable violation output, AgentConfigAsCode (`config-check`), a single `beadloom ci` gate, and a reusable composite GitHub Action + GitLab template, dogfooded on Beadloom's own CI. All additive — no schema/version bump.
Phase F4 "Living Knowledge Base + Visual Landscape" (BDL-040): a `beadloom docs site` VitePress generator with three showcases — an AaC/DocAsCode metrics dashboard, an interactive architecture + 🌟 cross-repo landscape map, and the published validated docs with per-doc `doc_sync` badges. Deterministic, honest-by-construction, and dogfooded by building Beadloom's own site with a real `vitepress build`. No schema bump.
GitHub Pages deploy (BDL-042): the VitePress site is published as a project page at `https://zoologov.github.io/beadloom/` — `base: "/beadloom/"` set, Mermaid `click` targets made base-aware at runtime (`DiagramViewer` prepends `import.meta.env.BASE_URL`; generated Markdown stays base-agnostic), and `.github/workflows/deploy-site.yml` regenerates + builds + deploys on every push to `main` (so the published page never drifts from the code).
Phase F4.4 "Site rendering fixes + dashboard UX" (BDL-041): hardens F4 — fixes the two F4 Mermaid render bugs and adds a generation-time validity guard (a broken diagram fails pytest, not the browser), pan/zoom/fullscreen on every diagram, a real interactive ECharts dashboard (critical-first alert banner + status cards, gauges, category charts, honest trends, recommendations — the verbose text dump removed), and a local contract-graph landscape with safe page-aware clicks. Dogfooded on Beadloom's own site (real `vitepress build` exit 0, render browser-confirmed). **F4 and F4.4 ship together** (a published broken diagram = a published lie). No schema bump.
Portal IA + bilingual About (BDL-046): reshapes the generated VitePress portal — About (the README) becomes the landing page, a single ordered EN sidebar replaces the old nav, the architecture overview moves to `/architecture`, the Documentation group gains a descriptive Overview, the top nav is removed, and About becomes bilingual (EN/RU) via an in-page toggle (VitePress `locales` was evaluated and dropped). Browser-confirmed on the deployed site. No schema bump.

### Added (BDL-046)
- **Portal navigation restructure** — the generated left sidebar is now a single ordered EN tree: About (`/`) · Getting Started (only if its page exists) · Dashboard (flat) · Architecture (collapsed, led by an "Architecture overview" → `/architecture`) · Landscape map (flat) · Documentation (expanded, led by an Overview). Dashboard and Landscape are flattened (the single-child "Metrics" / "Map" groups removed) (`application/site_nav.py` — `render_sidebar()`) (BDL-046 BEAD-02/BEAD-03)
- **About = README landing (EN `/`, RU `/ru/`)** — the home page is generated from `README.md` (and `README.ru.md`) by `application/site_about.render_about()`, which rebases repo-relative links so they resolve on the site (published `docs/<x>.md` → `/docs/<x>`; unpublished internal targets → absolute GitHub URL; external URLs / shields.io badges / anchors untouched; the badge-link `[![alt](img)](target)` idiom handled). The architecture overview that used to be the landing moves to `/architecture` (BDL-046 BEAD-01/BEAD-03)
- **Bilingual About via in-page toggle** — the README's `[Русский](README.ru.md)` / `[English](README.md)` line is rewritten to the counterpart route (`/` ↔ `/ru/`), so the language toggle appears only on About and never 404s elsewhere; the rest of the portal stays EN (`site._CROSS_LINK_ROUTES`) (BDL-046 BEAD-11)
- **Documentation Overview** — `docs/index.md` is now a short descriptive page (intro + a one-sentence description naming each section's members as text) instead of a flat link wall; the expanded Documentation sidebar is the navigable map (`application/site._render_docs_overview()`) (BDL-046 BEAD-03)
- **Top nav removed** — the top `nav` is empty (`render_nav()` → `[]`); the default theme still renders the appearance toggle + built-in search (BDL-046 BEAD-02)
- **Feature-SPEC tracking + neutral reference badge** — per-symbol `# beadloom:feature=<ref>` source annotations bind a file to a graph node (read by `doc_sync`'s `build_sync_state`) so a feature SPEC is freshness-checked rather than badged as untracked; a doc tied to no sync pair now shows the neutral **"📘 reference — overview/guide, not tied to a code symbol"** badge (reworded from "untracked", with no misleading coverage %) (`application/site_published.py`, `doc_sync/engine.py`) (BDL-046 BEAD-14)

### Changed (BDL-046)
- **Badge-link rebasing fix** — `render_about` now rewrites the README's README↔README cross-link to the counterpart About route instead of dropping it, and recurses the inner image of a `[![badge](img)](link)` so an absolute shields.io badge stays untouched while a relative inner target is still rebased (BDL-046 BEAD-01/BEAD-11)
- **VitePress `locales` evaluated and dropped** — the original plan used VitePress i18n for the language switch; live dogfood proved it the wrong tool for curated About-only (its global `/x ↔ /ru/x` mapping translated the whole menu and 404'd off `/ru/`), so `locales` / `navRu` / `sidebarRu` were removed in favour of the in-page About toggle (BDL-046 BEAD-11)

### Added (F4)
- **`beadloom docs site [--out DIR] [--federated FILE]`** — generates a VitePress knowledge-base content tree from the indexed graph (read-only), under `--out` (default `site/`); never writes into the source `docs/`. Emits an architecture overview, one page per node, the three showcases below, and `.vitepress/config.generated.mjs` (nav/sidebar). Output is deterministic (sorted, stable frontmatter, no wall-clock in the diffed tree). **Beadloom produces, VitePress renders** — no live server, no LLM (`application/site.py` + `site_pages.py`) (BDL-040 BEAD-01)
- **Showcase A — AaC/DocAsCode metrics dashboard** (`dashboard.md` + `dashboard.data.json`): lint count + severity, debt score + trend, doc coverage / `sync-check` freshness / stale count, the `doctor` summary, and an optional federated rollup. **Honest by construction** — every figure comes from the SAME code path as its gate (`graph/linter.lint` / `debt_report` / `doc_sync` `sync_state` / `doctor.run_checks` / the `federate` output verbatim); the page never invents a number (`application/site_dashboard.py`) (BDL-040 BEAD-02)
- **Showcase B — 🌟 cross-repo landscape map** (`landscape.md`): the F2 federated contract graph rendered as a clickable **Mermaid** diagram — satellites as nodes, contract edges carrying the hub's verdict verbatim, edges labelled by verdict, a `classDef` health overlay (green/red/grey), broken edges red, nodes clickable to their intra-repo page. With `--federated` it reads a `federate` hub artifact; without it the map degenerates to the local graph. Thin slice = Mermaid only (Cytoscape/D3 is a follow-up; no schema bump) (`application/site_landscape.py`) (BDL-040 BEAD-03)
- **Showcase C — published validated docs** (`docs/**` + `docs/index.md`): the REAL `docs/` tree copied verbatim (the source of truth, rendered as-is) with a per-doc validation badge injected into the COPY only — the source `docs/` is **NEVER mutated** (no AI prose-rewriting; that is the deferred F4.1). The badge status comes from `doc_sync`'s `check_sync` — the SAME path `beadloom sync-check` runs — and shows `fresh` / `stale — <reason>` / `untracked`, the stored `last synced` (deterministic), and the node's source-coverage %; marker-delimited so regeneration overwrites only the badge region (`application/site_published.py`) (BDL-040 BEAD-04)
- **Committed VitePress scaffold** (`site/package.json`, `site/.vitepress/config.mjs`) renders the generated tree; build output + `node_modules` are gitignored. Build with `cd site && npm install && npm run docs:build`; preview with `npm run docs:preview`. See `docs/guides/vitepress-site.md` (BDL-040 BEAD-01/BEAD-05)
- **Dogfood proof (F4)** — built Beadloom's own site end-to-end (`vitepress build` exit 0). The real build surfaced and fixed two genuine generator bugs invisible to unit tests — `.DS_Store` pollution copied into the published tree, and 24 dead intra-site links — validating the honesty principle: only a real build proves the produced tree renders (BDL-040 BEAD-05)
- **F4.1 deferred (next follow-up epic)** — the AI tech-writer in CI (orchestrating an *external* model to refresh drifted docs, scoped by `sync-check` / `docs polish --json`, with team review on a PR) is intentionally NOT in this release. The published-docs showcase computes badges, it does not rewrite prose.

### Added (F4.4)
- **Mermaid render correctness + generation-time guard** — the two F4 diagram bugs that rendered broken in the browser are fixed at the source: landscape node ids are **prefixed** (`n_<sanitized>`) so a node named `graph` can never collide with the `graph LR` keyword (the "got GRAPH" crash), and C4 emits a `Rel(a, b)` only between **declared** diagram nodes (dropping — and logging — Rels to the undrawable `System` root that crashed `drawRels`; the relationship still lives in the graph + the landscape). A new generation-time guard (`application/site_mermaid_guard.validate_mermaid`) runs targeted structural validators over every emitted diagram and raises `MermaidValidationError` at generation/pytest time on a reserved-id/charset or undeclared-C4-Rel issue — **closing the "build green ≠ renders ok" gap** so a broken page fails the build, not the browser (BDL-041 BEAD-01)
- **Pan / zoom / fullscreen diagrams** — a global `DiagramViewer` theme component attaches pan + wheel-zoom + reset (`svg-pan-zoom`) and a Fullscreen toggle to every rendered Mermaid SVG (re-scanning on route change since Mermaid renders async); SSR-safe and gracefully static when JS is off (BDL-041 BEAD-02)
- **Interactive ECharts dashboard** — `dashboard.md` is now a thin page (title + intro + component mounts) backed by `dashboard.data.json`; committed Vue/ECharts widgets render it client-side: a **critical-first** `AlertBanner` + `StatusCards` (severity computed deterministically in Python — BREAKING leads; an empty alert list = all-clear), `HealthGauges`, `CategoryChart`, `TrendCharts`, and a `Recommendations` panel. **Honest trends** come only from real recorded points in an additive `.beadloom/metrics_history.json` append-log (seeded day-one from `graph_snapshots`) — sparse at first, no interpolation, timestamps stored not `now()` — and `recommendations` are built from the EXISTING gate data (lint / BREAKING-DRIFT contracts / stale docs / worst-debt), severity-ordered and deterministic. The verbose per-metric **text dump was removed** (no `<noscript>` fallback) — the widgets are the single presentation surface; data honesty lives in `dashboard.data.json` (`application/site_dashboard.py` + `site_metrics_history.py`) (BDL-041 BEAD-03/BEAD-04/BEAD-12)
- **Local contract-graph landscape + safe clicks** — without `--federated`, `landscape.md` is now the repo's **own contract graph**: it reconciles the local `produces`/`consumes` edges by `contract_key` into `Contract`s, classifies each to a `ContractVerdict`, and renders one verdict-coloured edge per producer→consumer (Beadloom's own site — which now models a real `beadloom --produces--> vitepress-site` / `vitepress-site --consumes--> beadloom` contract in its graph — renders a single `beadloom → vitepress-site` **CONFIRMED** edge; a repo with no contracts → an empty map). Clicks are **page-aware** (`existing_page_urls`): a node links to `/<dir>/<ref>` only when a page was actually generated for it, so a `site` node or a foreign federated repo renders without a click — killing the dead-link 404/MIME bug. `--federated` still renders the cross-repo hub map (BDL-041 BEAD-09)
- **Navigation trees** — the generated `.vitepress/config.generated.mjs` now carries a `collapsed`, `part_of`-nested **Architecture** tree (service → domains → features) with human-readable labels (`context-oracle` → "Context Oracle") and a nested, collapsible **Documentation** tree mirroring the `docs/` directory; both deterministic with no dead links (`application/site_nav.py`) (BDL-041)
- **Dogfood proof (F4.4)** — regenerated and rebuilt Beadloom's own site: the real `vitepress build` exits 0, all diagrams pass the guard, the landscape shows the real CONFIRMED contract edge with no dead clicks, and the ECharts dashboard render was browser-confirmed (BDL-041 BEAD-05)

### Added (F3)
- **Landscape gate** (`federate --fail-on <csv>`) — turns the F2 contract/edge verdicts into a CI gate: exits `1` when any verdict matches the fail-set, but **always writes `.beadloom/federated.json` + the report first** so CI can upload the artifact even on failure. A bare `--fail-on` / `default` arms the safe-default set `breaking,drift,orphaned_consumer,undeclared_producer` (+ edge-level `undeclared`); no-false-gate verdicts (`external`/`expected`/`dead`/`unmapped`/`confirmed`/`ok`/`cleanup_candidate`) can never be armed (rejected, exit `2`). Backed by the pure `gate_failures(fed, fail_on)` + `SAFE_DEFAULT_FAIL_ON` / `NEVER_FAIL_VERDICTS` in `graph/federation.py` (BDL-039 BEAD-01)
- **Agent-actionable output** — every architecture violation carries a `Violation.remediation` ("how to fix"), surfaced by `beadloom lint --format json` (a `remediation` key) and `--format github` (rendered into `::error` annotations so it shows inline on the PR) (BDL-039 BEAD-02)
- **AgentConfigAsCode** (`beadloom config-check [--fix]`) — regenerates `AGENTS.md`, the auto-managed regions of `CLAUDE.md`, and the IDE rules adapters **in memory** (reusing the exact `setup-rules --refresh` generator — no parallel reimplementation) and diffs them against disk; exits `1` on drift. Checks only the `beadloom:auto-start`/`auto-end` regions, never user-authored prose (`onboarding/config_sync.py`) (BDL-039 BEAD-03)
- **Unified gate** (`beadloom ci`) — composes reindex → `lint --strict` → sync-check → config-check → doctor → optional `federate --fail-on` (`--hub`) into one verdict with a single exit code; never short-circuits, names every step with an honest PASS/FAIL/SKIP, and shares one finding shape (`{kind, rule, severity, locations, why, remediation}`) so `--format rich|json|github` applies uniformly (`application/gate.py`) (BDL-039 BEAD-04)
- **Reusable CI integration** — a thin composite GitHub Action (`.github/actions/beadloom-gate`) wrapping `beadloom ci` (all logic in the CLI) + a GitLab template, with a documented pull-based hub pattern for the cross-service landscape (satellites publish commit-SHA-tagged exports; a hub job pulls ≥2 + `federate --fail-on`). Dogfooded on Beadloom's own CI (BDL-039 BEAD-05)
- **Dogfood proof (F3)** — the gate blocks a real boundary violation, a cross-service `BREAKING`, and a drifted agent-config; AgentConfigAsCode caught a genuine `AGENTS.md` drift on Beadloom itself during the dogfood (BDL-039 BEAD-06)

### Added
- **Cross-service contract graph (F2 moat)** — federation reconciles AMQP **and** GraphQL contracts into first-class `Contract`s (`graph/contracts.py`) keyed by a protocol-prefixed, **language-neutral** `contract_key` (AMQP `amqp:<exchange>/<routing>:<message_type>`, GraphQL `graphql:<schema>`), so a cross-language edge (e.g. a TS client ↔ a backend's GraphQL schema) resolves by contract *name*, never by code symbol (BDL-038 U3/G2/G3)
- **GraphQL SDL contract source** (`graph/sdl.py`) — extracts a producer's `exposed` SDL surface and a consumer's `references`; a presence-based **`BREAKING`** verdict fires when `references ⊄ exposed` (a consumer relies on a name the producer no longer exposes — caught before it ships, not a version diff) (BDL-038 U2/G3)
- **Contract-level intent-vs-reality verdicts** (`ContractVerdict`) — `CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` / `EXTERNAL` / `DEAD` / `EXPECTED`, with declared edge `lifecycle` (`external` > `dead` > `deprecated` > `planned` > `active`) folded onto the contract so intent dominates the shape check. Contract-level `DRIFT` is intentionally subsumed by `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER`; `DRIFT` stays the edge-level `EdgeVerdict` (BDL-038 G5)
- **`external` / `unmapped` lifecycle** — a node declared present-but-not-ours (`lifecycle: external`, e.g. a native Swift/Kotlin bridge) → `EXTERNAL`; a foreign ref that resolves but is exported without a usable surface → `EdgeVerdict.UNMAPPED`; both suppress DRIFT and stay distinct from a genuinely-absent `unresolved_refs` target (BDL-038 U4/G7)
- **Nested landscapes — product vs company scope** — an optional `landscape` provenance scopes implicit same-key contract matching to `(landscape, contract_key)`, so unrelated products sharing a coincidental message_type/schema name never auto-confirm or cross-pollute verdicts; a genuine cross-product contract is promoted cross-landscape via an explicit `@repo:` consumer edge. `federate` composes one product-landscape or a company-landscape of several (BDL-038 U5)
- **Paradigm-agnostic node/edge kinds** — arbitrary `kind`/`edge_kind` round-trips through `export`/`federate` without loss or rejection (FSD `page`/`feature`/`entity`/`repository` alongside DDD `domain`/`service`); the DDD-only DB `kind` CHECK was dropped (BDL-038 U1)
- **Dogfood proof (F2)** — verified end-to-end on a real landscape: a real GraphQL `BREAKING` mismatch caught before ship (a consumer-referenced field absent from the producer's current SDL), and a separate FSD-architecture product round-tripped through `export`/`federate` with zero kind loss, native bridges classified `EXTERNAL` (not DRIFT), and zero cross-pollution as a contract-less member of a company-landscape run (BDL-038)

### Added (F1)
- **Cross-repo node identity** — a graph ref may name a node in another repo as `@<repo>:<ref_id>` (`FederatedRef` / `parse_ref` in `graph/federation.py`); plain refs stay local. Malformed `@...` refs are surfaced as errors, never silently accepted. Cross-repo edges persist in a new `foreign_edges` table (BDL-037 F1)
- **`lifecycle` field** on every node and edge — `active` (default) | `planned` | `deprecated` | `dead`, as a first-class SQLite column (not `extra`). Only `active` edges count as live for `no-dependency-cycles` / `architecture-layers`; the federation hub reconciles `lifecycle` against reality into a three-valued intent-vs-reality verdict (BDL-037 F1)
- **`beadloom export`** — emit the indexed graph as a deterministic, self-describing federation artifact (schema v1: `repo`, `commit_sha`, `exported_at`, `generator`, `nodes`[lifecycle], `edges`[lifecycle + optional AMQP `contract` meta]). Byte-stable diffs (sorted nodes/edges + sorted keys); `commit_sha` is `null` when it cannot be honestly verified (BDL-037 F1)
- **`beadloom federate`** — hub aggregation of ≥2 satellite exports into one namespaced federated graph: resolve `@repo:` refs, assign an `EdgeVerdict` per edge (`OK` / `DRIFT` / `EXPECTED` / `CLEANUP_CANDIDATE` / `UNDECLARED` / `DEAD`), reconcile AMQP contracts (confirmed both-sides vs one-sided), report per-satellite staleness. Writes `.beadloom/federated.json` + `.beadloom/federated.txt` (BDL-037 F1)
- **Dogfood proof** — F1 verified end-to-end on the real core-monolith ↔ integration-service RabbitMQ contract: all 4 message types confirmed both-sides, 16 edges OK, no unresolved refs (BDL-037, UX #104)

### Migration
- **Schema versions (F2)** — `EXPORT_SCHEMA_VERSION` 1 → 2 (GraphQL SDL `contract` meta on edges), `FEDERATION_SCHEMA_VERSION` 1 → 2 (contract-level `verdict`/`protocol`/`contract_key`/`lifecycle` on hub output, GraphQL `exposed`/`references`/`missing`), and **SQLite schema 3 → 4**. All backward-compatible: `federate` still ingests v1 **and** v2 exports (the two export/federation versions are independent), and an older DB migrates idempotently with no data loss (BDL-038)
- **SQLite schema 3 → 4** — additive, idempotent table-rebuild (SQLite cannot `ALTER` a CHECK in place): adds `external` to the `lifecycle` CHECK on `nodes`/`edges`/`foreign_edges`, and drops the DDD-only `kind` CHECK so paradigm-agnostic kinds (FSD `page`/`feature`/`entity`/`repository`) load without rejection. Composes with the F1 changes; no regression (BDL-038 U1/G6/G7)
- **SQLite schema 2 → 3** — additive, idempotent: `lifecycle` columns on `nodes`/`edges`, a `foreign_edges` table, `produces`/`consumes` added to the `edges.kind` CHECK, and `contract_key` added to the edges primary key so multiple AMQP contracts on one node pair survive. Existing DBs upgrade cleanly (BDL-037)

### Changed
- **New `application` layer** — orchestrators (`reindex`, `doctor`, `debt_report`, `watcher`) moved from `infrastructure/` to a new `src/beadloom/application/` DDD layer. `infrastructure/` is now domain-agnostic (zero domain imports); layer order is `services → application → domains → infrastructure`. Module import paths changed `beadloom.infrastructure.{reindex,doctor,debt_report,watcher}` → `beadloom.application.*` (BDL-036 #91)
- **Architecture rules enforced** — `no-dependency-cycles` and `architecture-layers` restored to `severity: error`; `beadloom lint --strict` now fails on real cycle/layer violations and is genuinely clean on Beadloom itself (BDL-036 #91)
- **Generated bootstrap rule** is now `feature-needs-parent` (`has_edge_to: {}`) so a fresh `beadloom init --bootstrap` passes `lint --strict` out-of-the-box (BDL-036 #71)

### Fixed
- **doctor version drift** — reads in-tree `__version__` instead of stale `importlib.metadata` (BDL-036 #92)
- **AGENTS.md MCP tool count** — driven by a single-source catalog pinned to the live MCP registry; no longer drifts (13→14) (BDL-036 #93)
- **Incremental reindex "Nodes: 0"** — reports true live-DB node/edge totals on the docs/code-only path (BDL-036 #88)
- **Silent YAML failure** — graph loader raises `GraphParseError` with file+line on malformed YAML instead of silently producing 0 nodes (BDL-036 #86)
- **sync-check false `untracked_files`** — file-level `# beadloom:domain=` annotations on symbol-less modules and `<!-- beadloom:track= -->` doc markers now count as tracking signals (BDL-036 #89/#90)
- **Over-broad exception handling** in reindex narrowed to `sqlite3.OperationalError` for missing-table cases (BDL-036 #94)
- **`export` dropped declared cross-repo edges** — `@repo:` edges now persist in a `foreign_edges` table and union into the export artifact, so a satellite's intent-declared cross-repo links reach the hub (BDL-037 #100)
- **`produces`/`consumes` edge kinds rejected** — added to the `edges.kind` CHECK (the edges table is rebuilt, since SQLite cannot `ALTER` a CHECK) so contract edges persist through the real reindex → export path (BDL-037 #101)
- **Multiple contracts on one node pair collapsed** — `contract_key` (derived from `contract.message_type`) is part of the edges primary key, so a producer publishing N message types to one target survives instead of hitting `UNIQUE constraint failed` (BDL-037 #102)
- **`export` `commit_sha` leaked the host repo's HEAD** — `current_commit_sha` returns `null` when the project root is not the git toplevel, instead of an enclosing repo's sha (BDL-037 #103)

### Known
- `beadloom sync-check` still reports pre-existing documentation drift across several domains (accumulated content staleness, not a mechanism bug); a dedicated repo-wide doc-refresh is tracked as BDL-UX #99.

## [1.9.0] - 2026-03-10

Data accuracy, docs audit precision, and sync-check reliability. 6 UX issues resolved, 43 new tests. 2580 tests total.

### Fixed
- **Rules DB completeness** -- `_load_rules_into_db()` now handles all 9 v3 rule types (`ForbidCyclesRule`, `LayerRule`, `CardinalityRule`, `ForbidImportRule`, `ForbidEdgeRule`) instead of silently dropping 5 of 9 (BDL-034, UX #67)
- **Rule type labels** -- `_build_rules_section()` and `_read_rules_data()` detect all 7 YAML rule keys (`require`, `deny`, `forbid_cycles`, `layers`, `check`, `forbid_import`, `forbid_edge`) instead of binary require/deny classification (BDL-034, UX #68)
- **AGENTS.md regeneration** -- replaced `## Custom` marker with `<!-- beadloom:custom-start/end -->` HTML comment markers to prevent content duplication on `setup-rules --refresh` (BDL-034, UX #69)

### Changed
- **Docs audit false positive rate** -- reduced from ~60% to ~11% via three-layer filtering: blocklist modifiers (`>=`, `%`, `up to`), proximity scoring (keyword-distance weighting), and file-type heuristics (lower confidence for SPEC.md, CONTRIBUTING.md) (BDL-034, UX #65)
- **Two-phase sync-check** -- added `doc_hash_at_last_edit` column to `sync_state` table; `sync-check` now detects code changes since last doc edit, preventing `reindex` from masking stale documentation (BDL-034, UX #70)

### Verified
- **Snapshot diffing** -- confirmed `beadloom snapshot save/list/compare` CLI commands and `compare_snapshots()` diff logic already fully functional (BDL-034, UX #66 — closed as already resolved)

## [1.8.0] - 2026-02-21

C4 diagrams, debt reporting, interactive TUI, docs audit, agent instructions freshness, enhanced architecture rules, and 60+ UX fixes. 2537 tests.

### Added
- **C4 architecture diagrams** -- `beadloom graph --format=c4` (Mermaid C4 syntax) and `--format=c4-plantuml` (PlantUML with standard macros) (BDL-023)
- **C4 drill-down levels** -- `--level=context|container|component` for multi-resolution views; `--scope=<ref-id>` for component-level diagrams (BDL-023)
- **C4 external systems** -- `external: true` tag renders as `System_Ext`; database/storage tags render as `ContainerDb` (BDL-023)
- **C4 level mapping** -- automatic level inference from `part_of` depth + kind heuristics (BDL-023)
- **Architecture debt report** -- `beadloom status --debt-report` with aggregated score 0-100 and severity labels (BDL-024)
- **Debt scoring formula** -- weighted: rule violations (errors x3 + warnings x1), doc gaps (undocumented x2 + stale x1), complexity smells (BDL-024)
- **Debt CI gates** -- `--debt-report --json` for CI consumption; `--fail-if=score>N` and `--fail-if=errors>0` (BDL-024)
- **Debt trend tracking** -- delta per category vs last snapshot; top offenders list ranked by debt contribution (BDL-024)
- **MCP tool `get_debt_report`** -- debt report for AI agents (BDL-024)
- **Multi-screen TUI** -- 3-screen architecture workstation with Dashboard, Explorer, and Doc Status screens (`beadloom tui`) (BDL-025)
- **7 data providers** -- thin read-only wrappers over existing infrastructure APIs (Graph, Lint, Sync, Debt, Activity, Why, Context) (BDL-025)
- **GraphTreeWidget** -- interactive architecture hierarchy tree with doc status indicators (fresh/stale/missing) and edge count badges (BDL-025)
- **DebtGaugeWidget** -- debt score display with severity coloring (green/yellow/red) (BDL-025)
- **LintPanelWidget** -- violation counts with severity icons and individual violation details (BDL-025)
- **ActivityWidget** -- per-domain git activity progress bars with color coding (BDL-025)
- **StatusBarWidget** -- health metrics, watcher status indicator, auto-dismissing notifications (BDL-025)
- **NodeDetailPanel** -- node deep-dive with ref_id, kind, summary, source, edges, doc status (BDL-025)
- **DependencyPathWidget** -- upstream/downstream dependency tree visualization with impact summary (BDL-025)
- **ContextPreviewWidget** -- context bundle preview with token estimation (BDL-025)
- **DocHealthTable** -- per-node documentation health table with coverage tracking and row selection (BDL-025)
- **FileWatcherWorker** -- background file watcher with 500ms debounce, extension filtering, `ReindexNeeded` messages (BDL-025)
- **SearchOverlay** -- modal FTS5 search with LIKE fallback and result navigation (BDL-025)
- **HelpOverlay** -- modal keybinding reference organized by context (BDL-025)
- **17 keyboard bindings** -- screen switching (1/2/3), navigation, actions (r/l/s/S), overlays (?//) (BDL-025)
- `beadloom tui` command (primary), `beadloom ui` kept as alias (BDL-025)
- `--no-watch` flag to disable file watcher (BDL-025)
- **Docs audit** -- `beadloom docs audit` zero-config meta-doc staleness detection with fact registry (BDL-026, experimental)
- **Fact registry** -- auto-compute version, node/edge/test counts, CLI commands, MCP tools (BDL-026)
- **Doc scanner** -- keyword-proximity matching for fact verification; Rich color-coded output (stale/fresh/unmatched) (BDL-026)
- **Docs audit CI gates** -- `--json` output, `--fail-if=stale>0` (BDL-026)
- **Agent instructions freshness** -- `beadloom doctor` now checks CLAUDE.md and AGENTS.md for stale facts (BDL-030)
- **6 fact extraction helpers** -- version, packages, CLI commands, MCP tools, stack, test framework (BDL-030)
- **`beadloom setup-rules --refresh`** -- auto-update CLAUDE.md dynamic sections with `--dry-run` preview (BDL-030)
- **`<!-- beadloom:auto-start/auto-end -->` markers** -- safe section regeneration for agent instruction files (BDL-030)
- **NodeMatcher `exclude` filter** -- `exclude` field on NodeMatcher dataclass filters specific nodes from rule evaluation; used in `service-needs-parent` to skip root node (BDL-032)
- **`forbid_import` rules** -- 2 new rules: `tui-no-direct-infra` and `onboarding-no-direct-infra` enforce import boundaries via `code_imports` table (BDL-032)
- **Rules schema v3 tags** -- bulk tag assignments in `rules.yml` v3; `layer-service`, `layer-domain`, `layer-infra` tags for architecture layer enforcement (BDL-032)
- **5 new architecture rules** -- `no-dependency-cycles`, `architecture-layers`, `domain-size-limit`, `tui-no-direct-infra`, `onboarding-no-direct-infra` (9 rules total, 6/7 types exercised) (BDL-032)
- **API CHANGE tracking in agent skills** -- `/dev`, `/review`, `/tech-writer` skills updated with explicit API change handoff protocol to prevent doc staleness (BDL-032)

### Changed
- Textual dependency upgraded from `>=0.50` to `>=0.80` (BDL-025)
- Explorer `e` keybinding opens any node including domain nodes (BDL-029)
- Edge count legend uses `[N edges]` format instead of raw `[N]` (BDL-029)
- Tree icons: fixed triangle display for childless nodes at cold start (BDL-029)
- Doctor promoted undocumented nodes to WARNING severity (BDL-027)
- Untracked file details included in debt report output (BDL-027)
- Init now scans all code directories for React Native projects (BDL-027)
- Rules schema version upgraded from v1 to v3 with backward compatibility (BDL-032)
- `service-needs-parent` rule uses `exclude: [beadloom]` to skip root service node (BDL-032)
- Architecture lint: 9 rules evaluated (was 4), covering 6 of 7 rule types (BDL-032)

### Fixed
- **C4 depth computation** -- correct boundary nesting for deeply nested nodes (BDL-027)
- **C4 label/description separation** -- labels no longer include description text (BDL-027)
- **C4 self-referencing edges** -- filtered out to prevent diagram errors (BDL-027)
- **C4 boundary ordering** -- stable ordering for deterministic diagram output (BDL-027)
- **PlantUML level selection** -- correct C4 level passed to PlantUML output (BDL-027)
- **Debt report oversized false positive** -- parent nodes no longer flagged incorrectly (BDL-027)
- **Docs audit number filter** -- skip numbers <10 to avoid false matches (BDL-027)
- **Docs audit year filter** -- year values excluded from staleness checks (BDL-027)
- **Docs audit SPEC.md exclusion** -- specification files excluded from audit scope (BDL-027)
- **Docs audit dynamic versioning** -- correct version detection for hatch-vcs projects (BDL-027)
- **Docs audit full path display** -- show complete file paths in audit output (BDL-027)
- **TUI aggregate parent test counts** -- parent nodes show sum of child test counts (BDL-027)
- **TUI route extraction self-exclusion** -- node's own routes excluded from dependency view (BDL-027)
- **TUI route formatting** -- consistent route display across widgets (BDL-027)
- **File watcher thread shutdown** -- clean shutdown via `threading.Event` instead of daemon thread (BDL-028)
- **Static widgets not updating** -- `update()` instead of `refresh()` after screen switch (BDL-028)
- **Esc (Back) crash** -- `ScreenStackError` on `switch_screen` navigation fixed (BDL-029)

## [1.7.0] - 2026-02-17

AaC Rules v2, Init Quality, and Architecture Intelligence. 1657 tests.

### Added
- **NodeMatcher** — tag/kind-based node matching for rule definitions; `matches(ref_id, kind, tags=)` method (BDL-021 BEAD-01)
- **Node tags/labels** — tags stored in `extra` JSON column, bulk assignment via `tags:` block in rules.yml v3; `get_node_tags()` API (BDL-021 BEAD-01)
- **ForbidEdgeRule** — deny rules evaluated against `edges` table (vs DenyRule which checks `code_imports`); supports tag-based matching (BDL-021 BEAD-02)
- **LayerRule** — enforce layered architecture: define ordered layers with `allow_skip`, violation on reverse-direction edges (BDL-021 BEAD-03)
- **CycleRule** — circular dependency detection via iterative DFS; configurable `edge_kind` (single or tuple) and `max_depth`; reports full cycle path (BDL-021 BEAD-04)
- **ImportBoundaryRule** — file-level import restrictions using fnmatch glob patterns on `code_imports` file paths (BDL-021 BEAD-05)
- **CardinalityRule** — architectural smell detection: `max_symbols`, `max_files`, `min_doc_coverage` thresholds per node (BDL-021 BEAD-06)
- **Rules schema v3** — top-level `tags:` block for bulk tag assignments; backward compatible with v1/v2 (BDL-021 BEAD-01)
- **`load_rules_with_tags()`** — returns both rules and tag assignments from rules.yml (BDL-021 BEAD-01)
- **Architecture snapshots** — `beadloom snapshot save/list/compare`: save graph state to `graph_snapshots` table, list history, compare any two snapshots (BDL-021 BEAD-12)
- **Enhanced diff** — `NodeChange` now tracks source path changes, tag changes, symbol counts; `compute_diff_from_snapshot()` for snapshot-based comparison (BDL-021 BEAD-13)
- **Non-interactive init** — `beadloom init --mode bootstrap --yes --force` for CI/scripts; `non_interactive_init()` API (BDL-021 BEAD-08)
- **Doc auto-linking** — `auto_link_docs()` fuzzy-matches existing docs to graph nodes by path/ref_id similarity during init (BDL-021 BEAD-11)
- **Docs generate in init** — `beadloom init` offers doc skeleton generation as a final step (BDL-021 BEAD-10)
- **Enhanced `why --reverse`** — `render_why_tree()` for reverse dependency view; `--reverse` and `--format` flags on CLI (BDL-021 BEAD-14)
- **Scan all code directories** — bootstrap now scans all top-level dirs with code files, not just manifest-adjacent ones (BDL-021 BEAD-07)
- **249 new tests** (1657 total)

### Changed
- **Rule engine** — `Rule` type union expanded: `DenyRule | RequireRule | CycleRule | ImportBoundaryRule | ForbidEdgeRule | LayerRule | CardinalityRule`
- **`evaluate_all()`** — dispatches all 7 rule types (was 2)
- **`render_diff()`** — shows source path changes, tag changes, symbol counts for changed nodes
- **4 domain docs refreshed** — context-oracle, graph, onboarding, cli documentation updated

### Fixed
- **Root service rule** — `service-needs-parent` rule no longer fails on root node; root detection uses `part_of` edge presence (BDL-021 BEAD-09)

## [1.6.0] - 2026-02-17

Deep Code Analysis, Honest Doc-Sync, and Agent Infrastructure. 1408 tests.

### Added
- **API route extraction** — tree-sitter + regex detection for 12 frameworks: FastAPI, Flask, Django, Express, NestJS, Spring Boot, Gin, Echo, Fiber, Actix, GraphQL (schema + code-first), gRPC (BDL-017 BEAD-01)
- **Git history analysis** — `analyze_git_activity()` classifies modules as hot/warm/cold/dormant based on 6-month commit history (BDL-017 BEAD-02)
- **Test mapping** — `map_tests()` detects test framework (pytest, jest, go test, JUnit, XCTest) and maps test files to source modules (BDL-017 BEAD-03)
- **Rule severity levels** — rules support `severity: warn` vs `severity: error` (default); `beadloom lint` shows both, `--strict` fails only on errors; backward-compatible v1→v2 migration (BDL-017 BEAD-04)
- **MCP tool `why`** — impact analysis via MCP: upstream dependencies + downstream dependents as structured JSON (BDL-017 BEAD-05)
- **MCP tool `diff`** — graph changes since a git ref via MCP (BDL-017 BEAD-06)
- **MCP tool `lint`** — architecture validation via MCP with severity in JSON output (BDL-017 BEAD-12)
- **Deep config reading** — extracts scripts, workspaces, path aliases from pyproject.toml, package.json, tsconfig.json, Cargo.toml, build.gradle (BDL-017 BEAD-07)
- **Context cost metrics** — `beadloom status` shows average/max bundle sizes in estimated tokens (BDL-017 BEAD-08)
- **Smart `docs polish`** — enriched with routes, activity, tests, config data from deep analysis (BDL-017 BEAD-14)
- **AGENTS.md v3** — now documents 13 MCP tools (was 10) (BDL-017 BEAD-15)
- **3-layer staleness detection** — `check_sync()` now detects: `symbols_changed` (hash mismatch), `untracked_files` (files in source dir not tracked), `missing_modules` (doc doesn't mention module) (BDL-018)
- **Source coverage check** — `check_source_coverage()` finds Python files in node source directories not tracked in sync_state or code_symbols (BDL-018 BEAD-02)
- **Doc coverage check** — `check_doc_coverage()` verifies documentation mentions all modules in source directory (BDL-018 BEAD-03)
- **Hierarchy-aware coverage** — `check_source_coverage()` queries `part_of` edges to recognize files annotated to child feature nodes as tracked under parent domain (BDL-020 BEAD-02)
- **`/tech-writer` role** — new agent skill for systematic documentation updates using sync-check + ctx + sync-update workflow (BDL-019)
- **`/task-init` skill** — unified task initialization for all types (epic, feature, bug, task, chore); replaces `/epic-init` (BDL-021)
- **`BRIEF.md` template** — simplified doc format for bug/task/chore (one-approval flow)
- **255 new tests** (1408 total)

### Changed
- **`sync-check` CLI output** — now shows reason (symbols_changed, untracked_files, missing_modules) and details per stale entry (BDL-018)
- **`sync-check --json`** — structured JSON output with `reason` and `details` fields (BDL-018)
- **Routes/activity/tests integrated into reindex** — stored as JSON in `nodes.extra` during full and incremental reindex (BDL-017 BEAD-09, BEAD-10, BEAD-11)
- **Deep config integrated into bootstrap** — config data in root node `extra.config` (BDL-017 BEAD-13)
- **13 domain/service docs refreshed** — all documentation updated to match current code (BDL-019)
- **`.claude/commands/templates.md`** — stabilized: no numbered sections, strict status lifecycle (Draft/Approved/Done)
- **`.claude/CLAUDE.md`** — added `/task-init`, `/tech-writer`; updated file memory to include BRIEF.md

### Fixed
- **Symbol drift detection E2E** — `incremental_reindex()` now preserves `symbols_hash` baseline across reindexes (BDL-016)
- **`_compute_symbols_hash()` annotation query** — fixed to handle both `"ref_id"` and `["ref_id"]` JSON formats (BDL-018 BEAD-01)
- **Sync baseline preservation** — `_snapshot_sync_baselines()` preserves symbol hashes during full reindex (BDL-018 BEAD-01)
- **4 annotation mismatches** — `why.py` (was `impact-analysis`→`context-oracle`), `doctor.py` (was `doctor`→`infrastructure`), `watcher.py` (was `watcher`→`infrastructure`), `app.py` (was missing→`tui`) (BDL-020 BEAD-01)

## [1.5.0] - 2026-02-16

Smart Bootstrap v2, Doc Sync v2, 5 new languages, and a full documentation overhaul. 1153 tests.

### Changed
- **README.md + README.ru.md** — rewritten with new positioning: "Architecture as Code → Architectural Intelligence"; Agent Prime as flagship feature; real dogfooding examples; research references; full EN/RU parity
- **`docs/architecture.md`** — rewritten: 13 SQLite tables (was 7), 22 CLI commands (was 21), 9 import analysis languages (was 4); new sections: Rules Engine, Cache Architecture, Incremental Reindex, Health Snapshots, Agent Prime, Configuration
- **`.claude/CLAUDE.md`** — Beadloom dogfooding: `beadloom prime` as first session step, `beadloom ctx`/`why` for context discovery, expanded CLI reference (17 commands)
- **`.claude/commands/*`** — all 7 skills updated with Beadloom integration (`prime`, `ctx`, `why`, `search`, `lint --strict`)
- **Social preview** — `.github/social-preview.svg` for GitHub/messenger previews

### Added
- **README/doc ingestion** — `_ingest_readme()` extracts project description, tech stack, and architecture notes from README.md, CONTRIBUTING.md, ARCHITECTURE.md
- **Extended framework detection (18+)** — FastAPI, Flask, Django, Express, NestJS, Angular, Next.js, Vue, Spring Boot, Actix, Gin, SwiftUI, Jetpack Compose, React Native, Expo, and more
- **Entry point discovery** — `_discover_entry_points()` detects CLI tools (Click, Typer, argparse), server entry points, `__main__.py`, and `func main()` across 6 languages
- **Import analysis at bootstrap** — `_quick_import_scan()` infers `depends_on` edges between clusters from import statements (capped at 50)
- **Contextual node summaries** — `_build_contextual_summary()` combines framework, symbols, README excerpt, and entry points into rich summaries like "FastAPI service: auth — JWT auth, 3 classes, 5 fns"
- **Symbol-level drift detection** — `_compute_symbols_hash()` tracks SHA-256 of code symbols per ref_id; `check_sync()` detects semantic drift even when file hashes match
- **Doctor drift warnings** — `_check_symbol_drift()` and `_check_stale_sync()` surface drift/stale entries in `beadloom doctor`
- **Symbol diff in polish** — `_detect_symbol_changes()` shows drift warnings in `beadloom docs polish` output
- **`service-needs-parent` rule** — auto-generated require rule: every service node must have a `part_of` edge
- **Kotlin support** — `_load_kotlin()`, `_extract_kotlin_imports()` with stdlib filtering (kotlin.*, kotlinx.*, java.*, javax.*, android.*)
- **Java support** — `_load_java()`, `_extract_java_imports()` with static/wildcard imports and stdlib filtering
- **Swift support** — `_load_swift()`, `_extract_swift_imports()` with 35 Apple framework filters
- **C/C++ support** — `_load_c()`, `_load_cpp()`, `_extract_c_cpp_imports()` with 80+ system header filters; extended `_get_symbol_name()` for declarator chains
- **Objective-C support** — `_load_objc()`, `_extract_objc_imports()` with #import/#include and @import support; 48 system framework filters
- **306 new tests** (1153 total)

### Fixed
- **Reindex graph YAML detection** — `_graph_yaml_changed()` checks graph files before `_diff_files` to catch changes even with stale `file_index`
- **AGENTS.md template** — added `beadloom ctx <ref-id>` and `beadloom search "<query>"` CLI commands
- **Content-aware `setup_rules_auto()`** — detects beadloom adapter files vs user content; updates adapters, skips user files

## [1.4.0] - 2026-02-14

Agent Prime: cross-IDE context injection for AI agents. Full documentation audit.

### Added
- **`beadloom prime`** — output compact project context (architecture summary, health, rules, domains) for AI agent session start
- **`prime` MCP tool** — 10th tool; returns JSON context for agent sessions
- **`beadloom setup-rules`** — create IDE adapter files (`.cursorrules`, `.windsurfrules`, `.clinerules`) that reference `.beadloom/AGENTS.md`
- **AGENTS.md v2** — `generate_agents_md()` produces `.beadloom/AGENTS.md` with MCP tool list, architecture rules from `rules.yml`, and `## Custom` section preservation
- **`prime_context()`** — three-layer architecture: static config + dynamic DB queries with graceful degradation
- **`setup_rules_auto()`** — auto-detect IDEs by marker files; integrated into `beadloom init --bootstrap`
- **`agent-prime` graph node** — 20th node in architecture graph (feature under onboarding)
- **Architecture lint CI** — `.github/workflows/beadloom-aac-lint.yml` runs `beadloom lint --strict` on PRs
- **Known Issues section** — README.md and README.ru.md link to UX Issues Log
- **36 new tests** (847 total)

### Fixed
- **12 documentation discrepancies** — README/architecture/CLI/MCP docs all said "18 commands, 8 tools" (actual: 21 commands, 10 tools); `docs polish` documented `--ref` flag but code uses `--ref-id`; MCP docs used `ref_ids` (array) but schema is `ref_id` (string); `list_nodes` had undocumented `kind` filter; onboarding README missing 3 exported functions; infrastructure README missing 5 reindex pipeline steps; getting-started.md said "Python only" (supports 4 languages); root graph node said "v1.3.0" (was v1.3.1)
- **`docs/getting-started.md`** — fully rewritten to reflect current bootstrap flow (rules, skeletons, MCP, IDE adapters, sync-check)
- **`.beadloom/README.md`** — added missing `get_status` and `prime` to MCP tools list

## [1.3.1] - 2026-02-13

Onboarding Quality: 10 bug-fixes from dogfooding on real projects (core-monolith, secondary-system).

### Fixed
- **Doctor 0% coverage** — `generate_skeletons()` writes `docs:` field back to services.yml (core-monolith: 0% → 95%, secondary-system: 0% → 83%)
- **Lint false positives** — empty `has_edge_to: {}` matcher (any node), removed `service-needs-parent` rule (core-monolith: 33 → 0 violations)
- **Polish deps empty** — `generate_polish_data()` reads `depends_on` edges from SQLite post-reindex
- **Polish text = 1 line** — new `format_polish_text()` with node details, symbols, deps, doc status
- **Preset misclassifies mobile** — `detect_preset()` checks React Native/Expo/Flutter before `services/` heuristic
- **Missing parser warning** — `check_parser_availability()` warns about missing tree-sitter grammars in bootstrap/reindex
- **Generic summaries** — detects Django apps, React components, Python packages, Dockerized services
- **Parenthesized ref_ids** — strips `()` from Expo router dirs (`(tabs)` → `tabs`)
- **Reindex ignores parsers** — parser fingerprint tracked; new parsers trigger full reindex
- **Skeleton count** — CLI shows "N created, M skipped (pre-existing)"

## [1.3.0] - 2026-02-13

Plug & Play Onboarding: from install to first useful result in one command.

### Added
- **`beadloom docs generate`** — generate doc skeletons (architecture.md, domain READMEs, service pages, feature SPECs) from knowledge graph
- **`beadloom docs polish`** — structured JSON/text output with code symbols, Mermaid diagrams, and AI enrichment prompts for agent-driven doc polish
- **`generate_docs` MCP tool** — 9th tool, returns polish data as JSON for AI agents
- **Auto-rules generation** — `beadloom init --bootstrap` now generates `rules.yml` with structural require rules (domain-needs-parent, feature-needs-domain, service-needs-parent)
- **Auto MCP config** — bootstrap auto-detects editor (Cursor, Windsurf, Claude Code) and creates `.mcp.json`
- **Root node + project name detection** — reads name from pyproject.toml/package.json/go.mod/Cargo.toml with directory fallback
- **Enhanced init output** — summary with Graph/Rules/Docs/MCP/Index counts and Next steps
- **Doc-generator feature** — added to knowledge graph under onboarding domain
- **13 end-to-end integration tests** — full pipeline from bootstrap through docs generate/polish with idempotency checks

## [1.2.0] - 2026-02-13

DDD restructuring: code, docs, and knowledge graph now follow domain-driven design.

### Changed
- **Code → DDD packages** — flat modules reorganized into 5 domain packages (`infrastructure/`, `context_oracle/`, `doc_sync/`, `onboarding/`, `graph/`) with `__init__.py` re-exports
- **Package names aligned to docs** — `context/` → `context_oracle/`, `sync/` → `doc_sync/`, `infra/` → `infrastructure/`
- **Services layer** — `cli.py` and `mcp_server.py` moved into `services/` package
- **Loose files absorbed** — `doctor.py` → `infrastructure/`, `watcher.py` → `infrastructure/`, `why.py` → `context_oracle/`
- **Docs → domain-first layout** — `docs/` restructured into `domains/`, `services/`, `guides/` directories
- **Knowledge graph updated** — 18 nodes (5 domains, 3 services, 9 features, 1 root), 32+ edges reflecting DDD structure; `doctor` and `watcher` reclassified as features under `infrastructure`
- **Architecture lint rules** — 2 rules: `domain-needs-parent`, `feature-needs-domain`
- **CLI reference** — all 18 commands documented
- **MCP docs** — all 8 tools documented
- **Doc coverage 100%** — SPEC.md for all 9 features (cache, search, why, graph-diff, rule-engine, import-resolver, doctor, reindex, watcher) + TUI service doc
- **`guides/ci-setup.md`** — linked to `beadloom` root node in knowledge graph
- **`architecture.md` constraints** — updated for multi-language support and configurable paths
- **`import-resolver` summary** — corrected from "Python import analysis" to "Multi-language import analysis"
- **README.md + README.ru.md** — abstract examples replaced with real Beadloom data (architecture rules, docs tree, context bundle example)

### Fixed
- Circular import in `graph/linter.py` resolved via lazy import of `incremental_reindex`
- Integration tests updated for new graph structure (domain nodes instead of `linter` node)

## [1.1.0] - 2026-02-12

Improved import analysis and broader project support.

### Added
- **Deep import analysis** — `depends_on` edges generated from resolved imports between graph nodes
- **Hierarchical source-prefix resolver** — handles Django-style imports (`apps.core.models`), TypeScript `@/` aliases, and nodes with/without trailing slash
- **Auto-reindex after init** — no more manual `beadloom reindex` needed after `--bootstrap` or interactive setup
- **Noise directory filtering** — `static`, `templates`, `migrations`, `fixtures`, `locale`, `media`, `assets` excluded from architecture node generation

### Fixed
- Source dir discovery expanded (`backend`, `frontend`, `server`, `client`, etc.) with fallback to scanning all non-vendor dirs
- `reindex` and `import_resolver` now read `scan_paths` from `config.yml` instead of hardcoding `src/lib/app`
- `node_modules` and other junk dirs filtered from recursive scans
- `.vue` files recognized as code extensions

## [1.0.0] - 2026-02-11

Architecture as Code: Beadloom evolves from documentation tool to architecture enforcement platform.

### Added
- **`beadloom lint`** — validate code against architecture boundary rules defined in YAML
- **Rule engine** — declarative `rules.yml` with `deny` and `require` directives
- **Import resolver** — static analysis for Python, TypeScript/JavaScript, Go, and Rust
- **Agent-aware constraints** — `get_context` MCP tool returns active rules alongside context
- **CI architecture gate** — `beadloom lint --strict` exits 1 on violations

### Fixed
- `beadloom ui` traceback when textual not installed (lazy import guard)
- TUI shows real data — edges, docs, sync status, proper counts
- `beadloom reindex` shows "up to date" with DB totals when nothing changed
- `beadloom watch` traceback when watchfiles not installed

## [0.7.0] - 2026-02-11

Developer Experience: interactive exploration and real-time feedback.

### Added
- **`beadloom ui`** — interactive terminal dashboard (Textual) for browsing domains, nodes, and edges
- **`beadloom why REF_ID`** — impact analysis showing upstream deps and downstream dependents
- **`beadloom diff`** — show graph changes since a git ref (nodes/edges added, removed, modified)
- **`beadloom watch`** — auto-reindex on file changes during development

## [0.6.0] - 2026-02-10

Performance and agent-native evolution: caching, search, and write operations.

### Added
- **L1 in-memory cache** — ContextCache integrated with MCP server for token savings
- **L2 SQLite cache** — persistent `bundle_cache` table survives MCP restarts
- **Incremental reindex** — `file_index` tracks hashes, only re-processes changed files
- **Auto-reindex in MCP** — detects stale index, triggers incremental reindex before responding
- **FTS5 full-text search** — `beadloom search` command + MCP `search` tool
- **MCP write tools** — `update_node`, `mark_synced` for agent-driven graph updates
- **`beadloom search`** — CLI command for searching nodes, docs, and code symbols

### Removed
- `sync-update --auto` flag and `llm_updater.py` — Beadloom is now fully agent-native with no LLM API dependency

## [0.5.0] - 2026-02-10

Team adoption: CI integration, health metrics, and external linking.

### Added
- **CI integration** — `beadloom sync-check --porcelain` for GitHub Actions / GitLab CI
- **Health dashboard** — `beadloom status` shows doc coverage trends, stale doc counts
- **`beadloom link`** — connect graph nodes to Jira, GitHub Issues, Linear
- **MCP templates** — ready-made `.mcp.json` snippets for Cursor, Claude Code, Windsurf

## [0.4.0] - 2026-02-10

Lower the barrier: from install to useful context in under 5 minutes.

### Added
- **Architecture presets** — `beadloom init --preset {monolith,microservices,monorepo}`
- **Smarter bootstrap** — infers domains from directory structure, detects common patterns
- **Zero-doc mode** — graph-only workflow without any Markdown files
- **Interactive bootstrap review** — confirm/edit generated nodes before committing

## [0.3.0] - 2026-02-10

Foundation and agent-native pivot.

### Added
- **AGENTS.md generation** — `beadloom reindex` produces `.beadloom/AGENTS.md` for AI agents
- **README rewrite** — new positioning, value proposition, comparison table
- **README.ru.md** — Russian translation

### Changed
- Deprecated `sync-update --auto` in favor of agent-native workflow
- Annotation coverage improved to 100% across all modules

## [0.2.0] - 2026-02-09

Extended features: interactive sync, multi-language indexing, PyPI publishing.

### Added
- `sync-update --auto` — LLM-assisted doc update (later removed in v0.6)
- Interactive `sync-update` review mode
- Multi-language tree-sitter indexer
- Init wizard for guided project setup
- PyPI publishing workflow with dynamic versioning
- End-to-end test suite

### Fixed
- Module-level annotation parsing
- Doc ref_map collision on duplicate prefixes
- Heading collision in Mermaid graph output

## [0.1.0] - 2026-02-09

Initial release: Context Oracle + Doc Sync Engine.

### Added
- **Context Oracle** — BFS graph traversal, deterministic context bundles
- **Doc Sync Engine** — code-to-doc relationship tracking, staleness detection
- **Knowledge graph** — YAML-based node/edge definition
- **MCP server** — stdio transport with `get_context`, `get_graph`, `list_nodes`, `sync_check`, `get_status`
- **CLI** — `init`, `reindex`, `ctx`, `graph`, `status`, `doctor`, `sync-check`, `sync-update`
- **Tree-sitter indexer** — Python source code annotation extraction
- **Git hooks** — pre-commit doc sync check
- mypy strict mode, 91% test coverage, MIT license
