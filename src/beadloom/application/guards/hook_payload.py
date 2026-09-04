# beadloom:domain=application
# beadloom:feature=flow-guards
"""The guard's evaluation context: its vocabulary, and how an event becomes one (BDL-061 S1).

A harness hook hands its own JSON shape to whatever it invokes. Rather than let
each adapter script dig the file path out of that payload — which would put
decisions in the one place we cannot test — the adapter forwards the event
verbatim and Beadloom does the translation here.

That keeps the promise the epic is built on: **no behaviour exists only inside a
harness**. Supporting a second tool is one entry in
:data:`HOOK_CONTEXT_BUILDERS`, not a second code path, and every harness ends up
in the same :func:`~beadloom.application.guards.evaluation.evaluate_guard` call
with the same context keys, so the verdict cannot diverge between callers.

The vocabulary itself lives here for the same reason, and since
``beadloom-0mdo.43`` it is also what bounds DISCLOSURE. The context is echoed
into the verdict and appended to ``.beadloom/guard-firings.jsonl``, so a key
this module admits is a value written to a plaintext file in the project
directory for as long as the record keeps it. A shell command line is therefore
reduced to the facts the guard reasons about before it is admitted —
:func:`shell_command_context` — and the line itself reaches nothing downstream.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.application.guards.shell_targets import (
    ShellCommand,
    read_shell_command,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

#: Context key for the file an edit targets.
PATH_KEY = "path"

#: The key a CALLER may supply a raw shell command line under — ``--context
#: command=...`` on the command line, ``tool_input.command`` in a harness event.
#: It is an INPUT spelling and never a context key: :func:`shell_command_context`
#: replaces it with the three keys below before anything sees the context, so no
#: verdict and no firing record carries the line itself (``beadloom-0mdo.43``).
COMMAND_KEY = "command"

#: Context key for the program a shell edit runs — ``sed``, ``git``, ``python3``.
#: Present for every shell edit and for no other, so it is also the fact that
#: says one happened; its value may be ``""`` when no command word could be read.
COMMAND_NAME_KEY = "command_name"

#: Context key for the files a shell edit was seen to write, one per line. A
#: LOWER BOUND, never the set — see
#: :mod:`~beadloom.application.guards.shell_targets`. Absent when nothing was
#: derived, which is the ordinary case for an interpreter invocation.
COMMAND_WRITES_KEY = "command_writes"

#: Context key for why a command line could not be tokenized at all. Absent when
#: it could. Separate from an empty :data:`COMMAND_WRITES_KEY`, because "nothing
#: was derived" and "nothing could be read" are different facts.
COMMAND_UNREADABLE_KEY = "command_unreadable"

#: Separates the derived write targets inside :data:`COMMAND_WRITES_KEY`. A
#: newline rather than a space, because a path may contain a space and the
#: record has to be splittable back into the paths that went into it.
WRITES_SEPARATOR = "\n"

#: How much of the derived facts one shell edit contributes to the context, and
#: therefore to the firing record. It bounds SIZE and nothing else: what keeps a
#: credential out of the record is the shape above — a program name and a list of
#: paths, with the line itself never carried — and a length limit is a denylist's
#: worth of protection, which is to say none. Whole values are dropped rather
#: than cut: a truncated lower bound is still a lower bound, while half a path is
#: a file nobody wrote, which is the confident wrongness this feature exists not
#: to produce.
COMMAND_LIMIT = 2000


class HookPayloadError(ValueError):
    """A hook payload that is not readable as the named harness's event."""


class UnknownHarnessError(HookPayloadError):
    """A ``--hook`` naming a harness Beadloom cannot translate.

    Separate from its base because the two fail for different reasons and the
    caller owes them different exit codes: an unsupported harness is a *wiring*
    defect that fails identically on every invocation until a human edits the
    adapter, while an unreadable payload is runtime data about one edit, from a
    harness that is supported (BDL-061.29).
    """


def _claude_code_context(payload: Mapping[str, object]) -> dict[str, str]:
    """Context from a Claude Code hook event (``PreToolUse`` and friends).

    Reads ``tool_input.file_path`` (``notebook_path`` for notebook edits), the
    tool name and the event name. Missing keys are omitted rather than guessed:
    a guard states an absent path in ``not_covered``, which is honest, whereas a
    guessed path would silently evaluate the wrong file.

    The shell tool describes its edit as ``tool_input.command`` and never as a
    path, which is why a whole class of edits to this repository fired no guard
    at all (BDL-UX #170). The line is read into the facts the guard reasons about
    and is not carried past this function — see :func:`shell_command_context`.
    """
    context: dict[str, str] = {}
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        target = tool_input.get("file_path") or tool_input.get("notebook_path")
        if isinstance(target, str) and target:
            context[PATH_KEY] = target
        command = tool_input.get("command")
        if isinstance(command, str) and command:
            context.update(shell_command_context(command))
    tool_name = payload.get("tool_name")
    if isinstance(tool_name, str) and tool_name:
        context["tool"] = tool_name
    event = payload.get("hook_event_name")
    if isinstance(event, str) and event:
        context["event"] = event
    return context


