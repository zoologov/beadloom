"""Showcase B — the 🌟 cross-repo landscape map (BDL-040 BEAD-03).

Builds the landscape *data* — a deterministic, JSON-safe dict of nodes
(services/repos) and edges (cross-repo contract links) — and renders it as a
**Mermaid** diagram (``landscape.md``). The map is GENERATED from data, never
hand-drawn:

- **Source.** With ``--federated <federated.json>`` (the F2 ``federate`` hub
  output) the map is the cross-repo union: nodes = satellites (``repos[]``),
  edges = the namespaced cross-repo ``edges[]`` between them, each carrying the
  hub's already-computed verdict. Without it, the map is the **LOCAL contract
  graph** (BDL-041 F4.4): the nodes that participate in ``produces`` /
  ``consumes`` contracts and the contract edges between them, each coloured by
  its reconciled :class:`~beadloom.graph.contracts.ContractVerdict`. It is NOT
  the structural intra-repo architecture (that lives in the C4 overview) and NOT
  a foreign fixture — it is the real, honest set of producer→consumer links that
  exist *in this repo* (e.g. the ``beadloom`` service produces the site data the
  ``vitepress-site`` consumes → one ``CONFIRMED`` edge).
- **Verdict labels.** Each edge is labelled by a ``ContractVerdict``-style
  verdict (CONFIRMED / BREAKING / DRIFT / ORPHANED_CONSUMER /
  UNDECLARED_PRODUCER / EXTERNAL …) — carried verbatim from the federated
  artifact, or reconciled locally via :func:`reconcile_contracts` + ``classify``.
- **Health overlay.** A Mermaid ``classDef`` per health bucket (green =
  healthy, red = broken, grey = external/expected) is applied to nodes; broken
  edges get a red ``linkStyle``.
- **Clickable — hardened (BDL-041 F4.4).** A node emits ``click <id> "<url>"``
  ONLY when ``url`` is a page that actually exists in the generated tree (the
  ``pages`` map passed by the generator). A node with no page (a foreign repo,
  or a non-page kind like ``site``) emits NO click — never a dead link (the live
  404/MIME bug: clicks went to ``/services/<ref>`` for pages that did not exist).

Thin slice = Mermaid only (VitePress renders it natively + supports ``click``);
no JS graph library. Output is deterministic (sorted nodes/edges, stable Mermaid
text, no wall-clock) and is written only under ``--out``.
"""

# beadloom:domain=application

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from beadloom.graph.contracts import Contract, ContractEndpoint, classify

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)

# Edge kinds that carry a cross-service contract (the local landscape's source).
_CONTRACT_EDGE_KINDS = ("produces", "consumes")

# Verdicts treated as a real, actionable break (red health). Mirrors the
# F3 SAFE_DEFAULT_FAIL_ON intent: a cross-service drift/breaking/orphan/undeclared
# is unhealthy. The edge-level AMQP equivalent ``undeclared`` is included too.
_BROKEN_VERDICTS = frozenset(
    {"drift", "breaking", "orphaned_consumer", "undeclared_producer", "undeclared"}
)
# Verdicts that are intentional / not-ours (grey, neither healthy nor broken).
_NEUTRAL_VERDICTS = frozenset({"external", "expected", "dead", "unmapped"})

# Health class names (also the Mermaid classDef ids).
_HEALTHY = "healthy"
_BROKEN = "broken"
_NEUTRAL = "neutral"

# The default verdict for an intra-repo edge in the degenerate single-repo map:
# there is no cross-repo peer to reconcile against, so the link is "confirmed".
_DEFAULT_LOCAL_VERDICT = "confirmed"


def _health_class(verdict: str) -> str:
    """Map a verdict to its Mermaid health class (green / red / grey)."""
    if verdict in _BROKEN_VERDICTS:
        return _BROKEN
    if verdict in _NEUTRAL_VERDICTS:
        return _NEUTRAL
    return _HEALTHY


def _mermaid_id(raw: str) -> str:
    """Sanitize a node id into a Mermaid-safe identifier (``n_[A-Za-z0-9_]``).

    Mermaid node ids may not contain ``-`` / ``:`` / ``@`` (used by the
    namespaced ``@repo:ref`` form), so they are replaced with ``_``. The result
    is also **prefixed** with ``n_`` so the id can NEVER equal a reserved Mermaid
    keyword: a node named ``graph`` (charset-valid, but colliding with the
    ``graph LR`` keyword → the live ``got 'GRAPH'`` parse crash) becomes
    ``n_graph``. The mapping is deterministic; the human label and the ``click``
    route keep the original id.
    """
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", raw)


