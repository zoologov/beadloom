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

### Composed, not snapshotted (BDL-061 S3, completed by BDL-068 `beadloom-iur5`)

The commands and `CLAUDE.md` used to be byte-identical snapshots of Beadloom's
own live `.claude/`, refreshed by `sync_agentic_flow`. That direction was the
defect: the distributed artifact could not differ from one project's local text
by construction, so a project-local paragraph — a bead id and a claim about this
repo's branch protection that is false for an adopter — reached the shipped
template, was corrected, and was re-propagated over the correction by the very
next run (BDL-UX #177).

BDL-061 S3 reversed it for two artifact kinds and left the third. Five
`templates/agentic_flow/agents/*.md.txt` assets remained a snapshot of this
repository's live `.claude/agents/`, refreshed by the same `sync_agentic_flow`
and asserted byte-identical by two tests. `beadloom-iur5` deleted the assets and
the function.

The direction is now reversed for every artifact this command writes:

- the shipped CORE is **authored package data** — `templates/agentic_flow/` for
  the commands and `CLAUDE.md`, `templates/roles/` for the role protocols;
- `.claude/CLAUDE.md`, `.claude/commands/*` and `.claude/agents/*` are all
  **composed** from it — `composed_claude_md()` / `composed_command()` /
  `role_composer.compose_all_roles()` call `composer.compose(...)` for the
  repo's `flow.yml` plus its `.beadloom/flow/` project layer;
- a local divergence is **reported** by `config-check`, not flowed outward;
- **no function in this module writes package data.** That is what makes the
  reversal structural rather than a convention: there is nothing left to run
  that could carry a local file outward.

Nothing writes the `CLAUDE.md` core, which also closes BDL-UX #132: a `--force`
run inside Beadloom's own repo can no longer overwrite the
`__BEADLOOM_PROJECT_NAME__` placeholder with the substituted name.

### Role files

`AGENT_FILES` is `role_composer.ROLE_NAMES` itself since BDL-068 S1.5, not a second literal beside it: the two used to be separate tuples whose comments each claimed to mirror the other, so a role added to one was present to the composer and absent from this module's scaffold and from `orphaned_flow_files`.

Since BDL-052 the role files (`.claude/agents/*`) are composed from a CORE
definition plus DDD/FSD and stack overlays by `role_adapters.generate_adapters`,
which is the source of truth for those files and writes one adapter set per
configured tool. `scaffold(..., include_agents=False)` leaves them to it, and the
CLI passes exactly that.

The default, `include_agents=True`, is not dead and is not a byte-copy any more.
It is reached from `config_sync.refresh_agentic_flow_files()`, which passes
`include_agents=not has_flow` — so `config-check --fix` on a repository that
adopted the flow before `.beadloom/flow.yml` existed writes the single
`.claude/agents/` set here, because `refresh_composed_adapters()` returns empty
without a `flow.yml` and there is no adapter generator to defer to. Since
`beadloom-iur5` that path goes through `_scaffold_composed()` like the commands:
the bodies are `compose_all_roles(config, project_root)`, each write is recorded
in the flow manifest, and a hand-edited file is preserved and reported instead of
being compared against fixed bytes and skipped without a remedy.

That change has a second effect worth stating plainly: the snapshot was ONE
composition — this project's `ddd` and `python` — so an adopter whose flow
declared anything else received role protocols for an architecture they do not
use. They now receive their own.

### One policy for every artifact the command writes

The command writes three kinds of artifact into a repository it does not own:
the composed role adapters (`.claude/agents/*`), the slash commands
(`.claude/commands/*`) and `.claude/CLAUDE.md`. All three answer a hand edit the
same way, and `--force` is the one door that adopts the composed body over one.

`_scaffold_composed()` classifies the commands and `CLAUDE.md` through the flow
manifest before touching them; the role adapters are classified by
`config_sync.declined_adapter_rewrites()` — the same classification
`config-check` prints and `--fix` decides on — and passed to
`generate_adapters(..., preserve=…)`:

| state | action |
|-------|--------|
| `clean` | nothing |
| `stale` — matches what Beadloom last wrote | recomposed in place |
| `hand_edited` | **skipped**, reported with the `.beadloom/flow/<kind>/<name>.md` path the edit belongs in |
| `unverified` — nothing accounts for it | skipped, reported, `--force` adopts the composed version |
| `missing` — recorded and gone from disk | recomposed in place |

That is the difference between an idempotent generator and one that eats work.

#### The role adapters were the exception until BDL-068 `.67` (BDL-UX #191)

They were composed through `generate_adapters(config, project_root)` with no
`preserve` argument, so one command answered one hand edit two ways and nothing
an adopter could read said which was intended. Measured before the fix, on a
scratch project scaffolded by the shipped command, with the same two lines
appended to one file of each kind and one re-run with no flags:

| file | outcome | what the run printed |
|------|---------|----------------------|
| `.claude/agents/dev.md` | edit destroyed | `Wrote .claude/agents/dev.md (claude)` |
| `.claude/commands/coordinator.md` | edit preserved | `Skipped …` + the migration note |
| `.claude/CLAUDE.md` | edit preserved | `Skipped …` + the migration note |

Two readings were defensible — a repair must not destroy, a scaffold may
reasonably reinstate the shipped flow — so the inconsistency was the defect
either way. It was settled towards preservation on evidence already in the
product rather than on preference:

- The `--force` flag is documented as "Overwrite hand-edited scaffolded flow
  files (default: preserve them)". A role adapter is a scaffolded flow file, so
  the default was already specified and only the adapters broke it.
- `config-check` prints the identical sentence over `.claude/agents/dev.md` and
  `.claude/commands/coordinator.md` — "hand-edited: … It will **NOT** be
  rewritten" — under a remediation that says to re-run `setup-agentic-flow`.
  Following that remediation literally destroyed one of the two edits.
- It removes a policy rather than adding one. Three artifact kinds now answer
  one question one way, and the flow manifest still lets every body Beadloom
  wrote be recomposed, so an upgrade lands unchanged.

The decision was previously recorded in one place only: the docstring of
`tests/test_cli_setup_agentic_flow.py::test_cli_recomposes_hand_edited_agent_file`,
which asserted the opposite of what the same file's command help promised. That
test now asserts preservation and carries the retired reading in its docstring.

A neighbouring artifact was settled the other way for its own reason and does
not contradict this: the generated `.gitignore` block is **reported and never
rewritten at all**, because `ignore_block`'s published contract is written-once
and no manifest could prove a line there is Beadloom's. Here a manifest can, so
"recompose what we wrote" stays available. See the
[config-check SPEC](../config-check/SPEC.md).

### Cross-major re-init (BDL-UX #137)

`orphaned_flow_files(project_root)` reports files a PRIOR layout left behind —
the four role files and `epic-init.md` under `.claude/commands/`, which this
layout no longer owns — each with the exact `rm -f` command and, for a role, the
path it moved to. They are **reported, never removed**: deleting a file the
adopter may have edited is not ours to decide.

**They now reach the terminal (BDL-UX #188).** Until BDL-061 S3b both this list
and `ScaffoldResult.migration_notes` were computed on every run and read by
nothing outside the library: `#137` was recorded as closed *by the orphan
report* and S3's criterion "a hand-edited scaffolded file is reported with
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
  reported with somewhere to put the edit — for **every** artifact kind the
  command writes, the role adapters included (BDL-UX #191).
- A file the flow manifest proves Beadloom wrote is still recomposed on every
  run, so an upgrade lands without `--force`.
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
- `ScaffoldResult` — files written/skipped, the CLAUDE.md path and changed
  sections, plus `orphans`, `migration_notes` and `flow_config_written`
- `SUPERSEDED_COMMAND_FILES` — what a prior layout left in `.claude/commands/`

## Testing

Tests: `tests/test_cli_setup_agentic_flow.py`, `tests/test_flow_composition.py`
