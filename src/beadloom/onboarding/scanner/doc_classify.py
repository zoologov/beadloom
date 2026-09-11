"""Documentation classification, import, and auto-linking to graph nodes."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from beadloom.infrastructure.atomic_io import write_yaml_atomic
from beadloom.onboarding.graph_files import each_graph_file
from beadloom.onboarding.scanner.parent_edges import missing_parent_edges, parented_by
from beadloom.onboarding.scanner.ref_ids import RefIdAllocator

if TYPE_CHECKING:
    from pathlib import Path

# Doc classification patterns.
_ADR_RE = re.compile(r"(decision|status:\s*(accepted|deprecated|superseded))", re.I)
_FEATURE_RE = re.compile(r"(user\s+story|feature|requirement|spec)", re.I)
_ARCH_RE = re.compile(r"(architect|system\s+design|infrastructure|deployment)", re.I)

#: The graph file this module writes, and the one thing this reader asks of
#: `each_graph_file` that no other caller asks: skip it, because this run is
#: about to replace it and the graph it must read is the one it will be added
#: to. `rules.yml` is not named here — a rules file is not a graph file for any
#: reader, so it belongs to the shared policy (`graph_files.NOT_A_GRAPH_FILE`)
#: rather than to this caller.
_ABOUT_TO_BE_REPLACED = frozenset({"imported.yml"})


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


@dataclass(frozen=True)
class ExistingGraph:
    """What a writer adding to a graph has to know about the one already there.

    Three answers off one read, because they are three questions about the same
    nodes: which node is the root to attach to, which ref_ids already have a
    parent, and which ref_ids are spoken for. The third joined the other two in
    BDL-069: a document named after an existing node was written as a second node
    under that node's ref_id, and the loader kept one of them (BDL-UX #214).
    """

    root_ref_id: str | None
    parented: frozenset[str]
    ref_ids: frozenset[str]


def _existing_graph(graph_dir: Path) -> ExistingGraph:
    """Read the graph already on disk: its root node, who has a parent, what is named.

    The root is the one node of kind `service` that no `part_of` edge leaves —
    which is what `bootstrap_project` writes and why `generate_rules` dropped
    `service-needs-parent` (the root has no parent by definition). When the
    graph holds no such node, or more than one, this returns *None*: naming a
    parent by guessing between candidates would write an edge that claims
    something the graph does not say.

    "More than one" counts distinct ref_ids, not node entries. The graph
    identifies a node by its ref_id — the loader keeps one node per ref_id, and
    `parented` and `parent_edges.missing_parent_edges`' `seen` are both sets of ref_ids — so
    a single root written twice is a single candidate. Until BDL-067 `.17` the
    candidates were collected into a list and counted there, and
    `bootstrap_project` produced the duplicate on an ordinary project shape: it
    wrote the root service node under the project name and skipped the cluster
    whose sanitized name equalled that name, so a repository named after one of
    its own source directories left two unparented `service` entries under one
    ref_id. The import then attached nothing and `init --yes --mode both` exited
    1 on every run — measured on a project named `core` holding `src/core/` and
    `src/orders/` (the review of BDL-067 `.16`, major 1). Since BDL-069 no writer
    produces that shape: ref_ids are handed out by `RefIdAllocator`, one per node.
    The distinct-ref_id count stays, because this function reads a directory a
    hand edit can reach and a graph file an earlier version wrote.

    The ref_id is read off the node as written rather than recomputed from the
    project name. Cluster refs pass through `_sanitize_ref_id` and the root ref
    does not, so a recomputed destination silently resolves to nothing for a
    project whose name carries parentheses (BDL-067 `.1`).

    A file that is not readable YAML is skipped rather than raised on: `init`
    can meet a hand-edited graph file, and failing the import over it would
    replace a missing edge with a traceback. That skip is `each_graph_file`'s
    since BDL-067 `.24`, along with the three other bodies that held a version
    of it; `imported.yml` is this caller's own reason and is passed as one.
    """
    nodes: list[dict[str, Any]] = []
    parented: set[str] = set()
    for _yml, data in each_graph_file(graph_dir, also_skip=_ABOUT_TO_BE_REPLACED):
        nodes.extend(data.get("nodes") or [])
        parented.update(parented_by(data.get("edges") or []))
    roots = sorted(
        {
            str(n["ref_id"])
            for n in nodes
            if n.get("kind") == "service" and n.get("ref_id") not in parented
        }
    )
    return ExistingGraph(
        root_ref_id=roots[0] if len(roots) == 1 else None,
        parented=frozenset(parented),
        ref_ids=frozenset(str(n["ref_id"]) for n in nodes if n.get("ref_id") is not None),
    )


def import_docs(
    project_root: Path,
    docs_dir: Path,
) -> list[dict[str, str]]:
    """Import and classify existing documentation.

    Post-condition, and the reason this function reads the graph before it
    writes one: every node written here carries an outgoing `part_of` edge to
    the graph's root, unless the graph has no single root to attach it to.

    This is the SECOND writer of `domain` nodes, and the post-condition it holds
    is the same object `bootstrap_project` holds — `parent_edges` — rather than a
    second statement of it. Until BDL-067 `.21` there were two functions with one
    name in two modules, and their only stated connection was a docstring here
    naming a symbol that had been renamed away. They had already drifted once and
    were repaired by editing both (the review of `.16`, minor 2; the review of
    `.20`, major 3). What this writer computes for itself is `parented`, read off
    the graph already on disk, because it is adding to a graph rather than
    producing one.

    Returns list of dicts with path, kind for each classified doc.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str]] = []
    nodes: list[dict[str, Any]] = []

    # Read the graph before writing one, and hand out ref_ids against it. The
    # ref_id a document asks for is its file name, which says nothing about the
    # directory it sits in and nothing about the graph it is joining: two
    # documents called `setup.md` in two areas ask for one name, and a document
    # named after the project asks for the root's. Both were written and one of
    # each pair was dropped at load (BDL-UX #214). `imported.yml` is not among
    # the files read — this run replaces it — so a re-import hands out the same
    # ref_ids it handed out last time.
    existing = _existing_graph(graph_dir)
    ref_ids = RefIdAllocator(existing.ref_ids)

    for md_path in sorted(docs_dir.rglob("*.md")):
        if not md_path.is_file():
            continue
        kind = classify_doc(md_path)
        rel_path = str(md_path.relative_to(docs_dir))
        results.append({"path": rel_path, "kind": kind})

        # Generate a node for classifiable docs.
        node_kind = kind if kind in ("feature", "adr", "domain", "service") else "domain"
        ref_id = ref_ids.take(
            md_path.stem.replace(" ", "-").lower(), qualifier=node_kind
        )
        nodes.append(
            {
                "ref_id": ref_id,
                "kind": node_kind,
                "summary": f"Imported from {rel_path}",
                "docs": [f"docs/{rel_path}"],
            }
        )

    if nodes:
        graph_data: dict[str, Any] = {"nodes": nodes}
        if existing.root_ref_id is not None:
            edges = missing_parent_edges(
                nodes, existing.root_ref_id, set(existing.parented)
            )
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
