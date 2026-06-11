# beadloom:domain=ai_agents
# beadloom:feature=ai-techwriter
"""Append-only run-record store (G9): ``.beadloom/ai_techwriter_runs.json``.

Mirrors the honest-by-construction ``site_metrics_history`` store: a JSON array
appended to, never interpolated. The record's ``ts`` is injected (not
``now()``) so emission is deterministic in tests.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.ai_agents.ai_techwriter.models import RunRecord

RUNS_FILENAME = "ai_techwriter_runs.json"


def runs_store_path(project_root: Path) -> Path:
    """Path to the append-only run-record store under ``.beadloom/``."""
    return project_root / ".beadloom" / RUNS_FILENAME


def load_runs(project_root: Path) -> list[dict[str, object]]:
    """Load existing run-records (empty list if the store is absent/empty)."""
    path = runs_store_path(project_root)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        return []
    return [r for r in parsed if isinstance(r, dict)]


def append_run(project_root: Path, record: RunRecord) -> Path:
    """Append *record* to the store (creating ``.beadloom/`` if needed)."""
    path = runs_store_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = load_runs(project_root)
    records.append(record.to_json())
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return path