def _strip_namespace(raw: str) -> str:
    """Reduce a federated endpoint id to its owning repo.

    ``@svc-a:plans`` -> ``svc-a`` (the node in the landscape map is the *service*,
    not the intra-repo symbol). A plain id is returned unchanged.
    """
    if raw.startswith("@"):
        body = raw[1:]
        repo, sep, _ = body.partition(":")
        if sep:
            return repo
    return raw


# ---------------------------------------------------------------------------
# Data model build
# ---------------------------------------------------------------------------


def _federated_landscape(federated: Path) -> dict[str, object]:
    """Build the landscape data from a federated.json (F2 hub output).

    Reuses the F2 ``federate`` artifact verbatim: nodes = satellites
    (``repos[]``), edges = the cross-repo ``edges[]`` collapsed to their owning
    repos, each carrying the hub's already-computed ``verdict``. A self-edge
    (both endpoints in the same repo) is dropped — the map shows *between*-service
    links. Contract-level verdicts already ride on the matching edges, so no
    re-derivation happens here.
    """
    payload = _read_json(federated)
    repos = [r for r in _as_list(payload.get("repos")) if isinstance(r, dict)]
    raw_edges = [e for e in _as_list(payload.get("edges")) if isinstance(e, dict)]

    node_ids: set[str] = {
        str(r.get("repo", "")) for r in repos if r.get("repo")
    }
    edges: list[dict[str, object]] = []
    for edge in raw_edges:
        src = _strip_namespace(str(edge.get("src", "")))
        dst = _strip_namespace(str(edge.get("dst", "")))
        if not src or not dst or src == dst:
            continue
        node_ids.add(src)
        node_ids.add(dst)
        verdict = str(edge.get("verdict") or _DEFAULT_LOCAL_VERDICT)
        edges.append({"src": src, "dst": dst, "verdict": verdict})

    return _assemble(node_ids, edges, scope="company" if len(repos) > 1 else "product")


def _local_landscape(conn: sqlite3.Connection) -> dict[str, object]:
    """Local **contract** map: the real producer→consumer links in this repo.

    Reads the ``produces`` / ``consumes`` edges, groups them by ``contract_key``
    into a :class:`~beadloom.graph.contracts.Contract`, and assigns each a
    :class:`~beadloom.graph.contracts.ContractVerdict` via ``classify`` (intent
    vs reality — ``CONFIRMED`` when both a producer and a consumer are present,
    ``ORPHANED_CONSUMER`` / ``UNDECLARED_PRODUCER`` otherwise). Each contract
    becomes one landscape edge per producer→consumer pair carrying that verdict;
    nodes = the participating endpoints only.

    This is the *contract* graph, NOT the structural intra-repo architecture
    (which lives in the C4 overview) — so a repo with no produces/consumes
    contracts yields an empty map. Reads the indexed DB read-only.
    """
    edge_rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, contract_key, lifecycle FROM edges "
        "WHERE kind IN ('produces', 'consumes') "
        "ORDER BY contract_key, src_ref_id, dst_ref_id, kind"
    ).fetchall()
    contracts = _group_local_contracts(edge_rows)
    node_ids: set[str] = set()
    edges: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for contract in contracts:
        verdict = (contract.verdict or classify(contract)).value
        producers = sorted({e.ref_id for e in contract.producers})
        consumers = sorted({e.ref_id for e in contract.consumers})
        node_ids.update(producers, consumers)
        for src in producers:
            for dst in consumers:
                if src == dst or (src, dst) in seen:
                    continue
                seen.add((src, dst))
                edges.append({"src": src, "dst": dst, "verdict": verdict})
    return _assemble(node_ids, edges, scope="product")


