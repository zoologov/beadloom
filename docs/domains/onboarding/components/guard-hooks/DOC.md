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
  `EDIT_MATCHER` (`Edit|Write|MultiEdit|NotebookEdit`) — the matcher is the
  enforcement surface, so its value belongs in the reference rather than behind
  its name. See below for what it leaves out.

## The enforcement surface

The registered entry pairs `EDIT_MATCHER` with one command per guard, so the
guards see exactly four tool calls: `Edit`, `Write`, `MultiEdit`, `NotebookEdit`.

**A file written through any other tool is unguarded.** `Bash` is the one that
matters — `sed -i`, a heredoc, `python3 - <<EOF` all reach the filesystem without
matching, so no guard is invoked and no firing is written. **`--liveness` cannot
see the difference:** it reads the firing record, and an edit no guard was asked
about leaves no record, so a session that wrote everything through `Bash` reports
exactly like a session that complied. That is not a verdict the guard can qualify
— nothing evaluated — which is why the limit is documented at the binding
(BDL-UX #170 — review finding M3 is the same gap seen from the routing side, and
both are S3 work).

Two facts about the exit codes the adapter forwards, because the script's own
comment does not carry the second one yet:

- The harness stops the tool call on exit `2` and on nothing else, so `block` and
  `error` are what actually block.
- Exit `3` — a defect in the declared configuration, or a command line that could
  not be used — is therefore **loud and non-blocking**. A `.beadloom/flow.yml`
  that will not parse leaves every bound guard reporting that it could not answer
  while the edits proceed. **BDL-061.33** owns the fix, and the emitted comment
  changes with it. The [flow-guards SPEC](../../../application/features/flow-guards/SPEC.md)
  states the cases and the trade-off.

This repository is not currently bound through the emitted script: its
`.claude/settings.json` registers the `beadloom guard` command directly, with a
narrower matcher. So the artifact adopters receive has not been exercised here —
recorded as review minor n1, and carried with M3 into S3 rather than patched in
one place.

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
