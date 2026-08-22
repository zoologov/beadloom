"""A ``forbid_import`` rule must be provably able to fire (BDL-061 S2 / BDL-UX #150).

Four of this repository's twelve rules printed ``0 violations`` for as long as they
existed, because their ``to:`` glob carried a ``src/`` prefix that the value it is matched
against never has: ``from:`` is matched against the repo-relative FILE PATH
(``src/beadloom/tui/app.py``), ``to:`` against the imported MODULE PATH with dots turned
into slashes (``beadloom/infrastructure/db``). The two are different vocabularies, and a
rule that mixes them up is silently inert — the S1 lesson (*a check that can never fail is
not a check*) inside the linter itself.

These tests pin the diagnosis, not the four corrected lines: a glob that matches nothing
in the whole index is REPORTED, and so is an exemption that suppresses nothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    ImportBoundaryRule,
    evaluate_import_boundary_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules import Violation

LIVENESS_KIND = "rule_liveness"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """An empty index with the full schema."""
    db = open_db(tmp_path / "test.db")
    create_schema(db)
    yield db  # type: ignore[misc]
    db.close()


def _add_import(conn: sqlite3.Connection, file_path: str, line: int, import_path: str) -> None:
    conn.execute(
        "INSERT INTO code_imports (file_path, line_number, import_path, file_hash) "
        "VALUES (?, ?, ?, ?)",
        (file_path, line, import_path, "h"),
    )


@pytest.fixture()
def indexed(conn: sqlite3.Connection) -> sqlite3.Connection:
    """An index holding the shape this repository has: ``src/``-rooted files, dotted imports."""
    _add_import(conn, "src/pkg/tui/app.py", 10, "pkg.application.graph_reads")
    _add_import(conn, "src/pkg/tui/data.py", 284, "pkg.infrastructure.git_activity")
    _add_import(conn, "src/pkg/onboarding/scan.py", 11, "pkg.infrastructure.atomic_io")
    return conn


def _liveness(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.rule_type == LIVENESS_KIND]


def _forbidden(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.rule_type == "forbid_import"]


# ---------------------------------------------------------------------------
# A glob that cannot match is reported
# ---------------------------------------------------------------------------


class TestDeadGlobIsDiagnosed:
    """A rule whose glob matches nothing across the whole index is named, not counted green."""

    def test_src_prefixed_to_glob_is_reported(self, indexed: sqlite3.Connection) -> None:
        """The exact defect: ``to: src/pkg/infrastructure/**`` can never match an import."""
        rule = ImportBoundaryRule(
            name="tui-no-direct-infra",
            description="TUI must not import infrastructure directly",
            from_glob="src/pkg/tui/**",
            to_glob="src/pkg/infrastructure/**",
        )

        findings = _liveness(evaluate_import_boundary_rules(indexed, [rule]))

        assert len(findings) == 1
        assert findings[0].rule_name == "tui-no-direct-infra"
        assert findings[0].severity == "warn"
        assert "to" in findings[0].message
        assert "src/pkg/infrastructure/**" in findings[0].message

    def test_dead_from_glob_is_reported(self, indexed: sqlite3.Connection) -> None:
        """A ``from:`` glob matching no indexed file is equally inert."""
        rule = ImportBoundaryRule(
            name="ghost-no-infra",
            description="A layer this project does not have",
            from_glob="src/pkg/ghost/**",
            to_glob="pkg/infrastructure/**",
        )

        findings = _liveness(evaluate_import_boundary_rules(indexed, [rule]))

        assert len(findings) == 1
        assert "from" in findings[0].message
        assert "src/pkg/ghost/**" in findings[0].message

    def test_both_sides_dead_is_one_finding_naming_both(
        self, indexed: sqlite3.Connection
    ) -> None:
        """One rule yields one finding; a wall of findings for one mistake helps nobody."""
        rule = ImportBoundaryRule(
            name="doubly-dead",
            description="Neither side exists",
            from_glob="src/pkg/ghost/**",
            to_glob="src/pkg/phantom/**",
        )

        findings = _liveness(evaluate_import_boundary_rules(indexed, [rule]))

        assert len(findings) == 1
        assert "src/pkg/ghost/**" in findings[0].message
        assert "src/pkg/phantom/**" in findings[0].message

    def test_a_live_rule_with_nothing_to_report_is_silent(
        self, indexed: sqlite3.Connection
    ) -> None:
        """Both globs match candidates, no import crosses the boundary: genuinely clean."""
        rule = ImportBoundaryRule(
            name="onboarding-no-git",
            description="Onboarding must not import git activity",
            from_glob="src/pkg/onboarding/**",
            to_glob="pkg/infrastructure/git_activity",
        )

        violations = evaluate_import_boundary_rules(indexed, [rule])

        assert violations == []

    def test_a_firing_rule_is_not_also_reported_as_dead(
        self, indexed: sqlite3.Connection
    ) -> None:
        """The corrected form fires on the real violation and produces no liveness noise."""
        rule = ImportBoundaryRule(
            name="tui-no-direct-infra",
            description="TUI must not import infrastructure directly",
            from_glob="src/pkg/tui/**",
            to_glob="pkg/infrastructure/**",
        )

        violations = evaluate_import_boundary_rules(indexed, [rule])

        assert _liveness(violations) == []
        assert len(_forbidden(violations)) == 1
        assert _forbidden(violations)[0].file_path == "src/pkg/tui/data.py"

    def test_each_dead_rule_is_reported_independently(
        self, indexed: sqlite3.Connection
    ) -> None:
        """A live neighbour does not vouch for a dead rule."""
        rules = [
            ImportBoundaryRule(
                name="live",
                description="live",
                from_glob="src/pkg/tui/**",
                to_glob="pkg/infrastructure/**",
            ),
            ImportBoundaryRule(
                name="dead",
                description="dead",
                from_glob="src/pkg/onboarding/**",
                to_glob="src/pkg/infrastructure/**",
            ),
        ]

        findings = _liveness(evaluate_import_boundary_rules(indexed, rules))

        assert [f.rule_name for f in findings] == ["dead"]

    def test_liveness_is_silent_when_the_index_holds_no_imports(
        self, conn: sqlite3.Connection
    ) -> None:
        """Nothing indexed is a different diagnosis (lint's header already says 0 scanned).

        Reporting every rule as dead against an empty index would fire on a fresh clone and
        on any project whose language Beadloom does not extract — noise that would teach
        adopters to ignore the finding that matters.
        """
        rule = ImportBoundaryRule(
            name="tui-no-direct-infra",
            description="TUI must not import infrastructure directly",
            from_glob="src/pkg/tui/**",
            to_glob="src/pkg/infrastructure/**",
        )

        assert evaluate_import_boundary_rules(conn, [rule]) == []

    def test_a_dead_error_rule_is_reported_as_warn(self, indexed: sqlite3.Connection) -> None:
        """An inert rule is a config smell, not a boundary breach.

        Severity is ``warn`` regardless of the rule's own severity so that upgrading
        Beadloom cannot turn an adopter's green pipeline red (BDL-061 CONTEXT constraint).
        """
        rule = ImportBoundaryRule(
            name="core-no-import-ai-agents",
            description="Core must not import ai_agents",
            from_glob="src/pkg/[!a]*/**",
            to_glob="src/pkg/ai_agents/**",
            severity="error",
        )

        findings = _liveness(evaluate_import_boundary_rules(indexed, [rule]))

        assert [f.severity for f in findings] == ["warn"]

    def test_the_finding_teaches_the_two_matching_vocabularies(
        self, indexed: sqlite3.Connection
    ) -> None:
        """The remediation must say what each side is matched against — that is the fix.

        Two engineers wrote ``src/``-prefixed ``to:`` globs into this repo's rules.yml; a
        matching form nobody can predict is the root cause, the four lines are a symptom.
        """
        rule = ImportBoundaryRule(
            name="tui-no-direct-infra",
            description="TUI must not import infrastructure directly",
            from_glob="src/pkg/tui/**",
            to_glob="src/pkg/infrastructure/**",
        )

        finding = _liveness(evaluate_import_boundary_rules(indexed, [rule]))[0]

        assert finding.remediation is not None
        assert "file path" in finding.remediation
        assert "import path" in finding.remediation
        assert "src/" in finding.remediation


