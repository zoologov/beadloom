<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T18:52:29.106245+00:00 · coverage 100% (`ai-techwriter`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# ai-techwriter

> Deterministic, seam-isolated PR-triggered documentation-refresh harness.

## Source

`src/beadloom/ai_agents/ai_techwriter/`

## Overview

The AI tech-writer is a deterministic harness that keeps documentation in sync
with code on every pull request. It orchestrates an external AI agent (Goose +
a model) behind mockable seams so the whole loop is unit-testable without the
agent, the model, or the network. Behaviour is the BDL-049/050 model,
byte-unchanged by the BDL-051 / S2 move into the `beadloom` package: PR-trigger,
`--since merge-base`, `--target pr-branch`, the `{ok, flagged, infra}` verdict,
the loop-guard, and `AI_TW_PAT` authentication.

The loop:

1. **discover scope** — parse `beadloom sync-check --json` into drift items;
2. **build packet** — per stale doc, assemble a context packet;
3. **invoke agent** (seam) — Goose rewrites the doc via the shipped recipe;
4. **re-baseline** — `beadloom sync-update` and iterate to a global fixpoint;
5. **gate** — `beadloom ci`;
6. **publish** (seam) — commit onto the PR head branch + comment (pr-branch), or
   cut a branch + open a PR (branch-pr);
7. **emit a run-record**.

## Invocation

```bash
python -m beadloom.ai_agents.ai_techwriter --platform {github|gitlab} \
    --target {pr-branch|branch-pr} --since <ref>
# console-script equivalent:
beadloom-ai-techwriter --platform github --target pr-branch --since <ref>
```

The harness ships inside the installed `beadloom` package, so adopters invoke it
directly (no vendoring). `beadloom setup-ai-techwriter --platform {github|gitlab}`
scaffolds the CI workflow that calls it, the getting-started guide, and the
operator artifacts (`recipe.yaml` + `provision-runner.sh`, copied from package
data).

## Modules

- **runner.py** — the deterministic orchestrator (the loop above) and the
  `{ok, flagged, infra}` verdict classification (`classify_verdict`). Per-doc
  repair runs in a bounded session pool (`HarnessConfig.max_parallel`, default 3
  — RAM-aware for the 8GB self-hosted VPS); each doc gets its own Goose session,
  and the per-session results are folded back in stale order so the aggregate /
  verdict is identical whether the pool ran them sequentially or concurrently.
- **backoff.py** — per-session 429/5xx exponential back-off (`RateLimitError`,
  `retry_with_backoff`) so concurrent sessions degrade gracefully against the
  rate-limited model endpoint instead of failing; the `sleep` seam is injected
  so the policy is deterministic and instant under test.
- **scope.py** — drift discovery from `beadloom sync-check --json`; when a
  `--since` baseline is given it also applies symbol-level narrowing
  (`symbol_scope`) before returning the stale set.
- **symbol_scope.py** — symbol-level scope narrowing (BDL-052 S4). Narrows the
  stale set from "changed FILE → all its doc pairs" to "doc references a CHANGED
  symbol", killing the god-file fan-out (a one-symbol edit to `cli.py` no longer
  drifts every doc the file is linked to). For each stale pair it intersects the
  symbols whose body changed in the touched file (vs `--since`, via git hunks ∩
  a Python `def`/`class` line-range map) with the symbols the doc references. The
  changed-symbol set unions BOTH diff sides — new-side edited/added defs AND
  **old-side removed/renamed** defs (so a doc naming a symbol that was deleted,
  whose name is gone from the new content, is still attributed and KEPT, never
  silently dropped); an
  empty intersection drops the pair from the agent run AND `sync-update`-baselines
  it so `sync-check` still reaches 0 without a rewrite. Conservative by
  construction: any unavailable/ambiguous attribution (no `--since`, a
  non-symbol drift reason, a non-Python file, a change outside any symbol body)
  keeps the pair in scope — it never under-refreshes. Shared by the local flow
  and the CI agent (both reach it through `discover_scope`).
- **packet.py** — per-doc context-packet assembly.
- **seams.py** — the mockable seams: the agent runner (Goose) and the review
  publisher (GitHub/GitLab, pr-branch + branch-pr variants), plus their fakes.
- **provider.py** — Goose provider config (Qwen via an OpenAI-compatible
  endpoint) and `default_recipe_path()` (the recipe shipped as package data,
  located via `importlib.resources`).
- **commands.py** — patchable wrappers around `beadloom` / `git` subprocess
  calls.
- **models.py** — typed, immutable harness data structures.
- **runs_store.py** — append-only run-record store.
- **cli.py** / **__main__.py** — the thin Click entrypoint CI invokes.

## Configuration

- `QWEN_API_KEY` (required on the runner; never inlined) — the model key.
- `QWEN_BASE_URL` (optional) — workspace MaaS endpoint; falls back to the
  generic DashScope gateway.
- `AI_TW_PAT` — token used for the refresh commit + PR/MR comment so the push
  re-triggers the required status check.

## Boundary

Part of the `ai_agents` domain (a leaf consumer). The harness consumes
`beadloom` / `bd` via subprocess seams and must not be imported by the core
(`core-no-import-ai-agents` / `application-no-import-ai-agents` rules).
