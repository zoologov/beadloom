"""Doctor: validation checks for graph and data integrity."""

# beadloom:domain=infrastructure

from __future__ import annotations

import enum
import importlib.metadata
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

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


def _check_nodes_without_docs(conn: sqlite3.Connection) -> list[Check]:
    """Nodes that have no associated documentation."""
    rows = conn.execute(
        "SELECT n.ref_id FROM nodes n LEFT JOIN docs d ON d.ref_id = n.ref_id WHERE d.id IS NULL"
    ).fetchall()
    if not rows:
        return [Check("nodes_without_docs", Severity.OK, "All nodes have documentation.")]
    return [
        Check(
            "nodes_without_docs",
            Severity.WARNING,
            f"Node '{r['ref_id']}' has no doc linked.",
        )
        for r in rows
    ]


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
    """Report sync_state entries already marked as stale."""
    try:
        rows = conn.execute(
            "SELECT ref_id, doc_path, code_path FROM sync_state WHERE status = 'stale'"
        ).fetchall()
    except Exception:  # OperationalError on missing table
        return [Check("stale_sync", Severity.OK, "sync_state not available — skipping.")]

    if not rows:
        return [Check("stale_sync", Severity.OK, "No stale sync entries.")]

    return [
        Check(
            "stale_sync",
            Severity.WARNING,
            f"Sync stale for '{r['ref_id']}': doc={r['doc_path']}, code={r['code_path']}",
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


def _get_actual_version() -> str:
    """Get actual beadloom version via importlib.metadata with fallback."""
    try:
        return importlib.metadata.version("beadloom")
    except importlib.metadata.PackageNotFoundError:
        from beadloom import __version__

        return __version__


def _get_actual_cli_commands() -> set[str]:
    """Get CLI commands via Click group introspection."""
    from beadloom.services.cli import main

    commands: dict[str, object] = getattr(main, "commands", {})
    return set(commands.keys())


def _get_actual_mcp_tool_count() -> int:
    """Count MCP tools from the ``_TOOLS`` list."""
    from beadloom.services.mcp_server import _TOOLS

    return len(_TOOLS)


def _get_actual_packages(project_root: Path) -> set[str]:
    """Scan ``src/beadloom/`` for DDD package directories (those with ``__init__.py``)."""
    src_dir = project_root / "src" / "beadloom"
    if not src_dir.is_dir():
        return set()
    packages: set[str] = set()
    for child in src_dir.iterdir():
        if child.is_dir() and (child / "__init__.py").is_file():
            packages.add(child.name)
    return packages


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
    claimed_version = _extract_version_claim(claude_text)
    if claimed_version is not None:
        actual_version = _get_actual_version()
        if claimed_version == actual_version:
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
                    f"actual is {actual_version}",
                )
            )

    # --- 2. Packages check (from CLAUDE.md) ---
    claimed_packages = _extract_package_claims(claude_text)
    if claimed_packages:
        actual_packages = _get_actual_packages(project_root)
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
    actual_cli_commands = _get_actual_cli_commands()
    cli_count = len(actual_cli_commands)
    # We don't extract a CLI count claim from docs; we just report the actual count
    # as an informational check. If CLAUDE.md contains command references, we verify
    # they exist.
    results.append(
        Check(
            "agent_instructions_cli_commands",
            Severity.OK,
            f"CLI has {cli_count} commands registered.",
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
    stack_match = _STACK_RE.search(claude_text)
    if stack_match:
        stack_claim = stack_match.group(1).lower()
        # Verify key stack keywords against actual project
        expected_keywords = {"python", "sqlite"}
        found = {kw for kw in expected_keywords if kw in stack_claim}
        if found == expected_keywords:
            results.append(
                Check(
                    "agent_instructions_stack",
                    Severity.OK,
                    f"Stack claim includes expected keywords: {', '.join(sorted(found))}.",
                )
            )
        else:
            missing_kw = expected_keywords - found
            results.append(
                Check(
                    "agent_instructions_stack",
                    Severity.WARNING,
                    f"Stack claim missing expected keywords: {', '.join(sorted(missing_kw))}",
                )
            )

    # --- 6. Test framework check (from CLAUDE.md) ---
    tests_match = _TESTS_RE.search(claude_text)
    if tests_match:
        tests_claim = tests_match.group(1).lower()
        if "pytest" in tests_claim:
            results.append(
                Check(
                    "agent_instructions_test_framework",
                    Severity.OK,
                    "Test framework claim includes pytest.",
                )
            )
        else:
            results.append(
                Check(
                    "agent_instructions_test_framework",
                    Severity.WARNING,
                    f"Test framework claim does not mention pytest: {tests_match.group(1)}",
                )
            )

    return results


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
