"""Documentation classification, import, and auto-linking to graph nodes."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import yaml

from beadloom.infrastructure.atomic_io import write_yaml_atomic

if TYPE_CHECKING:
    from pathlib import Path

# Doc classification patterns.
_ADR_RE = re.compile(r"(decision|status:\s*(accepted|deprecated|superseded))", re.I)
_FEATURE_RE = re.compile(r"(user\s+story|feature|requirement|spec)", re.I)
_ARCH_RE = re.compile(r"(architect|system\s+design|infrastructure|deployment)", re.I)

#: The graph file this module writes, and the one file under `_graph/` that
#: holds no nodes. Both are excluded when the existing graph is read: the first
#: because it is about to be replaced by this run, the second because a rules
#: file is not a graph.
_NOT_THE_EXISTING_GRAPH = frozenset({"imported.yml", "rules.yml"})


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


def _existing_graph(graph_dir: Path) -> tuple[str | None, set[str]]:
    """Read the graph already on disk: its root node, and who already has a parent.

    The root is the one node of kind `service` that no `part_of` edge leaves —
    which is what `bootstrap_project` writes and why `generate_rules` dropped
    `service-needs-parent` (the root has no parent by definition). When the
    graph holds no such node, or more than one, this returns *None*: naming a
    parent by guessing between candidates would write an edge that claims
    something the graph does not say.

    "More than one" counts distinct ref_ids, not node entries. The graph
    identifies a node by its ref_id — the loader keeps one node per ref_id, and
    `parented` and `_missing_parent_edges`' `seen` are both sets of ref_ids — so
    a single root written twice is a single candidate. Until BDL-067 `.17` the
    candidates were collected into a list and counted there, and
    `bootstrap_project` produces the duplicate on an ordinary project shape: it
    writes the root service node under the project name and its top-level
    attachment loop skips the cluster whose sanitized name equals that name
    (`bootstrap.py`), so a repository named after one of its own source
    directories yields two unparented `service` entries under one ref_id. The
    import then attached nothing and `init --yes --mode both` exited 1 on every
    run — measured on a project named `core` holding `src/core/` and
    `src/orders/` (the review of BDL-067 `.16`, major 1).

    The ref_id is read off the node as written rather than recomputed from the
    project name. Cluster refs pass through `_sanitize_ref_id` and the root ref
    does not, so a recomputed destination silently resolves to nothing for a
    project whose name carries parentheses (BDL-067 `.1`).

    A file that is not readable YAML is skipped rather than raised on: `init`
    can meet a hand-edited graph file, and failing the import over it would
    replace a missing edge with a traceback.
    """
    nodes: list[dict[str, Any]] = []
    parented: set[str] = set()
    for yml in sorted(graph_dir.glob("*.yml")):
        if yml.name in _NOT_THE_EXISTING_GRAPH:
            continue
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        nodes.extend(data.get("nodes") or [])
        parented.update(
            str(e["src"])
            for e in (data.get("edges") or [])
            if e.get("kind") == "part_of" and e.get("src")
        )
    roots = sorted(
        {
            str(n["ref_id"])
            for n in nodes
            if n.get("kind") == "service" and n.get("ref_id") not in parented
        }
    )
    return (roots[0] if len(roots) == 1 else None), parented


def _missing_parent_edges(
    nodes: list[dict[str, Any]],
    root_ref_id: str,
    parented: set[str],
) -> list[dict[str, str]]:
    """Name the `part_of` edges the imported nodes are still short of.

    The same post-condition `bootstrap_project` holds over its own output
    (`bootstrap._missing_domain_parent_edges`), stated here because `import_docs`
    is the SECOND writer of `domain` nodes and the first statement of it never
    reached this one: every document the classifier cannot place became a
    `domain` with no parent, in the same run that wrote `domain-needs-parent` at
    error severity, so `init --yes --mode both` exited 0 and the adopter's next
    `lint --strict` exited 1 (BDL-067 `.14`, reproducing BDL-UX #192 on a branch
    the epic had declared covered).

    The edge is written for every kind, not only for the two the generated rules
    require a parent for. An imported node is part of the project whatever the
    classifier called it, and a post-condition that tracked the current rule set
    would go stale the next time a rule is added.

    Two nodes are left alone: one whose ref_id already carries a `part_of` edge
    somewhere in the graph keeps the parent it has, and one whose ref_id is the
    root's own gets nothing, because an edge from a node to itself is not a
    parent.
    """
    edges: list[dict[str, str]] = []
    seen = set(parented)
    for node in nodes:
        ref_id = str(node["ref_id"])
        if ref_id == root_ref_id or ref_id in seen:
            continue
        edges.append({"src": ref_id, "dst": root_ref_id, "kind": "part_of"})
        seen.add(ref_id)
    return edges


def import_docs(
    project_root: Path,
    docs_dir: Path,
) -> list[dict[str, str]]:
    """Import and classify existing documentation.

    Post-condition, and the reason this function reads the graph before it
    writes one: every node written here carries an outgoing `part_of` edge to
    the graph's root, unless the graph has no single root to attach it to.

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
        root_ref_id, parented = _existing_graph(graph_dir)
        graph_data: dict[str, Any] = {"nodes": nodes}
        if root_ref_id is not None:
            edges = _missing_parent_edges(nodes, root_ref_id, parented)
            if edges:
                graph_data["edges"] = edges
        write_yaml_atomic(
            graph_dir / "imported.yml",
            graph_data,
            default_flow_style=False,
            allow_unicode=True,
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
