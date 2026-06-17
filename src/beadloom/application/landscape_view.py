# beadloom:domain=application
# beadloom:feature=site-generation
"""Interactive landscape data (G2, BDL-060 S4) — the renderer-agnostic artifact.

Builds ``landscape.data.json``: a deterministic, JSON-safe model of the local
contract landscape that the Cytoscape+ELK view (``site/.vitepress/theme``)
renders client-side. It is GENERATED from the SAME contract reconciliation the
gate/report use (:func:`beadloom.graph.contracts.reconcile_contracts`) — never a
re-implemented surface — so the map carries the real producer↔consumer links,
their :class:`~beadloom.graph.contracts.ContractVerdict`, and the deep field
surface of both protocols:

- **GraphQL** (S2, G1a): the typed Tier-A ``fields`` (producer ``exposed`` /
  consumer ``referenced``, each ``{name: {type, args}}``) + the named ``missing``
  break paths.
- **AMQP** (S3, G1b): the JSON-Schema ``body`` (producer ``exposed`` / consumer
  ``referenced``) + the named body-diff break paths.

Honest degradation (DATA-STRICTNESS): a contract with no declared field surface
carries an EMPTY ``fields`` / ``body`` block — the view renders "undeclared",
never a fabricated field. Determinism: nodes/edges/contracts are sorted and the
payload serializes with ``sort_keys`` so regeneration is byte-stable; the view
runs ELK with fixed, seedless options so layout adds no view-time randomness.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from beadloom.graph.contracts import Contract, ContractEndpoint, classify

if TYPE_CHECKING:
    import sqlite3

logger = logging.getLogger(__name__)

# Artifact schema version (additive bumps; the view tolerates missing blocks).
LANDSCAPE_SCHEMA_VERSION = 1

_GRAPHQL = "graphql"
_AMQP = "amqp"

# Verdicts treated as a real, actionable break (red health). Mirrors the Mermaid
# landscape's ``_BROKEN_VERDICTS`` so the two views agree on "where it hurts".
_BROKEN_VERDICTS = frozenset(
    {"drift", "breaking", "orphaned_consumer", "undeclared_producer", "undeclared"}
)
_NEUTRAL_VERDICTS = frozenset({"external", "expected", "dead", "unmapped"})

_HEALTHY = "healthy"
_BROKEN = "broken"
_NEUTRAL = "neutral"

# Health severity ordering: broken poisons neutral poisons healthy.
_SEVERITY = {_HEALTHY: 0, _NEUTRAL: 1, _BROKEN: 2}


def _health_class(verdict: str) -> str:
    """Map a verdict to its health bucket (healthy / broken / neutral)."""
    if verdict in _BROKEN_VERDICTS:
        return _BROKEN
    if verdict in _NEUTRAL_VERDICTS:
        return _NEUTRAL
    return _HEALTHY


# ---------------------------------------------------------------------------
# Contract reconciliation from the indexed DB
# ---------------------------------------------------------------------------


def _local_contracts(conn: sqlite3.Connection) -> list[Contract]:
    """Reconcile the local produces/consumes contracts from the indexed DB.

    Reconstructs the edge dicts the reconciler expects (``{src, dst, kind, repo,
    lifecycle, contract: {...}}``) from each contract-bearing edge's ``extra``
    JSON — mirroring the satellite export path
    (:func:`beadloom.graph.federation.export._export_edge`) so the SAME
    :func:`~beadloom.graph.contracts.reconcile_contracts` produces the full
    typed/body surface. The contract payload's ``direction`` is filled from the
    edge ``kind`` when absent (single-repo edges declare it via the kind).
    """
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, extra, lifecycle FROM edges "
        "WHERE kind IN ('produces', 'consumes') "
        "ORDER BY src_ref_id, dst_ref_id, kind"
    ).fetchall()
    edges: list[dict[str, object]] = []
    for row in rows:
        contract = _edge_contract(str(row["extra"] or ""))
        if contract is None:
            continue
        contract.setdefault("direction", str(row["kind"]))
        edges.append(
            {
                "src": str(row["src_ref_id"]),
                "dst": str(row["dst_ref_id"]),
                "kind": str(row["kind"]),
                "repo": "",
                "lifecycle": str(row["lifecycle"] or "active"),
                "contract": contract,
            }
        )
    from beadloom.graph.contracts import reconcile_contracts

    contracts = reconcile_contracts(edges)
    # The reconciler degrades to a name-level / empty surface for an edge whose
    # ``extra`` carried no contract payload but a non-empty ``contract_key``;
    # such legacy edges are still real contracts. Fold them in for completeness.
    contracts.extend(_legacy_contracts(conn, {c.contract_key for c in contracts}))
    return contracts


def _legacy_contracts(
    conn: sqlite3.Connection, seen_keys: set[str]
) -> list[Contract]:
    """Reconcile contract edges that carry only a ``contract_key`` (no payload).

    Older graphs (BDL-041 F4.4) persisted produces/consumes pairs with a bare
    ``contract_key`` and no ``extra.contract`` blob. These have no protocol or
    field surface, but they ARE real producer↔consumer links — surface them with
    an empty surface (honest) so the map is complete. Keyed-but-already-seen
    contracts are skipped (the payload path already produced them).
    """
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, contract_key FROM edges "
        "WHERE kind IN ('produces', 'consumes') AND contract_key != '' "
        "ORDER BY contract_key, src_ref_id, dst_ref_id, kind"
    ).fetchall()
    by_key: dict[str, Contract] = {}
    for row in rows:
        key = str(row["contract_key"])
        if key in seen_keys:
            continue
        contract = by_key.get(key)
        if contract is None:
            contract = Contract(contract_key=key, protocol="", name=key)
            by_key[key] = contract
        contract.endpoints.append(
            ContractEndpoint(repo="", ref_id=str(row["src_ref_id"]), direction=str(row["kind"]))
        )
    contracts = list(by_key.values())
    for contract in contracts:
        contract.verdict = classify(contract)
    return contracts


def _edge_contract(raw_extra: str) -> dict[str, object] | None:
    """Extract the optional ``contract`` payload from an edge's ``extra`` JSON."""
    if not raw_extra:
        return None
    try:
        extra = json.loads(raw_extra)
    except json.JSONDecodeError:
        return None
    if not isinstance(extra, dict):
        return None
    contract = extra.get("contract")
    return contract if isinstance(contract, dict) else None


