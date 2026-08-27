"""Doctor: validation checks for graph and data integrity."""

# beadloom:domain=application

from __future__ import annotations

import enum
import importlib.metadata
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

from beadloom.infrastructure.mcp_tools import MCP_TOOL_CATALOG
from beadloom.infrastructure.surface_registry import get_cli_group
from beadloom.onboarding.scanner.project_facts import (
    detect_project_version,
    detect_source_packages,
    manifest_text,
)

logger = logging.getLogger(__name__)


class Severity(enum.Enum):
    """Severity level for a check result."""

    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Check:
    """Result of a single validation check."""

    name: str
    severity: Severity
    description: str


def _check_empty_summaries(conn: sqlite3.Connection) -> list[Check]:
    """Nodes with empty summary."""
    rows = conn.execute(
        "SELECT ref_id FROM nodes WHERE summary = '' OR summary IS NULL"
    ).fetchall()
    if not rows:
        return [Check("empty_summaries", Severity.OK, "All nodes have summaries.")]
    return [
        Check(
            "empty_summaries",
            Severity.WARNING,
            f"Node '{r['ref_id']}' has empty summary.",
        )
        for r in rows
    ]


def _check_unlinked_docs(conn: sqlite3.Connection) -> list[Check]:
    """Docs without a ref_id link to a graph node."""
    rows = conn.execute("SELECT path FROM docs WHERE ref_id IS NULL").fetchall()
    if not rows:
        return [Check("unlinked_docs", Severity.OK, "All docs are linked to nodes.")]
    return [
        Check(
            "unlinked_docs",
            Severity.WARNING,
            f"Doc '{r['path']}' has no ref_id — unlinked from graph.",
        )
        for r in rows
    ]


#: Node key recording WHY a node carries no document. Any key the loader does
#: not map to a column is stored in ``nodes.extra``, so declaring it in the
#: graph YAML needs no schema change.
DOCS_ABSENT_KEY = "docs_absent"


def _docs_absent_reason(raw_extra: object) -> str | None:
    """The reason this node declares for having no document, if it declares one.

    A blank reason is not a reason: an excusal with nothing written in it excuses
    nothing, and returning it would let an empty string buy the silence a
    sentence has to earn.
    """
    if not isinstance(raw_extra, str) or not raw_extra:
        return None
    try:
        extra = json.loads(raw_extra)
    except json.JSONDecodeError:
        return None
    if not isinstance(extra, dict):
        return None
    reason = extra.get(DOCS_ABSENT_KEY)
    if not isinstance(reason, str) or not reason.strip():
        return None
    return reason.strip()


def _check_nodes_without_docs(conn: sqlite3.Connection) -> list[Check]:
    """Nodes with no document, kept apart from nodes that decided they need none.

    Three outcomes, not two. An undocumented node nobody has ruled on is a gap
    (``WARNING``). A node that records ``docs_absent`` with a reason is a
    decision, and is reported at ``INFO`` WITH that reason — reported, never
    hidden, because a reader has to be able to disagree with it. A node that
    records a reason and HAS a document is an inert declaration and goes back to
    ``WARNING``: a suppression that suppresses nothing reads as coverage it does
    not have (BDL-062 `.4`).
    """
    rows = conn.execute(
        "SELECT n.ref_id, n.extra, d.path FROM nodes n "
        "LEFT JOIN docs d ON d.ref_id = n.ref_id "
        "ORDER BY n.ref_id, d.path"
    ).fetchall()

    documented: dict[str, str] = {}
    reasons: dict[str, str | None] = {}
    for row in rows:
        ref_id = str(row["ref_id"])
        reasons.setdefault(ref_id, _docs_absent_reason(row["extra"]))
        if row["path"] is not None and ref_id not in documented:
            documented[ref_id] = str(row["path"])

    checks: list[Check] = []
    for ref_id, reason in reasons.items():
        doc_path = documented.get(ref_id)
        if doc_path is not None:
            if reason is not None:
                checks.append(
                    Check(
                        "nodes_without_docs",
                        Severity.WARNING,
                        f"Node '{ref_id}' declares {DOCS_ABSENT_KEY} but has a doc "
                        f"linked ({doc_path}); the declaration is inert -- remove it.",
                    )
                )
            continue
        if reason is not None:
            checks.append(
                Check(
                    "nodes_without_docs",
                    Severity.INFO,
                    f"Node '{ref_id}' has no doc by decision: {reason}",
                )
            )
        else:
            checks.append(
                Check(
                    "nodes_without_docs",
                    Severity.WARNING,
                    f"Node '{ref_id}' has no doc linked.",
                )
            )

    if not checks:
        return [Check("nodes_without_docs", Severity.OK, "All nodes have documentation.")]
    return checks


