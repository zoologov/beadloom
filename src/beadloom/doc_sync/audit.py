"""Documentation audit: fact registry, comparator, and audit facade.

Provides ``Fact`` and ``FactRegistry`` — auto-computes project facts from
existing Beadloom infrastructure (manifest, graph DB, code symbols, MCP
tools, CLI commands) for comparison against doc mentions.

Also provides ``AuditFinding``, ``AuditResult``, ``compare_facts()`` for
comparing mentions against ground truth, and ``run_audit()`` facade.
"""

# beadloom:feature=docs-audit

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.doc_sync.audit_coverage import FactCoverage, assess_coverage
from beadloom.doc_sync.audit_self_surface import (
    RUNNING_DISTRIBUTION,
    foreign_project_reason,
)
from beadloom.doc_sync.scanner import DocScanner, Mention, ScanSurface
from beadloom.infrastructure.mcp_tools import MCP_TOOL_CATALOG
from beadloom.infrastructure.surface_registry import get_cli_group

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
    "nodes_with_framework": 0.0,  # exact (rarely changes)
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
class FactSet:
    """What a project declares, and what the audit refused to declare for it.

    A collector that cannot compute a fact used to omit it, which left the
    denominator of "N of M declared fact(s) verified" moving silently: measured
    in this repository, an unregistered CLI surface turned nine declared facts
    into eight and nothing said which one left.  A decline is now a value in its
    own right, carrying the reason a reader needs to judge it.

    Attributes
    ----------
    facts:
        The facts the audit computed for this project, keyed by fact name.
    not_applicable:
        Fact name → the reason no value was declared for it.  Disjoint from
        ``facts``: a name is in exactly one of the two.
    """

    facts: dict[str, Fact]
    not_applicable: dict[str, str] = field(default_factory=dict)


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
    coverage:
        Per-fact coverage — what the run CHECKED, as opposed to what it found.
        A finding count says nothing about the facts nobody stated, and on this
        repo thirteen findings covered one fact of nine (BDL-UX #173).
    surface:
        Which documents were read and which were skipped, with reasons.
        ``None`` when the result was built from mentions directly rather than
        by scanning a project.
    not_applicable:
        Fact name → the reason the audit declared no value for it in THIS
        project.  These facts are outside the denominator entirely; they are
        neither verified nor unverified, and naming them is what keeps the
        denominator from shrinking in silence.
    """

    facts: dict[str, Fact]
    findings: list[AuditFinding]
    unmatched: list[Mention]
    coverage: dict[str, FactCoverage] = field(default_factory=dict)
    surface: ScanSurface | None = None
    not_applicable: dict[str, str] = field(default_factory=dict)

    @property
    def verified_facts(self) -> list[str]:
        """Declared facts at least one document stated and the run judged."""
        return sorted(name for name, cov in self.coverage.items() if cov.verified)

    @property
    def unverified_facts(self) -> list[str]:
        """Declared facts the run verified nothing for — named, not just counted.

        Includes both the facts no document states and the facts the scanner
        cannot read; the two read differently in the report, but neither is a
        verification and neither may be counted as one.
        """
        return sorted(
            name for name, cov in self.coverage.items() if not cov.verified
        )


@dataclass(frozen=True)
class IgnoreRule:
    """A targeted false-positive suppression rule (BDL-057.6).

    Suppresses exactly one ``{path, fact, value}`` mention triple so a known
    keyword-proximity false positive (e.g. "12 supported languages" matched
    against the in-repo ``language_count``, or an HTTP status "404" matched as a
    ``cli_command_count``) can be silenced WITHOUT rewording correct prose and
    WITHOUT masking genuine stale facts of the same type elsewhere.

    Attributes
    ----------
    path:
        Doc path the mention occurs in. Matched as a suffix of the mention's
        file path (so a repo-relative path in config matches the absolute path
        the scanner records).
    fact:
        The ``fact_name`` of the mention (e.g. ``"language_count"``).
    value:
        The mentioned value, compared as a string (e.g. ``"12"``, ``"404"``).
    """

    path: str
    fact: str
    value: str

    def matches(self, mention: Mention) -> bool:
        """True when *mention* is exactly the suppressed triple."""
        if mention.fact_name != self.fact:
            return False
        if str(mention.value) != self.value:
            return False
        return str(mention.file).replace("\\", "/").endswith(self.path)


#: ``stale``      — mentions that disagree with ground truth.
#: ``unverified`` — DECLARED FACTS the run checked nothing for.  A project that
#: wants every fact it declares to be stated somewhere can enforce it here;
#: without such a channel the coverage number would be reportable but not
#: actionable, which is how #178's honest-but-green log line failed.
_SUPPORTED_METRICS = frozenset({"stale", "unverified"})
_SUPPORTED_OPS = frozenset({">", ">="})
_FAIL_IF_RE = re.compile(r"^\s*(\w+)\s*(>=?)\s*(\d+)\s*$")


def _unreadable_table(table: str) -> str:
    """The reason a graph-database fact could not be computed."""
    return (
        f"the {table} table could not be read from the graph database — "
        "run `beadloom reindex`"
    )


def _foreign_surface_reason(surface: str, fact: str, clause: str) -> str:
    """The reason a surface of the running package says nothing about this project.

    ``clause`` is :func:`foreign_project_reason`'s statement of the identity
    mismatch.  The reason names the escape hatch as well as the refusal: a
    project with its own MCP server or CLI can declare the count under
    ``docs_audit.extra_facts`` and have it audited like any other fact.
    """
    return (
        f"{surface} describes the running {RUNNING_DISTRIBUTION} package, not "
        f"this project ({clause}); declare docs_audit.extra_facts.{fact} in "
        ".beadloom/config.yml to audit this project's own"
    )


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
            "Expected format: METRIC>N (e.g., stale>0, unverified>2)",
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


def metric_value(
    metric: str, *, stale_count: int, unverified_count: int
) -> int:
    """Return the run's value for a ``--fail-if`` metric.

    One place decides what each metric MEANS, so the reported number and the
    exit code can never disagree — the failure mode of a gate that prints one
    verdict and returns another.
    """
    return unverified_count if metric == "unverified" else stale_count


def fail_condition_triggered(
    condition: tuple[str, str, int], *, stale_count: int, unverified_count: int
) -> bool:
    """True when the run's value for *condition*'s metric crosses its threshold."""
    metric, op, threshold = condition
    value = metric_value(
        metric, stale_count=stale_count, unverified_count=unverified_count
    )
    return value > threshold if op == ">" else value >= threshold


def compare_facts(
    facts: dict[str, Fact],
    mentions: list[Mention],
    tolerances: dict[str, float] | None = None,
    ignore: list[IgnoreRule] | None = None,
    not_applicable: dict[str, str] | None = None,
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
    ignore:
        Optional targeted false-positive suppressions (BDL-057.6). A mention
        matching any rule's ``{path, fact, value}`` triple is dropped entirely
        (neither a finding nor unmatched) — this silences a known false match
        without masking genuine stale facts of the same type elsewhere.
    not_applicable:
        Fact name → the reason the registry declared no value for it here.
        Carried through to the result so the report can name the population it
        did not check, instead of leaving the denominator quietly smaller.

    Returns
    -------
    AuditResult
        Findings (stale/fresh) and unmatched mentions.
    """
    # Merge: defaults <- user overrides
    merged: dict[str, float] = {**DEFAULT_TOLERANCES}
    if tolerances:
        merged.update(tolerances)

    rules = ignore or []
    findings: list[AuditFinding] = []
    unmatched: list[Mention] = []

    for mention in mentions:
        if any(rule.matches(mention) for rule in rules):
            continue  # suppressed false positive — not a finding, not unmatched

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

    return AuditResult(
        facts=facts,
        findings=findings,
        unmatched=unmatched,
        coverage=assess_coverage(facts, findings),
        not_applicable=dict(not_applicable or {}),
    )


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


def _load_ignore_from_config(project_root: Path) -> list[IgnoreRule]:
    """Load targeted false-positive suppressions from ``.beadloom/config.yml``.

    Expected format (each entry is a ``{path, fact, value}`` triple)::

        docs_audit:
          ignore:
            - path: docs/domains/context-oracle/README.md
              fact: language_count
              value: 12
            - path: docs/guides/vitepress-site.md
              fact: cli_command_count
              value: 404

    Returns an empty list when none are configured. Malformed entries (not a
    mapping, or missing any of the three keys) are skipped with a warning.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.is_file():
        return []

    try:
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to read .beadloom/config.yml for audit ignores")
        return []

    if not isinstance(data, dict):
        return []
    audit_section = data.get("docs_audit")
    if not isinstance(audit_section, dict):
        return []
    raw = audit_section.get("ignore")
    if not isinstance(raw, list):
        return []

    rules: list[IgnoreRule] = []
    for entry in raw:
        if not isinstance(entry, dict):
            logger.warning("Skipping non-mapping docs_audit.ignore entry: %r", entry)
            continue
        path = entry.get("path")
        fact = entry.get("fact")
        value = entry.get("value")
        if path is None or fact is None or value is None:
            logger.warning("Skipping incomplete docs_audit.ignore entry: %r", entry)
            continue
        rules.append(IgnoreRule(path=str(path), fact=str(fact), value=str(value)))

    return rules


def run_audit(
    project_root: Path,
    db: sqlite3.Connection,
    *,
    scan_paths: list[str] | None = None,
) -> AuditResult:
    """Run full documentation audit: collect facts, scan docs, compare.

    Loads tolerance overrides and targeted false-positive suppressions
    (``docs_audit.tolerances`` / ``docs_audit.ignore``) from
    ``.beadloom/config.yml`` if present and passes them to
    :func:`compare_facts`.

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
    fact_set = registry.collect_set(project_root, db)

    scanner = DocScanner()
    surface = scanner.resolve_surface(project_root, scan_paths)
    mentions = scanner.scan(list(surface.scanned))

    tolerances = _load_tolerances_from_config(project_root)
    ignore = _load_ignore_from_config(project_root)
    result = compare_facts(
        fact_set.facts,
        mentions,
        tolerances=tolerances,
        ignore=ignore,
        not_applicable=fact_set.not_applicable,
    )
    return replace(result, surface=surface)


class FactRegistry:
    """Auto-computes project facts from existing data sources.

    All facts are collected via :meth:`collect_set`.  A source that cannot
    produce a value does not vanish: it records why, so the audit can report
    the facts it declined alongside the facts it declared.
    """

    def collect_set(
        self,
        project_root: Path,
        db: sqlite3.Connection,
    ) -> FactSet:
        """Collect every fact this project declares, and every one it does not.

        Parameters
        ----------
        project_root:
            Root of the project directory.
        db:
            Open SQLite connection to the Beadloom database.

        Returns
        -------
        FactSet
            ``facts`` — what was computed for THIS project.  ``not_applicable``
            — fact name → the reason nothing was computed, which is the half
            that used to be dropped without trace.
        """
        facts: dict[str, Fact] = {}
        declined: dict[str, str] = {}

        self._collect_version(project_root, facts, declined)
        self._collect_db_counts(db, facts, declined)
        self._collect_language_count(db, facts, declined)
        self._collect_test_count(db, facts, declined)
        self._collect_nodes_with_framework(db, facts, declined)
        self._collect_rule_type_count(db, facts, declined)
        self._collect_mcp_tool_count(project_root, facts, declined)
        self._collect_cli_command_count(project_root, facts, declined)
        self._collect_extra_facts(project_root, facts)

        # A project that declares its own value for a surface fact (the escape
        # hatch every decline reason names) has answered the question, so the
        # decline is withdrawn rather than reported beside a value.
        for name in facts:
            declined.pop(name, None)

        return FactSet(facts=facts, not_applicable=declined)

    def collect(
        self,
        project_root: Path,
        db: sqlite3.Connection,
    ) -> dict[str, Fact]:
        """The computed facts only — :meth:`collect_set` without the declines.

        Kept because it is the published entry point callers already use.  A
        caller that needs to report what the audit could not compute wants
        :meth:`collect_set`; this one cannot tell an absent fact from a
        declined one.
        """
        return self.collect_set(project_root, db).facts

    # ------------------------------------------------------------------
    # Version from manifest files
    # ------------------------------------------------------------------

    def _collect_version(
        self,
        project_root: Path,
        facts: dict[str, Fact],
        declined: dict[str, str],
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

        declined["version"] = (
            "no manifest under this project declares a version "
            "(looked in pyproject.toml, package.json, Cargo.toml)"
        )

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
        declined: dict[str, str],
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
            declined["node_count"] = _unreadable_table("nodes")

        try:
            row = db.execute("SELECT COUNT(*) AS cnt FROM edges").fetchone()
            facts["edge_count"] = Fact(
                name="edge_count", value=row["cnt"], source=source
            )
        except Exception:
            logger.warning("Cannot query edges table")
            declined["edge_count"] = _unreadable_table("edges")

    def _collect_language_count(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
        declined: dict[str, str],
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
            declined["language_count"] = _unreadable_table("code_symbols")

    def _collect_test_count(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
        declined: dict[str, str],
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
            declined["test_count"] = _unreadable_table("nodes")

    def _collect_nodes_with_framework(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
        declined: dict[str, str],
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

            facts["nodes_with_framework"] = Fact(
                name="nodes_with_framework",
                value=count,
                source="graph DB",
            )
        except Exception:
            logger.warning("Cannot query nodes for framework count")
            declined["nodes_with_framework"] = _unreadable_table("nodes")

    def _collect_rule_type_count(
        self,
        db: sqlite3.Connection,
        facts: dict[str, Fact],
        declined: dict[str, str],
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
            declined["rule_type_count"] = _unreadable_table("rules")

    # ------------------------------------------------------------------
    # MCP tool count — a surface of the RUNNING package, not of every project
    # ------------------------------------------------------------------

    def _collect_mcp_tool_count(
        self,
        project_root: Path,
        facts: dict[str, Fact],
        declined: dict[str, str],
    ) -> None:
        """Count MCP tools — only when the audited project provides that surface.

        The catalog is canonical for Beadloom and pinned equal to the server's
        live registry by a test, so the value never depends on whether the
        server module happens to be imported.  It is still a fact about
        Beadloom, which is why it is declared only for Beadloom.
        """
        foreign = foreign_project_reason(project_root)
        if foreign is not None:
            declined["mcp_tool_count"] = _foreign_surface_reason(
                "the MCP tool catalog", "mcp_tool_count", foreign
            )
            return
        facts["mcp_tool_count"] = Fact(
            name="mcp_tool_count",
            value=len(MCP_TOOL_CATALOG),
            source="MCP tool catalog",
        )

    # ------------------------------------------------------------------
    # CLI command count — likewise a surface of the RUNNING package
    # ------------------------------------------------------------------

    def _collect_cli_command_count(
        self,
        project_root: Path,
        facts: dict[str, Fact],
        declined: dict[str, str],
    ) -> None:
        """Count CLI commands from the Click main group, for that project only."""
        foreign = foreign_project_reason(project_root)
        if foreign is not None:
            declined["cli_command_count"] = _foreign_surface_reason(
                "the CLI command tree", "cli_command_count", foreign
            )
            return
        group = get_cli_group()
        if group is None:
            logger.warning("CLI surface unavailable — command count not audited")
            declined["cli_command_count"] = (
                "no CLI surface is registered in this process, so the command "
                "tree could not be counted — an absent surface is not an empty one"
            )
            return
        facts["cli_command_count"] = Fact(
            name="cli_command_count",
            value=self._count_click_commands(group),
            source="CLI",
        )

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
