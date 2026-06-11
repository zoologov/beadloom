# RFC: BDL-050 — CI consolidation

> **Status:** Approved
> **Created:** 2026-06-11
> **PRD:** ./PRD.md

---

## Summary

Replace the three PR workflows with **one `.github/workflows/ci.yml`** on `pull_request → main`:

```
ci.yml (on: pull_request → main)
  job gate        (ubuntu)        beadloom ci
  job tests       (ubuntu, 3.10–3.13 matrix)
  job site-build  (ubuntu)        beadloom docs site + vitepress build
  job ai-techwriter (self-hosted) needs: [gate, tests, site-build]   # runs only if all green
```
`deploy-site.yml` stays the ONLY thing on `push: main`. `beadloom-gate.yml` / `tests.yml` / `ai-techwriter.yml` are retired (folded into `ci.yml`); `workflow_dispatch` (branch-PR manual path) moves onto `ci.yml`. All actions bumped Node24-compatible.

## Decisions on the open questions

1. **AI-TW strictness → the Alternative (chosen by the owner):** `ai-techwriter` is a required check that is **red only on a genuine `flagged` doc-resolution failure**; an **infra failure passes** (green) with a loud annotation. Implemented by a **harness verdict** + **exit-code discipline** in `tools/ai_techwriter/` (one harness touch, no second job):
   - `runner.py` computes a `verdict ∈ {ok, flagged, infra}`:
     - **ok** — 0-stale no-op OR a clean refresh (gate green).
     - **flagged** (block) — the agent **produced output** (`input_tokens + output_tokens > 0`) but docs aren't clean: post-refresh `beadloom ci` red, fixpoint-not-reached, or budget-exceeded. Genuine "needs human".
     - **infra** (don't block) — the agent **never produced output** (`tokens == 0`) because the goose/provider call failed (process error, network, HTTP 5xx, quota exhausted) → it *couldn't run*, not a doc problem.
     - **Discriminator = `tokens > 0`.** Split today's blanket `result.flagged` accordingly (the "agent failed for ref after N attempts" reason becomes `infra` when no attempt produced tokens, `flagged` otherwise).
   - `cli.py` maps verdict → exit code: **ok→0, infra→0, flagged→1**. On `infra` it ALSO emits a GitHub `::warning::` annotation + (best-effort) a PR comment: "⚠ AI tech-writer could not run (infra) — docs were NOT checked on this PR; re-run before relying on freshness."
   - Net: a dead VPS / exhausted $30 quota does NOT freeze merges; a real unresolved doc drift does.
   - Rejected sub-option: a second `docs-gate` job reading the run-record. The single-job exit-code is simpler and sufficient.

2. **Ordering via `needs` + GitHub skipped-required semantics:** `ai-techwriter` has `needs: [gate, tests, site-build]`, so a red gate/test/site → `ai-techwriter` is **skipped** (no Qwen tokens). GitHub treats a *skipped* required check as **neutral/passing**, so the broken PR is still blocked **by the red gate/test/site** (not by the skipped ai-techwriter); once they're green, `ai-techwriter` actually runs and gates on its verdict. **The dogfood must confirm this exact behavior** (red gate ⇒ ai-techwriter skipped ⇒ PR blocked by the gate; all-green ⇒ ai-techwriter runs ⇒ verdict gates).

3. **`tests` required without stalling:** drop the `paths:` filter — the matrix runs on **every** PR, so each leg is a reliable required check.

4. **Required status checks (branch protection):** `gate`, `tests (3.10)`, `tests (3.11)`, `tests (3.12)`, `tests (3.13)`, `site-build`, `ai-techwriter`. Update `branch_protection.DEFAULT_STATUS_CHECK_CONTEXTS` to this set; re-apply via `setup-branch-protection`. Keep `enforce_admins: true`, 0 reviews (owner self-merges; strict trunk-based intact).

5. **No `push: main` gate/tests** — removed (main is green by construction under strict trunk-based). `deploy-site` (with `site-build` already proven on the PR) is the only push-main job + the loud main-side safety net.

## `ci.yml` shape (GitHub)

- `on: pull_request: {types:[opened,synchronize,reopened], branches:[main,master]}` + `workflow_dispatch` (branch-PR manual path).
- `concurrency: {group: ci-${{ github.event.pull_request.number || github.ref }}, cancel-in-progress: true}`.
- `permissions: {contents: write, pull-requests: write}` (for ai-techwriter's pr-branch push/comment).
- **gate / tests / site-build:** `runs-on: ubuntu-latest`, `actions/checkout@<v-node24>` (no PAT needed — read-only), `uv sync`, then `beadloom ci` / the pytest matrix / (`beadloom docs site --out site` + `npm ci` + `npm run docs:build`).
- **ai-techwriter:** `runs-on: [self-hosted, ai-techwriter]`, `needs: [gate, tests, site-build]`, the FULL BDL-049 body unchanged — loop-guard step, checkout with `token: ${{ secrets.AI_TW_PAT || github.token }}` on the PR head ref, `--since $(git merge-base origin/$BASE HEAD)`, `--target pr-branch`, `GH_TOKEN: AI_TW_PAT||GITHUB_TOKEN`, `PR_URL`. Only the trigger moves (into `ci.yml`) + the new verdict exit-code.

`deploy-site.yml`: unchanged logic; bump actions + `node-version` only.

## GitLab mirror

`.gitlab-ci.yml`: stage `verify` = `gate`,`tests`,`site-build` (parallel); stage `docs` = `ai-techwriter` with `needs: [gate, tests, site-build]` + `rules: $CI_PIPELINE_SOURCE == "merge_request_event"`. Same AI_TW_PAT push + verdict exit handling. Vendored templates (`templates/ai_techwriter/*`) mirror the consolidated structure; re-vendor (drift-guards green).

## Node24 bump (G6)

Bump every workflow's actions to the current Node24-running majors (the dev **verifies each tag actually runs on Node24**; if any laggards remain, set `env: FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` as a documented stopgap): `actions/checkout`, `astral-sh/setup-uv`, `actions/setup-node`, `actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages`. `deploy-site` `node-version: 18 → 22` (current LTS). Acceptance: no Node20 deprecation annotations.

## Component / file impact

| Component | Change |
|-----------|--------|
| `.github/workflows/ci.yml` (NEW) | consolidated gate/tests/site-build/ai-techwriter with `needs` |
| `.github/workflows/{beadloom-gate,tests,ai-techwriter}.yml` | **deleted** (folded into ci.yml) |
| `.github/workflows/deploy-site.yml` | actions + node-version bump only (stays push:main) |
| `.gitlab-ci.yml` | consolidated stages + needs mirror |
| `tools/ai_techwriter/runner.py` + `cli.py` | `verdict {ok,flagged,infra}` (tokens>0 discriminator) + exit-code map + infra annotation/comment |
| `src/beadloom/onboarding/branch_protection.py` | default contexts → the new 7-check set |
| `onboarding/templates/ai_techwriter/*` | consolidated CI template + gitlab mirror; re-vendor |
| `tests/*` | ci.yml structure (yaml-valid, needs, no push:main, Node24 tags), verdict classification (ok/flagged/infra exit codes), branch_protection contexts, drift-guard |
| docs/guides + CHANGELOG + ROADMAP | tech-writer |

## Alternatives considered

- **Keep 3 workflows + just add `needs` via `workflow_run` chaining.** Rejected: `workflow_run` runs in base-branch context, awkward for PR head + the agent's push; one `ci.yml` with `needs` is far simpler.
- **AI-TW Simple (any non-zero blocks).** Rejected by the owner — couples shipping to agent infra/$30 quota.
- **Second `docs-gate` job for the Alternative.** Rejected — single-job exit-code is enough.
- **Keep gate/tests on push:main as a safety net.** Rejected — redundant under strict trunk-based; `deploy-site` + `site-build`-on-PR already cover the main side.

## Risks & mitigations

- **GitHub skipped-required-check semantics** (the crux). → the dogfood explicitly verifies: red gate ⇒ ai-techwriter skipped ⇒ PR blocked by the gate; all-green ⇒ ai-techwriter runs ⇒ gates on verdict. Fallback if skipped-required behaves unexpectedly: an always-running `docs-gate` job that fails only on `verdict==flagged`.
- **verdict misclassification** (infra vs flagged on partial-token failures). → conservative rule: `tokens==0` ⇒ infra; any tokens ⇒ trust the doc-gate result; unit-test the boundary; the infra annotation makes a wrong "infra" visible (human re-runs).
- **Required-check rename lockout** (renaming beadloom-gate→gate while protection requires the old name). → apply the new branch-protection set in the SAME change; the dogfood confirms a PR is mergeable under the new names; escape hatch = temporarily drop protection via API.
- **Node24 tag drift.** → verify each action runs on Node24; FORCE env stopgap.

## Rollout

Waves: dev (`.1` ci.yml consolidation + delete old workflows + Node24 → `.2` AI-TW verdict classification in the harness → `.3` branch_protection contexts + GitLab mirror + re-vendor) → test → review → **dogfood (`.6`: this PR's own ci.yml gates it — confirm needs-ordering, tokens-saved-on-red, verdict exit codes, required-checks-block-correctly, deploy on merge)** → tech-writer. The PR for this feature is the live trunk-based proof.
