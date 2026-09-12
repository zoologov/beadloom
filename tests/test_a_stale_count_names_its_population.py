"""Every surface that counts stale PAIRS says pairs (BDL-069 `beadloom-yn6i`).

A pair is a document AND a code file, so three files of one package give three
stale pairs over one README. `beadloom-h7b3` changed the Gate's summary to
`N stale pair(s)` and made every `sync-check` line name its code file. Measured
before this bead on a foreign repository with one README over three stale pairs:
the terminal dashboard said `Sync: 3 stale doc(s)`, the site dashboard's alert said
`3 stale doc(s)`, and `prime` said `Health: 3 stale docs` above three identical
lines `- domains/ledger/README.md (ledger)`.

Each surface keeps its count of pairs and changes its noun, because each shows a
number another surface already shows as pairs. `prime`'s lines render the pair the
way `sync-check` does, so a line of the preview maps to one line of the full list
it points to.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application.site_dashboard import _build_alerts
from beadloom.onboarding.scanner.prime import (
    MAX_LISTED_FINDINGS,
    _format_prime_json,
    _format_prime_markdown,
)

if TYPE_CHECKING:
    from pathlib import Path

#: One document paired with three code files, as `prime_context` reads the rows.
DOCUMENT = "domains/ledger/README.md"
CODE_FILES = ("src/ledger/__init__.py", "src/ledger/core.py", "src/ledger/journal.py")


def _stale_rows(code_files: tuple[str, ...] = CODE_FILES) -> list[dict[str, str]]:
    return [
        {"doc_path": DOCUMENT, "code_path": code_path, "ref_id": "ledger"}
        for code_path in code_files
    ]


def _dynamic(stale: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "kind_counts": {"domain": 2},
        "symbols": 3,
        "domains": [],
        "stale_docs": stale,
        "violations": [],
        "last_reindex": "2026-09-11T00:00:00+00:00",
    }


def _stale_section(text: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index("## Stale Pairs") + 1
    listed: list[str] = []
    for line in lines[start:]:
        if line.startswith("#"):
            break
        if line.startswith("- "):
            listed.append(line)
    return listed


class TestPrimeListsPairs:
    def test_each_line_names_the_code_file_of_its_pair(self) -> None:
        text = _format_prime_markdown("myapp", [], _dynamic(_stale_rows()))
        assert _stale_section(text) == [
            f"- {DOCUMENT} <-> {code_path} (ledger)" for code_path in CODE_FILES
        ]

    def test_three_pairs_over_one_document_are_three_different_lines(self) -> None:
        lines = _stale_section(_format_prime_markdown("myapp", [], _dynamic(_stale_rows())))
        assert len(lines) == len(CODE_FILES)
        assert len(set(lines)) == len(lines)

    def test_the_health_line_counts_pairs_and_says_pairs(self) -> None:
        text = _format_prime_markdown("myapp", [], _dynamic(_stale_rows()))
        assert "Health: 3 stale pair(s), 0 lint violations" in text
        assert "stale docs," not in text

    def test_a_row_without_a_code_file_prints_the_document_alone(self) -> None:
        row = {"doc_path": DOCUMENT, "ref_id": "ledger"}
        lines = _stale_section(_format_prime_markdown("myapp", [], _dynamic([row])))
        assert lines == [f"- {DOCUMENT} (ledger)"]

    def test_a_cut_list_names_what_it_did_not_show_as_pairs(self) -> None:
        many = tuple(f"src/ledger/m{i}.py" for i in range(MAX_LISTED_FINDINGS + 2))
        text = _format_prime_markdown("myapp", [], _dynamic(_stale_rows(many)))
        assert "- ... and 2 more stale pair(s) — run `beadloom sync-check`" in text

    def test_no_stale_pair_still_prints_the_section(self) -> None:
        text = _format_prime_markdown("myapp", [], _dynamic([]))
        lines = text.splitlines()
        assert lines[lines.index("## Stale Pairs") + 1] == "(none)"

    def test_the_json_shape_is_untouched(self) -> None:
        """`--json` and the MCP `prime` tool already carry the code file under this key."""
        payload = _format_prime_json("myapp", "0.0.0", [], _dynamic(_stale_rows()))
        assert payload["health"]["stale_docs"] == _stale_rows()


class TestTheDashboardAlertCountsPairs:
    def test_the_stale_alert_says_pairs(self) -> None:
        alerts = _build_alerts(
            lint_data={"errors": 0},
            debt_data={},
            docs_data={"stale": 3},
            doctor_data={"errors": 0},
            federated_payload=None,
        )
        assert [a["message"] for a in alerts] == [
            "3 stale pair(s) — refresh and re-run `beadloom sync-check`"
        ]

    def test_the_alert_kind_is_untouched(self) -> None:
        """`kind` is a key the front-end and `status_cards` readers may select on."""
        alerts = _build_alerts(
            lint_data={},
            debt_data={},
            docs_data={"stale": 1},
            doctor_data={},
            federated_payload=None,
        )
        assert [a["kind"] for a in alerts] == ["stale_doc"]


class TestTheTerminalDashboardCountsPairs:
    def test_the_sync_check_notification_says_pairs(self, tmp_path: Path) -> None:
        pytest.importorskip("textual", reason="the terminal dashboard needs the `tui` extra")
        from beadloom.infrastructure.db import create_schema, open_db
        from beadloom.tui.app import BeadloomApp
        from beadloom.tui.data_providers import SyncDataProvider
        from beadloom.tui.widgets.status_bar import StatusBarWidget

        class ThreeStalePairs(SyncDataProvider):
            """A provider whose count is known, so the message is the only variable."""

            def refresh(self) -> None:
                return None

            def get_stale_count(self) -> int:
                return 3

        db_path = tmp_path / ".beadloom" / "beadloom.db"
        db_path.parent.mkdir(parents=True)
        conn = open_db(db_path)
        create_schema(conn)

        async def _run() -> str:
            app = BeadloomApp(db_path=db_path, project_root=tmp_path)
            async with app.run_test() as pilot:
                app.sync_provider = ThreeStalePairs(conn=conn, project_root=tmp_path)
                app.action_sync_check()
                await pilot.pause()
                message = app.screen.query_one(StatusBarWidget).last_action
                await pilot.press("q")
            return message

        try:
            assert asyncio.run(_run()) == "Sync: 3 stale pair(s)"
        finally:
            conn.close()