# ---------------------------------------------------------------------------
# Projection to the renderer-agnostic data model
# ---------------------------------------------------------------------------


def _routing(contract: Contract) -> dict[str, str]:
    """The protocol routing block: AMQP exchange/routing_key, else schema name."""
    if contract.protocol == _AMQP:
        # contract_key == amqp:<exchange>/<routing>:<message_type>
        prefix = _AMQP + ":"
        key = contract.contract_key
        body = key[len(prefix) :] if key.startswith(prefix) else ""
        route, _, message_type = body.rpartition(":")
        exchange, _, routing_key = route.partition("/")
        return {
            "exchange": exchange,
            "routing_key": routing_key,
            "message_type": message_type or contract.name,
        }
    if contract.protocol == _GRAPHQL:
        return {"schema": contract.name}
    return {}


def _contract_dict(contract: Contract) -> dict[str, object]:
    """Project one reconciled Contract to its JSON-safe pop-up payload.

    Carries the producer↔consumer endpoints, the verdict, the protocol routing,
    the named ``missing`` break paths, and the deep field surface: the GraphQL
    typed ``fields`` (S2) OR the AMQP ``body`` JSON-Schema (S3). An absent surface
    is an EMPTY block (the view renders "undeclared") — never a fabricated field.
    """
    verdict = (contract.verdict or classify(contract)).value
    return {
        "contract_key": contract.contract_key,
        "protocol": contract.protocol,
        "name": contract.name,
        "verdict": verdict,
        "lifecycle": contract.lifecycle,
        "routing": _routing(contract),
        "producers": sorted({e.ref_id for e in contract.producers}),
        "consumers": sorted({e.ref_id for e in contract.consumers}),
        "missing": list(contract.missing_references),
        "fields": {
            "exposed": contract.exposed_fields,
            "referenced": contract.referenced_fields,
        },
        "body": {
            "exposed": contract.exposed_body,
            "referenced": contract.referenced_body,
        },
    }


def _edges_from_contracts(
    contracts: list[Contract],
) -> tuple[list[dict[str, object]], dict[str, str]]:
    """Build the deduped landscape edges + the worst-health per node.

    One edge per producer→consumer pair (self-loops dropped), carrying the
    contract's verdict and key. Returns the edges (sorted) plus a health map
    (worst verdict touching each node) so a broken edge poisons its endpoints.
    """
    edges: list[dict[str, object]] = []
    health: dict[str, str] = {}
    seen: set[tuple[str, str, str]] = set()
    for contract in contracts:
        verdict = (contract.verdict or classify(contract)).value
        cls = _health_class(verdict)
        producers = sorted({e.ref_id for e in contract.producers})
        consumers = sorted({e.ref_id for e in contract.consumers})
        for ref in (*producers, *consumers):
            health[ref] = _worse(health.get(ref, _HEALTHY), cls)
        for src in producers:
            for dst in consumers:
                if src == dst:
                    continue
                key = (src, dst, contract.contract_key)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    {
                        "src": src,
                        "dst": dst,
                        "verdict": verdict,
                        "contract_key": contract.contract_key,
                    }
                )
    edges.sort(key=lambda e: (str(e["src"]), str(e["dst"]), str(e["contract_key"])))
    return edges, health


