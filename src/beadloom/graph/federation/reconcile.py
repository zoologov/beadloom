# beadloom:domain=graph
# beadloom:feature=federation
"""Hub aggregation: compose >=2 satellite exports into a federated graph (BEAD-04).

The hub :func:`aggregate_exports` namespaces every node/edge as ``@repo:ref_id``,
resolves foreign refs against the union, assigns a three-valued intent-vs-reality
:class:`EdgeVerdict` to every edge, reconciles AMQP/GraphQL contracts (delegating
to :mod:`beadloom.graph.contracts`), and records each satellite's staleness.
:func:`serialize_federation` / :func:`render_federation_report` project that
:class:`FederatedGraph` to deterministic JSON and a human report.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from datetime import datetime

from beadloom.graph.amqp_body import serialize_body
from beadloom.graph.contracts import (
    cross_landscape_keys,
    edge_group_key,
    reconcile_contracts,
)
from beadloom.graph.federation.refs import (
    _FOREIGN_MARKER,
    FederationRefError,
    is_foreign_ref,
    parse_ref,
)

# Federated graph artifact schema version (independent of the satellite export
# schema; bumped on breaking shape changes to ``federated.json``).
#
# v2 (BDL-038 BEAD-04): each ``contracts`` entry now carries a contract-level
# ``ContractVerdict`` (``verdict``) plus ``protocol`` / ``contract_key`` /
# ``lifecycle`` and, for GraphQL, ``exposed`` / ``references`` / the ``missing``
# names that triggered ``BREAKING``. F1's flat keys (``message_type`` /
# ``directions`` / ``repos`` / ``confirmed``) are KEPT as a subset, so older
# readers still work. ``contracts`` is now sorted by ``contract_key`` for
# deterministic, reviewable diffs. The bump is on the hub OUTPUT only — ``federate``
# still ingests v1 AND v2 satellite *exports* (the two versions are independent).
FEDERATION_SCHEMA_VERSION = 2


class EdgeVerdict(enum.Enum):
    """Three-valued (and then some) intent-vs-reality verdict for an edge.

    Computed at the hub by reconciling an edge's declared ``lifecycle`` with
    whether its target resolves in the federated union:

    - :attr:`OK`                 — declared ``active`` and target present.
    - :attr:`DRIFT`              — declared ``active`` but target absent
      (a real, broken cross-repo dependency — the killer signal).
    - :attr:`EXPECTED`           — declared ``planned`` and target absent
      (intentional: the target is not built yet).
    - :attr:`CLEANUP_CANDIDATE`  — declared ``deprecated`` but target still
      present (the dependency outlived its declared death).
    - :attr:`UNDECLARED`         — a present contract producer with no peer
      declaring the matching consume (emitting into the void).
    - :attr:`DEAD`               — declared ``dead``; not treated as live.
    - :attr:`EXTERNAL`           — the edge (or its target node) is declared
      ``external`` (a present-but-not-ours node, e.g. a native bridge); never
      DRIFT (BDL-038 G7).
    - :attr:`UNMAPPED`           — the target resolves in the union but is
      present-without-a-usable-surface (undescribed — empty summary); reported
      honestly, never DRIFT (BDL-038 U4).
    """

    OK = "ok"
    DRIFT = "drift"
    EXPECTED = "expected"
    CLEANUP_CANDIDATE = "cleanup_candidate"
    UNDECLARED = "undeclared"
    DEAD = "dead"
    EXTERNAL = "external"
    UNMAPPED = "unmapped"


@dataclass
class FederatedGraph:
    """The composed result of aggregating >=2 satellite exports.

    - ``nodes`` / ``edges``: the namespaced union (``@repo:ref_id`` identity).
    - ``repos``: per-satellite provenance + staleness (commit_sha, exported_at,
      age_seconds) — reported, never faked (Q4 honesty).
    - ``unresolved_refs``: foreign refs that did not resolve in the union
      (reported, not silently dropped).
    - ``contracts``: AMQP contract reconciliation (confirmed both-sides vs
      one-sided).
    """

    nodes: list[dict[str, object]] = field(default_factory=list)
    edges: list[dict[str, object]] = field(default_factory=list)
    repos: list[dict[str, object]] = field(default_factory=list)
    unresolved_refs: list[str] = field(default_factory=list)
    contracts: list[dict[str, object]] = field(default_factory=list)


def _namespace(repo: str, ref_id: str) -> str:
    """Qualify a local ``ref_id`` into the federated ``@repo:ref_id`` form."""
    return f"{_FOREIGN_MARKER}{repo}:{ref_id}"


def _resolve_endpoint(repo: str, raw: str) -> str:
    """Resolve an edge endpoint to its canonical federated id.

    A foreign endpoint (``@other:ref``) keeps its own namespace; a local
    endpoint is namespaced under the edge's own ``repo``. Malformed foreign
    refs fall back to the raw string (surfaced later via ``unresolved_refs``).
    """
    try:
        ref = parse_ref(raw)
    except FederationRefError:
        return raw
    if ref.is_foreign:
        return ref.qualified
    return _namespace(repo, ref.ref_id)


def _parse_age_seconds(exported_at: str, now: datetime) -> int | None:
    """Return the satellite export age in whole seconds, or ``None`` if unknown.

    The hub cannot know a satellite's live HEAD; "freshness" is how recently it
    was exported. An unparseable timestamp yields ``None`` (honest unknown).
    """
    try:
        exported = datetime.fromisoformat(exported_at)
    except (ValueError, TypeError):
        return None
    if exported.tzinfo is None:
        exported = exported.replace(tzinfo=now.tzinfo)
    return int((now - exported).total_seconds())


def _repo_provenance(export: dict[str, object], now: datetime) -> dict[str, object]:
    """Build the per-satellite provenance + staleness record."""
    exported_at = export.get("exported_at")
    age = (
        _parse_age_seconds(exported_at, now)
        if isinstance(exported_at, str)
        else None
    )
    landscape = _export_landscape(export)
    return {
        "repo": export.get("repo"),
        # Provenance default (BEAD-06, U5): a satellite with no declared landscape
        # belongs to a product named after its repo — reported honestly here even
        # though reconciliation treats undeclared landscapes as one shared group.
        "landscape": landscape if landscape is not None else export.get("repo"),
        "commit_sha": export.get("commit_sha"),
        "exported_at": exported_at,
        "schema_version": export.get("schema_version"),
        "age_seconds": age,
    }


def _verdict_for(lifecycle: str, *, target_present: bool) -> EdgeVerdict:
    """Reconcile a non-contract edge's declared lifecycle against reality."""
    if lifecycle == "planned":
        return EdgeVerdict.EXPECTED
    if lifecycle == "dead":
        return EdgeVerdict.DEAD
    if lifecycle == "deprecated":
        return (
            EdgeVerdict.CLEANUP_CANDIDATE if target_present else EdgeVerdict.EXPECTED
        )
    # active (default)
    return EdgeVerdict.OK if target_present else EdgeVerdict.DRIFT


