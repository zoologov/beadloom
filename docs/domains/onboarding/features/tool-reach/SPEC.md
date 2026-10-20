# Tool Reach

Where each declared tool reads the composed flow, and which layers one tool reads that
another does not.

**Source:** `src/beadloom/onboarding/tool_reach.py`

---

## Specification

### Purpose

Up to 9.0.0 the role files were the only artifact composed for every tool. The core,
the project layer, the STACK overlay and the four commands were written under
`.claude/` whatever `tools:` said, so a project naming Cursor received five role files
and a 17-line pointer. An agent on Cursor ran the flow with no tracker discipline, no
Definition of Done and no closure duties, and nothing compared one tool's composition
with another's (BDL-UX #356, BDL-083 RFC D13).

This module states the reach in one table and derives the comparison from it.

### What each tool reads

| Slot | Claude | Cursor | Composed as |
|------|--------|--------|-------------|
| core | `.claude/CLAUDE.md` | `.cursor/rules/beadloom-flow.mdc` | `claude` / `cursor` kind |
| commands | `.claude/commands/<name>.md` | `.cursor/rules/beadloom-<name>.mdc` | `commands` kind |
| roles | `.claude/agents/<role>.md` | `.cursor/agents/<role>.md` | `roles` kind |

`tool_targets(tool)` returns that table for one tool. A Cursor rule is the composed text
under front matter that applies it to every request:

```
---
description: <what the rule carries>
globs:
alwaysApply: true
---
<the composed body, byte for byte>
```

`cursor_rule_text(body, description=...)` writes that form and `rule_body(text)` reads
the body back, so the core rule's body is compared byte for byte with `.claude/CLAUDE.md`
and each command rule's body with its `.claude/commands/<name>.md`. The core rule's
auto-regions are rendered for the project by `scanner.render_auto_regions`, the same
renderer `refresh_claude_md` uses, which is what makes the two bodies identical.

### Which project layer reaches which tool

| Project-layer folder | Reaches |
|----------------------|---------|
| `.beadloom/flow/roles/` | every tool's role files |
| `.beadloom/flow/commands/` | every tool's commands |
| `.beadloom/flow/claude/` | every tool's core: `.claude/CLAUDE.md` and Cursor's core rule |
| `.beadloom/flow/cursor/` | Cursor's core rule only, composed after the `claude` fragment |

The `cursor` artifact kind reads the `claude` folder first, so a rule an adopter wrote
for the core reaches Cursor as it reaches Claude, from one copy. Two copies of one
Definition of Done drift the moment one is edited, which is the reason the shared role
fragments exist. The `cursor` folder holds text meant for Cursor alone.

This reading departs from the parenthetical of RFC D13, which says "`claude` reaches
Claude". It follows the decision's first sentence instead, "the same text `CLAUDE.md`
carries", and is recorded on `beadloom-ybxm` for the reviewer and the owner.

### Layer gaps

`layer_gaps(project_root, config)` compares every pair of declared tools. A tool reads
the layers of every target file that is on disk; a layer is identified by the fragment
it comes from, not by its label, because `core` is the label of several files. A gap is
the set of layers another declared tool reads and this one does not.

`config-check` reports each gap at `error`, naming the lacking tool, the tool it is
compared with and the layers: the shipped ones by count, the project layer by path.
`--fix` and `setup-agentic-flow` compose the missing files.

The case it exists for is a project 9.0.0 composed for both tools: Claude reads the
core, the STACK overlay and the project layer, Cursor reads none of them, and
`config-check` now exits 1 where 9.0.0 exited 0.

### Stated limits

- A target on disk is credited with the layers of its composition. Whether its body is
  still that composition is the drift check's verdict on the file (stale, hand-edited),
  so one cause is reported once.
- A layer folder named for one tool, `.beadloom/flow/cursor/`, is that tool's own and is
  never a gap for another.
- A project declaring one tool has nothing to compare, and the answer is empty.
- Guard hooks (`.claude/settings.json`) are Claude-only and are not a layer here.
- When `cursor` leaves `tools:`, the `.cursor/rules/*.mdc` files are not reported as
  orphaned; the orphan population is the agent directories.

## API

- `tool_targets(tool) -> tuple[ToolTarget, ...]`
- `cursor_core_rule_relpath()`, `cursor_command_rule_relpath(name)`, `LEGACY_CURSOR_POINTER`
- `cursor_rule_text(body, *, description)`, `rule_body(text)`
- `layer_gaps(project_root, config) -> tuple[LayerGap, ...]`; `LayerGap.tool`, `.against`,
  `.layers`, `.why`, `.remediation`, `.file`

## Testing

`tests/unit/onboarding/tool_reach/test_each_tool_reads_the_same_layers.py` and the
scenarios in `tests/acceptance/onboarding/tool-reach/`.
