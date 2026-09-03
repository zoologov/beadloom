# beadloom:domain=application
# beadloom:feature=flow-guards
"""The enforcement surface: what fraction of the write paths the binding sees.

``beadloom guard --liveness`` answers "did each declared guard fire?". That is a
question about the guards, and it was the only one asked — so a binding that
covered one write path out of three reported every guard healthy, firing and
green, which is byte-identical to the report of a binding that covered all three
(BDL-UX #170). A guard healthy on a third of the write paths is a third of a
guard, and nothing said so.

This module answers the other question: **what could the binding have seen at
all?** Three facts, each derived from an artifact the flow emits rather than from
a list written here:

* the **matchers** actually registered, read back out of
  ``.claude/settings.json`` under the hook event — not out of
  :data:`~beadloom.onboarding.guard_hooks.EDIT_MATCHER`, because the file on disk
  is what the harness obeys and a second entry added by hand widens the surface
  as truly as ours does;
* the **tool population**, read out of the ``tools:`` line of every emitted role
  adapter. A tool granted to a role is a tool that will be used, so the roles are
  where the population lives. A role file that grants a new tool enters the
  report with no edit here;
* which of those tools **write**, which is the one thing this module declares.

That last table is knowledge about a harness, and it is deliberately not a
closed-world one: a tool it does not classify is reported as **unclassified**,
never counted as a non-writer. The whole finding is that a write path nobody
listed reads as an absence of write paths, and a table that answered "not a
writer" for anything it had not heard of would reproduce it exactly one tool
later.

**An unreadable source is unresolved, not empty.** No coverage fraction is
reported when either artifact could not be read: a fraction over a population
nobody could enumerate is the false green this module exists to remove, and "100%
of the zero tools I found" is the most confident way to state it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.onboarding.guard_hooks import HOOK_EVENT, SETTINGS_RELPATH
from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS

if TYPE_CHECKING:
    from pathlib import Path

#: The harness whose hook binding Beadloom emits. Its role adapters are the
#: population the binding is measured against.
BOUND_HARNESS = "claude"

#: Tools of this harness through which a file reaches the disk. ``Bash`` is the
#: entry #170 is about: it is a write path whichever way the write is spelled —
#: a redirection, ``sed -i``, or an interpreter reading a heredoc.
WRITE_TOOLS = frozenset({"Bash", "Edit", "MultiEdit", "NotebookEdit", "Write"})

#: Tools of this harness that write no file. Kept to the ones the shipped role
#: adapters actually grant: a longer table would be a guess about tools nobody
#: declared, and a guess in this direction is the silence the report exists to
#: break.
READ_TOOLS = frozenset({"Glob", "Grep", "Read"})

#: A matcher that names every tool. The harness treats both spellings this way,
#: so a binding carrying either sees the whole population.
_CATCH_ALL_MATCHERS = frozenset({"", "*"})

#: Stated in ``unresolved`` when a source the surface is derived from is missing
#: or unreadable. Names the path, because the reader's next action is to look at
#: it.
UNREADABLE_SOURCE = "{path}: {reason} — the tools it would have named are unknown"


@dataclass(frozen=True)
class ToolBinding:
    """One tool of the harness, and whether the binding fires on it.

    ``writes`` is ``None`` for a tool the classification does not know. That is
    a third state and not a default: "this tool does not write" and "nobody has
    said whether this tool writes" are the two facts #170 was made of.
    """

    tool: str
    granted_by: tuple[str, ...]
    writes: bool | None
    bound: bool

    def to_dict(self) -> dict[str, object]:
        """JSON-ready mapping for ``--liveness --json``."""
        return {
            "tool": self.tool,
            "granted_by": list(self.granted_by),
            "writes": self.writes,
            "bound": self.bound,
        }


@dataclass(frozen=True)
class BindingSurface:
    """What the emitted binding could see, over the population that exists."""

    harness: str
    matchers: tuple[str, ...] = ()
    tools: tuple[ToolBinding, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def write_paths(self) -> tuple[str, ...]:
        """Every granted tool a file can reach the disk through."""
        return tuple(row.tool for row in self.tools if row.writes is True)

    @property
    def seen(self) -> tuple[str, ...]:
        """Write paths a registered matcher names."""
        return tuple(
            row.tool for row in self.tools if row.writes is True and row.bound
        )

    @property
    def unseen(self) -> tuple[str, ...]:
        """Write paths no registered matcher names — an edit through one fires nothing."""
        return tuple(
            row.tool for row in self.tools if row.writes is True and not row.bound
        )

    @property
    def unclassified(self) -> tuple[str, ...]:
        """Granted tools this report cannot say either way about."""
        return tuple(row.tool for row in self.tools if row.writes is None)

    @property
    def named_but_not_granted(self) -> tuple[str, ...]:
        """Tools a matcher names that no emitted role adapter is granted.

        The rule this project applies to every exclusion and every glob — a
        pattern that can match nothing reports itself — applied to a matcher.
        Reported, never treated as a defect: a matcher broader than the roles is
        the safe direction, and the shipped default is deliberately broader than
        any one project's grants. It is here so that a reader comparing the
        matcher against the population is not left to do the subtraction by eye.
        """
        if self.unresolved:
            return ()
        granted = {row.tool for row in self.tools}
        named = {
            tool
            for matcher in self.matchers
            if matcher not in _CATCH_ALL_MATCHERS
            for tool in matcher.split("|")
            if tool
        }
        return tuple(sorted(named - granted))

    @property
    def covered(self) -> tuple[int, int] | None:
        """Write paths seen out of write paths granted, or ``None`` when unknown.

        ``None`` whenever a source could not be read: a fraction is a claim
        about a population, and an unread source means there is no population to
        make it about.
        """
        if self.unresolved:
            return None
        return len(self.seen), len(self.write_paths)

    def to_dict(self) -> dict[str, object]:
        """JSON-ready mapping for ``--liveness --json``."""
        covered = self.covered
        return {
            "harness": self.harness,
            "matchers": list(self.matchers),
            "tools": [row.to_dict() for row in self.tools],
            "write_paths": list(self.write_paths),
            "seen": list(self.seen),
            "unseen": list(self.unseen),
            "unclassified": list(self.unclassified),
            "named_but_not_granted": list(self.named_but_not_granted),
            "unresolved": list(self.unresolved),
            "covered": list(covered) if covered is not None else None,
        }


def _read_matchers(project_root: Path) -> tuple[tuple[str, ...], str]:
    """Matchers registered under the hook event, or why they could not be read."""
    path = project_root / SETTINGS_RELPATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return (), UNREADABLE_SOURCE.format(
            path=SETTINGS_RELPATH.as_posix(), reason="no harness settings are emitted"
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        # UnicodeDecodeError is named because `read_text(encoding="utf-8")`
        # raises it and it is a ValueError, not an OSError: a settings file with
        # one non-UTF-8 byte would otherwise end this report in a traceback
        # instead of in the `unresolved` line it exists to produce.
        return (), UNREADABLE_SOURCE.format(
            path=SETTINGS_RELPATH.as_posix(), reason=str(exc)
        )
    hooks = data.get("hooks") if isinstance(data, dict) else None
    entries = hooks.get(HOOK_EVENT) if isinstance(hooks, dict) else None
    if not isinstance(entries, list):
        return (), UNREADABLE_SOURCE.format(
            path=SETTINGS_RELPATH.as_posix(),
            reason=f"it registers no {HOOK_EVENT} entries",
        )
    found = [
        entry["matcher"]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("matcher"), str)
    ]
    return tuple(sorted(set(found))), ""


def _declared_tools(body: str) -> tuple[str, ...]:
    """The ``tools:`` grant of one role adapter's front matter."""
    if not body.startswith("---"):
        return ()
    _, _, rest = body.partition("\n")
    front, _, _ = rest.partition("\n---")
    for line in front.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "tools":
            return tuple(
                item.strip() for item in value.split(",") if item.strip()
            )
    return ()


