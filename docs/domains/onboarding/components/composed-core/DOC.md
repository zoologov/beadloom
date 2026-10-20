# Composed Core (component)

Internal building block of the onboarding domain.

**Source:** `src/beadloom/onboarding/composed_core.py`

---

## Overview

Two files carry the composed core. Claude reads `.claude/CLAUDE.md`, and Cursor reads
`.cursor/rules/beadloom-flow.mdc`, whose body is the same text under front matter (RFC D13).
Both hold the auto-managed regions rendered for the project: `project-info` (stack,
dependencies, version) and `doc-language`. Those regions move with every release, while the
composition they sit in does not.

Before this component the two files were handled by two copies of the logic. The `CLAUDE.md`
checks blanked the regions before comparing the body and refreshed them separately. The
Cursor rule's check compared the whole body, and nothing refreshed its regions. Measured at
`b7d46e27` on a project composed for both tools: after the version went from 1.0.0 to 2.0.0
and a dependency was added, `config-check` exited 1 and blamed the Cursor rule on "CORE + the
flow.yml overlays + the project layer", none of which had moved, and `setup-rules --refresh`
repaired `CLAUDE.md` and left the rule stale (BDL-083 S2R pass 1 Major 1).

## Behaviour

- **One comparison.** A carrier's body is classified against its composition and the
  manifest's record with every region's body blanked on every side: the file, the
  composition, each alternate and the recorded digest. A moved region is therefore never a
  moved body.
- **One record.** The digest the scaffold writes for a carrier is taken over the blanked text,
  so a release does not turn a file Beadloom wrote into one it cannot account for.
- **One refresh.** The regions are re-rendered in every carrier on disk. A region edited by
  hand reads as the region gone stale, in either file, and the refresh re-renders it. An edit
  outside the regions is a hand edit of the body and is reported as one.

The refresh reaches a Cursor core rule on disk whether or not `flow.yml` still names
`cursor`. That is the same population limit the Cursor rules have elsewhere: they are not
in the orphan report when `cursor` leaves `tools:`.

## Public surface

- `core_carriers() -> tuple[str, ...]` — `.claude/CLAUDE.md` and the Cursor core rule,
  project-relative.
- `core_state(*, on_disk, expected, recorded, alternates=(), accounted=False) -> ArtifactState`
  — the one comparison.
- `core_digest(text) -> str` — the fingerprint recorded for a carrier.
- `refresh_core_regions(project_root, *, dry_run=False) -> dict[str, list[str]]` — the
  changed regions per carrier, for the carriers whose regions changed.
- `CLAUDE_MD_RELPATH` (`".claude/CLAUDE.md"`).

## Readers

`agentic_flow_setup` scaffolds both carriers through `_scaffold_core`. `config_sync` reads
`refresh_core_regions` in dry-run mode for the region findings, one per file, each reading
`auto-managed section(s) stale: <names>`. It reads `core_state` for the body of `CLAUDE.md`
and of the Cursor core rule, and `refresh_core_regions` again under `config-check --fix`.
`setup-rules --refresh` prints one line per carrier on disk.

## Testing

`tests/unit/onboarding/composed_core/test_the_carriers_of_the_composed_core.py` holds the
comparison, the digest and the refresh over hand-built texts. The verdicts they decide are
held by `tests/unit/onboarding/config_sync/test_a_release_moves_the_rendered_section_in_both_tools.py`
and `tests/acceptance/onboarding/config-check/a_release_moves_the_rendered_section_in_both_tools.feature`.
