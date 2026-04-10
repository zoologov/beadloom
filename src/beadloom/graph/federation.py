"""Cross-repo node identity + satellite export for federation (BDL-037).

A graph ref may name a node in *another* repo using the ``@<repo>:<ref_id>``
form (e.g. ``@integration-service:plans``). A plain ref (no leading ``@``) is
local, exactly as before — federation is purely additive.

This module owns the :class:`FederatedRef` value type and the :func:`parse_ref`
parser. Malformed foreign refs raise :class:`FederationRefError` so the loader
can record them in ``result.errors`` instead of silently dropping them.

It also owns the **satellite export** (:func:`build_export` /
:func:`serialize_export`): a deterministic, self-describing JSON artifact that a
hub aggregates (BEAD-04). Determinism (sorted keys + sorted node/edge arrays)
keeps exports reviewable as diffs. The export envelope records ``commit_sha``
and ``exported_at`` so the hub can report staleness it cannot otherwise verify.
"""

# beadloom:domain=graph

from __future__ import annotations

import enum
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.graph.contracts import reconcile_contracts

if TYPE_CHECKING:
    import sqlite3

# Marker that introduces a foreign (cross-repo) reference.
_FOREIGN_MARKER = "@"

# Export artifact schema version (bumped on breaking shape changes; the hub
# tolerates/reports mismatches).
#
# v2 (BDL-038 BEAD-03): adds the ``protocol: graphql`` contract wire — a producer
# edge carries ``contract.exposed`` (parsed SDL surface) and a consumer edge
# carries ``contract.references``. The change is purely additive: v1 exports
# (AMQP-only / no GraphQL fields) still read without error — ``aggregate_exports``
# never requires the new fields (missing -> empty surface).
EXPORT_SCHEMA_VERSION = 2


class FederationRefError(ValueError):
    """Raised when a ``@...`` foreign ref is malformed.

    A leading ``@`` signals the author intended a cross-repo reference, so a
    broken shape is an error to surface — never a silently-accepted local ref.
    Malformed examples: ``@:x`` (empty repo), ``@repo:`` (empty ref_id),
    ``@repo`` (no separator), ``@``.
    """


@dataclass(frozen=True)
class FederatedRef:
    """A graph reference that may point at another repo.

    ``repo is None`` means a local reference (the common case). Otherwise the
    ref names node ``ref_id`` in satellite repo ``repo``; it resolves against
    the federated union at the hub, not during a single-repo load.
    """

    repo: str | None
    ref_id: str

    @property
    def is_foreign(self) -> bool:
        """True when this ref targets another repo."""
        return self.repo is not None

    @property
    def qualified(self) -> str:
        """Canonical string form: ``@repo:ref_id`` (foreign) or ``ref_id`` (local)."""
        if self.repo is None:
            return self.ref_id
        return f"{_FOREIGN_MARKER}{self.repo}:{self.ref_id}"


def is_foreign_ref(raw: str) -> bool:
    """Cheap check: does *raw* look like a foreign ref (leading ``@``)?

    Does not validate the shape — use :func:`parse_ref` for that.
    """
    return raw.startswith(_FOREIGN_MARKER)


def parse_ref(raw: str) -> FederatedRef:
    """Parse a graph ref into a :class:`FederatedRef`.

    - ``"routing"``            -> local ``FederatedRef(None, "routing")``
    - ``"@repo:plans"``        -> foreign ``FederatedRef("repo", "plans")``
    - malformed ``@...``       -> :class:`FederationRefError`

    Only the first ``:`` after the marker separates repo from ref_id, so a
    foreign ref_id may itself contain colons (``@repo:ns:thing``). A plain ref
    with a colon and no leading ``@`` stays local untouched.
    """
    if not raw.startswith(_FOREIGN_MARKER):
        if not raw:
            raise FederationRefError("Empty ref is not a valid node reference.")
        return FederatedRef(repo=None, ref_id=raw)

    body = raw[len(_FOREIGN_MARKER) :]
    repo, sep, ref_id = body.partition(":")
    if not sep or not repo or not ref_id:
        raise FederationRefError(
            f"Malformed foreign ref '{raw}': expected '@<repo>:<ref_id>' "
            f"with non-empty repo and ref_id."
        )
    return FederatedRef(repo=repo, ref_id=ref_id)