def _group_local_contracts(edge_rows: list[sqlite3.Row]) -> list[Contract]:
    """Group local produces/consumes edge rows into reconciled Contracts.

    The grouping key is the persisted ``contract_key`` (already
    protocol-prefixed by the loader). Each edge contributes one endpoint whose
    ``direction`` is the edge ``kind`` (``produces`` / ``consumes``) and whose
    ``ref_id`` is the edge ``src`` (the declaring node). Deterministic: rows
    arrive pre-sorted, so contracts appear in ``contract_key`` order.
    """
    by_key: dict[str, Contract] = {}
    for row in edge_rows:
        key = str(row["contract_key"]) or f"{row['src_ref_id']}->{row['dst_ref_id']}"
        contract = by_key.get(key)
        if contract is None:
            contract = Contract(contract_key=key, protocol="", name=key)
            by_key[key] = contract
        contract.endpoints.append(
            ContractEndpoint(
                repo="",
                ref_id=str(row["src_ref_id"]),
                direction=str(row["kind"]),
            )
        )
        contract.lifecycle = str(row["lifecycle"] or "active")
    contracts = list(by_key.values())
    for contract in contracts:
        contract.verdict = classify(contract)
    return contracts


def _assemble(
    node_ids: set[str], edges: list[dict[str, object]], *, scope: str
) -> dict[str, object]:
    """Assemble the deterministic landscape data dict (sorted nodes + edges)."""
    nodes = [{"id": ref_id} for ref_id in sorted(node_ids)]
    edges = sorted(edges, key=lambda e: (str(e["src"]), str(e["dst"]), str(e["verdict"])))
    return {"scope": scope, "nodes": nodes, "edges": edges}


def existing_page_urls(conn: sqlite3.Connection) -> dict[str, str]:
    """Map every node that has a generated page to its absolute page URL.

    A node page is emitted only for kinds with an output directory (see
    :data:`beadloom.application.site_pages._KIND_DIR` — ``service`` / ``domain``
    / ``feature``). The URL mirrors that page's location (``/<dir>/<ref>``), so
    the landscape map's ``click`` links resolve to real pages — never a 404
    (BDL-041 F4.4). A node whose kind has no page directory is absent from the
    map and therefore renders without a click.
    """
    from beadloom.application.site_pages import _KIND_DIR

    rows = conn.execute("SELECT ref_id, kind FROM nodes ORDER BY ref_id").fetchall()
    urls: dict[str, str] = {}
    for row in rows:
        directory = _KIND_DIR.get(str(row["kind"]))
        if directory is not None:
            urls[str(row["ref_id"])] = f"/{directory}/{row['ref_id']}"
    return urls


def build_landscape_data(
    conn: sqlite3.Connection | None = None,
    *,
    federated: Path | None = None,
) -> dict[str, object]:
    """Build the deterministic landscape-map data (federated or single-repo).

    Args:
        conn: An open read-only connection to the indexed graph DB (the source
            for the degenerate single-repo map when no artifact is given).
        federated: Optional ``federate`` output JSON; when given, the map is the
            cross-repo union (nodes = satellites, edges = cross-repo links with
            the hub's verdicts).

    Returns:
        A JSON-safe dict ``{scope, nodes: [{id}], edges: [{src, dst, verdict}]}``
        with nodes and edges sorted for byte-stable Mermaid output.
    """
    if federated is not None:
        return _federated_landscape(federated)
    if conn is None:  # pragma: no cover - guarded by the CLI/generator wiring
        return _assemble(set(), [], scope="product")
    return _local_landscape(conn)


def _read_json(path: Path) -> dict[str, object]:
    """Read + parse a JSON artifact, returning ``{}`` on any read/parse error."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read federated artifact %s", path)
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------


def _node_lines(
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    pages: dict[str, str],
) -> list[str]:
    """Render node declarations + per-node health class + clickable links.

    A node's health is the worst verdict on any edge touching it (a broken edge
    poisons its endpoints red); otherwise grey when only neutral, else green.

    A ``click`` is emitted ONLY when the node has a real page in *pages* (the
    generator's set of existing page URLs). A node with no page (a foreign repo,
    or a non-page kind such as ``site``) emits no click — never a dead link
    (BDL-041 F4.4: the live 404/MIME bug came from a click to a page that did not
    exist).
    """
    health = _node_health(nodes, edges)
    lines: list[str] = []
    for node in nodes:
        ref = str(node["id"])
        mid = _mermaid_id(ref)
        lines.append(f"    {mid}[{ref}]")
        lines.append(f"    class {mid} {health[ref]}")
        url = pages.get(ref)
        if url:
            lines.append(f'    click {mid} "{url}"')
    return lines


def _node_health(
    nodes: list[dict[str, object]], edges: list[dict[str, object]]
) -> dict[str, str]:
    """Resolve each node's health bucket from the verdicts of its incident edges."""
    health: dict[str, str] = {str(n["id"]): _HEALTHY for n in nodes}
    for edge in edges:
        cls = _health_class(str(edge["verdict"]))
        for endpoint in (str(edge["src"]), str(edge["dst"])):
            if endpoint not in health:
                continue
            health[endpoint] = _worse(health[endpoint], cls)
    return health


