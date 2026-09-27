# beadloom:domain=application
# beadloom:component=mutation-scope
"""Survivors of a mutation run, listed under the node that owns their file (BDL-074 D1).

A score says how many mutants survived. Where they survived is what a reader
acts on, and in this project "where" is a node: the survivors of a change to the
rule engine are the rule engine's gap, not a percentage of the declared scope.

**The survivor list is names, not a tool.** A run writes a JSON list of objects,
each naming the source file a mutant lives in (``path``) and the runner's own
identifier for it (``mutant``). Ownership is the graph's rule — the most
specific node whose source covers the file — read from the index, so a survivor
lands under the same node ``ctx`` shows its file under. A file no node owns is
listed under no node rather than dropped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.infrastructure.repository import get_owning_ref_id

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable, Mapping
    from pathlib import Path

#: How a survivor whose file no node owns is labelled when printed.
NO_NODE = "(no node)"


@dataclass(frozen=True)
class Survivor:
    """One mutant a run's tests let live: the file it is in and its identifier."""

    path: str
    mutant: str


def read_survivors(path: Path) -> tuple[Survivor, ...] | None:
    """The survivors listed in *path*, or ``None`` when it holds no survivor list.

    An empty list is a list: a run in which nothing survived. An absent file, a
    file that is not JSON, or an entry without a string ``path`` and ``mutant``
    is no list at all, and the caller says so rather than printing "none".
    """
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, list):
        return None
    survivors: list[Survivor] = []
    for entry in data:
        if not isinstance(entry, dict):
            return None
        file_path, mutant = entry.get("path"), entry.get("mutant")
        if not isinstance(file_path, str) or not isinstance(mutant, str):
            return None
        survivors.append(Survivor(path=file_path, mutant=mutant))
    return tuple(survivors)


def survivors_by_node(
    conn: sqlite3.Connection, survivors: Iterable[Survivor]
) -> dict[str | None, tuple[Survivor, ...]]:
    """*survivors* grouped by the node owning their file; ``None`` for no owner."""
    grouped: dict[str | None, list[Survivor]] = {}
    owners: dict[str, str | None] = {}
    for survivor in survivors:
        if survivor.path not in owners:
            owners[survivor.path] = get_owning_ref_id(conn, survivor.path)
        grouped.setdefault(owners[survivor.path], []).append(survivor)
    return {node: tuple(members) for node, members in grouped.items()}


def describe_survivors(grouped: Mapping[str | None, tuple[Survivor, ...]]) -> list[str]:
    """The survivors as lines: a count, then one line per node naming its mutants."""
    total = sum(len(members) for members in grouped.values())
    if total == 0:
        return ["Survivors: none"]
    lines = [f"Survivors: {total} over {len(grouped)} node(s)"]
    for node, members in sorted(grouped.items(), key=lambda item: item[0] or ""):
        names = ", ".join(member.mutant for member in members)
        lines.append(f"  {node or NO_NODE}: {len(members)} survivor(s) — {names}")
    return lines


def survivors_payload(
    grouped: Mapping[str | None, tuple[Survivor, ...]],
) -> dict[str, list[dict[str, str]]]:
    """The grouping in the JSON shape the ``mutation`` command prints."""
    return {
        node or NO_NODE: [{"path": m.path, "mutant": m.mutant} for m in members]
        for node, members in grouped.items()
    }
