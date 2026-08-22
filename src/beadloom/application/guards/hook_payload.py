# beadloom:domain=application
# beadloom:feature=flow-guards
"""Translating a harness hook event into guard context (BDL-061 S1).

A harness hook hands its own JSON shape to whatever it invokes. Rather than let
each adapter script dig the file path out of that payload — which would put
decisions in the one place we cannot test — the adapter forwards the event
verbatim and Beadloom does the translation here.

That keeps the promise the epic is built on: **no behaviour exists only inside a
harness**. Supporting a second tool is one entry in
:data:`HOOK_CONTEXT_BUILDERS`, not a second code path, and every harness ends up
in the same :func:`~beadloom.application.guards.evaluation.evaluate_guard` call
with the same context keys, so the verdict cannot diverge between callers.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

#: Context key for the file an edit targets.
PATH_KEY = "path"


class HookPayloadError(ValueError):
    """A hook payload that is not readable as the named harness's event."""


def _claude_code_context(payload: Mapping[str, object]) -> dict[str, str]:
    """Context from a Claude Code hook event (``PreToolUse`` and friends).

    Reads ``tool_input.file_path`` (``notebook_path`` for notebook edits), the
    tool name and the event name. Missing keys are omitted rather than guessed:
    a guard states an absent path in ``not_covered``, which is honest, whereas a
    guessed path would silently evaluate the wrong file.
    """
    context: dict[str, str] = {}
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        target = tool_input.get("file_path") or tool_input.get("notebook_path")
        if isinstance(target, str) and target:
            context[PATH_KEY] = target
    tool_name = payload.get("tool_name")
    if isinstance(tool_name, str) and tool_name:
        context["tool"] = tool_name
    event = payload.get("hook_event_name")
    if isinstance(event, str) and event:
        context["event"] = event
    return context


#: Harness name -> payload translator. Adding a tool is adding an entry here.
HOOK_CONTEXT_BUILDERS: dict[str, Callable[[Mapping[str, object]], dict[str, str]]] = {
    "claude-code": _claude_code_context,
}

#: Harnesses whose hook payloads Beadloom can read, deterministically ordered.
SUPPORTED_HARNESSES: tuple[str, ...] = tuple(sorted(HOOK_CONTEXT_BUILDERS))


def context_from_hook_payload(harness: str, raw: str) -> dict[str, str]:
    """Translate *raw* JSON from *harness* into guard context.

    Raises :class:`HookPayloadError` for an unknown harness or unreadable JSON —
    a hook that cannot be understood must not read as "nothing to check".
    """
    builder = HOOK_CONTEXT_BUILDERS.get(harness)
    if builder is None:
        msg = (
            f"unknown harness {harness!r} — supported: {list(SUPPORTED_HARNESSES)}"
        )
        raise HookPayloadError(msg)
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        msg = f"{harness}: hook payload is not valid JSON — {exc}"
        raise HookPayloadError(msg) from exc
    if not isinstance(payload, dict):
        msg = f"{harness}: hook payload must be a JSON object"
        raise HookPayloadError(msg)
    return builder(payload)
