"""Discover scope: parse ``beadloom sync-check --json`` into drift items.

Deterministic. Groups the flat per-pair report into one :class:`DriftItem`
per stale ref (collecting its drift reasons + the code files involved).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.ai_techwriter.commands import beadloom_sync_check_json
from tools.ai_techwriter.models import DriftItem

if TYPE_CHECKING:
    from pathlib import Path


def discover_scope(project_root: Path, *, since: str | None = None) -> list[DriftItem]:
    """Return the stale doc refs (with drift reasons) for *project_root*.

    When *since* is given, drift is measured against the code state at that git
    ref (the push's parent commit) rather than the stored sync_state — the CI
    path, immune to a fresh-checkout re-baseline masking per-push drift.

    Empty list => nothing drifted => the harness no-ops (clean exit).
    """
    report = beadloom_sync_check_json(project_root, since=since)
    return parse_scope(report)


def parse_scope(report: dict[str, object]) -> list[DriftItem]:
    """Pure parse of a sync-check JSON report into grouped drift items.

    Split out from :func:`discover_scope` so the parsing is unit-testable from
    a fixture with no subprocess.
    """
    pairs = report.get("pairs")
    if not isinstance(pairs, list):
        return []

    by_ref: dict[str, _Accumulator] = {}
    order: list[str] = []
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        if pair.get("status") != "stale":
            continue
        ref_id = str(pair.get("ref_id", ""))
        if not ref_id:
            continue
        if ref_id not in by_ref:
            by_ref[ref_id] = _Accumulator(doc_path=str(pair.get("doc_path", "")))
            order.append(ref_id)
        acc = by_ref[ref_id]
        reason = pair.get("reason")
        if isinstance(reason, str) and reason and reason != "ok":
            acc.reasons.add(reason)
        code_path = pair.get("code_path")
        if isinstance(code_path, str) and code_path:
            acc.code_files.add(code_path)

    return [
        DriftItem(
            ref_id=ref_id,
            doc_path=by_ref[ref_id].doc_path,
            reasons=tuple(sorted(by_ref[ref_id].reasons)),
            code_files=tuple(sorted(by_ref[ref_id].code_files)),
        )
        for ref_id in order
    ]


class _Accumulator:
    """Mutable per-ref collector used only while grouping pairs."""

    def __init__(self, *, doc_path: str) -> None:
        self.doc_path = doc_path
        self.reasons: set[str] = set()
        self.code_files: set[str] = set()
