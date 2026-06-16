# beadloom:domain=context-oracle
"""Tests for beadloom.linter — Lint orchestrator: load rules, evaluate, format."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import incremental_reindex
from beadloom.graph.linter import (
    LintError,
    LintResult,
    format_github,
    format_json,
    format_porcelain,
    format_rich,
    lint,
)
from beadloom.graph.rule_engine import Violation
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    """Provide an empty database with full schema."""
    db_path = tmp_path / "test.db"
    conn = open_db(db_path)
    create_schema(conn)
    yield conn  # type: ignore[misc]
    conn.close()


@pytest.fixture()
def lint_project(tmp_path: Path) -> Path:
    """Create a minimal project with graph, code, and rules for lint testing.

    Layout:
    - .beadloom/_graph/services.yml with billing/auth domain nodes
    - .beadloom/_graph/rules.yml with a deny rule billing->auth
    - src/billing/invoice.py annotated as billing, importing auth.tokens
    - src/auth/tokens.py annotated as auth
    - docs/ (empty dir for reindex)
    """
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: billing\n"
        "    kind: domain\n"
        "    summary: Billing domain\n"
        "  - ref_id: auth\n"
        "    kind: domain\n"
        "    summary: Auth domain\n"
        "edges: []\n"
    )
    (graph_dir / "rules.yml").write_text(
        "version: 1\n"
        "rules:\n"
        "  - name: billing-no-auth\n"
        '    description: "Billing must not import auth"\n'
        "    deny:\n"
        "      from: { ref_id: billing }\n"
        "      to: { ref_id: auth }\n"
    )
    (tmp_path / "docs").mkdir()

    src_dir = tmp_path / "src" / "billing"
    src_dir.mkdir(parents=True)
    (src_dir / "invoice.py").write_text(
        "# beadloom:domain=billing\nimport auth.tokens\ndef process(): pass\n"
    )

    auth_dir = tmp_path / "src" / "auth"
    auth_dir.mkdir(parents=True)
    (auth_dir / "tokens.py").write_text("# beadloom:domain=auth\ndef verify(): pass\n")

    return tmp_path


@pytest.fixture()
def clean_lint_project(tmp_path: Path) -> Path:
    """Project with rules but no violations (no cross-boundary imports)."""
    graph_dir = tmp_path / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "services.yml").write_text(
        "nodes:\n"
        "  - ref_id: billing\n"
        "    kind: domain\n"
        "    summary: Billing domain\n"
        "  - ref_id: auth\n"
        "    kind: domain\n"
        "    summary: Auth domain\n"
        "edges: []\n"
    )
    (graph_dir / "rules.yml").write_text(
        "version: 1\n"
        "rules:\n"
        "  - name: billing-no-auth\n"
        '    description: "Billing must not import auth"\n'
        "    deny:\n"
        "      from: { ref_id: billing }\n"
        "      to: { ref_id: auth }\n"
    )
    (tmp_path / "docs").mkdir()

    # billing imports only from billing (no cross-boundary)
    src_dir = tmp_path / "src" / "billing"
    src_dir.mkdir(parents=True)
    (src_dir / "invoice.py").write_text("# beadloom:domain=billing\ndef process(): pass\n")

    return tmp_path


# ---------------------------------------------------------------------------
# Helper to populate DB directly for format tests
# ---------------------------------------------------------------------------


def _make_violations() -> list[Violation]:
    return [
        Violation(
            rule_name="billing-auth-boundary",
            rule_description="Billing must not import from auth directly",
            rule_type="deny",
            severity="error",
            file_path="src/billing/invoice.py",
            line_number=12,
            from_ref_id="billing",
            to_ref_id="auth",
            message="imports auth (auth.tokens)",
        ),
        Violation(
            rule_name="all-services-need-domain",
            rule_description="Every service must be part of a domain",
            rule_type="require",
            severity="error",
            file_path=None,
            line_number=None,
            from_ref_id="notifications",
            to_ref_id=None,
            message='Node "notifications" (service) has no edge to any domain node',
        ),
    ]


def _make_result(
    violations: list[Violation] | None = None,
    rules_evaluated: int = 3,
    files_scanned: int = 25,
    imports_resolved: int = 142,
    elapsed_ms: float = 800.0,
) -> LintResult:
    return LintResult(
        violations=violations if violations is not None else _make_violations(),
        rules_evaluated=rules_evaluated,
        files_scanned=files_scanned,
        imports_resolved=imports_resolved,
        elapsed_ms=elapsed_ms,
    )


# ---------------------------------------------------------------------------
# TestLint — lint() orchestrator function
# ---------------------------------------------------------------------------


class TestLint:
    """Tests for lint() — full orchestration."""

    def test_lint_with_violations(self, lint_project: Path) -> None:
        """Full lint run detects billing->auth violation.

        After reindex, we inject a resolved import record so the deny rule
        evaluation can find the cross-boundary import.  This mirrors the
        pattern in test_rule_engine where data is manually populated because
        the import_resolver and rule_engine use different ref_id conventions.
        """
        from beadloom.infrastructure.db import open_db as _open_db

        # First reindex to populate the DB with nodes, symbols, etc.
        result = lint(lint_project, reindex=incremental_reindex)
        assert result.rules_evaluated >= 1

        # Inject a resolved import record into the DB so rule evaluation
        # can detect the billing->auth boundary violation.
        db_path = lint_project / ".beadloom" / "beadloom.db"
        conn = _open_db(db_path)
        conn.execute(
            "INSERT OR REPLACE INTO code_imports"
            " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
            " VALUES (?, ?, ?, ?, ?)",
            ("src/billing/invoice.py", 2, "auth.tokens", "auth", "test"),
        )
        conn.commit()
        conn.close()

        # Now re-lint without reindex to pick up the injected import.
        result = lint(lint_project)
        assert result.rules_evaluated >= 1
        assert len(result.violations) >= 1
        assert any(v.rule_name == "billing-no-auth" for v in result.violations)
        assert result.elapsed_ms >= 0

    def test_lint_clean(self, clean_lint_project: Path) -> None:
        """Lint on a clean project returns 0 violations."""
        result = lint(clean_lint_project, reindex=incremental_reindex)
        assert result.rules_evaluated >= 1
        assert len(result.violations) == 0
        assert result.elapsed_ms >= 0

    def test_lint_no_rules_file(self, tmp_path: Path) -> None:
        """No rules.yml file returns 0 violations and 0 rules."""
        # Minimal project: no _graph/rules.yml
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: billing\n"
            "    kind: domain\n"
            "    summary: Billing domain\n"
            "edges: []\n"
        )
        (tmp_path / "docs").mkdir()
        result = lint(tmp_path, reindex=incremental_reindex)
        assert result.violations == []
        assert result.rules_evaluated == 0

    def test_lint_invalid_rules_raises_lint_error(self, tmp_path: Path) -> None:
        """Invalid rules.yml raises LintError."""
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "services.yml").write_text(
            "nodes:\n"
            "  - ref_id: billing\n"
            "    kind: domain\n"
            "    summary: Billing domain\n"
            "edges: []\n"
        )
        # Invalid rules: missing version field
        (graph_dir / "rules.yml").write_text(
            "rules:\n"
            "  - name: bad\n"
            "    deny:\n"
            "      from: { ref_id: a }\n"
            "      to: { ref_id: b }\n"
        )
        (tmp_path / "docs").mkdir()
        with pytest.raises(LintError, match="version"):
            lint(tmp_path, reindex=incremental_reindex)

    def test_lint_no_reindex_callback_skips_reindex(self, lint_project: Path) -> None:
        """With no injected reindex callback, lint does not reindex."""
        # Prepare the DB once via an explicit reindex.
        lint(lint_project, reindex=incremental_reindex)

        calls: list[Path] = []

        def spy(project_root: Path) -> None:
            calls.append(project_root)

        # Default (no reindex kwarg) must NOT invoke any reindex.
        result = lint(lint_project)
        assert isinstance(result, LintResult)

        # Injected callback IS invoked exactly once with the project root.
        result = lint(lint_project, reindex=spy)
        assert calls == [lint_project]
        assert isinstance(result, LintResult)

    def test_lint_custom_rules_path(self, lint_project: Path) -> None:
        """Custom rules_path overrides default location."""
        # Write a separate rules file with a require rule
        custom_rules = lint_project / "custom_rules.yml"
        custom_rules.write_text(
            "version: 1\n"
            "rules:\n"
            "  - name: custom-require\n"
            '    description: "Services need domain"\n'
            "    require:\n"
            "      for: { kind: service }\n"
            "      has_edge_to: { kind: domain }\n"
        )
        result = lint(lint_project, rules_path=custom_rules, reindex=incremental_reindex)
        assert result.rules_evaluated == 1
        # No services in this project, so no require violations
        assert len(result.violations) == 0

    def test_lint_counts_files_and_imports(self, lint_project: Path) -> None:
        """lint() correctly reports files_scanned and imports_resolved counts.

        After reindex, inject import records so the lint counts are non-zero.
        The current reindex does not populate code_imports, so we inject
        records manually (same pattern as test_lint_with_violations).
        """
        from beadloom.infrastructure.db import open_db as _open_db

        # First lint to create the DB
        lint(lint_project, reindex=incremental_reindex)

        # Inject import records
        db_path = lint_project / ".beadloom" / "beadloom.db"
        conn = _open_db(db_path)
        conn.executescript(
            "CREATE TABLE IF NOT EXISTS code_imports ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  file_path TEXT NOT NULL,"
            "  line_number INTEGER NOT NULL,"
            "  import_path TEXT NOT NULL,"
            "  resolved_ref_id TEXT,"
            "  file_hash TEXT NOT NULL,"
            "  UNIQUE(file_path, line_number, import_path)"
            ");"
        )
        conn.execute(
            "INSERT OR REPLACE INTO code_imports"
            " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
            " VALUES (?, ?, ?, ?, ?)",
            ("src/billing/invoice.py", 2, "auth.tokens", "auth", "hash1"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO code_imports"
            " (file_path, line_number, import_path, resolved_ref_id, file_hash)"
            " VALUES (?, ?, ?, ?, ?)",
            ("src/billing/invoice.py", 3, "os.path", None, "hash1"),
        )
        conn.commit()
        conn.close()

        # Re-lint without reindex to preserve injected data
        result = lint(lint_project)
        assert result.files_scanned >= 1
        assert result.imports_resolved >= 1


# ---------------------------------------------------------------------------
# TestFormatRich — human-readable output
# ---------------------------------------------------------------------------


class TestFormatRich:
    """Tests for format_rich() — Rich-style text output."""

    def test_format_with_violations(self) -> None:
        """Shows each violation with details."""
        result = _make_result()
        output = format_rich(result)

        assert "billing-auth-boundary" in output
        assert "all-services-need-domain" in output
        assert "Errors: 2" in output
        assert "3 rules evaluated" in output

    def test_format_no_violations(self) -> None:
        """Clean result shows success message."""
        result = _make_result(violations=[], rules_evaluated=3)
        output = format_rich(result)
        assert "No violations found" in output
        assert "3 rules evaluated" in output

    def test_format_summary_line(self) -> None:
        """Summary line contains correct counts and timing."""
        result = _make_result(elapsed_ms=1234.5)
        output = format_rich(result)
        assert "25 scanned" in output
        assert "142 imports resolved" in output
        assert "1.2s" in output


# ---------------------------------------------------------------------------
# TestFormatJson — structured JSON output
# ---------------------------------------------------------------------------


class TestFormatJson:
    """Tests for format_json() — JSON output."""

    def test_valid_json_output(self) -> None:
        """Output is valid JSON with correct top-level keys."""
        result = _make_result()
        raw = format_json(result)
        parsed = json.loads(raw)
        assert "violations" in parsed
        assert "summary" in parsed

    def test_violations_match_result(self) -> None:
        """Violations array matches the LintResult violations count."""
        result = _make_result()
        raw = format_json(result)
        parsed = json.loads(raw)
        assert len(parsed["violations"]) == 2
        v0 = parsed["violations"][0]
        assert "rule_name" in v0
        assert "rule_type" in v0
        assert "message" in v0

    def test_summary_fields_correct(self) -> None:
        """Summary object has correct numeric fields."""
        result = _make_result()
        raw = format_json(result)
        parsed = json.loads(raw)
        summary = parsed["summary"]
        assert summary["rules_evaluated"] == 3
        assert summary["violations_count"] == 2
        assert summary["files_scanned"] == 25
        assert summary["imports_resolved"] == 142
        assert summary["elapsed_ms"] == 800.0


# ---------------------------------------------------------------------------
# TestFormatPorcelain — machine-readable output
# ---------------------------------------------------------------------------


class TestFormatPorcelain:
    """Tests for format_porcelain() — one-line-per-violation output."""

    def test_one_line_per_violation(self) -> None:
        """Each violation produces one colon-separated line."""
        result = _make_result()
        output = format_porcelain(result)
        lines = output.strip().split("\n")
        assert len(lines) == 2

    def test_correct_format(self) -> None:
        """Deny violation has file_path and line, require violation has empty fields."""
        violations = _make_violations()
        result = _make_result(violations=violations)
        output = format_porcelain(result)
        lines = output.strip().split("\n")

        # deny violation — has file_path and line
        # Format: rule_name:rule_type:severity:file_path:line:from_ref:to_ref
        parts = lines[0].split(":")
        assert len(parts) == 7
        assert parts[0] in ("billing-auth-boundary", "all-services-need-domain")

        # Find the require violation line (no file_path)
        require_line = [line for line in lines if "require" in line]
        assert len(require_line) == 1
        rparts = require_line[0].split(":")
        assert rparts[1] == "require"
        assert rparts[2] == "error"  # severity
        # file_path and line_number should be empty
        assert rparts[3] == ""
        assert rparts[4] == ""

    def test_empty_result(self) -> None:
        """Empty violations produces empty string."""
        result = _make_result(violations=[])
        output = format_porcelain(result)
        assert output == ""

    def test_require_rule_empty_fields(self) -> None:
        """Require rule violation has empty file_path, line_number, and to_ref_id."""
        violations = [
            Violation(
                rule_name="svc-needs-domain",
                rule_description="Service must be part of domain",
                rule_type="require",
                severity="error",
                file_path=None,
                line_number=None,
                from_ref_id="notifications",
                to_ref_id=None,
                message="Node has no domain edge",
            ),
        ]
        result = _make_result(violations=violations, rules_evaluated=1)
        output = format_porcelain(result)
        # Format: rule_name:rule_type:severity:file_path:line:from_ref:to_ref
        parts = output.strip().split(":")
        assert parts[0] == "svc-needs-domain"
        assert parts[1] == "require"
        assert parts[2] == "error"  # severity
        assert parts[3] == ""  # file_path
        assert parts[4] == ""  # line_number
        assert parts[5] == "notifications"  # from_ref_id
        assert parts[6] == ""  # to_ref_id


# ---------------------------------------------------------------------------
# Agent-actionable output: remediation + findings + github (BDL-039 F3 BEAD-02)
# ---------------------------------------------------------------------------


def _remediated_violations() -> list[Violation]:
    return [
        Violation(
            rule_name="billing-no-auth",
            rule_description="Billing must not import auth",
            rule_type="deny",
            severity="error",
            file_path="src/billing/invoice.py",
            line_number=12,
            from_ref_id="billing",
            to_ref_id="auth",
            message="imports auth",
            remediation="remove the import `billing -> auth`",
        ),
        Violation(
            rule_name="svc-needs-domain",
            rule_description="Service must be part of domain",
            rule_type="require",
            severity="warn",
            file_path=None,
            line_number=None,
            from_ref_id="notifications",
            to_ref_id=None,
            message="no domain edge",
            remediation="add the required edge from `notifications`",
        ),
    ]


class TestFormatJsonAgentActionable:
    """Additive `remediation` key + stable `findings` array."""

    def test_violations_carry_remediation_key(self) -> None:
        result = _make_result(violations=_remediated_violations())
        parsed = json.loads(format_json(result))
        assert parsed["violations"][0]["remediation"] == "remove the import `billing -> auth`"

    def test_findings_array_present_and_shaped(self) -> None:
        result = _make_result(violations=_remediated_violations())
        parsed = json.loads(format_json(result))
        assert "findings" in parsed
        f0 = parsed["findings"][0]
        assert set(f0) == {"kind", "rule", "severity", "locations", "why", "remediation"}
        assert f0["kind"] == "deny"
        assert f0["rule"] == "billing-no-auth"
        assert f0["locations"] == [{"file": "src/billing/invoice.py", "line": 12}]
        assert f0["why"] == "imports auth"
        assert f0["remediation"] == "remove the import `billing -> auth`"

    def test_finding_without_location_has_empty_locations(self) -> None:
        result = _make_result(violations=_remediated_violations())
        parsed = json.loads(format_json(result))
        # second finding is a require rule with no file/line
        assert parsed["findings"][1]["locations"] == []

    def test_json_deterministic(self) -> None:
        result = _make_result(violations=_remediated_violations())
        assert format_json(result) == format_json(result)

    def test_existing_keys_not_regressed(self) -> None:
        result = _make_result()
        parsed = json.loads(format_json(result))
        v0 = parsed["violations"][0]
        for key in ("rule_name", "rule_type", "severity", "file_path", "message"):
            assert key in v0


class TestFormatGithub:
    """`--format github` GitHub Actions annotations."""

    def test_error_annotation_with_location(self) -> None:
        result = _make_result(violations=_remediated_violations())
        out = format_github(result)
        first = out.splitlines()[0]
        assert first.startswith("::error file=src/billing/invoice.py,line=12::")
        assert "deny billing-no-auth: imports auth" in first
        assert "remove the import `billing -> auth`" in first

    def test_warning_level_for_warn_severity(self) -> None:
        result = _make_result(violations=_remediated_violations())
        out = format_github(result)
        warn_line = [ln for ln in out.splitlines() if ln.startswith("::warning")]
        assert len(warn_line) == 1
        # require rule has no file/line -> no file= param
        assert "file=" not in warn_line[0]

    def test_empty_result_is_empty_string(self) -> None:
        result = _make_result(violations=[])
        assert format_github(result) == ""

    def test_newlines_escaped(self) -> None:
        violations = [
            Violation(
                rule_name="r",
                rule_description="d",
                rule_type="cycle",
                severity="error",
                file_path=None,
                line_number=None,
                from_ref_id="a",
                to_ref_id="b",
                message="line1\nline2",
                remediation=None,
            )
        ]
        out = format_github(_make_result(violations=violations))
        assert "\n" not in out  # single logical line
        assert "%0A" in out

    def test_github_deterministic(self) -> None:
        result = _make_result(violations=_remediated_violations())
        assert format_github(result) == format_github(result)
