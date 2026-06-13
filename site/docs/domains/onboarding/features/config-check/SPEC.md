<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`config-check`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Config Check (AgentConfigAsCode)

Drift detection for generated agent-config artifacts, in the onboarding domain.

**Source:** `src/beadloom/onboarding/config_sync.py`

---

## Specification

### Purpose

Treat the agent-config artifacts that Beadloom generates as code: detect drift
between the generated output and the committed files, and (with `--fix`)
re-render them. Three artifact classes are owned: `.beadloom/AGENTS.md` (fully
generated, with a preserved `custom` block), the auto-managed sections of
`.claude/CLAUDE.md` (between the `beadloom:auto-start` / `auto-end` markers),
and the thin IDE adapter files (`.cursorrules`, …).

### Contract

- **Input:** the project's committed config artifacts + the current generator.
- **Output:** a drift report per artifact; `config-check` exits non-zero on
  drift unless `--fix` re-baselines.
- **Invariants:** user-authored `custom` blocks and prose outside the managed
  markers are preserved across regeneration.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
