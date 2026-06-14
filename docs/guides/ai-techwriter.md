# AI tech-writer in CI (BDL-047 / F4.1 · BDL-049 · BDL-050)

The **AI tech-writer** closes Beadloom's DocAsCode loop at the "fix" step. Beadloom
is honest-by-construction at *detecting* doc drift (`beadloom sync-check` flags a
doc whose code changed underneath it). F4.1 adds automated *remediation*; **BDL-049**
makes it **trunk-based and PR-triggered**: when you open a PR to `main`/`master`, a
Goose agent (driving **Qwen3.7-Plus** over an external API) runs **once** against
that PR's diff, rewrites **only the drifted docs**, the harness verifies freshness
to a fixpoint, runs `beadloom ci`, then **commits its doc refresh back onto the PR
head branch** and posts a PR comment. Code + its doc updates review and merge in one
PR — no orphan doc-PRs. Nothing auto-merges — `sync-check → 0` proves *freshness*,
only a human (who merges the PR) proves *correctness*; `beadloom ci` as a required
check on `main` is the true enforcement.

**BDL-050** folds the agent into one consolidated `.github/workflows/ci.yml`: the
`ai-techwriter` job has `needs: [gate, tests, site-build]`, so it runs **only after**
the gate + the 3.10–3.13 test matrix + the VitePress site-build are all green — a
broken PR never spends Qwen tokens. The harness now classifies each run into a
**verdict** (`ok` / `flagged` / `infra`): a genuine unresolved doc drift (`flagged`)
blocks the PR, but an infra failure (`infra` — a dead runner / exhausted quota / a
provider 5xx) PASSES with a loud `::warning::` so it never freezes merges. See
[Verdict (BDL-050)](#verdict-ok-flagged-infra-bdl-050).

> This page is the getting-started guide for the maintainer. The same content is
> scaffolded into any target repo by `beadloom setup-ai-techwriter` (the vendored
> copy lives at `docs/guides/ai-techwriter.md` in that repo).

## The loop (BDL-049: trunk-based, PR-triggered · BDL-050: consolidated `ci.yml`)

```
open / update a PR to main/master  (pull_request: opened, synchronize, reopened)
  → loop-guard: if the PR head commit is the agent's own refresh
        (author beadloom-ai-techwriter OR a [skip ai-techwriter] subject)
        → skip the whole run (no re-trigger from the agent's own push)
  → beadloom reindex                       (fresh checkout re-indexes from scratch)
  → since = git merge-base origin/<base> HEAD   (exactly "what this PR changed";
        falls back to the PR base SHA if merge-base cannot resolve)
  → beadloom sync-check --json --since <since>
  → 0 stale  → exit 0 (no-op)
  → stale    → per drifted doc:
        Goose + Qwen3.7-Plus rewrite (scoped to that ref)
        → beadloom sync-update <ref> --yes   (re-baseline)
        → re-check --since <since>           (still drifted? retry ≤ 2)
  → global fixpoint: repeat until stable 0 (or round/budget cap)
  → gate: beadloom ci   (reindex → lint --strict → sync-check → config-check → doctor)
  → publish (--target pr-branch):
        commit the refresh ONTO the PR head branch with a
          "[skip ai-techwriter] docs: AI tech-writer refresh (N doc(s))" message
          (bot identity beadloom-ai-techwriter) + push to that branch
        post a PR comment summarizing docs refreshed + tokens + gate
        gate green     → comment is a plain refresh summary
        not green / budget exceeded → comment flagged "⚠ needs human"
  → verdict (BDL-050): ok/infra → exit 0; flagged → exit 1 (required check red)
  → human merges the PR when CI is green (no auto-merge)
```

BDL-050 runs this job as `ai-techwriter` inside the single `ci.yml`, gated on
`needs: [gate, tests, site-build]`. The job body is the BDL-049 model verbatim — only
the trigger moved into `ci.yml` and the exit code is now driven by the verdict.

Why `--since <merge-base>`: a fresh CI checkout reindexes from scratch and
re-baselines the stored `sync_state` to the PR's code, so a plain `sync-check`
would see 0 stale even when the PR left a doc behind. The workflow instead computes
`since = git merge-base origin/<base-ref> HEAD` — exactly "what this PR changed",
robust when the PR branch is behind or ahead of the base — and feeds it to
`beadloom sync-check --since <git-ref>` (falling back to the PR base SHA if the
merge-base cannot resolve). A pair is stale-since-ref iff its code changed since the
ref **and** its doc was not correspondingly updated. This is the authoritative
re-check for the loop; `beadloom ci` is an additional gate. (The earlier model
triggered `on: push` to `main` with `--since github.event.before`; BDL-049 replaced
it — see [Triggering](#triggering).)

### Why trunk-based (BDL-049)

The `on: push` model ran the agent **once per push to `main`**, which during the
F4.1/BDL-048 dogfood produced redundant 1h/768K-token re-refreshes (doc-touching
commits re-triggered a refresh of docs already being fixed), let `main` go **red**
between code landing and the doc-PR merging, and piled up **orphan doc-PRs**
decoupled from the code that caused the drift. Trunk-based + `pull_request` fixes
the cause: the agent runs **once per PR** against a clean `merge-base` baseline,
commits its fix **into the same PR**, and `main` is gated by a required `beadloom ci`
check so it stays always-green. See [`agentic-flow.md`](./agentic-flow.md) for the
trunk-based development flow itself.

### Honesty model

- **`sync-check` is a freshness gate, not a correctness gate.** It proves a doc
  references the current symbols/files; it does not prove the prose is right.
- **The human PR review is the correctness gate.** The agent's output is a
  *proposal*; the deterministic gate + human review is the source of truth.
- **No auto-merge, ever.** On the PR-triggered path (BDL-049) the harness commits
  the refresh onto the PR head branch and posts a comment (flagged **"⚠ needs human"**
  if the gate is not green); on the manual `workflow_dispatch` path it opens a fresh
  PR/MR (flagged the same way). Either way it never merges and never hangs — a
  flagged comment/PR is the failure mode, not a stuck job. **The human merges the
  PR**, and `beadloom ci` as a required check on `main` is the real gate.
- **The agent's blast radius is small.** Goose may write only `docs/**`, reads
  code/git/`beadloom` read-only, runs no arbitrary shell, and never marks docs
  synced or merges — those steps are deterministic and owned by the harness.
- Bounded by design: per-doc retries (default 2), max fixpoint rounds (10), and
  hard caps on total turns (50) / tokens (2M) act as a runaway safety net.

## Verdict: `ok` / `flagged` / `infra` (BDL-050)

The required `ai-techwriter` check is red **only** on a genuine doc failure, never on
broken infra. The harness (`beadloom.ai_agents.ai_techwriter.runner::classify_verdict`) maps each
finished run to one verdict; `cli.py` maps the verdict → exit code. The discriminator
between a doc problem and an infra failure is **whether the model ever produced output**
(`input_tokens + output_tokens > 0`):

| Verdict | When | Exit code | Effect |
|---|---|---|---|
| **ok** | 0-stale no-op **or** a clean refresh (`not flagged`) | `0` | check green |
| **flagged** | the model ran (`tokens > 0`) but docs still aren't clean — post-refresh `beadloom ci` red, fixpoint not reached, or budget exceeded mid-work | `1` | **check red → PR blocked** (a real "needs human") |
| **infra** | the agent never produced a token (`tokens == 0`) — dead self-hosted runner, provider 5xx / timeout, exhausted quota: it *couldn't run* | `0` | check green + a loud `::warning::` annotation + a best-effort PR comment ("docs were NOT checked — re-run before relying on freshness") |

Net: a dead VPS or an exhausted `$30` quota does **not** freeze merges; a real
unresolved doc drift does. The classification is conservative by construction
(`tokens == 0 ⇒ infra`); a misclassified `infra` is made loud by the annotation, so a
human re-runs rather than silently shipping stale docs.

## Scope + throughput knobs (BDL-052 S4 / S5)

BDL-052 narrowed *what* the agent rewrites and sped up *how* the run executes —
the loop behaviour and verdict above are byte-unchanged.

### Symbol-level scope (S4)

When a `--since` baseline is given (always, on the CI path), drift discovery
applies **symbol-level narrowing** (`ai_techwriter.symbol_scope`, called from
`scope.discover_scope`) before returning the stale set. Instead of "a changed
FILE drifts every doc linked to it", a stale pair is kept only when the doc
**references a symbol whose body actually changed** in the touched file — so a
one-symbol edit to a god-file like `cli.py` no longer fans out to every doc that
file is linked to. For each pair it intersects the changed-symbol set (computed
from git hunks ∩ a Python `def`/`class` line-range map) with the symbols the doc
references; an empty intersection drops the pair from the agent run **and**
`sync-update`-baselines it, so `sync-check` still reaches 0 without a needless
rewrite.

The changed-symbol set unions **both diff sides** — new-side edited/added defs
**and old-side removed/renamed defs** — so a doc that names a symbol which was
deleted/renamed (its name now gone from the new source) is still attributed and
**KEPT**, never silently dropped. Narrowing is **conservative by construction**:
any unavailable or ambiguous attribution (no `--since`, a non-symbol drift
reason, a non-Python file, a change outside any symbol body) keeps the pair in
scope, so it never under-refreshes.

### Bounded parallel sessions + back-off (S5)

Per-doc repair runs in a **bounded session pool** sized by
`HarnessConfig.max_parallel` (default **3** — RAM-aware for the 8 GB self-hosted
VPS). Each doc gets its own Goose session; at most `max_parallel` sessions are in
flight at once, and the per-session results are **folded back in stale order**, so
the aggregate, the budget accounting, and the verdict are identical whether the
pool ran sequentially (`max_parallel=1`) or concurrently. `max_parallel` is an
internal `HarnessConfig` knob (the CLI uses the default); lower it to 1 to force
sequential behaviour when debugging.

Concurrent sessions hitting the same rate-limited model endpoint degrade
gracefully via per-session **exponential back-off** (`ai_techwriter.backoff`:
`RateLimitError` / `retry_with_backoff`) on 429/5xx responses instead of failing
the run; the `sleep` seam is injected, so the policy is deterministic and instant
under test.

### CI caches (S5)

The consolidated `ci.yml` `ai-techwriter` job adds two caches that change only
speed, not behaviour:

- **uv dependency cache** — `setup-uv` with `enable-cache: true`, so the runner
  stops re-downloading wheels every PR.
- **Beadloom index cache** — `actions/cache` over `.beadloom/beadloom.db`, keyed
  on `hashFiles('.beadloom/_graph/**', 'src/**', 'docs/**')`. On a hit the index
  already matches this exact tree, so the `beadloom reindex` step is **skipped**;
  any graph/source/doc change rotates the key → miss → a full reindex runs. The
  freshness guarantee is unchanged (a stale tree can never produce a hit).

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

   This idempotently drops the platform wrapper (which calls the **packaged**
   harness `python -m beadloom.ai_agents.ai_techwriter` — no Python is vendored
   as of BDL-051 / S2), the operator artifacts `tools/ai_techwriter/recipe.yaml`
   + `tools/ai_techwriter/provision-runner.sh`, and this guide. Then on the VPS:

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

After that the loop runs on every PR to `main`/`master` (+ manual
`workflow_dispatch`). Nothing else is configured per-repo — the harness + recipe are
repo-agnostic and read *this* repo's own graph + docs.

To make the trunk-based model a hard guarantee, protect `main` so the
required-check gate is true enforcement (one-time, idempotent):

```bash
beadloom setup-branch-protection --repo OWNER/NAME    # GitHub; safe to re-run
```

This requires a PR to `main` (no direct push) with the consolidated `ci.yml`'s
**7 check-runs as required status checks** — `gate`, `tests (3.10)`, `tests (3.11)`,
`tests (3.12)`, `tests (3.13)`, `site-build`, `ai-techwriter` (BDL-050). Under strict
trunk-based (`enforce_admins: true`, BDL-049) even the owner integrates via a PR; with
0 required reviews the solo maintainer still self-merges. See `docs/services/cli.md`
for the full command + `--check`/`--branch`/`--dry-run` options.

## Triggering

| | GitHub | GitLab |
|---|---|---|
| Wrapper | `ai-techwriter` job in `.github/workflows/ci.yml` (BDL-050: was the standalone `ai-techwriter.yml`) | `ai-techwriter` job (stage `docs`) in `.gitlab-ci.yml` |
| Ordering | `needs: [gate, tests, site-build]` — runs only when all three are green | `needs: [gate, tests, site-build]` (stage `verify` → stage `docs`) |
| Primary trigger | `pull_request` (`opened`, `synchronize`, `reopened`) → `[main, master]` | rule `$CI_PIPELINE_SOURCE == "merge_request_event"` |
| Manual fallback | `workflow_dispatch` (no PR context → branch-PR path) | (manual pipeline / `web`) |
| Baseline (`--since`) | `git merge-base origin/$BASE_REF HEAD` → PR base SHA | `git merge-base origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME HEAD` → `$CI_MERGE_REQUEST_DIFF_BASE_SHA` |
| Publish target | `--target pr-branch`: commit onto `pull_request.head.ref` + `gh pr comment` | `--target pr-branch`: commit onto `$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME` + `glab` MR note |
| Secret | repository secret `QWEN_API_KEY` (+ optional `QWEN_BASE_URL`) | masked CI/CD variable `QWEN_API_KEY` |
| Push token | `AI_TW_PAT` (falls back to `github.token`) so the refresh commit triggers the `gate` check | `AI_TW_PAT` (falls back to `CI_JOB_TOKEN`) |
| Loop-guard | skip if head commit author is `beadloom-ai-techwriter` OR subject has `[skip ai-techwriter]` (sets `AI_TW_SKIP=1`) | same check on the head commit |
| Concurrency | `group: ci-<PR-number>`, `cancel-in-progress: true` (the whole `ci.yml`) | (single job per pipeline) |

Both wrappers call the **same** entrypoint — only the trigger, the secret naming,
`--platform`, and the publish `--target` differ:

```bash
# PR / MR path (commits the refresh into the existing PR/MR branch):
uv run python -m beadloom.ai_agents.ai_techwriter --platform <github|gitlab> --target pr-branch --since <merge-base>

# Manual workflow_dispatch path (no PR context → cut a branch + open a PR/MR):
uv run python -m beadloom.ai_agents.ai_techwriter --platform <github|gitlab> --target branch-pr --since <ref-or-HEAD~1>
```

`--target` selects the publish mode: `pr-branch` (the `pull_request` path) commits
the refresh onto the existing PR head branch and posts a PR/MR comment; `branch-pr`
(the default, used by the manual `workflow_dispatch` path that has no PR context)
cuts a fresh doc-refresh branch and opens a PR/MR. `--dry-run` reports the wiring
(including the resolved `since` + `target`) and exits without running the model or
publishing. An all-zero SHA (force-push / first-push) is treated as "no baseline".

**Loop-safe (BDL-049):** the agent commits its refresh with a `[skip ai-techwriter]`
message under the `beadloom-ai-techwriter` identity; the workflow's **loop-guard**
step inspects the PR head commit (`git log -1 --format='%an' / '%s'`) and skips the
run when the author is the bot OR the subject carries `[skip ai-techwriter]`, so the
agent's own `synchronize` push never spawns a second run. `cancel-in-progress: true`
also cancels a superseded in-flight run when a newer commit lands on the PR. The
human still merges the PR; that merge does not re-trigger the agent (it fires on PRs
to `main`, not on the merge commit).

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

- `docs/guides/agentic-flow.md` — the trunk-based development flow this PR-triggered
  loop is part of (feature branch → one PR to `main` → merge-when-green).
- `docs/services/cli.md` — `sync-check --since`, `sync-update --yes/--all`,
  `setup-ai-techwriter`, `setup-branch-protection`.
- `docs/domains/doc-sync/README.md` — `check_sync_since` / `mark_synced_by_ref`.
- `docs/domains/onboarding/README.md` — `ai_techwriter_setup.scaffold`.
- `docs/guides/ci-setup.md` — the general `beadloom ci` gate.
