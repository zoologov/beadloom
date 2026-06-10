# AI tech-writer in CI (BDL-047 / F4.1)

The **AI tech-writer** closes Beadloom's DocAsCode loop at the "fix" step. Beadloom
is honest-by-construction at *detecting* doc drift (`beadloom sync-check` flags a
doc whose code changed underneath it). F4.1 adds automated *remediation*: on push
to `main`/`master`, a Goose agent (driving **Qwen3.7-Plus** over an external API)
rewrites **only the drifted docs**, the harness verifies freshness to a fixpoint,
runs `beadloom ci`, and opens a **pull/merge request for human review**. Nothing
auto-merges — `sync-check → 0` proves *freshness*, only a human proves
*correctness*.

> This page is the getting-started guide for the maintainer. The same content is
> scaffolded into any target repo by `beadloom setup-ai-techwriter` (the vendored
> copy lives at `docs/guides/ai-techwriter.md` in that repo).

## The loop

```
push to main/master
  → beadloom reindex                       (fresh checkout re-indexes from scratch)
  → beadloom sync-check --json --since <parent>   (drift relative to the push parent)
  → 0 stale  → exit 0 (no-op)
  → stale    → per drifted doc:
        Goose + Qwen3.7-Plus rewrite (scoped to that ref)
        → beadloom sync-update <ref> --yes   (re-baseline)
        → re-check --since <parent>          (still drifted? retry ≤ 2)
  → global fixpoint: repeat until stable 0 (or round/budget cap)
  → gate: beadloom ci   (reindex → lint --strict → sync-check → config-check → doctor)
  → open PR/MR
        gate green     → normal PR/MR
        not green / budget exceeded → PR/MR flagged "⚠ needs human"
```

Why `--since <parent>`: a fresh CI checkout reindexes from scratch and
re-baselines the stored `sync_state` to the **just-pushed** code, so a plain
`sync-check` would see 0 stale even when the push left a doc behind.
`beadloom sync-check --since <git-ref>` instead measures drift against the code
state at a git ref (the push's parent — `github.event.before` /
`$CI_COMMIT_BEFORE_SHA`, falling back to `HEAD~1`). A pair is stale-since-ref iff
its code changed since the ref **and** its doc was not correspondingly updated.
This is the authoritative re-check for the loop; `beadloom ci` is an additional
gate.

### Honesty model

- **`sync-check` is a freshness gate, not a correctness gate.** It proves a doc
  references the current symbols/files; it does not prove the prose is right.
- **The human PR review is the correctness gate.** The agent's output is a
  *proposal*; the deterministic gate + human review is the source of truth.
- **No auto-merge, ever.** On a green gate the harness opens a normal PR/MR; on a
  failure within budget it opens a PR/MR flagged **"⚠ needs human"** (it never
  merges and never hangs — a flagged PR is the failure mode, not a stuck job).
- **The agent's blast radius is small.** Goose may write only `docs/**`, reads
  code/git/`beadloom` read-only, runs no arbitrary shell, and never marks docs
  synced or merges — those steps are deterministic and owned by the harness.
- Bounded by design: per-doc retries (default 2), max fixpoint rounds (10), and
  hard caps on total turns (50) / tokens (2M) act as a runaway safety net.

## Setup (3 steps)

1. **Register a self-hosted runner on the VPS** (where Goose + the API key
   live). The agent job runs `uv sync --extra dev --extra languages` + a reindex;
   a 1 GB box OOMs — an **8 GB / 4 CPU** box is the proven-good size. The
   provisioner refuses below ~2 GB RAM and needs ~5 GB free disk. The bundled
   `provision-runner.sh` does the registration for you (next step).
2. **Add the secrets.** `QWEN_API_KEY` — a **GitHub repository secret** *or* a
   **GitLab masked CI/CD variable** (referenced only by name in the wrapper,
   resolved on the runner, never written into the repo). Optionally set
   `QWEN_BASE_URL` the same way to point at a workspace-specific MaaS endpoint
   (defaults to the DashScope OpenAI-compatible gateway in the provider).
