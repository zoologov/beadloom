"""The debt report counts the rule engine's `info` finding as neither an error nor a warning.

BDL-083 S1b (``beadloom-q8x6``, BDL-UX #328; RFC D2) added the severity `info`: an
import rule whose `to:` glob can match an import and matches none today is stated live
with nothing to ban, and the linter counts that statement as neither an error nor a
warning. Until BDL-083 S1 fix 2 (``beadloom-ilrn``, S1R Major 2) the debt collector
counted every finding that was not an error as a warning, so the same statement was one
warning in the debt score: measured 1 on 2026-10-18 at ``8ff8154a`` on the monorepo
fixture, where 0 is the count lint gives.

The collector reads its rules from `rules.yml` or `.beadloom/rules.yml` only, and the
fixture declares them in `.beadloom/_graph/rules.yml` (BDL-UX #291), so the test writes
the one rule where the collector looks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.debt_report.collect import collect_debt_data
from beadloom.application.reindex import reindex
from beadloom.graph.rule_engine import INFO_SEVERITY, evaluate_all, load_rules
from beadloom.infrastructure.db import open_db
from tests.support.monorepo_fixture import monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.debt_report.models import DebtData

#: The fixture's own `forbid_import` rule, alone, where the debt collector reads rules.
_RULES = """\
version: 3
rules:
  - name: domain-no-io-imports-digest-os
    description: "The digest domain does no I/O: it imports nothing of os"
    forbid_import:
      from: "backend/src/digest/**"
      to: "os/**"
"""


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = monorepo_checkout(tmp_path)
    reindex(root)
    (root / ".beadloom" / "rules.yml").write_text(_RULES, encoding="utf-8")
    return root


def _debt(project: Path) -> DebtData:
    conn = open_db(project / ".beadloom" / "beadloom.db")
    try:
        return collect_debt_data(conn, project)
    finally:
        conn.close()


def test_the_rule_engine_states_the_rule_at_info(project: Path) -> None:
    """The population the counts below are taken over: one finding, and it is at info."""
    conn = open_db(project / ".beadloom" / "beadloom.db")
    try:
        findings = evaluate_all(
            conn, load_rules(project / ".beadloom" / "rules.yml"), project_root=project
        )
    finally:
        conn.close()

    assert [(f.rule_name, f.severity) for f in findings] == [
        ("domain-no-io-imports-digest-os", INFO_SEVERITY)
    ]


def test_an_info_statement_adds_neither_an_error_nor_a_warning(project: Path) -> None:
    data = _debt(project)

    assert (data.error_count, data.warning_count) == (0, 0)
