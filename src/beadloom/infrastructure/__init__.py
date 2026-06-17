"""Infrastructure layer — domain-agnostic database, health metrics, and git activity.

This layer is the lowest in the architecture and depends on nothing else in the
project.  The cross-domain orchestrators (``reindex``, ``doctor``, ``debt_report``,
``watcher``) live in :mod:`beadloom.application`, not here, so that infrastructure
never imports a domain (the DDD Dependency Rule).
"""

from beadloom.infrastructure.atomic_io import write_yaml_atomic
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
    "write_yaml_atomic",
]
