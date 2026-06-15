# Agentic Flow Setup

The `setup-agentic-flow` scaffolder, in the onboarding domain.

**Source:** `src/beadloom/onboarding/agentic_flow_setup.py`

---

## Specification

### Purpose

Make Beadloom's proven multi-agent development flow reproducible on a fresh repo
in one command. `beadloom setup-agentic-flow` drops the `.claude/commands/*`
slash skills (the coordinator playbook) byte-identical to the live flow and
generates the `.claude/CLAUDE.md` auto-managed regions for the target project —
the flow's effectiveness lives in the exact wording, so the vendored assets are
preserved verbatim, never rewritten or condensed.

### Role files

Since BDL-052, the role files (`.claude/agents/*`) are **composed** from a CORE
definition plus DDD/FSD and stack overlays by `role_adapters.generate_adapters`,
which is the source of truth for those files. `scaffold(..., include_agents=False)`
leaves them to the composer; the default still drops the vendored agents for the
plain byte-identical scaffold path. `sync_agentic_flow` refreshes the packaged
assets from a live `.claude/` so the templates and the canonical source cannot
silently diverge — the drift-guard the `config-check` step relies on.

## Invariants

- Vendored `commands/*` are written byte-for-byte (1:1) with the live flow.
- The scaffold is idempotent and safe to re-run; `force` overwrites
  hand-edited scaffolded files.
- A drift-guard catches divergence between the scaffolded files and the
  canonical source.

## API

Module `src/beadloom/onboarding/agentic_flow_setup.py`:

- `scaffold(project_root, *, force=False, include_agents=True) -> ScaffoldResult`
  — drop the vendored commands + generate the CLAUDE.md auto-regions.
- `sync_agentic_flow(live_claude_root) -> list[str]` — refresh the packaged
  assets from a live `.claude/`.
- `ScaffoldResult` — what was written/skipped (agents, commands, CLAUDE.md).

## Testing

Tests: `tests/test_cli_setup_agentic_flow.py`