def _check_isolated_nodes(conn: sqlite3.Connection) -> list[Check]:
    """Nodes with no incoming or outgoing edges."""
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n "
        "LEFT JOIN edges e1 ON e1.src_ref_id = n.ref_id "
        "LEFT JOIN edges e2 ON e2.dst_ref_id = n.ref_id "
        "WHERE e1.src_ref_id IS NULL AND e2.dst_ref_id IS NULL"
    ).fetchall()
    if not rows:
        return [Check("isolated_nodes", Severity.OK, "No isolated nodes.")]
    return [
        Check(
            "isolated_nodes",
            Severity.INFO,
            f"Node '{r['ref_id']}' has no edges (isolated).",
        )
        for r in rows
    ]


def _check_symbol_drift(conn: sqlite3.Connection) -> list[Check]:
    """Check for nodes with code symbol changes since last doc sync.

    Uses symbols_hash stored in sync_state (from BEAD-08) to detect
    when code symbols have changed but documentation hasn't been updated.
    """
    from beadloom.doc_sync.engine import _compute_symbols_hash

    # Gracefully handle old DBs without symbols_hash column.
    try:
        rows = conn.execute(
            "SELECT ref_id, doc_path, symbols_hash FROM sync_state "
            "WHERE symbols_hash != '' AND status = 'ok'"
        ).fetchall()
    except Exception:  # OperationalError on missing column
        return [
            Check(
                "symbol_drift",
                Severity.OK,
                "symbols_hash column not present — skipping drift check.",
            )
        ]

    if not rows:
        return [
            Check(
                "symbol_drift",
                Severity.OK,
                "No sync entries with symbols_hash to check.",
            )
        ]

    drifted: list[Check] = []
    for row in rows:
        ref_id: str = row["ref_id"]
        doc_path: str = row["doc_path"]
        stored_hash: str = row["symbols_hash"]
        current_hash = _compute_symbols_hash(conn, ref_id)
        if current_hash and current_hash != stored_hash:
            drifted.append(
                Check(
                    "symbol_drift",
                    Severity.WARNING,
                    f"Node '{ref_id}' has code changes since last doc update ({doc_path})",
                )
            )

    if not drifted:
        return [Check("symbol_drift", Severity.OK, "No symbol drift detected.")]
    return drifted


def _check_stale_sync(conn: sqlite3.Connection) -> list[Check]:
    """Report sync_state entries that are not fresh — stale OR missing.

    ``missing`` is included because a pair whose doc file is gone is not a pair
    with nothing to report: "No stale sync entries" over a deleted document is
    the same false green the verdict was introduced to end (BDL-UX #174).
    """
    try:
        rows = conn.execute(
            "SELECT ref_id, doc_path, code_path, status FROM sync_state "
            "WHERE status IN ('stale', 'missing')"
        ).fetchall()
    except Exception:  # OperationalError on missing table
        return [Check("stale_sync", Severity.OK, "sync_state not available — skipping.")]

    if not rows:
        return [Check("stale_sync", Severity.OK, "No stale sync entries.")]

    return [
        Check(
            "stale_sync",
            Severity.WARNING,
            f"Sync {r['status']} for '{r['ref_id']}': "
            f"doc={r['doc_path']}, code={r['code_path']}",
        )
        for r in rows
    ]


