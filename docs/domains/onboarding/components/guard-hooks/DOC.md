# Guard Hooks (component)

Internal building block of the onboarding domain.

**Source:** `src/beadloom/onboarding/guard_hooks.py`

---

## Overview

Emits the Claude Code hook adapter that binds the flow guards to the harness,
and registers it in the project's `.claude/settings.json`. The adapter is the
thinnest thing that can work:

```sh
exec beadloom guard "$1" --hook claude-code
```

**No logic in the adapter** is the rule the enforcement epic rests on. Anything
the script decided — which paths are exempt, how strict the project is, how to
dig a file path out of the event — would be behaviour that exists only inside
one tool, untested and unportable. The event is forwarded verbatim and every
decision happens in the CLI, which is why a hook and a shell cannot disagree.

## Public surface

- `scaffold_guard_hooks(project_root, *, guard_names)` — write the adapter and
  register one `PreToolUse` entry per guard; returns a `GuardHookResult`.
- `hook_command(guard_name)` — the settings command string (rooted at
  `$CLAUDE_PROJECT_DIR`, so it does not depend on the shell's working directory).
  The adapter passes no `--project`, because `beadloom guard` now discovers the
  project root itself — walking up from the working directory to the nearest
  ancestor holding `.beadloom/` — so the script anchor and the decision root
  agree without the adapter having to know anything. It used to take `cwd` as the root, which
  silently downgraded a declared `block` to a non-blocking `warn` for any
  invocation from a subdirectory.
- `GUARD_HOOK_RELPATH`, `SETTINGS_RELPATH`, `HOOK_EVENT` (`PreToolUse`),
  `EDIT_MATCHER` (`Edit|Write|MultiEdit|NotebookEdit|Bash`) — the matcher is the
  enforcement surface, so its value belongs in the reference rather than behind
  its name. See below for what it leaves out.

## The enforcement surface

The registered entry pairs `EDIT_MATCHER` with one command per guard, so the
guards see five tool calls: `Edit`, `Write`, `MultiEdit`, `NotebookEdit`, `Bash`.

`Bash` was added in BDL-068 S4 (BDL-UX #170). Before it, a file written through
the shell — `sed -i`, a heredoc, `python3 - <<EOF` — reached the filesystem
without matching, so no guard was invoked and no firing was written, and
`--liveness` could not see the difference: it reads the firing record, and an
edit no guard was asked about leaves no record.

### What widening the matcher changed about the RECORD

Binding the shell tool changed what `.beadloom/guard-firings.jsonl` holds, not only
how often a line is appended to it. A file edit reports a path; a shell edit reports
a command line, and until `beadloom-0mdo.43` that line was stored verbatim. Measured
on this repository's own record the day the review found it: 1 927 of 1 999 firings in
one rotated generation held a command line, 2.0 MB of one machine's shell history in a
plaintext file inside the project directory — on an adopter's machine as much as on
ours, and command lines are where credentials live in practice.

A shell edit therefore contributes three context keys and never the line:
`command_name` (the program, with any `VAR=value` prefix dropped), `command_writes`
(the derived write targets, which are a lower bound) and `command_unreadable` (why a
line could not be tokenized). That is everything the guard ever read of a command, so
nothing downstream lost an input. Replaying the same 1 999 firings through the
reduction: 557 bytes a record rather than 1 007, and 370 of them still name a write
target.

Reduction rather than redaction, because redaction is a denylist: masking `KEY=value`
and `--header`-shaped operands covers the spellings somebody thought of, and the next
credential arrives as a positional argument or inside a heredoc. What it costs is that
a human reading a firing sees which program ran and not how it was invoked.

**A file written through any tool the matcher does not name is still unguarded**,
and that is now reported rather than left to a paragraph.
`application/guards/surface.py` reads this file's matcher back off disk, reads the
`tools:` grant of every emitted role adapter, and reports which of the granted
write paths a registered matcher names. It is derived from the on-disk artifacts
and not from `EDIT_MATCHER` for a reason this module owns: registration is a
merge on the command string, so a project scaffolded before a matcher widened
keeps the narrow one across the upgrade, and the constant would report a coverage
the project does not have.

Review finding M3 — giving Beadloom its own event vocabulary, so the adapter
forwards what happened rather than which guard to run — is the same gap seen from
the routing side and is S3 work.

Two facts about the exit codes the adapter forwards, both now carried by the
script's own comment:

- The harness stops the tool call on exit `2` and on nothing else, so `block` and
  `error` are what actually block.
- **The adapter never returns `3`** (BDL-061.33). A defect in the declared
  configuration, or a command line that could not be used, exits `3` only for a
  caller that ran `beadloom guard` itself; reached through `--hook` the same
  class exits `2`. It did return `3` in S1, which stopped nothing: a
  `.beadloom/flow.yml` that would not parse left every bound guard reporting that
  it could not answer while the edits proceeded. The mapping lives in the CLI,
  keyed on the harness this script already declares, rather than in the script —
  a script that maps codes carries logic, and the next adapter would have to
  re-derive it. The [flow-guards SPEC](../../../application/features/flow-guards/SPEC.md)
  states the class and the reasoning.

## The dogfood runs the emitted script (BDL-061.35)

Until S3 this repository was **not** bound through the emitted adapter: its
`.claude/settings.json` registered the `beadloom guard` command directly, with a
matcher one tool narrower. The artifact adopters receive had therefore never run
here, so "dogfooded under the flow it builds" was evidence about a path adopters
do not use — the stated reason #170's narrow binding survived five review cycles.

`.claude/settings.json` now carries exactly what `scaffold_guard_hooks` writes,
and the entries were produced by running it rather than typed. Three tests hold
the two together against the scaffolder's own output rather than against
literals: every registered command equals `hook_command(name)`, no command is the
direct form, and the committed `.claude/hooks/beadloom-guard.sh` is byte-identical
to a freshly emitted one (and executable). The consequence is deliberate: this
repository now inherits `EDIT_MATCHER` in full, so #170's surface gap is a gap we
run under rather than one only adopters meet.

## Invariants

- **Merge, never rewrite.** An adopter's `settings.json` is their file: existing
  hooks (ours or anyone else's) survive, re-running adds nothing, and a file
  that cannot be parsed is reported and left untouched.
- **Guard names are a parameter, not an import.** The registry lives in the
  application layer above this domain; the CLI, which sits above both, supplies
  the names — so a guard added in a later release is wired by re-running
  `beadloom setup-agentic-flow`.

## Collaborators

Called by `beadloom setup-agentic-flow` (`services/commands/setup.py`) with
`GUARD_NAMES` from the guard registry. The emitted script calls `beadloom guard`
(`services/commands/guard.py`), whose decision path is
`application/guards/evaluation.py`.
