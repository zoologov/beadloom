"""Steps of `application/verdict-room/the_pipelines_the_census_reads_are_declared.feature`.

BDL-083 S2F1 (``beadloom-ba9w.22``), RFC D6 as amended on 2026-10-19. The monorepo fixture is
checked out as the adopter's clone, a GitHub workflow is written beside its GitLab pipeline,
and ``rooms`` runs through the CLI, so what the scenarios read is what an adopter reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.shipped_monorepo import shipped_monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/verdict-room/the_pipelines_the_census_reads_are_declared.feature")

_WORKFLOW = (
    "on: [push]\n"
    "jobs:\n"
    "  tests:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - run: uv sync --frozen\n"
)


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _rooms(root: Path, *flags: str) -> tuple[int, str]:
    result = CliRunner().invoke(main, ["rooms", *flags, "--project", str(root)])
    return result.exit_code, result.stdout


@given("the monorepo fixture checked out")
def _checked_out(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = shipped_monorepo_checkout(tmp_path)


@given("the checkout holds a GitHub workflow beside its GitLab pipeline")
def _github_workflow(state: dict[str, Any]) -> None:
    directory = state["root"] / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "ci.yml").write_text(_WORKFLOW, encoding="utf-8")


@given(parsers.parse('the checkout declares the pipelines "{pipelines}"'))
def _declares(state: dict[str, Any], pipelines: str) -> None:
    config = state["root"] / ".beadloom" / "config.yml"
    with config.open("a", encoding="utf-8") as handle:
        handle.write(f"rooms:\n  pipelines: {pipelines}\n")


@given("the checkout's GitLab pipeline removed")
def _no_gitlab(state: dict[str, Any]) -> None:
    (state["root"] / ".gitlab-ci.yml").unlink()


@when("the rooms are reported as JSON")
def _rooms_json(state: dict[str, Any]) -> None:
    code, out = _rooms(state["root"], "--json")
    assert code == 0, out
    state["rooms"] = json.loads(out)


@when("the rooms are reported as text")
def _rooms_text(state: dict[str, Any]) -> None:
    state["code"], state["text"] = _rooms(state["root"])


@then(parsers.parse('a declared room comes from "{source}"'))
def _room_source(state: dict[str, Any], source: str) -> None:
    sources = [room["source"] for room in state["rooms"]["declared"]]
    assert source in sources, sources


@then(parsers.parse('no declared room comes from "{prefix}"'))
def _no_room_from(state: dict[str, Any], prefix: str) -> None:
    sources = [room["source"] for room in state["rooms"]["declared"]]
    assert sources, state["rooms"]
    assert not [source for source in sources if source.startswith(prefix)], sources


@then(parsers.parse('an unresolved entry for "{source}" names "{words}"'))
def _unresolved_names(state: dict[str, Any], source: str, words: str) -> None:
    entries = [u for u in state["rooms"]["unresolved"] if u["source"] == source]
    assert len(entries) == 1, state["rooms"]["unresolved"]
    assert words in entries[0]["why"], entries[0]


@then("the command exits 0")
def _exits_clean(state: dict[str, Any]) -> None:
    assert state["code"] == 0, state["text"]


@then(parsers.parse('the room block says "{words}"'))
def _room_block(state: dict[str, Any], words: str) -> None:
    assert words in state["text"], state["text"]
