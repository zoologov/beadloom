"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/integration/graph/rules/test_import_boundary_liveness.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    ImportBoundaryRule,
    evaluate_import_boundary_rules,
    load_rules,
)
from beadloom.infrastructure.db import create_schema, open_db
from tests.support.repository_root import REPO_ROOT
from tests.support.violation_kinds import (
    forbidden_of,
    liveness_of,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """An empty index with the full schema."""
    db = open_db(tmp_path / "test.db")
    create_schema(db)
    yield db  # type: ignore[misc]
    db.close()


class TestBeadloomsOwnRules:
    """The suite reddens if a rule in ``.beadloom/_graph/rules.yml`` cannot fire.

    Built against a PRIVATE index (``index_imports`` into a temp database) rather than
    ``.beadloom/beadloom.db``, so the verdict does not depend on when anyone last
    reindexed — the failure mode this whole bead is about.
    """

    def _project_rules(self) -> list[ImportBoundaryRule]:
        root = REPO_ROOT
        rules = load_rules(root / ".beadloom" / "_graph" / "rules.yml")
        return [r for r in rules if isinstance(r, ImportBoundaryRule)]

    def _index(self, tmp_path: Path) -> sqlite3.Connection:
        from beadloom.graph.import_resolver import index_imports

        db = open_db(tmp_path / "own.db")
        create_schema(db)
        index_imports(REPO_ROOT, db)
        return db

    def test_every_import_rule_can_fire(self, tmp_path: Path) -> None:
        """Both globs of every ``forbid_import`` rule match something that exists."""
        conn = self._index(tmp_path)
        try:
            findings = liveness_of(evaluate_import_boundary_rules(conn, self._project_rules()))
        finally:
            conn.close()

        assert findings == [], "\n".join(f.message for f in findings)

    def test_the_node_source_exemption_names_the_one_caller_its_reason_names(self) -> None:
        """An exemption's `from:` covers what its reason argues for, and nothing else.

        The entry for `beadloom/infrastructure/node_source` argues one caller —
        "doc_generator is the one caller that crosses". Left at the default `*`
        it also excuses a second onboarding caller nobody argued for, and the
        crossing would be suppressed with no finding to read (BDL-069 review,
        Minor 1).
        """
        exemptions = [
            exemption
            for rule in self._project_rules()
            if rule.name == "onboarding-no-direct-infra"
            for exemption in rule.exempt
            if exemption.to_glob == "beadloom/infrastructure/node_source"
        ]

        assert [e.from_glob for e in exemptions] == [
            "src/beadloom/onboarding/doc_generator.py"
        ]

    def test_the_import_boundaries_are_genuinely_clean(self, tmp_path: Path) -> None:
        """Green because no boundary is crossed — not because nothing was checked."""
        conn = self._index(tmp_path)
        try:
            violations = forbidden_of(evaluate_import_boundary_rules(conn, self._project_rules()))
        finally:
            conn.close()

        assert violations == [], "\n".join(
            f"{v.file_path}:{v.line_number} {v.message}" for v in violations
        )