# Health severity ordering: broken poisons neutral poisons healthy.
_SEVERITY = {_HEALTHY: 0, _NEUTRAL: 1, _BROKEN: 2}


def _worse(current: str, candidate: str) -> str:
    """Return the more-severe of two health classes (broken > neutral > healthy)."""
    return candidate if _SEVERITY[candidate] > _SEVERITY[current] else current


def _edge_lines(edges: list[dict[str, object]]) -> tuple[list[str], list[int]]:
    """Render edge declarations (labelled by verdict); collect broken-edge indices."""
    lines: list[str] = []
    broken: list[int] = []
    for index, edge in enumerate(edges):
        src = _mermaid_id(str(edge["src"]))
        dst = _mermaid_id(str(edge["dst"]))
        verdict = str(edge["verdict"])
        lines.append(f"    {src} -->|{verdict.upper()}| {dst}")
        if _health_class(verdict) == _BROKEN:
            broken.append(index)
    return lines, broken


def _classdef_lines() -> list[str]:
    """The Mermaid ``classDef`` health overlay (green / red / grey)."""
    return [
        f"    classDef {_HEALTHY} fill:#d4edda,stroke:#28a745,color:#155724;",
        f"    classDef {_BROKEN} fill:#f8d7da,stroke:#dc3545,color:#721c24;",
        f"    classDef {_NEUTRAL} fill:#e2e3e5,stroke:#6c757d,color:#383d41;",
    ]


def _linkstyle_lines(broken: list[int]) -> list[str]:
    """Red ``linkStyle`` for each broken edge (by declaration index)."""
    return [
        f"    linkStyle {index} stroke:#dc3545,stroke-width:2px;"
        for index in broken
    ]


def render_landscape_md(
    data: dict[str, object], *, pages: dict[str, str] | None = None
) -> str:
    """Render the ``landscape.md`` page (a Mermaid diagram) from *data*.

    Args:
        data: The landscape data dict (``{scope, nodes, edges}``).
        pages: Map of ``ref_id -> existing page URL``. A node emits a ``click``
            only when present here, so the rendered map never links to a page
            that does not exist (BDL-041 F4.4 — the live 404/MIME fix). ``None``
            (no map) means no node is clickable.

    Deterministic: nodes/edges are already sorted in *data*; the Mermaid block,
    health ``classDef``s, clickable links, and broken-edge ``linkStyle``s are
    emitted in a stable order. No figure is recomputed here.
    """
    page_map = pages or {}
    nodes = [n for n in _as_list(data.get("nodes")) if isinstance(n, dict)]
    edges = [e for e in _as_list(data.get("edges")) if isinstance(e, dict)]
    scope = str(data.get("scope", "product"))

    edge_lines, broken = _edge_lines(edges)
    intro = (
        "The cross-repo contract landscape (company scope)."
        if scope == "company"
        else "The single-repo landscape (one product)."
    )
    body: list[str] = [
        "---",
        "title: Landscape map",
        "---",
        "",
        "# Landscape map",
        "",
        "Generated by `beadloom docs site` from the `federate` graph — never "
        "hand-drawn. Edges are labelled by their cross-repo `ContractVerdict`; "
        "node colour reflects health (green = healthy, red = broken, grey = "
        "external/expected). Click a service to open its page.",
        "",
        intro,
        "",
        "```mermaid",
        "graph LR",
    ]
    body.extend(_node_lines(nodes, edges, page_map))
    body.extend(edge_lines)
    body.extend(_classdef_lines())
    body.extend(_linkstyle_lines(broken))
    body.append("```")
    body.append("")
    return "\n".join(body) + "\n"
