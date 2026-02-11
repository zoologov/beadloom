# beadloom:domain=context-oracle
"""Tests for beadloom.linter — Lint orchestrator: load rules, evaluate, format."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.db import create_schema, open_db
from beadloom.linter import (
    LintError,
    LintResult,
    format_json,
    format_porcelain,
    format_rich,
    lint,
)
from beadloom.rule_engine import Violation

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
        from beadloom.db import open_db as _open_db

        # First reindex to populate the DB with nodes, symbols, etc.
        result = lint(lint_project, reindex_before=True)
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
        result = lint(lint_project, reindex_before=False)
        assert result.rules_evaluated >= 1
        assert len(result.violations) >= 1
        assert any(v.rule_name == "billing-no-auth" for v in result.violations)
        assert result.elapsed_ms >= 0

    def test_lint_clean(self, clean_lint_project: Path) -> None:
        """Lint on a clean project returns 0 violations."""
        result = lint(clean_lint_project, reindex_before=True)
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
        result = lint(tmp_path, reindex_before=True)
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
            lint(tmp_path, reindex_before=True)

    def test_lint_reindex_before_false(
        self, lint_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """reindex_before=False skips reindex call."""
        reindex_called = False
        original_incremental = None

        # First do a real reindex so the DB exists
        lint(lint_project, reindex_before=True)

        import beadloom.linter as linter_mod

        original_incremental = linter_mod.incremental_reindex

        def mock_reindex(project_root: Path) -> None:
            nonlocal reindex_called
            reindex_called = True
            return original_incremental(project_root)

        monkeypatch.setattr(linter_mod, "incremental_reindex", mock_reindex)

        result = lint(lint_project, reindex_before=False)
        assert not reindex_called
        # Should still produce a valid result from the already-existing DB
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
        result = lint(lint_project, rules_path=custom_rules, reindex_before=True)
        assert result.rules_evaluated == 1
        # No services in this project, so no require violations
        assert len(result.violations) == 0

    def test_lint_counts_files_and_imports(self, lint_project: Path) -> None:
        """lint() correctly reports files_scanned and imports_resolved counts.

        After reindex, inject import records so the lint counts are non-zero.
        The current reindex does not populate code_imports, so we inject
        records manually (same pattern as test_lint_with_violations).
        """
        from beadloom.db import open_db as _open_db

        # First lint to create the DB
        lint(lint_project, reindex_before=True)

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
        result = lint(lint_project, reindex_before=False)
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
        assert "2 violations found" in output
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
        parts = lines[0].split(":")
        assert len(parts) == 6
        assert parts[0] in ("billing-auth-boundary", "all-services-need-domain")

        # Find the require violation line (no file_path)
        require_line = [line for line in lines if "require" in line]
        assert len(require_line) == 1
        rparts = require_line[0].split(":")
        assert rparts[1] == "require"
        # file_path and line_number should be empty
        assert rparts[2] == ""
        assert rparts[3] == ""

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
                file_path=None,
                line_number=None,
                from_ref_id="notifications",
                to_ref_id=None,
                message="Node has no domain edge",
            ),
        ]
        result = _make_result(violations=violations, rules_evaluated=1)
        output = format_porcelain(result)
        parts = output.strip().split(":")
        assert parts[0] == "svc-needs-domain"
        assert parts[1] == "require"
        assert parts[2] == ""  # file_path
        assert parts[3] == ""  # line_number
        assert parts[4] == "notifications"  # from_ref_id
        assert parts[5] == ""  # to_ref_id
