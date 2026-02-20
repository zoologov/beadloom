"""Documentation audit: fact registry, comparator, and audit facade.

Provides ``Fact`` and ``FactRegistry`` — auto-computes project facts from
existing Beadloom infrastructure (manifest, graph DB, code symbols, MCP
tools, CLI commands) for comparison against doc mentions.

Also provides ``AuditFinding``, ``AuditResult``, ``compare_facts()`` for
comparing mentions against ground truth, and ``run_audit()`` facade.

Experimental — API may change in v1.9.
"""

# beadloom:feature=docs-audit

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.doc_sync.scanner import DocScanner, Mention

if TYPE_CHECKING:
    import sqlite3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in tolerance defaults (percentage as float, 0.0 = exact)
# ---------------------------------------------------------------------------

DEFAULT_TOLERANCES: dict[str, float] = {
    "version": 0.0,           # exact match required
    "node_count": 0.10,       # +/-10% (growing metric)
    "edge_count": 0.10,       # +/-10% (growing metric)
    "language_count": 0.0,    # exact (rarely changes)
    "test_count": 0.05,       # +/-5% (fluctuates)
    "framework_count": 0.0,   # exact (rarely changes)
    "mcp_tool_count": 0.0,    # exact
    "cli_command_count": 0.0, # exact
    "rule_type_count": 0.0,   # exact
}

# ---------------------------------------------------------------------------
# Extension → language mapping for language_count fact
# ---------------------------------------------------------------------------

_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".kt": "Kotlin",
    ".java": "Java",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C",
    ".hpp": "C++",
}


@dataclass(frozen=True)
class Fact:
    """A single ground-truth fact about the project.

    Attributes
    ----------
    name:
        Identifier, e.g. ``"version"``, ``"node_count"``.
    value:
        Ground-truth value (string for version, int for counts).
    source:
        Human-readable origin, e.g. ``"pyproject.toml"``, ``"graph DB"``.
    """

    name: str
    value: str | int
    source: str


@dataclass(frozen=True)
class AuditFinding:
    """A single audit finding: a mention compared against a ground-truth fact.

    Attributes
    ----------
    mention:
        The documentation mention being evaluated.
    fact:
        The ground-truth fact it was compared against.
    status:
        ``"stale"`` if the mention disagrees with the fact,
        ``"fresh"`` if it matches.
    tolerance:
        Applied tolerance (0.0 = exact match required).
        Will be configurable in a future tolerance system.
    """

    mention: Mention
    fact: Fact
    status: str
    tolerance: float


@dataclass(frozen=True)
class AuditResult:
    """Result of a documentation audit run.

    Attributes
    ----------
    facts:
        Ground-truth facts collected from the project.
    findings:
        Findings (stale/fresh) for mentions with a matching fact.
    unmatched:
        Mentions that had no corresponding fact in the registry.
    """

    facts: dict[str, Fact]
    findings: list[AuditFinding]
    unmatched: list[Mention]


_SUPPORTED_METRICS = frozenset({"stale"})
_SUPPORTED_OPS = frozenset({">", ">="})
_FAIL_IF_RE = re.compile(r"^\s*(\w+)\s*(>=?)\s*(\d+)\s*$")


def parse_fail_condition(expr: str) -> tuple[str, str, int]:
    """Parse a ``--fail-if`` expression like ``'stale>0'``.

    Parameters
    ----------
    expr:
        Expression string, e.g. ``"stale>0"``, ``"stale>=5"``.

    Returns
    -------
    tuple[str, str, int]
        ``(metric, operator, threshold)`` — e.g. ``("stale", ">", 0)``.

    Raises
    ------
    click.BadParameter
        On invalid syntax or unsupported metric/operator.
    """
    import click

    match = _FAIL_IF_RE.match(expr)
    if match is None:
        raise click.BadParameter(
            f"Invalid --fail-if expression {expr!r}. "
            "Expected format: stale>N (e.g., stale>0, stale>5)",
            param_hint="'--fail-if'",
        )

    metric, op, threshold_str = match.group(1), match.group(2), match.group(3)

    if metric not in _SUPPORTED_METRICS:
        raise click.BadParameter(
            f"Unsupported metric {metric!r}. Supported: {', '.join(sorted(_SUPPORTED_METRICS))}",
            param_hint="'--fail-if'",
        )

    if op not in _SUPPORTED_OPS:
        raise click.BadParameter(
            f"Unsupported operator {op!r}. Supported: {', '.join(sorted(_SUPPORTED_OPS))}",
            param_hint="'--fail-if'",
        )

    return metric, op, int(threshold_str)


