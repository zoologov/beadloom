"""Build the per-doc context packet handed to the agent seam (RFC Q4).

Deterministic assembly: current doc content + drift reason + the polish-json
slice for the ref + ctx(ref) + why(ref).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.ai_techwriter.commands import (
    beadloom_ctx_json,
    beadloom_docs_polish_json,
    beadloom_why,
)
from tools.ai_techwriter.models import ContextPacket, DriftItem

if TYPE_CHECKING:
    from pathlib import Path


def build_packet(
    project_root: Path,
    item: DriftItem,
    *,
    polish_report: dict[str, object] | None = None,
) -> ContextPacket:
    """Assemble the context packet for one drifted doc.

    *polish_report* may be passed in (so the harness fetches the whole
    ``docs polish`` report once and reuses it across all docs); when omitted it
    is fetched here.
    """
    if polish_report is None:
        polish_report = beadloom_docs_polish_json(project_root)
    polish_slice = select_polish_for_ref(polish_report, item.ref_id)
    ctx = beadloom_ctx_json(project_root, item.ref_id)
    why = beadloom_why(project_root, item.ref_id)
    return ContextPacket(
        ref_id=item.ref_id,
        doc_path=item.doc_path,
        current_content=read_doc(project_root, item.doc_path),
        drift_reason=item.reason_summary(),
        docs_polish_json=polish_slice,
        ctx=ctx,
        why=why,
    )


def select_polish_for_ref(report: dict[str, object], ref_id: str) -> dict[str, object]:
    """Return the polish-json node for *ref_id* (empty dict if absent)."""
    nodes = report.get("nodes")
    if not isinstance(nodes, list):
        return {}
    for node in nodes:
        if isinstance(node, dict) and node.get("ref_id") == ref_id:
            return node
    return {}


def read_doc(project_root: Path, doc_path: str) -> str:
    """Read the current doc content, or '' if the file does not exist yet."""
    target = project_root / doc_path
    if not target.exists():
        return ""
    return target.read_text(encoding="utf-8")