# ---------------------------------------------------------------------------
# Exemptions: a named, expiring baseline instead of a weakened rule
# ---------------------------------------------------------------------------


class TestExemptions:
    """A pre-existing violation may be recorded, never silently tolerated."""

    def test_an_exemption_suppresses_only_what_it_names(
        self, indexed: sqlite3.Connection
    ) -> None:
        """The exempted import is not a violation; its neighbours still are."""
        from beadloom.graph.rule_engine import ImportExemption

        rule = ImportBoundaryRule(
            name="pkg-no-direct-infra",
            description="No direct infrastructure imports",
            from_glob="src/pkg/*/**",
            to_glob="pkg/infrastructure/**",
            exempt=(
                ImportExemption(
                    to_glob="pkg/infrastructure/atomic_io",
                    reason="every graph-YAML writer routes through it by design",
                    until="a repository seam exists (BDL-UX #150)",
                ),
            ),
        )

        violations = _forbidden(evaluate_import_boundary_rules(indexed, [rule]))

        assert [v.file_path for v in violations] == ["src/pkg/tui/data.py"]

    def test_an_exemption_can_narrow_by_source_too(self, indexed: sqlite3.Connection) -> None:
        """``from`` is optional and defaults to the rule's own scope."""
        from beadloom.graph.rule_engine import ImportExemption

        rule = ImportBoundaryRule(
            name="pkg-no-direct-infra",
            description="No direct infrastructure imports",
            from_glob="src/pkg/*/**",
            to_glob="pkg/infrastructure/**",
            exempt=(
                ImportExemption(
                    from_glob="src/pkg/tui/**",
                    to_glob="pkg/infrastructure/*",
                    reason="baselined",
                    until="BDL-UX #150",
                ),
            ),
        )

        violations = _forbidden(evaluate_import_boundary_rules(indexed, [rule]))

        assert [v.file_path for v in violations] == ["src/pkg/onboarding/scan.py"]

    def test_an_exemption_that_suppresses_nothing_is_reported(
        self, indexed: sqlite3.Connection
    ) -> None:
        """Its exit condition has been met — the finding is what says so."""
        from beadloom.graph.rule_engine import ImportExemption

        rule = ImportBoundaryRule(
            name="pkg-no-direct-infra",
            description="No direct infrastructure imports",
            from_glob="src/pkg/*/**",
            to_glob="pkg/infrastructure/**",
            exempt=(
                ImportExemption(
                    to_glob="pkg/infrastructure/health",
                    reason="was true in 2026-08",
                    until="the TUI reads health through the facade",
                ),
            ),
        )

        findings = _liveness(evaluate_import_boundary_rules(indexed, [rule]))

        assert len(findings) == 1
        assert "pkg/infrastructure/health" in findings[0].message
        assert findings[0].severity == "warn"

    def test_a_dead_rule_does_not_also_blame_its_exemptions(
        self, indexed: sqlite3.Connection
    ) -> None:
        """When the rule itself cannot match, its exemptions cannot be judged."""
        from beadloom.graph.rule_engine import ImportExemption

        rule = ImportBoundaryRule(
            name="pkg-no-direct-infra",
            description="No direct infrastructure imports",
            from_glob="src/pkg/*/**",
            to_glob="src/pkg/infrastructure/**",
            exempt=(
                ImportExemption(
                    to_glob="src/pkg/infrastructure/atomic_io",
                    reason="baselined",
                    until="BDL-UX #150",
                ),
            ),
        )

        findings = _liveness(evaluate_import_boundary_rules(indexed, [rule]))

        assert len(findings) == 1
        assert "to" in findings[0].message


