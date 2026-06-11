# PRD: BDL-050 — CI consolidation ("порядок в CI")

> **Status:** Approved
> **Created:** 2026-06-11
> **Follows:** BDL-049 (trunk-based + PR-triggered AI tech-writer).

---

## Problem

After BDL-047→049 the CI is functional but **messy + partly redundant**, and two latent breakages reached `main` because not everything is gated on PRs:

- **Three independent PR workflows** (`beadloom-gate.yml`, `tests.yml`, `ai-techwriter.yml`) with no ordering: `ai-techwriter` runs **in parallel** with gate/tests, so it spends Qwen tokens (a paid $30/mo plan) even when the PR is already broken (gate/tests red).
- **Redundant `push: main` runs:** `beadloom-gate` + `tests` trigger on BOTH `pull_request` and `push: main`. Under strict trunk-based (`enforce_admins: true`, BDL-049) **nothing reaches `main` except via a green PR**, so the push-to-main runs are wasted compute (main is green by construction).
- **`tests.yml` is path-filtered** (`src/**`,`tests/**`,…) → it can't be a reliable strict *required* check (a PR not touching those paths skips it → a strict-required check would stall). That's why only `beadloom-gate` is required today — so a PR can merge without the matrix tests being required.
- **VitePress build is NOT a PR check** — it only runs on `push: main` (`deploy-site.yml`). Two breaks (SC2174; a `{{ }}` Vue-interpolation) merged green and only broke **after** landing on main.
- **Node20 action deprecation** (GitHub default switches 2026-06-16): every workflow uses `actions/checkout@v4` / `setup-uv@v5` / `setup-node@v4` / `configure-pages@v5` / `upload-pages-artifact@v3` on the Node20 runtime; `deploy-site` even pins `node-version: 18`.

## Impact

Consolidate to a single, ordered, fully-gated PR pipeline + a clean deploy, so merge-ability means "everything that protects `main` is green", tokens aren't wasted on broken PRs, and there are no redundant runs. Desired shape (owner):

```
PR open ─► gate ─┐
          tests ─┼─(all green?)─► ai-techwriter ─(ok / no-op?)─► PR unblocked
          site  ─┘   └─(any red)──────────────────────────────► PR blocked (ai-techwriter not even started)
merge → main ─────────────────────────────────────────────────► Deploy VitePress
```

Success criterion: **one `ci.yml` on `pull_request → main` runs gate + tests + site-build in parallel; `ai-techwriter` runs only after all three are green; the four are the required status checks (all green ⇒ mergeable, any red ⇒ blocked); no `push: main` gate/tests runs remain; `deploy-site` runs only on merge to main; all actions are Node24-compatible — dogfooded by this very PR.**

## Goals

- [ ] **G1 — One consolidated `ci.yml`** on `pull_request → main` with jobs: `gate` (`beadloom ci`), `tests` (3.10–3.13 matrix), `site-build` (`beadloom docs site` + vitepress build), and `ai-techwriter` with **`needs: [gate, tests, site-build]`** (runs only when all three succeed → no Qwen tokens on broken PRs).
- [ ] **G2 — `tests` reliably required:** drop the `paths:` filter (or run the matrix unconditionally on PRs) so `tests` always runs on every PR → it can be a strict required check without stalling.
- [ ] **G3 — `site-build` as a PR check** (closes `beadloom-wozp`): build the VitePress site on every PR → VitePress/mermaid/dead-link/interpolation breaks are caught **before** merge, not on `main`.
- [ ] **G4 — Required status checks = `gate`, `tests`, `site-build`, `ai-techwriter`.** Update `branch_protection` defaults + re-apply: all green ⇒ PR mergeable; any red ⇒ blocked. Owner still self-merges (0 reviews), `enforce_admins: true` kept.
- [ ] **G5 — Remove redundant `push: main` triggers** from gate/tests (now PR-only). `deploy-site` stays the ONLY thing on `push: main`.
- [ ] **G6 — Node24-compatible actions** across ALL workflows (closes `beadloom-t7vn`): bump `actions/*` to versions running on Node24 (and `deploy-site` `node-version` to a current LTS) before the 2026-06-16 default switch.
- [ ] **G7 — Preserve the BDL-049 model exactly:** `ai-techwriter` keeps `--since merge-base`, `--target pr-branch` (commit-into-PR), the loop-guard, `AI_TW_PAT` push, `cancel-in-progress`, and the `workflow_dispatch` branch-PR fallback. Vendored CI templates mirror the consolidation + re-vendored (drift-guard green).
- [ ] **G8 — Dogfood + docs:** this PR's own `ci.yml` gates this PR (eat our own dog food); guide/CHANGELOG/ROADMAP updated.

## Open architecture question (→ decided in the RFC)

**AI-TW as a required check — how strict?**
- **(Simple)** any non-zero `ai-techwriter` exit blocks the PR. Easiest, but an **infra failure** (Qwen 5xx / quota exhausted on the $30 plan / VPS runner down / `uv sync` fail) **blocks ALL merges** — even a perfect code-only PR with no doc drift. Couples shipping to agent operational health.
- **(Alternative)** block **only on a genuine `flagged`** result (agent ran, produced output, but couldn't make docs green) and **pass on infra failure** (agent never produced output — `tokens == 0` / process/provider error → exit 0 + a loud "⚠ docs NOT checked — re-run" annotation/comment). Requires the harness to **classify** flagged causes (doc-unresolvable/budget → block; process/network/5xx/quota → don't block) via a `tokens>0` discriminator, plus exit-code discipline (and possibly a second `docs-gate` job for clean separation). Harder, but decouples shipping from agent infra/budget.
- Lean: given the **$30 token plan + single self-hosted runner**, the Alternative is worth its modest extra complexity. RFC decides + sizes it.

## Non-goals (out of scope)

- **Rewriting the harness internals** / the BDL-049 publish model — only the trigger/structure/required-checks change (the AI-TW failure-classification in the Alternative is the one harness touch).
- **Auto-merge** — the human still merges; the required checks just gate it.
- **Moving runners** — gate/tests/site-build stay GitHub-hosted; ai-techwriter stays on the self-hosted VPS.
- **GitLab parity beyond mirroring** the same structure into the vendored templates (GitLab uses `needs`/stages analogously; validated separately on the team repo).
- **Model tiering** (principle 10).

## User stories

### US-1: Broken PR doesn't waste Qwen tokens
**As** the maintainer on a $30 token plan, **I want** `ai-techwriter` to run only after gate + tests + site-build are green, **so that** a broken PR never spends model tokens.
**Acceptance:** with a red gate or test, the `ai-techwriter` job is `skipped` (never starts); with all-green, it runs once.

### US-2: Everything that protects main is gated on the PR
**As** the maintainer, **I want** gate, tests, AND the VitePress build all required on PRs, **so that** nothing that breaks `main` (test failure, doc-build error) can merge green.
**Acceptance:** a PR with a failing matrix test OR a VitePress build error is **blocked**; `main` stays green + deployable by construction.

### US-3: No redundant runs, Node24-ready
**As** the maintainer, **I want** no `push: main` gate/tests runs and all actions Node24-compatible, **so that** CI is lean and won't break on 2026-06-16.
**Acceptance:** merging a PR triggers only `deploy-site` on main; no gate/tests run on the merge; no Node20 deprecation warnings.
