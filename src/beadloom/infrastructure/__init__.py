"""Infrastructure domain — database layer, health metrics, and reindex orchestrator.

Note: ``beadloom.infrastructure.reindex`` is intentionally NOT re-exported here because
it is an orchestrator with cross-domain dependencies (graph, context, sync) and
eagerly importing it would create circular imports.  Import it directly::

    from beadloom.infrastructure.reindex import reindex, incremental_reindex
"""

from beadloom.infrastructure.db import (
    SCHEMA_VERSION,
    create_schema,
    get_meta,
    open_db,
    set_meta,
)
from beadloom.infrastructure.health import (
    HealthSnapshot,
    compute_trend,
    get_latest_snapshots,
    take_snapshot,
)

__all__ = [
    "SCHEMA_VERSION",
    "HealthSnapshot",
    "compute_trend",
    "create_schema",
    "get_latest_snapshots",
    "get_meta",
    "open_db",
    "set_meta",
    "take_snapshot",
]