class TestExemptionParsing:
    """An exclusion without a reason and an exit condition is a config error (CONTEXT)."""

    def _write(self, tmp_path: Path, exempt_block: str) -> Path:
        rules = tmp_path / "rules.yml"
        rules.write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: pkg-no-direct-infra\n"
            '    description: "no direct infra"\n'
            "    forbid_import:\n"
            '      from: "src/pkg/tui/**"\n'
            '      to: "pkg/infrastructure/**"\n' + exempt_block,
            encoding="utf-8",
        )
        return rules

    def test_exemption_is_parsed(self, tmp_path: Path) -> None:
        """A complete entry loads into the rule."""
        path = self._write(
            tmp_path,
            "      exempt:\n"
            '        - to: "pkg/infrastructure/atomic_io"\n'
            '          reason: "documented design"\n'
            '          until: "BDL-UX #150"\n',
        )

        rule = load_rules(path)[0]

        assert isinstance(rule, ImportBoundaryRule)
        assert len(rule.exempt) == 1
        assert rule.exempt[0].to_glob == "pkg/infrastructure/atomic_io"
        assert rule.exempt[0].reason == "documented design"
        assert rule.exempt[0].until == "BDL-UX #150"
        assert rule.exempt[0].from_glob == "*"

    def test_exemption_without_reason_is_rejected(self, tmp_path: Path) -> None:
        """An unnamed exclusion is how a gate gets quietly switched off."""
        path = self._write(
            tmp_path,
            "      exempt:\n"
            '        - to: "pkg/infrastructure/atomic_io"\n'
            '          until: "BDL-UX #150"\n',
        )

        with pytest.raises(ValueError, match="reason"):
            load_rules(path)

    def test_exemption_without_until_is_rejected(self, tmp_path: Path) -> None:
        """An exclusion with no exit condition is permanent by accident."""
        path = self._write(
            tmp_path,
            "      exempt:\n"
            '        - to: "pkg/infrastructure/atomic_io"\n'
            '          reason: "documented design"\n',
        )

        with pytest.raises(ValueError, match="until"):
            load_rules(path)

    def test_exemption_matching_neither_side_is_rejected(self, tmp_path: Path) -> None:
        """An entry with no ``from`` and no ``to`` would exempt the entire rule."""
        path = self._write(
            tmp_path,
            "      exempt:\n"
            '        - reason: "documented design"\n'
            '          until: "BDL-UX #150"\n',
        )

        with pytest.raises(ValueError, match=r"from.*to"):
            load_rules(path)


