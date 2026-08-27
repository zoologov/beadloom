"""An excused pair says it was excused, in every count that names the others.

BDL-061 S5, bead `beadloom-mr2l.76` (finding BDL-061.18-5). The `exempt` verdict
was in no arithmetic any surface prints: `_sync_summary` counted `ok` as fresh
and `stale`/`missing` as failures and passed over `exempt` entirely; the
`sync-check --json` summary carried total, ok, stale, missing, unverified,
unchecked, surface_drift and declared_docs and had no `exempt` key; the human
output never contained the word, because an exempt row fell through to the
`[ok]` marker.

Measured by `.18` in a clean room with one WORKING document declared: 341 pairs =
326 ok + 11 exempt + 4 incomplete, printed as *total 341, ok 326, stale 0,
missing 0, unverified 0, unchecked 0*. The gate line read *326 pair(s) fresh*
where the same tree without the declaration read 326 of 330 — the count fell by
the pairs that were excused and nothing said so.

That is the shape `_sync_summary`'s own docstring was written against: a bare
`N pair(s) fresh` was true of a run in which six pairs had just been deleted
(BDL-UX #174) and of a run that could not detect staleness at all (#175). A
verdict added after that docstring reintroduced it. Unverifiable, excused and
clean are three states and must not print one word.

`incomplete` is counted here too, and for the same reason rather than as a bonus:
the verdicts have to sum to the total, and they cannot while any verdict has no
key. The sync-check SPEC stated that gap honestly and it is now closed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import _sync_summary
from beadloom.doc_sync.engine import (
    REASON_WORKING_SPACE,
    STATUS_EXEMPT,
    STATUS_INCOMPLETE,
    STATUS_OK,
)
from beadloom.doc_sync.surface_ledger import SurfaceVerdict
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_REASON = "an ACTIVE document records progress, not what the code is"


def _rows(*, ok: int = 0, exempt: int = 0, stale: int = 0) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {"status": STATUS_OK, "doc_path": f"ok-{i}.md"} for i in range(ok)
    ]
    rows += [
        {
            "status": STATUS_EXEMPT,
            "doc_path": f"ACTIVE-{i}.md",
            "reason": REASON_WORKING_SPACE,
            "details": _REASON,
        }
        for i in range(exempt)
    ]
    rows += [
        {"status": "stale", "doc_path": f"stale-{i}.md", "reason": "hash_changed"}
        for i in range(stale)
    ]
    return rows


def _clean() -> SurfaceVerdict:
    return SurfaceVerdict(True, False, "")


class TestTheGateLineCountsWhatItExcused:
    """`_sync_summary`'s promise: how many were checked, how many could not be."""

    def test_the_line_states_the_pairs_it_excused(self) -> None:
        line = _sync_summary(_rows(ok=5, exempt=6), [], _clean())

        assert "6 exempt" in line

    def test_it_states_the_reason_the_exemption_was_declared_with(self) -> None:
        """A skip always says why, and the row already carries the declaration."""
        line = _sync_summary(_rows(ok=5, exempt=6), [], _clean())

        assert _REASON in line

    def test_a_failing_run_still_says_what_it_excused(self) -> None:
        """The count that fell is exactly what a failing run must not hide."""
        line = _sync_summary(_rows(ok=5, exempt=6, stale=2), [], _clean())

        assert "2 stale doc(s)" in line
        assert "6 exempt" in line

    def test_a_run_that_excused_nothing_keeps_its_line(self) -> None:
        """The control: the everyday line is not made longer for everybody."""
        line = _sync_summary(_rows(ok=5), [], _clean())

        assert line == "5 pair(s) fresh"

    def test_a_row_with_no_declared_reason_still_counts(self) -> None:
        """A missing reason is a config error elsewhere, not a reason to hide."""
        rows: list[dict[str, object]] = [
            {"status": STATUS_EXEMPT, "doc_path": "ACTIVE.md", "reason": REASON_WORKING_SPACE}
        ]

        line = _sync_summary(rows, [], _clean())

        assert "1 exempt" in line


