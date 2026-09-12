"""Step implementations for `features/stale_pairs_on_every_surface.feature`.

BDL-069 `beadloom-yn6i`. Every step runs the surface an adopter meets against the
repository `package_lacking_a_module` builds — one README paired with three code
files of its package, one of which the README no longer names — and compares the
surface's count with the pairs `sync-check --json` reports for the same tree.

Every count assertion first checks that pairs and documents differ on this tree.
Where they are equal a count of either passes for the other, and the scenario
would prove nothing about which one a surface counts.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from .package_lacking_a_module import build, run, stale_pairs

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/stale_pairs_on_every_surface.feature")

#: The heading `prime` lists stale pairs under; the list ends at the next heading.
PRIME_STALE_HEADING = "## Stale Pairs"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _pairs_outnumbering_documents(project: Path) -> list[dict[str, Any]]:
    """The stale pairs, once it is established that they outnumber their documents."""
    pairs = stale_pairs(project)
    documents = {pair["doc_path"] for pair in pairs}
    assert len(pairs) > len(documents), (pairs, documents)
    return pairs


@given("a git repository whose package document does not name one of its modules")
def _given_a_document_lacking_a_module(
    world: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world["project"] = build(tmp_path, monkeypatch)
    world["tmp_path"] = tmp_path


# --- prime --------------------------------------------------------------------


@when("beadloom prime is run on the repository")
def _when_prime(world: dict[str, Any]) -> None:
    # `prime` reads the verdicts the last check persisted, as it does for an
    # agent at session start after `beadloom ci` or `sync-check` has run.
    checked = run(world["project"], "sync-check")
    assert checked.exit_code == 2, checked.output
    result = run(world["project"], "prime")
    assert result.exit_code == 0, result.output
    world["prime"] = result.stdout


def _prime_stale_lines(world: dict[str, Any]) -> list[str]:
    lines = world["prime"].splitlines()
    assert PRIME_STALE_HEADING in lines, world["prime"]
    listed: list[str] = []
    for line in lines[lines.index(PRIME_STALE_HEADING) + 1 :]:
        if line.startswith("#"):
            break
        if line.startswith("- "):
            listed.append(line)
    return listed


@then("every stale line prime lists names the code file of its pair")
def _then_prime_lines_name_code_files(world: dict[str, Any]) -> None:
    pairs = _pairs_outnumbering_documents(world["project"])
    lines = _prime_stale_lines(world)
    assert len(lines) == len(pairs), (lines, pairs)
    for pair in pairs:
        label = f"{pair['doc_path']} <-> {pair['code_path']}"
        assert any(label in line for line in lines), (pair, lines)


@then("no two stale lines prime lists are the same")
def _then_prime_lines_are_distinct(world: dict[str, Any]) -> None:
    lines = _prime_stale_lines(world)
    assert len(lines) > 1, lines
    assert len(set(lines)) == len(lines), lines


@then("prime's health line counts stale pairs, as many as sync-check reports in JSON")
def _then_prime_health_counts_pairs(world: dict[str, Any]) -> None:
    pairs = _pairs_outnumbering_documents(world["project"])
    health = [line for line in world["prime"].splitlines() if line.startswith("Health:")]
    assert len(health) == 1, world["prime"]
    assert f"Health: {len(pairs)} stale pair(s)," in health[0], health[0]


# --- the site dashboard ----------------------------------------------------------


@when("the documentation site is generated for the repository")
def _when_docs_site(world: dict[str, Any]) -> None:
    # The dashboard reads the verdicts the last check persisted, as `ci` leaves them.
    checked = run(world["project"], "sync-check")
    assert checked.exit_code == 2, checked.output
    out = world["tmp_path"] / "site"
    result = run(world["project"], "docs", "site", "--out", str(out))
    assert result.exit_code == 0, result.output
    data = (out / "public" / "dashboard.data.json").read_text(encoding="utf-8")
    world["dashboard"] = json.loads(data)


@then("the dashboard's stale alert counts stale pairs, as many as sync-check reports in JSON")
def _then_alert_counts_pairs(world: dict[str, Any]) -> None:
    pairs = _pairs_outnumbering_documents(world["project"])
    alerts = [a for a in world["dashboard"]["alerts"] if a["kind"] == "stale_doc"]
    assert len(alerts) == 1, world["dashboard"]["alerts"]
    assert str(alerts[0]["message"]).startswith(f"{len(pairs)} stale pair(s)"), alerts[0]


# --- the terminal dashboard ------------------------------------------------------


@when("sync-check is run from the terminal dashboard")
def _when_tui_sync_check(world: dict[str, Any]) -> None:
    pytest.importorskip("textual", reason="the terminal dashboard needs the `tui` extra")
    from beadloom.tui.app import BeadloomApp
    from beadloom.tui.widgets.status_bar import StatusBarWidget

    project = world["project"]

    async def _press_sync_check() -> str:
        app = BeadloomApp(db_path=project / ".beadloom" / "beadloom.db", project_root=project)
        async with app.run_test() as pilot:
            await pilot.press("s")
            await pilot.pause()
            message = app.screen.query_one(StatusBarWidget).last_action
            await pilot.press("q")
        return message

    world["status_bar"] = asyncio.run(_press_sync_check())


@then("the status bar counts stale pairs, as many as sync-check reports in JSON")
def _then_status_bar_counts_pairs(world: dict[str, Any]) -> None:
    pairs = _pairs_outnumbering_documents(world["project"])
    assert world["status_bar"] == f"Sync: {len(pairs)} stale pair(s)", world["status_bar"]
