"""The node ids this repository's graph binds to the portal scaffold, read from the graph.

BDL-076 ``beadloom-ujzb.18``. The scaffold's source files carry
``beadloom:component=<ref>`` lines so that this repository's graph binds the
theme to its slice nodes, and those refs are exactly the nodes whose declared
``source:`` lies inside the scaffold package. Reading them from the graph rather
than listing them keeps a check over a written portal true when a slice is
added, renamed or retired.

Read through :data:`tests.support.package_under_test.SHIPPED_FROM`, so an
acceptance step copied away from the checkout still reads this project's graph.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from beadloom.graph.loader import parse_graph_file
from beadloom.services.cli import main
from tests.support.package_under_test import SHIPPED_FROM

#: This repository's graph directory.
GRAPH_DIR = SHIPPED_FROM / ".beadloom" / "_graph"

#: The scaffold package, as a node's ``source:`` names it.
SCAFFOLD_SOURCE = "src/beadloom/site_scaffold/"


def scaffold_node_ids() -> frozenset[str]:
    """Every node of this repository's graph whose source lies inside the scaffold."""
    ids: set[str] = set()
    for path in sorted(GRAPH_DIR.glob("*.yml")):
        for node in parse_graph_file(path).nodes:
            source = node.get("source")
            if isinstance(source, str) and source.startswith(SCAFFOLD_SOURCE):
                ids.add(str(node["ref_id"]))
    return frozenset(ids)


def node_ids_named(text: str, ids: frozenset[str]) -> list[str]:
    """The ids in *ids* that *text* names as a whole token, hyphens included."""
    return sorted(ref for ref in ids if re.search(rf"(?<![\w-]){re.escape(ref)}(?![\w-])", text))


def repository_node_ids() -> frozenset[str]:
    """Every node id of this repository's graph, the scaffold's own and the rest."""
    return frozenset(
        str(node["ref_id"])
        for path in sorted(GRAPH_DIR.glob("*.yml"))
        for node in parse_graph_file(path).nodes
    )


def coined(ids: frozenset[str]) -> frozenset[str]:
    """The ids in *ids* this repository coined: two words joined, and no command of the tool.

    A one-word id (``graph``, ``impact``, ``search``, ``status``) is also a word
    of the portal's own vocabulary - a URL value, a data key, a command - and of
    any adopter's code, so its presence in a file says nothing about whose graph
    the file was written against. A compound id is a name a project chose -
    unless it is also the name of a ``beadloom`` command (``sync-check``,
    ``config-check``), which an adopter runs and a portal may name. The command
    names are read from the CLI itself, so the exemption is not a list.
    Selection by any literal id, one word or two, is checked apart, by shape
    (:func:`literal_id_comparisons`).
    """
    commands = frozenset(main.commands)
    return frozenset(ref for ref in ids if re.search(r"[-_]", ref) and ref not in commands)


#: A node's id compared with a string literal: a subject chosen by name.
_LITERAL_ID_RE = re.compile(r"""\.id\s*[!=]==?\s*["'`]|["'`]\s*[!=]==?\s*\w+\.id\b""")


def literal_id_comparisons(text: str) -> list[int]:
    """The 1-based lines of *text* that compare a node's ``.id`` with a string literal."""
    return [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if _LITERAL_ID_RE.search(line)
    ]


#: The tracker export, relative to a checkout: every bead id the project has issued.
TRACKER_EXPORT = Path(".beads") / "issues.jsonl"

#: An epic key of this repository's planning corpus.
_EPIC_KEY_RE = re.compile(r"\bBDL-\d+")


def tracker_ids(checkout: Path) -> frozenset[str]:
    """Every bead id in the tracker export of *checkout*.

    Pass the self-check snapshot, never this checkout: the tracker is live
    state, and the contact guard (tests/support/contact_guard.py) fails a test
    that opens it.
    """
    ids: set[str] = set()
    for line in (checkout / TRACKER_EXPORT).read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if isinstance(record.get("id"), str):
                ids.add(record["id"])
    return frozenset(ids)


def tracker_references(text: str, beads: frozenset[str]) -> list[str]:
    """The epic keys and the bead ids of *beads* that *text* cites, sorted."""
    cited = set(_EPIC_KEY_RE.findall(text))
    cited.update(
        bead for bead in beads if re.search(rf"(?<![\w-]){re.escape(bead)}(?![\w.-]?\w)", text)
    )
    return sorted(cited)
