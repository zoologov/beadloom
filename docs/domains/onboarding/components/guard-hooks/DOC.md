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
- `GUARD_HOOK_RELPATH`, `SETTINGS_RELPATH`, `HOOK_EVENT`, `EDIT_MATCHER`.

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