def shell_command_context(command: str) -> dict[str, str]:
    """The context keys one shell command line contributes — never the line.

    This is the one door a model-supplied command line goes through, and what
    comes out the other side is what the guard reasons about: the program, the
    write targets a declared shape names, and the reason the line could not be
    read. Everything else the line said is dropped here rather than stored.

    The reason is disclosure, and it is a decision about the record's CONTENTS
    rather than about how often it is written (``beadloom-0mdo.43``). Widening
    the binding to the shell tool (BDL-UX #170) turned a record of file paths
    into a record of every command an agent runs, in a plaintext file inside the
    project directory, on every adopter's machine — and command lines are where
    credentials live in practice (``GITHUB_TOKEN=… gh api …``, ``curl -H
    "Authorization: Bearer …"``, ``psql "postgres://user:pass@host/db"``).

    Reduction rather than redaction, deliberately. Redacting ``KEY=value`` and
    ``--header``-shaped operands is a denylist, and a denylist is a list of the
    spellings somebody thought of: the next credential arrives as a positional
    argument, inside a heredoc, or under a flag nobody enumerated, and it is
    stored. Keeping only the derived facts is a decision about what is kept, so
    a spelling nobody anticipated is outside it by construction. What the choice
    costs is stated rather than hidden: a human reading a firing can no longer
    see the exact invocation, only which program ran and which files it was seen
    to name. Nothing in Beadloom read the rest — the line's only consumer was
    :func:`~beadloom.application.guards.shell_targets.read_shell_command`.

    An empty or blank command contributes nothing at all, so the absence of
    :data:`COMMAND_NAME_KEY` keeps meaning "this was not a shell edit".
    """
    if not command.strip():
        return {}
    read = read_shell_command(command)
    context = {COMMAND_NAME_KEY: _bounded((read.name,))}
    writes = _bounded(read.targets)
    if writes:
        context[COMMAND_WRITES_KEY] = writes
    if read.unreadable:
        context[COMMAND_UNREADABLE_KEY] = read.unreadable
    return context


def _bounded(values: tuple[str, ...]) -> str:
    """*values* joined, dropping whole entries once :data:`COMMAND_LIMIT` is met."""
    kept: list[str] = []
    used = 0
    for value in values:
        used += len(value) + len(WRITES_SEPARATOR)
        if used > COMMAND_LIMIT:
            break
        kept.append(value)
    return WRITES_SEPARATOR.join(kept)


def shell_edit_from_context(context: Mapping[str, str]) -> ShellCommand | None:
    """The shell edit *context* describes, or ``None`` when it describes none.

    The counterpart of :func:`shell_command_context`, kept beside it so that the
    joining and the splitting of :data:`COMMAND_WRITES_KEY` cannot drift apart.
    """
    name = context.get(COMMAND_NAME_KEY)
    if name is None:
        return None
    writes = context.get(COMMAND_WRITES_KEY) or ""
    return ShellCommand(
        name=name,
        targets=tuple(writes.split(WRITES_SEPARATOR)) if writes else (),
        unreadable=context.get(COMMAND_UNREADABLE_KEY) or "",
    )


#: Harness name -> payload translator. Adding a tool is adding an entry here.
HOOK_CONTEXT_BUILDERS: dict[str, Callable[[Mapping[str, object]], dict[str, str]]] = {
    "claude-code": _claude_code_context,
}

#: Harnesses whose hook payloads Beadloom can read, deterministically ordered.
SUPPORTED_HARNESSES: tuple[str, ...] = tuple(sorted(HOOK_CONTEXT_BUILDERS))


def context_from_hook_payload(harness: str, raw: str) -> dict[str, str]:
    """Translate *raw* JSON from *harness* into guard context.

    Raises :class:`UnknownHarnessError` for a harness with no translator and
    :class:`HookPayloadError` for unreadable JSON — a hook that cannot be
    understood must not read as "nothing to check".
    """
    builder = HOOK_CONTEXT_BUILDERS.get(harness)
    if builder is None:
        msg = (
            f"unknown harness {harness!r} — supported: {list(SUPPORTED_HARNESSES)}"
        )
        raise UnknownHarnessError(msg)
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        msg = f"{harness}: hook payload is not valid JSON — {exc}"
        raise HookPayloadError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"{harness}: hook payload must be a JSON object"
        raise HookPayloadError(msg)
    return builder(payload)