def compare_facts(
    facts: dict[str, Fact],
    mentions: list[Mention],
    tolerances: dict[str, float] | None = None,
) -> AuditResult:
    """Compare mentions against ground-truth facts.

    Applies configurable tolerance per fact type.  Built-in defaults:
    exact for versions, +/-5% for test counts, +/-10% for growing
    metrics (node_count, edge_count).  User overrides via *tolerances*
    dict take precedence over ``DEFAULT_TOLERANCES``.

    Parameters
    ----------
    facts:
        Ground-truth facts keyed by fact name.
    mentions:
        Mentions extracted from documentation.
    tolerances:
        Optional per-fact tolerance overrides.  Merged on top of
        ``DEFAULT_TOLERANCES`` (user values win).

    Returns
    -------
    AuditResult
        Findings (stale/fresh) and unmatched mentions.
    """
    # Merge: defaults <- user overrides
    merged: dict[str, float] = {**DEFAULT_TOLERANCES}
    if tolerances:
        merged.update(tolerances)

    findings: list[AuditFinding] = []
    unmatched: list[Mention] = []

    for mention in mentions:
        fact = facts.get(mention.fact_name)
        if fact is None:
            unmatched.append(mention)
            continue

        tolerance = merged.get(mention.fact_name, 0.0)

        # Compare values with tolerance
        status = (
            "fresh"
            if _values_match_with_tolerance(fact.value, mention.value, tolerance)
            else "stale"
        )

        findings.append(
            AuditFinding(
                mention=mention,
                fact=fact,
                status=status,
                tolerance=tolerance,
            )
        )

    return AuditResult(facts=facts, findings=findings, unmatched=unmatched)


def _values_match_with_tolerance(
    fact_value: str | int,
    mention_value: str | int,
    tolerance: float,
) -> bool:
    """Check if a mention value matches the fact value within tolerance.

    For version strings: always exact string comparison (tolerance ignored).
    For numeric values with tolerance > 0: range check ``[actual*(1-t), actual*(1+t)]``.
    For numeric values with tolerance == 0: exact integer equality.

    Parameters
    ----------
    fact_value:
        Ground-truth value (string for versions, int for counts).
    mention_value:
        Value found in documentation.
    tolerance:
        Allowed deviation as a fraction (e.g. 0.05 = +/-5%).
    """
    # Both are version strings — always exact
    if isinstance(fact_value, str) and isinstance(mention_value, str):
        fv = fact_value.lstrip("v")
        mv = mention_value.lstrip("v")
        return fv == mv

    # Numeric comparison
    try:
        actual = int(str(fact_value))
        mentioned = int(str(mention_value))
    except (ValueError, TypeError):
        return str(fact_value) == str(mention_value)

    if tolerance > 0.0:
        # Special case: actual == 0 — only exact match is valid
        if actual == 0:
            return mentioned == 0
        lower = actual * (1 - tolerance)
        upper = actual * (1 + tolerance)
        return lower <= mentioned <= upper

    return actual == mentioned