def _edge_contract_payload(edge: dict[str, object]) -> dict[str, object] | None:
    """Return the edge's contract dict if it carries one."""
    contract = edge.get("contract")
    return contract if isinstance(contract, dict) else None


def aggregate_exports(
    exports: list[dict[str, object]],
    *,
    now: str | None = None,
) -> FederatedGraph:
    """Compose one federated graph from >=2 satellite export artifacts.

    Namespaces every node/edge endpoint as ``@repo:ref_id``, resolves foreign
    refs against the union (unresolved ones recorded, never dropped), assigns a
    three-valued intent-vs-reality :class:`EdgeVerdict` to every edge, reconciles
    AMQP contracts into confirmed-both-sides / one-sided, and records each
    satellite's staleness. ``now`` (ISO-8601) is injected for deterministic age
    in tests; the CLI passes wall-clock UTC.
    """
    now_dt = _resolve_now(now)
    fed = FederatedGraph()
    present_ids: set[str] = set()

    for export in exports:
        repo = str(export.get("repo", ""))
        fed.repos.append(_repo_provenance(export, now_dt))
        for node in _export_nodes(export):
            ns_id = _namespace(repo, str(node.get("ref_id", "")))
            present_ids.add(ns_id)
            fed.nodes.append({**node, "ref_id": ns_id, "repo": repo})

    for export in exports:
        repo = str(export.get("repo", ""))
        landscape = _export_landscape(export)
        for edge in _export_edges(export):
            fed.edges.append(_resolve_edge(repo, edge, landscape))

    _assign_verdicts(fed, present_ids)
    fed.contracts.extend(_reconcile_contracts(fed.edges))
    _mark_undeclared(fed)
    fed.contracts.sort(key=lambda c: str(c.get("contract_key", "")))
    fed.nodes.sort(key=lambda n: str(n["ref_id"]))
    fed.edges.sort(key=lambda e: (str(e["src"]), str(e["dst"]), str(e["kind"])))
    fed.repos.sort(key=lambda r: str(r["repo"]))
    fed.unresolved_refs = sorted(set(fed.unresolved_refs))
    return fed


