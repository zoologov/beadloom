"""Metrics-history append-store for honest dashboard trends (BDL-041 F4.4).

A tiny additive append-log of real metric points persisted to
``.beadloom/metrics_history.json``. ``docs site`` records one point per run
(:func:`append_metrics_point`); :func:`read_history` returns the sorted series
that :mod:`beadloom.application.site_dashboard` emits into
``dashboard.data.json.trends``.

Design invariants (honest + deterministic):

- **No fabrication.** The series is *exactly* the recorded points — no
  interpolation, no synthesized in-between samples. Sparse at first is correct.
- **Injected timestamp.** The point's ``ts`` is supplied by the caller (never
  ``now()`` inside this module), so tests are deterministic and the diffed
  ``dashboard.data.json`` is byte-stable for a fixed history.
- **Idempotent per ts.** Appending the same ``ts`` overwrites that point (a
  re-run of one build does not double-count the series).
- **Day-one backfill.** :func:`backfill_structural_history` seeds *structural*
  counts (nodes/edges/symbols) from the existing ``graph_snapshots`` history so
  the structural trend isn't empty before the first ``docs site`` run; it never
  overwrites a richer recorded point.

The store is additive append-state (a JSON file), NOT a versioned artifact — no
schema bump.
"""

# beadloom:domain=application

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

logger = logging.getLogger(__name__)

_HISTORY_FILENAME = "metrics_history.json"


@dataclass(frozen=True)
class MetricsPoint:
    """One recorded metrics sample (a single ``docs site`` run / a backfill).

    ``ts`` is an ISO-8601 timestamp supplied by the caller. The remaining fields
    mirror the honest gate metrics surfaced on the dashboard.
    """

    ts: str
    lint_violations: int
    debt_score: float
    coverage_pct: float
    sync_pct: float
    nodes: int
    edges: int
    symbols: int


def history_path(project_root: Path) -> Path:
    """Return the on-disk path of the metrics-history store for *project_root*."""
    return project_root / ".beadloom" / _HISTORY_FILENAME


def _as_int(value: object, default: int) -> int:
    """Coerce a JSON-loaded value to int, falling back to *default*."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    return default


def _as_float(value: object, default: float) -> float:
    """Coerce a JSON-loaded value to float, falling back to *default*."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _coerce_point(raw: dict[str, object]) -> MetricsPoint | None:
    """Build a :class:`MetricsPoint` from a stored dict, skipping malformed rows."""
    ts = raw.get("ts")
    if not isinstance(ts, str) or not ts:
        return None
    return MetricsPoint(
        ts=ts,
        lint_violations=_as_int(raw.get("lint_violations"), 0),
        debt_score=_as_float(raw.get("debt_score"), 0.0),
        coverage_pct=_as_float(raw.get("coverage_pct"), 0.0),
        sync_pct=_as_float(raw.get("sync_pct"), 100.0),
        nodes=_as_int(raw.get("nodes"), 0),
        edges=_as_int(raw.get("edges"), 0),
        symbols=_as_int(raw.get("symbols"), 0),
    )


def read_history(project_root: Path) -> list[MetricsPoint]:
    """Return the recorded series, sorted by ``ts`` (empty when no store yet).

    Only real recorded points are returned — never an interpolated or fabricated
    sample. Malformed rows are skipped (the store is best-effort, additive).
    """
    path = history_path(project_root)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read metrics history %s", path)
        return []
    if not isinstance(payload, list):
        return []
    points = [
        pt
        for raw in payload
        if isinstance(raw, dict) and (pt := _coerce_point(raw)) is not None
    ]
    return sorted(points, key=lambda p: p.ts)


def _write_history(project_root: Path, points: list[MetricsPoint]) -> None:
    """Persist *points* deterministically (sorted by ts, key-sorted JSON)."""
    ordered = sorted(points, key=lambda p: p.ts)
    serialized = json.dumps(
        [asdict(p) for p in ordered], sort_keys=True, indent=2, ensure_ascii=False
    )
    path = history_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")


def append_metrics_point(project_root: Path, point: MetricsPoint) -> None:
    """Append (or overwrite by ts) one recorded point and persist the store.

    The caller supplies ``point.ts`` (injected, never ``now()`` here). Appending
    an existing ``ts`` overwrites that point so a re-run of one build does not
    double-count the series.
    """
    by_ts = {p.ts: p for p in read_history(project_root)}
    by_ts[point.ts] = point
    _write_history(project_root, list(by_ts.values()))


def _normalize_snapshot_ts(created_at: str) -> str:
    """Normalize a ``graph_snapshots.created_at`` value to an ISO-8601 UTC ts.

    Snapshots store ``'YYYY-MM-DD HH:MM:SS'`` (SQLite ``datetime('now')``); we
    render it as ``'YYYY-MM-DDTHH:MM:SS+00:00'`` so a backfilled structural point
    can dedup against a recorded point taken at the same instant.
    """
    text = created_at.strip()
    if "T" not in text and " " in text:
        text = text.replace(" ", "T", 1)
    if not text.endswith("+00:00") and "+" not in text and "Z" not in text:
        text = f"{text}+00:00"
    return text


def backfill_structural_history(conn: sqlite3.Connection, project_root: Path) -> None:
    """Seed structural points (nodes/edges/symbols) from ``graph_snapshots``.

    For every snapshot whose normalized timestamp has no recorded point yet, add
    a structural-only point (full metrics default to neutral values). Existing
    recorded points are never overwritten — real, richer data always wins. The
    operation is idempotent (re-running adds nothing new).
    """
    by_ts = {p.ts: p for p in read_history(project_root)}
    rows = conn.execute(
        "SELECT created_at, nodes_json, edges_json, symbols_count "
        "FROM graph_snapshots ORDER BY created_at, id"
    ).fetchall()
    added = False
    for row in rows:
        ts = _normalize_snapshot_ts(str(row["created_at"]))
        if ts in by_ts:
            continue
        nodes = len(json.loads(row["nodes_json"]))
        edges = len(json.loads(row["edges_json"]))
        by_ts[ts] = MetricsPoint(
            ts=ts,
            lint_violations=0,
            debt_score=0.0,
            coverage_pct=0.0,
            sync_pct=100.0,
            nodes=nodes,
            edges=edges,
            symbols=int(row["symbols_count"]),
        )
        added = True
    if added:
        _write_history(project_root, list(by_ts.values()))