3. **Scaffold + provision + enable.** Run the scaffold, provision the runner,
   then commit:

   ```bash
   beadloom setup-ai-techwriter --platform github   # or: gitlab
   ```

   This idempotently drops the vendored harness (`tools/ai_techwriter/`), the
   platform wrapper, `tools/ai_techwriter/provision-runner.sh`, and this guide.
   Then on the VPS:

   ```bash
   ./tools/ai_techwriter/provision-runner.sh \
     --platform <github|gitlab> --repo <repo-url> --token <reg-token>
   ```

   The script guarantees swap **before** any apt/build, runs RAM/disk
   prechecks, installs the toolchain + the runner, **registers** it (labels/tags
   `self-hosted,ai-techwriter`) and starts the service — fail-hard on those
   critical steps. Goose / beadloom / bd are installed best-effort and
   **verified + reported** at the end (install any reported MISSING). The token
   is passed via `--token` (or the `REG_TOKEN` env var) and is never written into
   the repo. Safe to re-run. Finally **commit** the scaffolded files and enable
   the pipeline.

After that the loop runs on push to `main`/`master` (+ manual). Nothing else is
configured per-repo — the harness + recipe are repo-agnostic and read *this*
repo's own graph + docs.

## Triggering

| | GitHub | GitLab |
|---|---|---|
| Wrapper | `.github/workflows/ai-techwriter.yml` | `ai-techwriter` job in `.gitlab-ci.yml` |
| On push | `push: branches: [main, master]` | rule `$CI_COMMIT_BRANCH == "main"/"master"` |
| Manual | `workflow_dispatch` | `$CI_PIPELINE_SOURCE == "web"` (manual) |
| Push parent (`--since`) | `github.event.before` → `HEAD~1` | `$CI_COMMIT_BEFORE_SHA` → `HEAD~1` |
| Secret | repository secret `QWEN_API_KEY` | masked CI/CD variable `QWEN_API_KEY` |
| Open review | `gh pr create` | `glab` / GitLab MR API |
| Serialize runs | `concurrency: ai-techwriter` | (single job) |

Both wrappers call the **same** entrypoint — only the trigger, the secret naming,
and `--platform` differ:

```bash
uv run python -m tools.ai_techwriter --platform <github|gitlab> --since <push-parent>
```

`--dry-run` reports the wiring and exits without running the model or opening a
PR. An all-zero SHA (force-push / first-push) is treated as "no baseline" and
falls back to `HEAD~1`.

**Loop-safe:** the agent's PR is merged by a human → that merge push finds 0
stale → no-op (no infinite loop; `concurrency` serializes GitHub runs).

## Dashboard widget (G9)

Each run appends an honest **run-record** to the append-only store
`.beadloom/ai_techwriter_runs.json`: `{ ts (stored, not now()), platform,
docs_refreshed[], input_tokens, output_tokens, model, gate (green/flagged),
pr_url }`. Token counts come from the model API's `usage` field — **fact**.

The VitePress dashboard renders an **"AI tech-writer activity"** widget
(`AiTechwriterActivity`, built from `site_dashboard.build_dashboard_data`'s
`ai_techwriter` section): docs-refreshed over time + input/output token spend per
run and cumulative, plus a `cost_estimate`. Only real recorded runs are shown
(no interpolation — sparse-at-first is correct). **Tokens are a fact; any dollar
figure is a clearly-labeled estimate** ("est. @ $X/1M tokens") at the configured
rate, never a hard cost. An absent/empty/corrupt store renders an
empty-but-present section, never an error.

## Cost & safety

- **Quality first, scope-bounded cost.** Extended thinking stays on; cost is
  bounded by scope (only drifted docs + scoped context) plus generous runaway
  hard caps, never by capping reasoning. Top-tier model only — no tiering.
- **No secrets in logs;** the key lives only on the runner; the runner is scoped
  to this repo with an ephemeral per-run workspace.

## Updating

Re-run `beadloom setup-ai-techwriter --platform <github|gitlab>` to refresh the
vendored harness, recipe, and this guide to the version shipped with your
installed `beadloom`. The re-run is idempotent (a clean overwrite of the
generated files).

## See also

- `docs/services/cli.md` — `sync-check --since`, `sync-update --yes/--all`,
  `setup-ai-techwriter`.
- `docs/domains/doc-sync/README.md` — `check_sync_since` / `mark_synced_by_ref`.
- `docs/domains/onboarding/README.md` — `ai_techwriter_setup.scaffold`.
- `docs/guides/ci-setup.md` — the general `beadloom ci` gate.