def _read_grants(project_root: Path) -> tuple[dict[str, list[str]], str]:
    """Tool -> the role adapters granting it, or why the adapters could not be read."""
    relative_dir = TOOL_AGENT_DIRS[BOUND_HARNESS]
    directory = project_root / relative_dir
    try:
        files = sorted(path for path in directory.iterdir() if path.suffix == ".md")
    except OSError as exc:
        return {}, UNREADABLE_SOURCE.format(
            path=relative_dir.as_posix(), reason=exc.strerror or str(exc)
        )
    if not files:
        return {}, UNREADABLE_SOURCE.format(
            path=relative_dir.as_posix(), reason="it holds no role adapter"
        )
    grants: dict[str, list[str]] = {}
    for path in files:
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        role = (relative_dir / path.name).as_posix()
        for tool in _declared_tools(body):
            grants.setdefault(tool, []).append(role)
    return grants, ""


def _classify(tool: str) -> bool | None:
    """Whether *tool* writes a file, or ``None`` when nothing here says."""
    if tool in WRITE_TOOLS:
        return True
    if tool in READ_TOOLS:
        return False
    return None


def _bound(tool: str, matchers: tuple[str, ...]) -> bool:
    """True when a registered matcher fires on *tool*."""
    return any(
        matcher in _CATCH_ALL_MATCHERS or tool in matcher.split("|")
        for matcher in matchers
    )


def build_surface(project_root: Path) -> BindingSurface:
    """The binding's surface over the tool population the emitted roles grant."""
    matchers, matcher_problem = _read_matchers(project_root)
    grants, grant_problem = _read_grants(project_root)
    unresolved = tuple(
        problem for problem in (matcher_problem, grant_problem) if problem
    )
    tools = tuple(
        ToolBinding(
            tool=tool,
            granted_by=tuple(roles),
            writes=_classify(tool),
            bound=_bound(tool, matchers),
        )
        for tool, roles in sorted(grants.items())
    )
    return BindingSurface(
        harness=BOUND_HARNESS,
        matchers=matchers,
        tools=tools,
        unresolved=unresolved,
    )
