# beadloom:domain=graph
# beadloom:feature=federation
"""Cross-repo federation (BDL-037): node identity, satellite export, hub aggregation.

This package decomposes the federation feature by responsibility (BDL-059 S3):

- :mod:`.refs`       — the ``@<repo>:<ref_id>`` reference model + parser.
- :mod:`.export`     — the deterministic satellite export artifact.
- :mod:`.reconcile`  — hub aggregation into a :class:`FederatedGraph` + verdicts.
- :mod:`.gate`       — the landscape gate (verdicts -> block/pass findings).

Every public symbol is re-exported here, so ``from beadloom.graph.federation
import X`` is unchanged for all callers — the split is purely internal.
"""

from __future__ import annotations

from beadloom.graph.federation.export import (
    EXPORT_SCHEMA_VERSION,
    build_export,
    current_commit_sha,
    resolve_landscape,
    resolve_repo_name,
    serialize_export,
)
from beadloom.graph.federation.gate import (
    NEVER_FAIL_VERDICTS,
    SAFE_DEFAULT_FAIL_ON,
    GateFailure,
    gate_failure_remediation,
    gate_failures,
)
from beadloom.graph.federation.reconcile import (
    FEDERATION_SCHEMA_VERSION,
    EdgeVerdict,
    FederatedGraph,
    aggregate_exports,
    render_federation_report,
    serialize_federation,
)
from beadloom.graph.federation.refs import (
    _FOREIGN_MARKER as _FOREIGN_MARKER,
)
from beadloom.graph.federation.refs import (
    FederatedRef,
    FederationRefError,
    is_foreign_ref,
    parse_ref,
)

__all__ = [
    "EXPORT_SCHEMA_VERSION",
    "FEDERATION_SCHEMA_VERSION",
    "NEVER_FAIL_VERDICTS",
    "SAFE_DEFAULT_FAIL_ON",
    "EdgeVerdict",
    "FederatedGraph",
    "FederatedRef",
    "FederationRefError",
    "GateFailure",
    "aggregate_exports",
    "build_export",
    "current_commit_sha",
    "gate_failure_remediation",
    "gate_failures",
    "is_foreign_ref",
    "parse_ref",
    "render_federation_report",
    "resolve_landscape",
    "resolve_repo_name",
    "serialize_export",
    "serialize_federation",
]