def _project(tmp_path: Path, *, doc: str) -> Path:
    """One node whose declared document is paired with code, indexed."""
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "billing.py").write_text(
        "def charge() -> None:\n    return None\n", encoding="utf-8"
    )
    path = tmp_path / "docs" / doc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# billing\n", encoding="utf-8")
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(tmp_path / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("billing", "component", "billing", "src/billing.py"),
    )
    conn.execute(
        "INSERT INTO declared_docs (declared_path, doc_path, ref_id) VALUES (?, ?, ?)",
        (f"docs/{doc}", doc, "billing"),
    )
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc, "src/billing.py", "billing", "baseline", "baseline", "2026-01-01", "ok"),
    )
    conn.commit()
    conn.close()
    return tmp_path


class TestTheJsonAccountsForEveryPairItCounted:
    """`#148`'s surface: a caller reads exit codes and JSON, never lines."""

    @staticmethod
    def _summary(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
        from beadloom.services.cli import main

        monkeypatch.chdir(root)
        result = CliRunner().invoke(main, ["sync-check", "--json"])
        return dict(json.loads(result.stdout)["summary"])

    def test_the_verdicts_sum_to_the_total(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        summary = self._summary(_project(tmp_path, doc="ACTIVE.md"), monkeypatch)

        assert summary["total"] == sum(
            summary[key]
            for key in ("ok", "stale", "missing", "unverified", "exempt", "incomplete")
        )

    def test_the_excused_pair_is_the_one_it_counts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        summary = self._summary(_project(tmp_path, doc="ACTIVE.md"), monkeypatch)

        assert summary["exempt"] == 1
        assert summary["ok"] == 0

    def test_a_pair_that_was_checked_is_not_counted_as_excused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The control: the new key does not absorb the verdicts beside it.

        The same fixture under a name of no declared kind is compared against
        its stored baseline and found stale, which is the outcome an exemption
        was hiding.
        """
        summary = self._summary(_project(tmp_path, doc="billing.md"), monkeypatch)

        assert summary["exempt"] == 0
        assert summary["stale"] == 1


class TestTheHumanOutputSaysTheWord:
    """Three states, three words. An exempt row printed `[ok]`."""

    def test_the_row_is_marked_exempt_rather_than_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beadloom.services.cli import main

        monkeypatch.chdir(_project(tmp_path, doc="ACTIVE.md"))
        result = CliRunner().invoke(main, ["sync-check"])

        assert "[exempt]" in result.output
        assert "[ok]" not in result.output

    def test_the_row_states_the_declared_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beadloom.services.cli import main

        monkeypatch.chdir(_project(tmp_path, doc="ACTIVE.md"))
        result = CliRunner().invoke(main, ["sync-check"])

        assert "records progress" in result.output

    def test_the_porcelain_line_carries_the_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beadloom.services.cli import main

        monkeypatch.chdir(_project(tmp_path, doc="ACTIVE.md"))
        result = CliRunner().invoke(main, ["sync-check", "--porcelain"])

        assert result.output.startswith(f"{STATUS_EXEMPT}\t")


class TestExcusedIsNotFailed:
    """The verdict stays non-blocking; only its visibility changed."""

    def test_the_exit_code_is_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from beadloom.services.cli import main

        monkeypatch.chdir(_project(tmp_path, doc="ACTIVE.md"))
        result = CliRunner().invoke(main, ["sync-check"])

        assert result.exit_code == 0

    def test_an_incomplete_pair_is_counted_without_becoming_a_failure(self) -> None:
        rows: list[dict[str, object]] = [
            {"status": STATUS_INCOMPLETE, "doc_path": "a.md", "reason": "missing_sections"}
        ]

        line = _sync_summary(rows, [], _clean())

        assert "0 pair(s) fresh" in line
