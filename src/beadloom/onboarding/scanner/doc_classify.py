"""Documentation classification, import, and auto-linking to graph nodes."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

# Doc classification patterns.
_ADR_RE = re.compile(r"(decision|status:\s*(accepted|deprecated|superseded))", re.I)
_FEATURE_RE = re.compile(r"(user\s+story|feature|requirement|spec)", re.I)
_ARCH_RE = re.compile(r"(architect|system\s+design|infrastructure|deployment)", re.I)


def classify_doc(doc_path: Path) -> str:
    """Classify a markdown document by content heuristics."""
    text = doc_path.read_text(encoding="utf-8")

    if _ADR_RE.search(text):
        return "adr"
    if _FEATURE_RE.search(text):
        return "feature"
    if _ARCH_RE.search(text):
        return "architecture"
    return "other"


def import_docs(
    project_root: Path,
    docs_dir: Path,
) -> list[dict[str, str]]:
    """Import and classify existing documentation.

    Returns list of dicts with path, kind for each classified doc.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str]] = []
    nodes: list[dict[str, Any]] = []

    for md_path in sorted(docs_dir.rglob("*.md")):
        if not md_path.is_file():
            continue
        kind = classify_doc(md_path)
        rel_path = str(md_path.relative_to(docs_dir))
        results.append({"path": rel_path, "kind": kind})

        # Generate a node for classifiable docs.
        ref_id = md_path.stem.replace(" ", "-").lower()
        nodes.append(
            {
                "ref_id": ref_id,
                "kind": kind if kind in ("feature", "adr", "domain", "service") else "domain",
                "summary": f"Imported from {rel_path}",
                "docs": [f"docs/{rel_path}"],
            }
        )

    if nodes:
        graph_data: dict[str, Any] = {"nodes": nodes}
        (graph_dir / "imported.yml").write_text(
            yaml.dump(graph_data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    return results


def auto_link_docs(
    project_root: Path,
    nodes: list[dict[str, Any]],
) -> int:
    """Match existing docs to graph nodes by path/ref_id similarity.

    Scans the ``docs/`` directory for ``.md`` files, then attempts to match
    each file to a graph node using several heuristics:

    1. Exact ref_id match: ``docs/{ref_id}/README.md`` or ``docs/{ref_id}.md``
    2. Partial ref_id match: file name contains the ref_id
    3. Path-segment match: last dir segment matches ref_id

    When a match is found, updates the node's ``docs`` field in
    ``services.yml`` via the existing ``_patch_docs_field()`` mechanism.

    Parameters
    ----------
    project_root:
        Root of the project.
    nodes:
        List of node dicts from bootstrap (each has ``ref_id``, ``kind``, etc.).

    Returns
    -------
    int
        Number of docs successfully linked.
    """
    docs_dir = project_root / "docs"
    if not docs_dir.is_dir():
        return 0

    # Collect all .md files under docs/.
    md_files: list[Path] = sorted(f for f in docs_dir.rglob("*.md") if f.is_file())
    if not md_files:
        return 0

    # Build a set of ref_ids that don't already have docs linked.
    eligible: dict[str, str] = {}  # ref_id -> ref_id (identity, for lookup)
    for node in nodes:
        ref_id: str = node.get("ref_id", "")
        if not ref_id:
            continue
        # Skip nodes that already have a docs field.
        if node.get("docs"):
            continue
        eligible[ref_id] = ref_id

    if not eligible:
        return 0

    # Score candidates: ref_id -> (score, relative_doc_path).
    # Higher score = better match.  We only keep the best match per ref_id.
    best: dict[str, tuple[int, str]] = {}

    for ref_id in eligible:
        # Strategy 1: Exact path matches (highest priority, score=100).
        exact_candidates = [
            docs_dir / ref_id / "README.md",
            docs_dir / f"{ref_id}.md",
            docs_dir / "domains" / ref_id / "README.md",
            docs_dir / "features" / ref_id / "README.md",
            docs_dir / "services" / ref_id / "README.md",
        ]
        for candidate in exact_candidates:
            if candidate.is_file():
                rel = str(candidate.relative_to(project_root))
                best[ref_id] = (100, rel)
                break

        if ref_id in best:
            continue

        # Strategy 2: Scan md_files for stem or parent-dir matches.
        for md_file in md_files:
            rel_path = str(md_file.relative_to(project_root))
            score = 0

            # Stem match: docs/auth.md -> node "auth" (score=80).
            if md_file.stem == ref_id:
                score = 80

            # Parent dir match: docs/auth/architecture.md -> node "auth" (score=60).
            elif md_file.parent.name == ref_id:
                score = 60

            # Partial stem match: docs/auth-service.md contains "auth" (score=40).
            # Only match if ref_id is reasonably long to avoid false positives.
            elif len(ref_id) >= 3 and ref_id in md_file.stem:
                score = 40

            if score > 0:
                current = best.get(ref_id)
                if current is None or score > current[0]:
                    best[ref_id] = (score, rel_path)

    if not best:
        return 0

    # Build docs_map for _patch_docs_field: ref_id -> relative_doc_path.
    docs_map: dict[str, str] = {ref_id: path for ref_id, (_score, path) in best.items()}

    # Patch YAML graph files.
    from beadloom.onboarding.doc_generator import _patch_docs_field

    graph_dir = project_root / ".beadloom" / "_graph"
    if graph_dir.is_dir() and docs_map:
        _patch_docs_field(graph_dir, docs_map)

    return len(docs_map)
