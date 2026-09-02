# Agentic Flow Setup

The `setup-agentic-flow` scaffolder, in the onboarding domain.

**Source:** `src/beadloom/onboarding/agentic_flow_setup.py`

---

## Specification

### Purpose

Make Beadloom's proven multi-agent development flow reproducible on a fresh repo
in one command. `beadloom setup-agentic-flow` writes the `.claude/commands/*`
slash skills and `.claude/CLAUDE.md`, and generates the CLAUDE.md auto-managed
regions for the target project. The flow's effectiveness lives in the exact
wording, so the shipped CORE is preserved verbatim — never rewritten or
condensed — and a project adapts it by *appending*, not by editing.

### Composed, not snapshotted (BDL-061 S3)

The commands and `CLAUDE.md` used to be byte-identical snapshots of Beadloom's
own live `.claude/`, refreshed by `sync_agentic_flow`. That direction was the
defect: the distributed artifact could not differ from one project's local text
by construction, so a project-local paragraph — a bead id and a claim about this
repo's branch protection that is false for an adopter — reached the shipped
template, was corrected, and was re-propagated over the correction by the very
next run (BDL-UX #177).

The direction is now reversed:

- the shipped CORE is **authored package data**;
- `.claude/CLAUDE.md` and `.claude/commands/*` are **composed** from it —
  `composed_claude_md()` / `composed_command()` call
  `composer.compose(...)` for the repo's `flow.yml` plus its `.beadloom/flow/`
  project layer;
- a local divergence is **reported** by `config-check`, not flowed outward.

`sync_agentic_flow(live_claude_root)` therefore refreshes the packaged **agent**
assets only. Nothing writes the `CLAUDE.md` core any more, which also closes
BDL-UX #132: a `--force` run inside Beadloom's own repo can no longer overwrite
the `__BEADLOOM_PROJECT_NAME__` placeholder with the substituted name.

### Role files

`AGENT_FILES` is `role_composer.ROLE_NAMES` itself since BDL-068 S1.5, not a second literal beside it: the two used to be separate tuples whose comments each claimed to mirror the other, so a role added to one was present to the composer and absent from this module's vendored scaffold and from `orphaned_flow_files`.

Since BDL-052 the role files (`.claude/agents/*`) are composed from a CORE
definition plus DDD/FSD and stack overlays by `role_adapters.generate_adapters`,
which is the source of truth for those files. `scaffold(..., include_agents=False)`
leaves them to the composer; the default still drops the vendored agents for the
plain byte-identical scaffold path (a repo with no `flow.yml`).

### What a re-run does to an existing file

`_scaffold_composed()` classifies each target through the flow manifest before
touching it:

| state | action |
|-------|--------|
| `clean` | nothing |
| `stale` — matches what Beadloom last wrote | recomposed in place |
| `hand_edited` | **skipped**, reported in `ScaffoldResult.migration_notes` with the `.beadloom/flow/<kind>/<name>.md` path the edit belongs in |
| `unverified` — nothing accounts for it | skipped, reported, `--force` adopts the composed version |
| `missing` — recorded and gone from disk | recomposed in place |

That is the difference between an idempotent generator and one that eats work.

### Cross-major re-init (BDL-UX #137)

`orphaned_flow_files(project_root)` reports files a PRIOR layout left behind —
the four role files and `epic-init.md` under `.claude/commands/`, which this
layout no longer owns — each with the exact `rm -f` command and, for a role, the
path it moved to. They are **reported, never removed**: deleting a file the
adopter may have edited is not ours to decide.

**They now reach the terminal (BDL-UX #188).** Until BDL-061 S3b both this list
and `ScaffoldResult.migration_notes` were computed on every run and read by
nothing outside the library: `#137` was recorded as closed *by the orphan
report* and S3's criterion "a hand-edited vendored file is reported with
migration guidance" as met, and both claims were true of `scaffold()` and false
of `beadloom setup-agentic-flow`. What the user actually saw was `Skipped
.claude/commands/coordinator.md (hand-edited; use --force)` — advice to run the
destructive flag, naming nowhere the edit could safely go. The command prints
both lists after the write summary; the `--force` line is gone. NO CALLER, NO
CAPABILITY: a function nothing calls reads as "the feature exists".

### The configuration is recorded, not just resolved (BDL-UX #187)

A first scaffold writes `.beadloom/flow.yml` — the selection every composed
artifact is built from — through `persist_flow_config()`, and never over an
existing one. See the flow-config SPEC for why a virgin scaffold used to leave
`config-check` at exit 1.

## Invariants

- The scaffold is idempotent and safe to re-run.
- A hand-edited file is never rewritten without `--force`, and is always
  reported with somewhere to put the edit.
- Orphans from a previous layout are named, never deleted — **and printed**.
- A first scaffold leaves `beadloom config-check` at exit 0.
- Beadloom's own `.claude/` reproduces exactly from CORE + its overlays + its
  own project layer — the drift-guard that replaced "the template equals our
  file".

## API

Module `src/beadloom/onboarding/agentic_flow_setup.py`:

- `scaffold(project_root, *, force=False, include_agents=True, config=None) -> ScaffoldResult`
  — `config` is the caller's already-resolved selection (the CLI's, with its
  flags); omitting it re-resolves from disk
- `composed_command(name, config, project_root) -> str`
- `composed_claude_md(config, project_root, *, project_name) -> str`
- `orphaned_flow_files(project_root) -> list[str]`
- `sync_agentic_flow(live_claude_root) -> list[str]` — agents only
- `ScaffoldResult` — files written/skipped, the CLAUDE.md path and changed
  sections, plus `orphans`, `migration_notes` and `flow_config_written`
- `SUPERSEDED_COMMAND_FILES` — what a prior layout left in `.claude/commands/`

## Testing

Tests: `tests/test_cli_setup_agentic_flow.py`, `tests/test_flow_composition.py`