# --- Satellite export (BEAD-03) ---------------------------------------------


def _export_node(row: sqlite3.Row) -> dict[str, object]:
    """Serialize one ``nodes`` row into a deterministic node dict."""
    return {
        "ref_id": row["ref_id"],
        "kind": row["kind"],
        "summary": row["summary"],
        "lifecycle": row["lifecycle"],
        "source": row["source"],
    }


def _export_edge(row: sqlite3.Row) -> dict[str, object]:
    """Serialize one ``edges`` row into a deterministic edge dict.

    AMQP/contract metadata (when present under the ``contract`` key of the
    edge's ``extra`` JSON) is surfaced as a top-level ``contract`` field;
    edges without it omit the key entirely (smaller, stable diffs).
    """
    edge: dict[str, object] = {
        "src": row["src_ref_id"],
        "dst": row["dst_ref_id"],
        "kind": row["kind"],
        "lifecycle": row["lifecycle"],
    }
    contract = _edge_contract(row["extra"])
    if contract is not None:
        edge["contract"] = contract
    return edge


def _edge_contract(raw_extra: str | None) -> dict[str, object] | None:
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


def build_export(
    conn: sqlite3.Connection,
    *,
    repo: str,
    commit_sha: str | None,
    exported_at: str,
    generator: str,
) -> dict[str, object]:
    """Build the satellite export artifact from the indexed graph.

    Pure with respect to its inputs: ``exported_at`` and ``commit_sha`` are
    injected so the output is deterministic (tests pass fixed values; the CLI
    passes wall-clock UTC + git HEAD). Nodes are sorted by ``ref_id`` and edges
    by ``(src, dst, kind)`` so identical graphs serialize byte-identically.
    """
    node_rows = conn.execute(
        "SELECT ref_id, kind, summary, source, lifecycle FROM nodes ORDER BY ref_id"
    ).fetchall()
    edges = [_export_edge(r) for r in _edge_rows(conn)]
    edges.sort(key=lambda e: (str(e["src"]), str(e["dst"]), str(e["kind"])))
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "repo": repo,
        "commit_sha": commit_sha,
        "exported_at": exported_at,
        "generator": generator,
        "nodes": [_export_node(r) for r in node_rows],
        "edges": edges,
    }


def _edge_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Union local ``edges`` with cross-repo ``foreign_edges`` (#100).

    Declared ``@repo:`` edges live in ``foreign_edges`` (their endpoint cannot
    satisfy the local FK) and would otherwise never reach the artifact, so the
    hub could not see intent-declared cross-repo links. Both tables expose the
    same columns; sorting happens in :func:`build_export`.
    """
    rows = list(
        conn.execute(
            "SELECT src_ref_id, dst_ref_id, kind, extra, lifecycle FROM edges"
        ).fetchall()
    )
    if _has_foreign_edges_table(conn):
        rows.extend(
            conn.execute(
                "SELECT src_ref_id, dst_ref_id, kind, extra, lifecycle FROM foreign_edges"
            ).fetchall()
        )
    return rows


def _has_foreign_edges_table(conn: sqlite3.Connection) -> bool:
    """True when the ``foreign_edges`` table exists (older DBs may lack it)."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='foreign_edges'"
    ).fetchone()
    return row is not None


def serialize_export(export: dict[str, object]) -> str:
    """Serialize an export dict to deterministic JSON (sorted keys, 2-space)."""
    return json.dumps(export, sort_keys=True, indent=2, ensure_ascii=False)


def resolve_repo_name(project_root: Path) -> str:
    """Resolve the repo name for an export (Q3).

    Precedence: ``.beadloom/config.yml`` ``repo:`` key > git remote basename >
    project directory name. Deterministic and overridable.
    """
    from_config = _repo_from_config(project_root)
    if from_config:
        return from_config
    from_git = _repo_from_git_remote(project_root)
    if from_git:
        return from_git
    return project_root.resolve().name


