"""The debt report counts the rule engine's one `info` finding among its warnings.

BDL-083 S1b (``beadloom-q8x6``, BDL-UX #328; RFC D2) added the severity `info`: an
import rule whose `to:` glob can match an import and matches none today is stated live
with nothing to ban, and the linter counts that statement as neither an error nor a
warning. The debt collector counts every finding that is not an error as a warning, so
the same statement is a warning there. The bead's completion note names this as a
follow-up outside its layer; this file records it for the S1 review, measured on
2026-10-18 at `8ff8154a` on the monorepo fixture.

The collector reads its rules from `rules.yml` or `.beadloom/rules.yml` only, and the
fixture declares them in `.beadloom/_graph/rules.yml` (BDL-UX #291), so the test writes
the one rule where the collector looks. That is also why no score on this repository or
on the fixture has moved yet: the collector loads no rule on either.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.debt_report.collect import collect_debt_data
from beadloom.application.reindex import reindex
from beadloom.graph.rule_engine import evaluate_all, load_rules
from beadloom.infrastructure.db import open_db
from tests.support.monorepo_fixture import monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "FINDING BDL-083 S1b (beadloom-q8x6), for the S1 review: "
        "application/debt_report/collect.py counts any finding that is not an error "
        "as a warning, so the info statement of a live rule with nothing to ban is "
        "one warning in the debt report and none in lint. Measured 2026-10-18: 1"
    ),
)
def test_a_rule_stated_live_with_nothing_to_ban_adds_no_warning(project: Path) -> None:
    conn = open_db(project / ".beadloom" / "beadloom.db")
    try:
        data = collect_debt_data(conn, project)
    finally:
        conn.close()

    assert data.warning_count == 0


def test_the_one_warning_counted_is_the_info_statement(project: Path) -> None:
    """The red above is red for the reason it states: one finding, and it is at info."""
    conn = open_db(project / ".beadloom" / "beadloom.db")
    try:
        findings = evaluate_all(
            conn, load_rules(project / ".beadloom" / "rules.yml"), project_root=project
        )
        data = collect_debt_data(conn, project)
    finally:
        conn.close()

    assert [(f.rule_name, f.severity) for f in findings] == [
        ("domain-no-io-imports-digest-os", "info")
    ]
    assert (data.error_count, data.warning_count) == (0, 1)
