"""The relation report over a project's tracker export, and the facts it is checked against."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml

from beadloom.application.doc_spaces import (
    SpacesReport,
    beads_by_epic,
    check_spaces,
)
from beadloom.infrastructure.doc_roots import (
    resolve_doc_spaces,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: Where the shipped flow writes an epic's planning documents.
EPICS = ".claude/development/docs/features"


def relation_report_of(
    root: Path,
    *,
    known: set[str] | None = None,
    documented: set[str] | None = None,
    declared: set[str] | None = None,
    beads: Mapping[str, tuple[str, ...]] | None = None,
) -> SpacesReport:
    """``check_spaces`` with the graph supplied as data, never as a database."""
    return check_spaces(
        root,
        spaces=resolve_doc_spaces(root),
        known_refs=frozenset(known or ()),
        documented_refs=frozenset(documented or ()),
        declared_doc_paths=frozenset(declared or ()),
        beads_by_epic=beads,
    )


def repo_beads(root: Path) -> dict[str, tuple[str, ...]]:
    """This repository's own tracker export, grouped by epic key.

    *root* is the self-check snapshot (BDL-074 A2): the export is tracked, so the
    copy carries it, and a concurrent ``bd`` write to the live file cannot land
    between two reads of one test.
    """
    text = (root / ".beads" / "issues.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return beads_by_epic(records)


def repo_report(root: Path) -> SpacesReport:
    return relation_report_of(
        root,
        known=repo_known_refs(root),
        documented=repo_known_refs(root),
        beads=repo_beads(root),
    )


def repo_known_refs(root: Path) -> set[str]:
    """Ref ids read from the committed graph YAML, not from an index.

    The database is a build artifact whose freshness is the thing under test
    elsewhere; the YAML is the declaration.
    """
    refs: set[str] = set()
    for path in (root / ".beadloom" / "_graph").glob("*.yml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for node in data.get("nodes", []) or []:
            if isinstance(node, dict) and isinstance(node.get("ref_id"), str):
                refs.add(node["ref_id"])
    return refs


#: Roots handed out by :func:`_tmp`, removed after each test by the fixture
#: below. A factory rather than the ``tmp_path`` fixture because several helpers
#: here are static and take no fixtures.
HANDED_OUT: list[Path] = []
