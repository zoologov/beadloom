<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`agentic-flow-setup`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Agentic Flow Setup

The `setup-agentic-flow` scaffolder, in the onboarding domain.

**Source:** `src/beadloom/onboarding/agentic_flow_setup.py`

---

## Specification

### Purpose

Make Beadloom's proven multi-agent development flow reproducible on a fresh repo
in one command. `beadloom setup-agentic-flow` vendors the `.claude/agents/*.md`
and `.claude/commands/*.md` templates (the role protocols + coordinator
playbook) **1:1** — the flow's effectiveness lives in the exact wording, so it
is preserved verbatim, never rewritten or condensed.

### Contract

- **Input:** the target repo.
- **Output:** the `agents/*` + `commands/*` templates plus a drift-guard.
- **Invariants:** templates are vendored byte-for-byte (1:1); a drift-guard
  catches divergence from the canonical source.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
