# CONTEXT: BDL-050 — CI consolidation

> **Status:** Approved
> **Created:** 2026-06-11
> **PRD/RFC:** ./PRD.md · ./RFC.md

---

## State

- **Workflows today:** `beadloom-gate.yml` (push:main + PR), `tests.yml` (push:main + PR, **paths-filtered**, `workflow_call`), `ai-techwriter.yml` (PR + dispatch, BDL-049 model: `--since merge-base`, `--target pr-branch`, loop-guard, `AI_TW_PAT` push, `cancel-in-progress`), `deploy-site.yml` (push:main + dispatch; `node-version: 18`, `setup-node@v4`, `configure-pages@v5`, `upload-pages-artifact@v3`).
- **Branch protection (BDL-049):** `enforce_admins: true`, required check `beadloom-gate`, 0 reviews; `branch_protection.py` `DEFAULT_STATUS_CHECK_CONTEXTS=("beadloom-gate",)` + `--check` override + `setup-branch-protection` CLI.
- **Harness exit codes (BDL-049):** `cli.py` → 0-stale/clean→0, flagged→1; `runner.py` sets `result.flagged` + `flagged_reasons` for budget-exceeded / fixpoint-stuck / agent-failed-all-attempts; `result.input_tokens`/`output_tokens` already tracked (the verdict discriminator).
- **Site build:** `beadloom docs site --out site` then `npm ci` + `npm run docs:build` (vitepress) — currently only in `deploy-site`.
- **Repo is strict trunk-based** (see [[project_trunk_based]]) — work on `features/BDL-050`, PR to main, self-merge when the (new) checks are green.

## Decisions (from PRD/RFC)

- One `ci.yml` (pull_request→main): `gate ∥ tests(3.10–3.13) ∥ site-build` → `ai-techwriter` (`needs:` all three). Delete the 3 old workflows; `deploy-site` stays the only push:main job.
- **AI-TW = Alternative:** harness `verdict ∈ {ok, flagged, infra}` (discriminator `tokens>0`); `cli.py` exit ok/infra→0, flagged→1; infra emits a `::warning::` + PR comment. A dead runner / exhausted $30 quota must NOT block merges; real unresolved drift must.
- Required checks = `gate`, `tests (3.10..3.13)`, `site-build`, `ai-techwriter`; `branch_protection` default updated + re-applied (enforce_admins:true, 0 reviews kept).
- Drop `tests` paths filter; remove push:main from gate/tests; Node24-bump all actions + `deploy-site` node 18→22.
- Preserve BDL-049 ai-techwriter body 1:1; re-vendor CI templates; GitLab mirror via stages+needs.

## Code standards (from CLAUDE.md §0.1)

- Python 3.10+, Click, mypy --strict, ruff, pytest (≥80% changed), DDD boundaries (`lint --strict`). No `Any`/ignore w/o reason, no bare except, no `import *`, no mutable defaults. Shell: `-f` on cp/mv/rm.
- The only Python touch is `tools/ai_techwriter/{runner,cli}.py` (verdict) + `onboarding/branch_protection.py` (contexts); the rest is workflow YAML + templates + tests.
- Valid YAML (`yaml.safe_load` in tests); `bash -n` for inline shell.

## Constraints / invariants

- **This feature's own PR is the dogfood** — once `ci.yml` lands on `main`, the dogfood is a follow-up PR on the live consolidated pipeline (GitHub runs `pull_request` workflows from the PR branch, so the new `ci.yml` is exercised on this very PR too; the required-check **set** only takes effect after branch-protection is re-applied).
- Beadloom green on its own `beadloom ci` + full pytest after each wave.
- BDL-048 drift-guard must stay green (re-vendor after editing CI templates).
- Verdict classification must be conservative: `tokens==0 ⇒ infra`; never misclassify a real doc failure as infra without it being visible (annotation).
- Anonymize third-party project names in committed artifacts.

## Definition of done

All G1–G8 met; one `ci.yml` with the needs-ordering; AI-TW verdict (ok/flagged/infra) gates correctly; tests un-filtered + required; site-build a PR check; no push:main gate/tests; Node24-clean; branch protection updated; templates re-vendored; dogfood-proven (red gate ⇒ ai-tw skipped ⇒ blocked; all-green ⇒ ai-tw runs ⇒ verdict gates; deploy on merge); docs updated; suite + `beadloom ci` green.