def _check_source_coverage(conn: sqlite3.Connection) -> list[Check]:
    """Check for nodes with untracked source files.

    Uses :func:`beadloom.doc_sync.engine.check_source_coverage` to detect
    Python files in a node's source directory that are not tracked in
    sync_state or code_symbols.
    """
    from pathlib import Path

    from beadloom.doc_sync.engine import check_source_coverage

    # Derive project_root from the database path.
    try:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        project_root = Path(db_path).parent.parent
    except Exception:
        return [
            Check(
                "source_coverage",
                Severity.OK,
                "Could not determine project root — skipping source coverage check.",
            )
        ]

    try:
        gaps = check_source_coverage(conn, project_root)
    except Exception:
        return [
            Check(
                "source_coverage",
                Severity.OK,
                "Source coverage check failed — skipping.",
            )
        ]

    if not gaps:
        return [Check("source_coverage", Severity.OK, "All source files are tracked.")]

    results: list[Check] = []
    for gap in gaps:
        ref_id: str = gap["ref_id"]
        untracked: list[str] = gap["untracked_files"]
        file_names = ", ".join(Path(f).name for f in untracked)
        results.append(
            Check(
                "source_coverage",
                Severity.WARNING,
                f"Node '{ref_id}' has untracked source files: {file_names}",
            )
        )
    return results


# ---------------------------------------------------------------------------
# Agent instructions freshness helpers
# ---------------------------------------------------------------------------

# Pattern: **Current version:** X.Y.Z (optional trailing text)
_VERSION_RE = re.compile(r"\*\*Current version:\*\*\s*(\d+\.\d+\.\d+)")

# Pattern: backtick-wrapped directory names like `infrastructure/`
_PACKAGE_RE = re.compile(r"`(\w+)/`")

# Pattern: MCP tool table rows like | `tool_name` |
_MCP_TOOL_RE = re.compile(r"\|\s*`(\w+)`\s*\|")

# Pattern: **Stack:** <text>
_STACK_RE = re.compile(r"\*\*Stack:\*\*\s*(.+)")

# Pattern: **Tests:** <text>
_TESTS_RE = re.compile(r"\*\*Tests:\*\*\s*(.+)")

# Pattern: a word in a prose claim (for matching a named tool against a manifest).
_WORD_RE = re.compile(r"[A-Za-z][\w.-]*")


def _extract_version_claim(text: str) -> str | None:
    """Extract version from CLAUDE.md (pattern: ``**Current version:** X.Y.Z``)."""
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def _extract_package_claims(text: str) -> set[str]:
    """Extract architecture package names from CLAUDE.md.

    Looks for backtick-wrapped directory names like ``infrastructure/``.
    Only matches lines containing "Architecture" or "DDD" to avoid false positives.
    """
    packages: set[str] = set()
    for line in text.splitlines():
        if "Architecture" in line or "DDD" in line or "packages" in line.lower():
            packages.update(_PACKAGE_RE.findall(line))
    return packages


def get_actual_version() -> str:
    """Get actual beadloom version from the in-tree ``__version__``.

    Public version-resolution entry point — callers and tests depend on this
    name (not a private symbol), so version resolution is assertable through a
    stable public API.

    The in-tree ``beadloom.__version__`` is the source of truth. Installed
    package metadata (``importlib.metadata``) is deliberately *not* consulted
    first: editable installs frequently carry stale metadata, which produced
    false "version drift" diagnoses (BDL-UX-Issues #92). Falls back to package
    metadata only if the source version is somehow unavailable.
    """
    try:
        from beadloom import __version__

        return __version__
    except ImportError:  # pragma: no cover - defensive fallback
        return importlib.metadata.version("beadloom")


def _get_actual_cli_commands() -> set[str] | None:
    """Registered CLI command names, or ``None`` when the surface is unknown.

    Read through the ``surface_registry`` port rather than importing
    ``services.cli``: this is the application layer, and reaching up into
    services inverted the dependency direction (BDL-UX #159). ``None`` means
    nobody provided the surface — the caller reports that as unverified, never
    as "no commands".
    """
    group = get_cli_group()
    if group is None:
        return None
    commands: dict[str, object] = getattr(group, "commands", {})
    return set(commands.keys())


def _get_actual_mcp_tool_count() -> int:
    """Number of MCP tools, from the canonical lower-layer catalog.

    Reads ``infrastructure/mcp_tools.MCP_TOOL_CATALOG`` rather than importing
    the server: the catalog is pinned equal to the server's live registry by a
    test, and unlike the CLI group it is available in every process — so this
    count is never "unknown" (BDL-UX #159).
    """
    return len(MCP_TOOL_CATALOG)