def _resolve_now(now: str | None) -> datetime:
    """Return a tz-aware reference time (injected ISO string or wall-clock UTC)."""
    from datetime import timezone

    if now is None:
        return datetime.now(tz=timezone.utc)
    parsed = datetime.fromisoformat(now)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _export_nodes(export: dict[str, object]) -> list[dict[str, object]]:
    raw = export.get("nodes")
    return [n for n in raw if isinstance(n, dict)] if isinstance(raw, list) else []


def _export_edges(export: dict[str, object]) -> list[dict[str, object]]:
    raw = export.get("edges")
    return [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []


def _export_landscape(export: dict[str, object]) -> str | None:
    """Return an export's declared landscape, or ``None`` (F1 back-compat).

    A landscape-less export belongs to the shared run-level default group, so a
    single-product / no-landscape ``federate`` run reconciles exactly as F1.
    """
    landscape = export.get("landscape")
    return landscape if isinstance(landscape, str) and landscape else None


def _resolve_edge(
    repo: str, edge: dict[str, object], landscape: str | None
) -> dict[str, object]:
    """Namespace + foreign-resolve an edge's endpoints into a federated edge.

    Tags the federated edge with its satellite's ``landscape`` (BEAD-06, U5) so
    the hub can scope implicit contract matching by ``(landscape, contract_key)``
    — ``None`` means the export declared no landscape (one shared default group).
    """
    src = _resolve_endpoint(repo, str(edge.get("src", "")))
    dst = _resolve_endpoint(repo, str(edge.get("dst", "")))
    resolved: dict[str, object] = {
        "src": src,
        "dst": dst,
        "kind": edge.get("kind"),
        "lifecycle": edge.get("lifecycle", "active"),
        "repo": repo,
    }
    if landscape is not None:
        resolved["landscape"] = landscape
    contract = _edge_contract_payload(edge)
    if contract is not None:
        resolved["contract"] = _normalize_contract_surface(contract)
    return resolved


def _normalize_contract_surface(contract: dict[str, object]) -> dict[str, object]:
    """Return a copy of *contract* with its GraphQL surface made canonical.

    ``exposed`` / ``references`` are carried verbatim from the satellite export,
    so a producer (or consumer) emitting an equivalent surface in a different
    order would otherwise serialize differently in the per-edge ``contract``
    mirror — breaking the byte-identical determinism invariant that the
    reconciled ``contracts[]`` section already upholds. Sort + dedupe those
    lists; likewise canonicalize the TYPED ``fields`` block (BDL-060 S2): sort
    fields by name and each field's args by name. The AMQP ``body`` JSON-Schema
    (BDL-060 S3) is canonicalized the same way (properties + ``required`` sorted,
    recursively, via :func:`beadloom.graph.amqp_body.serialize_body`). Leave every
    other field untouched. Shallow-copies so the input edge/contract dict is never
    mutated.
    """
    normalized = dict(contract)
    for key in ("exposed", "references"):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = sorted({str(item) for item in value})
    fields = normalized.get("fields")
    if isinstance(fields, list):
        normalized["fields"] = _normalize_typed_fields(fields)
    body = normalized.get("body")
    if isinstance(body, dict) and body:
        normalized["body"] = serialize_body(body)
    return normalized


def _normalize_typed_fields(fields: list[object]) -> list[dict[str, object]]:
    """Sort a typed ``fields`` block (fields by name, args by name) — deduped.

    Mirrors :func:`beadloom.graph.graphql_surface.serialize_typed_surface` so the
    federated per-edge mirror is byte-identical to a freshly serialized surface,
    regardless of the satellite's field/arg ordering. A malformed entry is
    dropped (honest), never fabricated.
    """
    normalized: dict[str, dict[str, object]] = {}
    for entry in fields:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        raw_args = entry.get("args")
        args = (
            [a for a in raw_args if isinstance(a, dict) and a.get("name")]
            if isinstance(raw_args, list)
            else []
        )
        normalized[name] = {
            "name": name,
            "type": entry.get("type", ""),
            "args": sorted(args, key=lambda a: str(a.get("name", ""))),
        }
    return [normalized[name] for name in sorted(normalized)]


def _assign_verdicts(fed: FederatedGraph, present_ids: set[str]) -> None:
    """Assign an :class:`EdgeVerdict` to each edge; record unresolved targets.

    External targets (the edge or its target node declares ``external``) resolve
    to :attr:`EdgeVerdict.EXTERNAL` and a present-but-undescribed target resolves
    to :attr:`EdgeVerdict.UNMAPPED` — both suppress DRIFT (BDL-038 G7/U4). Only a
    genuinely-absent active foreign target is recorded as an unresolved ref, so
    the unresolved-ref set (absent) stays distinct from ``unmapped`` (present).
    """
    nodes_by_id = {str(node["ref_id"]): node for node in fed.nodes}
    for edge in fed.edges:
        dst = str(edge["dst"])
        target_present = dst in present_ids
        lifecycle = str(edge.get("lifecycle", "active"))
        verdict = _edge_verdict(
            lifecycle, target_present=target_present, target=nodes_by_id.get(dst)
        )
        edge["verdict"] = verdict.value
        if (
            not target_present
            and is_foreign_ref(dst)
            and verdict in (EdgeVerdict.DRIFT, EdgeVerdict.EXPECTED)
        ):
            fed.unresolved_refs.append(dst)


def _edge_verdict(
    lifecycle: str, *, target_present: bool, target: dict[str, object] | None
) -> EdgeVerdict:
    """Reconcile an edge's lifecycle + its target node against the union (G7/U4).

    Precedence: an ``external`` edge **or** an ``external`` target node suppresses
    DRIFT (``EXTERNAL``); a present-but-undescribed target (empty summary) is
    ``UNMAPPED``; otherwise the F1 three-valued lifecycle reconciliation applies.
    """
    if lifecycle == "external" or _is_external(target):
        return EdgeVerdict.EXTERNAL
    if target_present and lifecycle == "active" and _is_undescribed(target):
        return EdgeVerdict.UNMAPPED
    return _verdict_for(lifecycle, target_present=target_present)


def _is_external(target: dict[str, object] | None) -> bool:
    """True when the resolved target node declares ``lifecycle: external``."""
    return target is not None and str(target.get("lifecycle", "")) == "external"


def _is_undescribed(target: dict[str, object] | None) -> bool:
    """True when a present target node has no usable surface (empty summary, U4)."""
    return target is not None and not str(target.get("summary", "")).strip()


def _reconcile_contracts(
    edges: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Reconcile AMQP contract edges into confirmed-both-sides / one-sided.

    Delegates to the first-class :mod:`beadloom.graph.contracts` model (F2,
    BDL-038) and projects each :class:`~beadloom.graph.contracts.Contract` back
    to F1's flat ``{message_type, directions, repos, confirmed}`` shape, so the
    federated output is byte-identical to F1.
    """
    return [c.to_report_dict() for c in reconcile_contracts(edges)]


def _contract_directions(contract: dict[str, object]) -> list[str]:
    """Return a contract's ``directions`` as a list of strings (typed accessor)."""
    directions = contract.get("directions")
    if isinstance(directions, list):
        return [str(d) for d in directions]
    return []


def _mark_undeclared(fed: FederatedGraph) -> None:
    """Flag present producer contract edges whose contract has no consumer.

    A satellite producing into a contract that no peer declares consuming is
    emitting into the void — :attr:`EdgeVerdict.UNDECLARED`. Scoped by
    ``(landscape, contract_key)`` (BEAD-06, U5) so two unrelated products that
    share a coincidental message_type never silence each other's honest
    UNDECLARED — and an explicit cross-product key (collapsed to a shared group)
    confirms across landscapes.
    """
    xkeys = cross_landscape_keys(fed.edges)
    consumed_groups: set[tuple[str | None, str]] = set()
    for edge in fed.edges:
        group = edge_group_key(edge, xkeys)
        if group is None:
            continue
        contract = _edge_contract_payload(edge)
        if contract is not None and contract.get("direction") == "consumes":
            consumed_groups.add(group)
    for edge in fed.edges:
        contract = _edge_contract_payload(edge)
        if contract is None or contract.get("protocol") != "amqp":
            continue
        if contract.get("direction") != "produces":
            continue
        group = edge_group_key(edge, xkeys)
        if group is not None and group not in consumed_groups:
            edge["verdict"] = EdgeVerdict.UNDECLARED.value


def serialize_federation(fed: FederatedGraph) -> str:
    """Serialize a :class:`FederatedGraph` to deterministic JSON (sorted keys)."""
    payload = {
        "schema_version": FEDERATION_SCHEMA_VERSION,
        "repos": fed.repos,
        "nodes": fed.nodes,
        "edges": fed.edges,
        "contracts": fed.contracts,
        "unresolved_refs": fed.unresolved_refs,
    }
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)


def _format_age(age_seconds: int | None) -> str:
    """Human-readable age string ('unknown' when the hub can't verify)."""
    if age_seconds is None:
        return "unknown age"
    days, rem = divmod(age_seconds, 86400)
    hours = rem // 3600
    if days:
        return f"{days}d {hours}h ago"
    minutes = (rem % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m ago"
    return f"{minutes}m ago"


def render_federation_report(fed: FederatedGraph) -> str:
    """Render a human-readable text report of the federated graph + verdicts."""
    lines: list[str] = ["# Beadloom Federation Report", ""]
    lines.extend(_report_repos(fed))
    lines.extend(_report_verdicts(fed))
    lines.extend(_report_contracts(fed))
    lines.extend(_report_unresolved(fed))
    return "\n".join(lines) + "\n"


def _report_repos(fed: FederatedGraph) -> list[str]:
    """Satellites grouped by landscape (BEAD-06, U5) — makes the product vs
    company-landscape composition visible, then the per-satellite provenance."""
    by_landscape: dict[str, list[dict[str, object]]] = {}
    for repo in fed.repos:
        landscape = str(repo.get("landscape") or repo.get("repo") or "")
        by_landscape.setdefault(landscape, []).append(repo)
    scope = "product" if len(by_landscape) == 1 else "company"
    lines = [f"## Satellites ({len(fed.repos)}) — {scope}-landscape", ""]
    for landscape in sorted(by_landscape):
        lines.append(f"### landscape: {landscape}")
        for repo in by_landscape[landscape]:
            sha = repo.get("commit_sha") or "unknown HEAD"
            age = _format_age(_as_age(repo.get("age_seconds")))
            lines.append(f"- {repo.get('repo')}: {sha} — exported {age}")
        lines.append("")
    return lines


def _as_age(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _report_verdicts(fed: FederatedGraph) -> list[str]:
    counts: dict[str, int] = {}
    for edge in fed.edges:
        verdict = str(edge.get("verdict", ""))
        counts[verdict] = counts.get(verdict, 0) + 1
    lines = [f"## Edges ({len(fed.edges)})", ""]
    for verdict in sorted(counts):
        lines.append(f"- {verdict.upper()}: {counts[verdict]}")
    lines.append("")
    drifts = [e for e in fed.edges if e.get("verdict") == EdgeVerdict.DRIFT.value]
    if drifts:
        lines.append("### DRIFT (declared active, target missing)")
        for edge in drifts:
            lines.append(f"- {edge['src']} --[{edge['kind']}]--> {edge['dst']}")
        lines.append("")
    return lines


# Contract verdicts that are actionable signals (worth an explicit call-out in
# the report, beyond the per-verdict counts). Ordered most-urgent-first.
_ACTIONABLE_VERDICTS = (
    "breaking",
    "drift",
    "orphaned_consumer",
    "undeclared_producer",
)


def _report_contracts(fed: FederatedGraph) -> list[str]:
    """Report contract-level verdicts: counts + explicit actionable lists (G5)."""
    if not fed.contracts:
        return []
    lines = [f"## Contracts ({len(fed.contracts)})", ""]
    lines.extend(_contract_verdict_counts(fed))
    lines.extend(_contract_actionable(fed))
    return lines


def _contract_verdict_counts(fed: FederatedGraph) -> list[str]:
    counts: dict[str, int] = {}
    for contract in fed.contracts:
        verdict = str(contract.get("verdict", ""))
        counts[verdict] = counts.get(verdict, 0) + 1
    lines = [f"- {verdict.upper()}: {counts[verdict]}" for verdict in sorted(counts)]
    lines.append("")
    return lines


def _contract_actionable(fed: FederatedGraph) -> list[str]:
    """Explicit, name-level call-outs for the verdicts a human must act on."""
    lines: list[str] = []
    for verdict in _ACTIONABLE_VERDICTS:
        matches = [c for c in fed.contracts if c.get("verdict") == verdict]
        if not matches:
            continue
        lines.append(f"### {verdict.upper()}")
        lines.extend(_contract_line(c) for c in matches)
        lines.append("")
    return lines


def _contract_line(contract: dict[str, object]) -> str:
    """One actionable contract line; appends the BREAKING ``missing`` names."""
    key = contract.get("contract_key", contract.get("message_type", ""))
    dirs = ", ".join(_contract_directions(contract))
    line = f"- {key} ({dirs})"
    missing = contract.get("missing")
    if isinstance(missing, list) and missing:
        line += f" — missing: {', '.join(str(m) for m in missing)}"
    return line


def _report_unresolved(fed: FederatedGraph) -> list[str]:
    if not fed.unresolved_refs:
        return []
    lines = ["## Unresolved foreign refs", ""]
    lines.extend(f"- {ref}" for ref in fed.unresolved_refs)
    lines.append("")
    return lines
