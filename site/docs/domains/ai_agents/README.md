<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T18:52:29.106245+00:00 · coverage 100% (`ai_agents`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# AI Agents

Governed AI-agent harnesses that ship **inside** the installed `beadloom`
package. This domain hosts deterministic, seam-isolated harnesses that
orchestrate an external AI agent (Goose + a model) over Beadloom's own read
APIs and the `beadloom` / `bd` shell commands.

Introduced in BDL-051 / S2, when the AI tech-writer harness moved here from the
former `tools/ai_techwriter` repo-tooling package so it is graph-tracked,
lint-governed, and shipped as part of the wheel — adopters run it directly via
`python -m beadloom.ai_agents.ai_techwriter` (no vendoring).

## Boundary

`ai_agents` is a **leaf consumer**: it MAY consume `application` /
`context_oracle` / `graph` / `doc_sync` read APIs + the stdlib + the `beadloom`
/ `bd` shells, but it MUST NOT be imported BY the core domains or services. The
`core-no-import-ai-agents` / `application-no-import-ai-agents` `forbid_import`
rules in `.beadloom/_graph/rules.yml` enforce this (`lint --strict`).

## Features

- **ai-techwriter** — the deterministic, PR-triggered documentation-refresh
  harness (see `features/ai-techwriter/SPEC.md`).

## Specification

### Sub-packages

- **ai_techwriter/** — the AI tech-writer harness package. Annotated
  `# beadloom:feature=ai-techwriter`; the substantive modules are documented in
  the feature SPEC. The Goose recipe (`recipe.yaml`) and the runner provisioner
  (`provision-runner.sh`) ride alongside the package as **package data**, read
  via `importlib.resources` (the recipe by `provider.default_recipe_path()`).

### Modules

| Module | Source | Description |
|--------|--------|-------------|
| `backoff` | `backoff.py` | Per-session 429/5xx exponential back-off (`retry_with_backoff`, `RateLimitError`); deterministic schedule, injected `sleep` seam |
| `cli` | `cli.py` | Thin Click entrypoint (`main`); assembles seams, injects timestamp, delegates to `runner.run_harness`; exit codes driven by the three-verdict classifier (BDL-050) |
| `commands` | `commands.py` | Patchable subprocess wrappers (`run_command`, `beadloom_sync_check_json`, `beadloom_ctx_json`, `beadloom_why`, `git_changed_line_numbers`, etc.); the single `subprocess.run` seam |
| `models` | `models.py` | Frozen dataclasses crossing seams: `DriftItem`, `ContextPacket`, `AgentResult`, `GateResult`, `PublishResult`, `RunRecord`, `HarnessConfig`, `HarnessResult` |
| `packet` | `packet.py` | Deterministic context-packet assembly (`build_packet`, `select_polish_for_ref`, `read_doc`) |
| `provider` | `provider.py` | `ProviderConfig` (Qwen3.7-Plus / OpenAI-compatible endpoint), `qwen_provider`, `default_recipe_path`; API key resolved from env at run time, never inlined |
| `runner` | `runner.py` | Deterministic orchestrator (`run_harness`): discover → bounded-parallel per-doc repair → global fixpoint → `beadloom ci` gate → publish → emit record; three-verdict classifier (`classify_verdict`: `ok` / `flagged` / `infra`) |
| `runs_store` | `runs_store.py` | Append-only run-record store (`.beadloom/ai_techwriter_runs.json`); `runs_store_path`, `load_runs`, `append_run` |
| `scope` | `scope.py` | Drift-scope discovery (`discover_scope`, `parse_scope`): parses `beadloom sync-check --json` into grouped `DriftItem`s, then applies symbol-level narrowing |
| `seams` | `seams.py` | Mockable protocols + real implementations: `AgentRunner` / `GooseAgentRunner`, `ReviewPublisher` / `CommentPublisher` with GitHub + GitLab adapters (`GitHubPublisher`, `GitLabPublisher`, `GitHubPRBranchPublisher`, `GitLabPRBranchPublisher`), `FakeAgentRunner`, `FakePublisher` |
| `symbol_scope` | `symbol_scope.py` | Symbol-level scope narrowing (BDL-052 S4): `python_symbol_ranges`, `changed_symbols`, `narrow_by_changed_symbols`; conservative-by-construction — never under-refreshes |

### Pipeline overview

The harness loop in `runner.run_harness` proceeds deterministically given the
injected seams (agent, publisher) and clock:

1. **Discover scope** (`scope.discover_scope`) — runs `beadloom sync-check --json`
   (optionally `--since <ref>` for per-push drift), groups stale pairs into
   `DriftItem`s, then applies symbol-level narrowing (`symbol_scope`).
2. **Bounded-parallel repair** (`runner._repair_each_doc`) — each drifted doc
   gets its own Goose session in a `ThreadPoolExecutor` capped at
   `HarnessConfig.max_parallel` (default 3); each session is wrapped in
   429/5xx exponential back-off (`backoff.retry_with_backoff`). Sessions fold
   back into the shared `HarnessResult` in deterministic stale order.
3. **Global fixpoint** (`runner._run_fixpoint`) — re-baselines newly re-staled
   siblings until the stale set reaches 0, no-progress is detected, or the
   round cap is exhausted.
4. **Gate** (`runner._run_gate`) — runs `beadloom ci`; failure ⇒ flagged.
5. **Emit record** (`runner._emit_record`) — appends a `RunRecord` to the
   runs store (G9 observability).
6. **Publish** (`runner._publish`) — opens a PR/MR via the publisher seam;
   branch name is deterministic and git/FS-safe (`runner._branch_name`).

The three-verdict classifier (`runner.classify_verdict`, BDL-050) distinguishes
**ok** (clean / no-op), **flagged** (model ran but docs not clean — blocks CI),
and **infra** (model never produced tokens — does NOT block CI; posts a
best-effort PR/MR note instead).