def _check_agent_instructions(project_root: Path) -> list[Check]:
    """Check agent instruction files for factual drift.

    Reads ``.claude/CLAUDE.md`` and ``.beadloom/AGENTS.md`` from *project_root*,
    extracts factual claims via regex, compares with actual runtime state,
    and returns ``list[Check]`` with ``Severity.WARNING`` for drift and
    ``Severity.OK`` for match.

    Checks at least 6 fact types: version, packages, CLI count, MCP count,
    stack keywords, and test framework.
    """
    results: list[Check] = []

    # Collect text from both instruction files.
    claude_md_path = project_root / ".claude" / "CLAUDE.md"
    agents_md_path = project_root / ".beadloom" / "AGENTS.md"

    claude_text = ""
    agents_text = ""

    if claude_md_path.is_file():
        try:
            claude_text = claude_md_path.read_text(encoding="utf-8")
        except OSError:
            logger.debug("Could not read %s", claude_md_path)

    if agents_md_path.is_file():
        try:
            agents_text = agents_md_path.read_text(encoding="utf-8")
        except OSError:
            logger.debug("Could not read %s", agents_md_path)

    # Nothing to check if neither file exists.
    if not claude_text and not agents_text:
        return results

    # --- 1. Version check (from CLAUDE.md) ---
    # Against the version THIS project declares — not `get_actual_version()`,
    # which returns Beadloom's own `__version__` and is right about Beadloom
    # (BDL-UX #92) and about nobody else (BDL-UX #183).
    claimed_version = _extract_version_claim(claude_text)
    if claimed_version is not None:
        actual_version = detect_project_version(project_root)
        if actual_version is None:
            results.append(
                Check(
                    "agent_instructions_version",
                    Severity.INFO,
                    f"CLAUDE.md claims version {claimed_version}; this project "
                    "declares none in pyproject.toml, package.json or Cargo.toml "
                    "— not verified.",
                )
            )
        elif claimed_version == actual_version:
            results.append(
                Check(
                    "agent_instructions_version",
                    Severity.OK,
                    f"Version claim matches: {actual_version}",
                )
            )
        else:
            results.append(
                Check(
                    "agent_instructions_version",
                    Severity.WARNING,
                    f"Version drift: CLAUDE.md claims {claimed_version}, "
                    f"this project declares {actual_version}",
                )
            )

    # --- 2. Packages check (from CLAUDE.md) ---
    claimed_packages = _extract_package_claims(claude_text)
    if claimed_packages:
        actual_packages = detect_source_packages(project_root)
        missing = claimed_packages - actual_packages
        extra = actual_packages - claimed_packages
        if missing or extra:
            parts: list[str] = []
            if missing:
                parts.append(f"claimed but missing: {', '.join(sorted(missing))}")
            if extra:
                parts.append(f"undocumented: {', '.join(sorted(extra))}")
            results.append(
                Check(
                    "agent_instructions_packages",
                    Severity.WARNING,
                    f"Package drift: {'; '.join(parts)}",
                )
            )
        else:
            results.append(
                Check(
                    "agent_instructions_packages",
                    Severity.OK,
                    f"All {len(actual_packages)} packages documented correctly.",
                )
            )

    # --- 3. CLI command count check ---
    # An unknown surface is reported as unknown: claiming "0 commands" because
    # nobody provided the CLI would be a check announcing a result it never
    # looked at.
    actual_cli_commands = _get_actual_cli_commands()
    if actual_cli_commands is None:
        results.append(
            Check(
                "agent_instructions_cli_commands",
                Severity.INFO,
                "CLI surface not available in this process — command count not verified.",
            )
        )
    else:
        results.append(
            Check(
                "agent_instructions_cli_commands",
                Severity.OK,
                f"CLI has {len(actual_cli_commands)} commands registered.",
            )
        )

    # --- 4. MCP tool count check (from AGENTS.md) ---
    actual_mcp_count = _get_actual_mcp_tool_count()
    claimed_mcp_tools = set(_MCP_TOOL_RE.findall(agents_text))
    if claimed_mcp_tools:
        # Compare documented tool names against actual tool count
        if len(claimed_mcp_tools) == actual_mcp_count:
            results.append(
                Check(
                    "agent_instructions_mcp_tools",
                    Severity.OK,
                    f"MCP tool count matches: {actual_mcp_count} tools.",
                )
            )
        else:
            results.append(
                Check(
                    "agent_instructions_mcp_tools",
                    Severity.WARNING,
                    f"MCP tool drift: AGENTS.md documents {len(claimed_mcp_tools)} tools, "
                    f"actual is {actual_mcp_count}",
                )
            )
    elif agents_text:
        # AGENTS.md exists but has no tool table — just report count
        results.append(
            Check(
                "agent_instructions_mcp_tools",
                Severity.OK,
                f"MCP server has {actual_mcp_count} tools (no table in AGENTS.md to verify).",
            )
        )

    # --- 5. Stack check (from CLAUDE.md) ---
    results.extend(_check_stack_claim(claude_text, project_root))

    # --- 6. Test framework check (from CLAUDE.md) ---
    results.extend(_check_test_framework_claim(claude_text, project_root))

    return results