def _load_tolerances_from_config(project_root: Path) -> dict[str, float] | None:
    """Load tolerance overrides from ``.beadloom/config.yml``.

    Expected format::

        docs_audit:
          tolerances:
            test_count: 0.10
            node_count: 0.05

    Returns ``None`` if no overrides are configured.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.is_file():
        return None

    try:
        import yaml

        content = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except Exception:
        logger.warning("Failed to read .beadloom/config.yml for tolerances")
        return None

    if not isinstance(data, dict):
        return None

    audit_section = data.get("docs_audit")
    if not isinstance(audit_section, dict):
        return None

    raw_tolerances = audit_section.get("tolerances")
    if not isinstance(raw_tolerances, dict):
        return None

    result: dict[str, float] = {}
    for key, value in raw_tolerances.items():
        if isinstance(value, (int, float)):
            result[str(key)] = float(value)
        else:
            logger.warning(
                "Ignoring non-numeric tolerance for %s: %r", key, value
            )

    return result if result else None


def run_audit(
    project_root: Path,
    db: sqlite3.Connection,
    *,
    scan_paths: list[str] | None = None,
) -> AuditResult:
    """Run full documentation audit: collect facts, scan docs, compare.

    Loads tolerance overrides from ``.beadloom/config.yml`` if present
    and passes them to :func:`compare_facts`.

    Parameters
    ----------
    project_root:
        Root of the project directory.
    db:
        Open SQLite connection to the Beadloom database.
    scan_paths:
        Optional glob patterns for scanning (defaults to DocScanner defaults).

    Returns
    -------
    AuditResult
        Full audit result with facts, findings, and unmatched mentions.
    """
    registry = FactRegistry()
    facts = registry.collect(project_root, db)

    scanner = DocScanner()
    paths = scanner.resolve_paths(project_root, scan_paths)
    mentions = scanner.scan(paths)

    tolerances = _load_tolerances_from_config(project_root)
    return compare_facts(facts, mentions, tolerances=tolerances)


class FactRegistry:
    """Auto-computes project facts from existing data sources.

    All facts are collected via :meth:`collect`; each source is wrapped
    in a try/except so missing data is gracefully skipped.
    """

    def collect(
        self,
        project_root: Path,
        db: sqlite3.Connection,
    ) -> dict[str, Fact]:
        """Collect all facts from available sources.

        Parameters
        ----------
        project_root:
            Root of the project directory.
        db:
            Open SQLite connection to the Beadloom database.

        Returns
        -------
        dict[str, Fact]
            Mapping of fact name to ``Fact`` instance.  Facts that cannot
            be computed are silently omitted.
        """
        facts: dict[str, Fact] = {}

        self._collect_version(project_root, facts)
        self._collect_db_counts(db, facts)
        self._collect_language_count(db, facts)
        self._collect_test_count(db, facts)
        self._collect_framework_count(db, facts)
        self._collect_rule_type_count(db, facts)
        self._collect_mcp_tool_count(facts)
        self._collect_cli_command_count(facts)
        self._collect_extra_facts(project_root, facts)

        return facts

    # ------------------------------------------------------------------
    # Version from manifest files
    # ------------------------------------------------------------------

    def _collect_version(
        self,
        project_root: Path,
        facts: dict[str, Fact],
    ) -> None:
        """Extract version from project manifests with priority fallback.

        Handles dynamic versioning (Hatch ``[tool.hatch.version]``) and
        falls back to ``importlib.metadata`` for installed packages.
        """
        extractors: list[tuple[str, str]] = [
            ("pyproject.toml", "pyproject.toml"),
            ("package.json", "package.json"),
            ("Cargo.toml", "Cargo.toml"),
        ]

        for filename, source_label in extractors:
            manifest = project_root / filename
            if not manifest.is_file():
                continue

            try:
                version = self._parse_version(
                    manifest, filename, project_root=project_root,
                )
            except Exception:
                logger.warning("Failed to parse version from %s", filename)
                continue

            if version is not None:
                facts["version"] = Fact(
                    name="version",
                    value=version,
                    source=source_label,
                )
                return  # first match wins

    @staticmethod
    def _parse_version(
        path: Path,
        filename: str,
        *,
        project_root: Path | None = None,
    ) -> str | None:
        """Parse version string from a manifest file.

        For ``pyproject.toml``, detects dynamic versioning:

        1. If ``dynamic = ["version"]`` and ``[tool.hatch.version] path``
           is set, reads ``__version__`` from that source file.
        2. Falls back to ``importlib.metadata.version(package_name)``.
        3. Otherwise, looks for a static ``version = "X.Y.Z"`` line.

        Uses regex to avoid heavy TOML parser dependencies.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("Cannot read %s", path)
            return None

        if filename == "pyproject.toml":
            # Check for dynamic versioning
            is_dynamic = bool(
                re.search(r'^\s*dynamic\s*=\s*\[.*"version"', content, re.MULTILINE)
            )

            if is_dynamic:
                # Try Hatch: [tool.hatch.version] path = "..."
                hatch_match = re.search(
                    r'^\[tool\.hatch\.version\]\s*\n\s*path\s*=\s*"([^"]+)"',
                    content,
                    re.MULTILINE,
                )
                if hatch_match and project_root is not None:
                    version_file = project_root / hatch_match.group(1)
                    if version_file.is_file():
                        try:
                            src_content = version_file.read_text(encoding="utf-8")
                            ver_match = re.search(
                                r'__version__\s*=\s*["\']([^"\']+)["\']',
                                src_content,
                            )
                            if ver_match:
                                return ver_match.group(1)
                        except OSError:
                            logger.warning("Cannot read %s", version_file)

                # Fallback: importlib.metadata
                name_match = re.search(
                    r'^\s*name\s*=\s*"([^"]+)"',
                    content,
                    re.MULTILINE,
                )
                if name_match:
                    pkg_name = name_match.group(1)
                    try:
                        import importlib.metadata

                        return importlib.metadata.version(pkg_name)
                    except Exception:
                        logger.debug(
                            "importlib.metadata.version(%r) failed", pkg_name,
                        )

                return None  # dynamic but couldn't resolve

            # Static version
            match = re.search(
                r'^\s*version\s*=\s*"([^"]+)"',
                content,
                re.MULTILINE,
            )
            return match.group(1) if match else None

        if filename == "package.json":
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    version = data.get("version")
                    return str(version) if version else None
            except (json.JSONDecodeError, ValueError):
                return None

        if filename == "Cargo.toml":
            match = re.search(
                r'^\s*version\s*=\s*"([^"]+)"',
                content,
                re.MULTILINE,
            )
            return match.group(1) if match else None

        return None

    # ------------------------------------------------------------------
    # Database count facts
    # ------------------------------------------------------------------

    def _collect_db_counts(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
    ) -> None:
        """Collect node_count and edge_count from graph DB."""
        source = "graph DB"

        try:
            row = db.execute("SELECT COUNT(*) AS cnt FROM nodes").fetchone()
            facts["node_count"] = Fact(
                name="node_count", value=row["cnt"], source=source
            )
        except Exception:
            logger.warning("Cannot query nodes table")

        try:
            row = db.execute("SELECT COUNT(*) AS cnt FROM edges").fetchone()
            facts["edge_count"] = Fact(
                name="edge_count", value=row["cnt"], source=source
            )
        except Exception:
            logger.warning("Cannot query edges table")

    def _collect_language_count(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
    ) -> None:
        """Count distinct languages from file extensions in code_symbols."""
        try:
            rows = db.execute(
                "SELECT DISTINCT file_path FROM code_symbols"
            ).fetchall()

            languages: set[str] = set()
            for row in rows:
                file_path: str = row["file_path"]
                ext = Path(file_path).suffix.lower()
                lang = _EXT_TO_LANGUAGE.get(ext)
                if lang is not None:
                    languages.add(lang)

            facts["language_count"] = Fact(
                name="language_count",
                value=len(languages),
                source="code symbols",
            )
        except Exception:
            logger.warning("Cannot query code_symbols for language count")

    def _collect_test_count(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
    ) -> None:
        """Sum test_count from nodes.extra JSON tests.test_count."""
        try:
            rows = db.execute("SELECT extra FROM nodes").fetchall()
            total = 0
            for row in rows:
                extra_str: str = row["extra"] or "{}"
                try:
                    extra = json.loads(extra_str)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(extra, dict):
                    tests_data = extra.get("tests")
                    if isinstance(tests_data, dict):
                        count = tests_data.get("test_count", 0)
                        if isinstance(count, int):
                            total += count

            facts["test_count"] = Fact(
                name="test_count", value=total, source="graph DB"
            )
        except Exception:
            logger.warning("Cannot query nodes for test count")

    def _collect_framework_count(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
    ) -> None:
        """Count nodes with non-empty framework detection data in extra."""
        try:
            rows = db.execute("SELECT extra FROM nodes").fetchall()
            count = 0
            for row in rows:
                extra_str: str = row["extra"] or "{}"
                try:
                    extra = json.loads(extra_str)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(extra, dict):
                    tests_data = extra.get("tests")
                    if isinstance(tests_data, dict):
                        framework = tests_data.get("framework", "")
                        if framework:
                            count += 1

            facts["framework_count"] = Fact(
                name="framework_count",
                value=count,
                source="graph DB",
            )
        except Exception:
            logger.warning("Cannot query nodes for framework count")

    def _collect_rule_type_count(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
    ) -> None:
        """Count rules from the rules table."""
        try:
            row = db.execute("SELECT COUNT(*) AS cnt FROM rules").fetchone()
            facts["rule_type_count"] = Fact(
                name="rule_type_count",
                value=row["cnt"],
                source="graph DB",
            )
        except Exception:
            logger.warning("Cannot query rules table")

    # ------------------------------------------------------------------
    # MCP tool count
    # ------------------------------------------------------------------

    def _collect_mcp_tool_count(
        self,
        facts: dict[str, Fact],
    ) -> None:
        """Count MCP tools from the server definition module."""
        try:
            from beadloom.services.mcp_server import _TOOLS

            facts["mcp_tool_count"] = Fact(
                name="mcp_tool_count",
                value=len(_TOOLS),
                source="MCP server",
            )
        except Exception:
            logger.warning("Cannot introspect MCP tools")

    # ------------------------------------------------------------------
    # CLI command count
    # ------------------------------------------------------------------

    def _collect_cli_command_count(
        self,
        facts: dict[str, Fact],
    ) -> None:
        """Count CLI commands from the Click main group."""
        try:
            from beadloom.services.cli import main

            count = self._count_click_commands(main)
            facts["cli_command_count"] = Fact(
                name="cli_command_count",
                value=count,
                source="CLI",
            )
        except Exception:
            logger.warning("Cannot introspect CLI commands")

    @staticmethod
    def _count_click_commands(group: object) -> int:
        """Recursively count commands in a Click group.

        Traverses nested groups (e.g., ``docs``, ``snapshot``) to get
        a total count of leaf commands + groups.
        """
        import click

        if not isinstance(group, click.Group):
            return 0

        count = 0
        ctx = click.Context(group)
        for name in group.list_commands(ctx):
            cmd = group.get_command(ctx, name)
            if cmd is None:
                continue
            count += 1
            if isinstance(cmd, click.Group):
                count += FactRegistry._count_click_commands(cmd)
        return count

    # ------------------------------------------------------------------
    # Extra facts from config
    # ------------------------------------------------------------------

    def _collect_extra_facts(
        self,
        project_root: Path,
        facts: dict[str, Fact],
    ) -> None:
        """Load extra facts from ``.beadloom/config.yml`` ``docs_audit.extra_facts``.

        Expected format::

            docs_audit:
              extra_facts:
                custom_metric:
                  value: 42
                  source: "manual config"
        """
        config_path = project_root / ".beadloom" / "config.yml"
        if not config_path.is_file():
            return

        try:
            import yaml

            content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except Exception:
            logger.warning("Failed to read .beadloom/config.yml for extra facts")
            return

        if not isinstance(data, dict):
            return

        audit_section = data.get("docs_audit")
        if not isinstance(audit_section, dict):
            return

        extra_facts = audit_section.get("extra_facts")
        if not isinstance(extra_facts, dict):
            return

        for fact_name, fact_def in extra_facts.items():
            if not isinstance(fact_def, dict):
                logger.warning("Skipping malformed extra fact: %s", fact_name)
                continue

            value = fact_def.get("value")
            source = fact_def.get("source", "config.yml")

            if value is None:
                logger.warning("Extra fact %s has no value, skipping", fact_name)
                continue

            if not isinstance(value, (str, int)):
                logger.warning(
                    "Extra fact %s has unsupported value type %s, skipping",
                    fact_name,
                    type(value).__name__,
                )
                continue

            facts[str(fact_name)] = Fact(
                name=str(fact_name),
                value=value,
                source=str(source),
            )