def _repo_from_config(project_root: Path) -> str | None:
    """Read the ``repo:`` key from ``.beadloom/config.yml`` if present."""
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.exists():
        return None
    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    repo = config.get("repo")
    return repo if isinstance(repo, str) and repo else None


def _repo_from_git_remote(project_root: Path) -> str | None:
    """Derive the repo name from the ``origin`` git remote URL basename."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    if not url:
        return None
    basename = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    if basename.endswith(".git"):
        basename = basename[: -len(".git")]
    return basename or None


def current_commit_sha(project_root: Path) -> str | None:
    """Return the current git HEAD sha, or ``None`` outside a git repo (Q4).

    Returns ``None`` when *project_root* is not itself the git toplevel (#103):
    ``git`` walks UP to the enclosing repo for a nested non-repo dir, which
    would otherwise leak an unrelated (host) repo's HEAD into the export. An
    honest "unknown HEAD" beats a misleading provenance sha.
    """
    if not _is_git_toplevel(project_root):
        return None
    sha = _run_git(project_root, "rev-parse", "HEAD")
    return sha or None


def _is_git_toplevel(project_root: Path) -> bool:
    """True when *project_root* is the toplevel of its own git repository."""
    toplevel = _run_git(project_root, "rev-parse", "--show-toplevel")
    if toplevel is None:
        return False
    try:
        return Path(toplevel).resolve() == project_root.resolve()
    except OSError:
        return False


def _run_git(cwd: Path, *args: str) -> str | None:
    """Run ``git <args>`` in *cwd*; return stripped stdout, or ``None`` on failure."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


# --- Hub aggregation (BEAD-04) ----------------------------------------------

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
    """

    OK = "ok"
    DRIFT = "drift"
    EXPECTED = "expected"
    CLEANUP_CANDIDATE = "cleanup_candidate"
    UNDECLARED = "undeclared"
    DEAD = "dead"


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
    return {
        "repo": export.get("repo"),
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
        for edge in _export_edges(export):
            fed.edges.append(_resolve_edge(repo, edge))

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


def _resolve_edge(repo: str, edge: dict[str, object]) -> dict[str, object]:
    """Namespace + foreign-resolve an edge's endpoints into a federated edge."""
    src = _resolve_endpoint(repo, str(edge.get("src", "")))
    dst = _resolve_endpoint(repo, str(edge.get("dst", "")))
    resolved: dict[str, object] = {
        "src": src,
        "dst": dst,
        "kind": edge.get("kind"),
        "lifecycle": edge.get("lifecycle", "active"),
        "repo": repo,
    }
    contract = _edge_contract_payload(edge)
    if contract is not None:
        resolved["contract"] = contract
    return resolved


def _assign_verdicts(fed: FederatedGraph, present_ids: set[str]) -> None:
    """Assign an :class:`EdgeVerdict` to each edge; record unresolved targets."""
    for edge in fed.edges:
        dst = str(edge["dst"])
        target_present = dst in present_ids
        lifecycle = str(edge.get("lifecycle", "active"))
        verdict = _verdict_for(lifecycle, target_present=target_present)
        edge["verdict"] = verdict.value
        if (
            not target_present
            and is_foreign_ref(dst)
            and verdict in (EdgeVerdict.DRIFT, EdgeVerdict.EXPECTED)
        ):
            fed.unresolved_refs.append(dst)


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
    """Flag present producer contract edges whose message has no consumer.

    A satellite producing to a queue/contract that no peer declares consuming is
    emitting into the void — :attr:`EdgeVerdict.UNDECLARED`.
    """
    consumed = {
        c["message_type"]
        for c in fed.contracts
        if "consumes" in _contract_directions(c)
    }
    for edge in fed.edges:
        contract = _edge_contract_payload(edge)
        if contract is None or contract.get("protocol") != "amqp":
            continue
        if contract.get("direction") != "produces":
            continue
        if str(contract.get("message_type", "")) not in consumed:
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
    lines = [f"## Satellites ({len(fed.repos)})", ""]
    for repo in fed.repos:
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