# ---------------------------------------------------------------------------
# This repository's own rules, against this repository's own imports
# ---------------------------------------------------------------------------


class TestBeadloomsOwnRules:
    """The suite reddens if a rule in ``.beadloom/_graph/rules.yml`` cannot fire.

    Built against a PRIVATE index (``index_imports`` into a temp database) rather than
    ``.beadloom/beadloom.db``, so the verdict does not depend on when anyone last
    reindexed — the failure mode this whole bead is about.
    """

    def _project_rules(self) -> list[ImportBoundaryRule]:
        root = Path(__file__).resolve().parents[1]
        rules = load_rules(root / ".beadloom" / "_graph" / "rules.yml")
        return [r for r in rules if isinstance(r, ImportBoundaryRule)]

    def _index(self, tmp_path: Path) -> sqlite3.Connection:
        from beadloom.graph.import_resolver import index_imports

        db = open_db(tmp_path / "own.db")
        create_schema(db)
        index_imports(Path(__file__).resolve().parents[1], db)
        return db

    def test_every_import_rule_can_fire(self, tmp_path: Path) -> None:
        """Both globs of every ``forbid_import`` rule match something that exists."""
        conn = self._index(tmp_path)
        try:
            findings = _liveness(evaluate_import_boundary_rules(conn, self._project_rules()))
        finally:
            conn.close()

        assert findings == [], "\n".join(f.message for f in findings)

    def test_the_import_boundaries_are_genuinely_clean(self, tmp_path: Path) -> None:
        """Green because no boundary is crossed — not because nothing was checked."""
        conn = self._index(tmp_path)
        try:
            violations = _forbidden(evaluate_import_boundary_rules(conn, self._project_rules()))
        finally:
            conn.close()

        assert violations == [], "\n".join(
            f"{v.file_path}:{v.line_number} {v.message}" for v in violations
        )


# ---------------------------------------------------------------------------
# What a `to:` glob covers
# ---------------------------------------------------------------------------


class TestWhatAToGlobCovers:
    """`from pkg.infra import db` is a crossing — the extractor records the PACKAGE.

    A Python `from X import Y` is indexed with ``import_path == X``, so the most
    common way to reach into a forbidden package produces the target
    ``pkg/infrastructure`` — which a glob written ``pkg/infrastructure/**`` did not
    match. Found while verifying this bead: the coordinator's own injected probe
    (`from beadloom.infrastructure import db` in `tui/app.py`) never fired under ANY
    of the glob forms tried, including the repaired one.
    """

    def test_importing_the_package_itself_is_caught(self, conn: sqlite3.Connection) -> None:
        """A `to:` glob covering a package covers a bare import of it."""
        _add_import(conn, "src/pkg/tui/app.py", 6, "pkg.infrastructure")
        rule = ImportBoundaryRule(
            name="tui-no-direct-infra",
            description="TUI must not import infrastructure directly",
            from_glob="src/pkg/tui/**",
            to_glob="pkg/infrastructure/**",
        )

        violations = _forbidden(evaluate_import_boundary_rules(conn, [rule]))

        assert [v.line_number for v in violations] == [6]

    def test_a_sibling_package_with_a_longer_name_is_not_caught(
        self, conn: sqlite3.Connection
    ) -> None:
        """`pkg/infrastructure/**` must not swallow `pkg.infrastructure_docs`."""
        _add_import(conn, "src/pkg/tui/app.py", 6, "pkg.infrastructure_docs")
        _add_import(conn, "src/pkg/tui/app.py", 7, "pkg.infrastructure.db")
        rule = ImportBoundaryRule(
            name="tui-no-direct-infra",
            description="TUI must not import infrastructure directly",
            from_glob="src/pkg/tui/**",
            to_glob="pkg/infrastructure/**",
        )

        violations = _forbidden(evaluate_import_boundary_rules(conn, [rule]))

        assert [v.line_number for v in violations] == [7]

    def test_an_exemption_covers_the_package_form_too(self, conn: sqlite3.Connection) -> None:
        """Both sides use one matching function — an exemption cannot be half-blind."""
        from beadloom.graph.rule_engine import ImportExemption

        _add_import(conn, "src/pkg/onboarding/scan.py", 11, "pkg.infrastructure")
        rule = ImportBoundaryRule(
            name="onboarding-no-direct-infra",
            description="Onboarding must not import infrastructure directly",
            from_glob="src/pkg/onboarding/**",
            to_glob="pkg/infrastructure/**",
            exempt=(
                ImportExemption(
                    to_glob="pkg/infrastructure/**",
                    reason="baselined",
                    until="BDL-UX #150 follow-up",
                ),
            ),
        )

        assert evaluate_import_boundary_rules(conn, [rule]) == []