def _worse(current: str, candidate: str) -> str:
    """Return the more-severe of two health classes (broken > neutral > healthy)."""
    return candidate if _SEVERITY[candidate] > _SEVERITY[current] else current


def _node_dicts(
    conn: sqlite3.Connection,
    participant_ids: set[str],
    health: dict[str, str],
    pages: dict[str, str],
) -> list[dict[str, object]]:
    """Build the landscape nodes (contract participants only), sorted by id.

    Each node carries its ``kind`` + ``group`` (the page directory bucket —
    services / domains / features / other — used by the view to cluster by
    landscape/service), its worst-health class, a human ``label``, and a
    ``url`` that is non-empty ONLY when a real page exists (no dead link).
    """
    from beadloom.application.site_pages import _KIND_DIR

    rows = conn.execute(
        "SELECT ref_id, kind, summary FROM nodes ORDER BY ref_id"
    ).fetchall()
    kind_by_id = {str(r["ref_id"]): str(r["kind"]) for r in rows}
    nodes: list[dict[str, object]] = []
    for ref_id in sorted(participant_ids):
        kind = kind_by_id.get(ref_id, "")
        group = _KIND_DIR.get(kind, "other")
        nodes.append(
            {
                "id": ref_id,
                "label": ref_id,
                "kind": kind,
                "group": group,
                "health": health.get(ref_id, _HEALTHY),
                "url": pages.get(ref_id, ""),
            }
        )
    return nodes


def build_landscape_view_data(
    conn: sqlite3.Connection,
    *,
    pages: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build the deterministic interactive-landscape data model (G2, S4).

    Args:
        conn: An open read-only connection to the indexed graph DB.
        pages: Map of ``ref_id -> existing page URL`` (a node gets a non-empty
            ``url`` only when present, so a click never resolves to a dead page).

    Returns:
        A JSON-safe dict ``{schema_version, scope, nodes, edges, contracts}`` with
        every section sorted for byte-stable serialization.
    """
    page_map = pages or {}
    contracts = _local_contracts(conn)
    contracts.sort(key=lambda c: c.contract_key)
    edges, health = _edges_from_contracts(contracts)
    participant_ids: set[str] = set()
    for contract in contracts:
        participant_ids.update(e.ref_id for e in contract.endpoints)
    nodes = _node_dicts(conn, participant_ids, health, page_map)
    contract_dicts = [_contract_dict(c) for c in contracts]
    return {
        "schema_version": LANDSCAPE_SCHEMA_VERSION,
        "scope": "product",
        "nodes": nodes,
        "edges": edges,
        "contracts": contract_dicts,
    }


def serialize_landscape_view(data: dict[str, object]) -> str:
    """Serialize the landscape data to deterministic JSON (sorted keys, 2-space)."""
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def render_landscape_view_md(data: dict[str, object]) -> str:
    """Render the interactive landscape page (``landscape.md``) from *data*.

    The page mounts the client-side ``<LandscapeMap>`` (Cytoscape + ELK, reads
    ``landscape.data.json``) inside ``<ClientOnly>`` so the build stays SSR-safe,
    plus a static honest fallback (the node/contract/problem counts + a link to
    the secondary Mermaid diagram) for when JS is disabled. The component is the
    single interactive surface; this function recomputes no figure — the counts
    are read straight from *data* (which ``build_landscape_view_data`` produced).
    Deterministic: a pure function of *data*.
    """
    nodes = _as_list(data.get("nodes"))
    contracts = _as_list(data.get("contracts"))
    edges = _as_list(data.get("edges"))
    problems = sum(
        1
        for e in edges
        if isinstance(e, dict) and _health_class(str(e.get("verdict", ""))) == _BROKEN
    )
    lines: list[str] = [
        "---",
        "title: Landscape map",
        "---",
        "",
        "# Landscape map",
        "",
        "Generated by `beadloom docs site` from the reconciled contract graph — "
        "never hand-drawn. Nodes are services/repos, edges are cross-service "
        "contracts coloured by health (verdict); click a node or edge for the "
        "contract card (protocol, routing, producer↔consumer, verdict, and the "
        "field/type surface). Layout is ELK (orthogonal routing, non-overlapping "
        "nodes); the deep field data degrades honestly to *undeclared* when a "
        "surface was not declared.",
        "",
        "<ClientOnly>",
        "  <LandscapeMap />",
        "</ClientOnly>",
        "",
        f"_Static summary (JS-off fallback): {len(nodes)} services, "
        f"{len(contracts)} contracts, {problems} problem edge(s)._ See the "
        "[secondary diagram](/landscape-diagram) for a static Mermaid fallback.",
        "",
    ]
    return "\n".join(lines) + "\n"