def _check_stack_claim(claude_text: str, project_root: Path) -> list[Check]:
    """Audit the ``**Stack:**`` bullet against the stack THIS project declares.

    The expected keyword set used to be the literal ``{"python", "sqlite"}`` —
    Beadloom's own stack, applied to everybody's file. A TypeScript adopter was
    told their correct stack line was "missing expected keywords".
    """
    stack_match = _STACK_RE.search(claude_text)
    if not stack_match:
        return []
    declared = _declared_stack(project_root)
    if not declared:
        return [
            Check(
                "agent_instructions_stack",
                Severity.INFO,
                "Stack claim present; this project declares no `stack:` in "
                ".beadloom/flow.yml — not verified.",
            )
        ]
    claim = stack_match.group(1).lower()
    missing = sorted(name for name in declared if name.lower() not in claim)
    if not missing:
        return [
            Check(
                "agent_instructions_stack",
                Severity.OK,
                f"Stack claim covers the declared stack: {', '.join(sorted(declared))}.",
            )
        ]
    return [
        Check(
            "agent_instructions_stack",
            Severity.WARNING,
            f"Stack claim does not mention the declared stack: {', '.join(missing)}",
        )
    ]


def _check_test_framework_claim(claude_text: str, project_root: Path) -> list[Check]:
    """Audit the ``**Tests:**`` bullet against the project's own manifests.

    The old check asserted the literal string ``pytest``, so every non-Python
    adopter's correct claim was a warning. A framework is now verified the only
    way that generalises: it must appear where the project declares its
    dependencies.
    """
    tests_match = _TESTS_RE.search(claude_text)
    if not tests_match:
        return []
    claim = tests_match.group(1)
    manifests = manifest_text(project_root)
    if manifests is None:
        return [
            Check(
                "agent_instructions_test_framework",
                Severity.INFO,
                f"Test framework claim {claim!r}; this project has no dependency "
                "manifest Beadloom can read — not verified.",
            )
        ]
    haystack = manifests.lower()
    named = [word for word in _WORD_RE.findall(claim.lower()) if len(word) > 2]
    if any(word in haystack for word in named):
        return [
            Check(
                "agent_instructions_test_framework",
                Severity.OK,
                f"Test framework claim is declared by this project: {claim}",
            )
        ]
    return [
        Check(
            "agent_instructions_test_framework",
            Severity.WARNING,
            f"Test framework claim names nothing this project declares: {claim}",
        )
    ]


def _declared_stack(project_root: Path) -> tuple[str, ...]:
    """The ``stack:`` overlays declared in this project's ``flow.yml``."""
    from beadloom.onboarding.flow_config import load_flow_config

    try:
        return load_flow_config(project_root).stack
    except (FileNotFoundError, ValueError):
        return ()


def run_checks(
    conn: sqlite3.Connection,
    *,
    project_root: Path | None = None,
) -> list[Check]:
    """Run all validation checks and return results."""
    results: list[Check] = []
    results.extend(_check_empty_summaries(conn))
    results.extend(_check_unlinked_docs(conn))
    results.extend(_check_nodes_without_docs(conn))
    results.extend(_check_isolated_nodes(conn))
    results.extend(_check_symbol_drift(conn))
    results.extend(_check_stale_sync(conn))
    results.extend(_check_source_coverage(conn))
    if project_root is not None:
        results.extend(_check_agent_instructions(project_root))
    return results
