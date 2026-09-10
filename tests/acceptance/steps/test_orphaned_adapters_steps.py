"""Step implementations for `features/orphaned_adapters.feature` (BDL-068 S6).

Thin by design: every step scaffolds a real project with the real
``setup-agentic-flow`` command, edits ``flow.yml`` the way an adopter would, and
reads the findings the real ``check_config_drift`` returns. Nothing here builds
a manifest by hand except the two scenarios whose subject IS the manifest, so a
pass here is a statement about the command an adopter runs.

A finding is recognised by the marker :data:`ORPHAN_MARKER`, exported by the
derivation itself rather than spelled here, because a check that is matched by a
sentence is a check one rewording walks past.

The module is named ``test_*`` so default pytest collection picks the scenarios
up -- the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.onboarding.config_sync import check_config_drift
from beadloom.onboarding.flow_manifest import FLOW_MANIFEST_RELPATH, digest
from beadloom.onboarding.role_adapters import ORPHAN_MARKER
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.config_sync import ConfigDrift

scenarios("../features/orphaned_adapters.feature")

_HAND_EDIT = "\n## OUR TEAM RULE\n\nEvery pull request needs two reviewers.\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    root = tmp_path / "acme"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "acme"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return {"root": root}


def _scaffold(world: dict[str, Any], *tools: str) -> None:
    args = ["setup-agentic-flow", "--project", str(world["root"]), "--stack", "python"]
    for tool in tools:
        args += ["--tool", tool]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output


def _manifest(world: dict[str, Any]) -> dict[str, str]:
    path = world["root"] / FLOW_MANIFEST_RELPATH
    return dict(json.loads(path.read_text(encoding="utf-8"))["written"])


def _orphans(world: dict[str, Any]) -> list[ConfigDrift]:
    return [d for d in world["drifts"] if ORPHAN_MARKER in d.reason]


@given(parsers.parse("a project whose flow scaffolded claude and cursor"))
def _both_tools(world: dict[str, Any]) -> None:
    _scaffold(world, "claude", "cursor")


@given(parsers.parse("a project whose flow scaffolded claude only"))
def _claude_only(world: dict[str, Any]) -> None:
    _scaffold(world, "claude")


@given('a project with no flow.yml and a ".cursor/agents/dev.md" on disk')
def _no_flow_config(world: dict[str, Any]) -> None:
    path = world["root"] / ".cursor" / "agents" / "dev.md"
    path.parent.mkdir(parents=True)
    path.write_text("# dev\n", encoding="utf-8")


@given("cursor is removed from the flow's tools")
def _drop_cursor(world: dict[str, Any]) -> None:
    path = world["root"] / ".beadloom" / "flow.yml"
    text = path.read_text(encoding="utf-8")
    assert "- cursor\n" in text
    path.write_text(text.replace("- cursor\n", ""), encoding="utf-8")


@given(parsers.parse('"{relpath}" is edited by hand'))
def _edit(world: dict[str, Any], relpath: str) -> None:
    path = world["root"] / relpath
    path.write_text(path.read_text(encoding="utf-8") + _HAND_EDIT, encoding="utf-8")


@given(parsers.parse('a hand-authored "{relpath}" the manifest does not record'))
def _hand_authored(world: dict[str, Any], relpath: str) -> None:
    path = world["root"] / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# our own Cursor role\n", encoding="utf-8")
    assert relpath not in _manifest(world)


@given(parsers.parse('the manifest records "{relpath}" and the file exists'))
def _record_extra(world: dict[str, Any], relpath: str) -> None:
    path = world["root"] / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "# a role an earlier release composed\n"
    path.write_text(body, encoding="utf-8")
    manifest_path = world["root"] / FLOW_MANIFEST_RELPATH
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["written"][relpath] = digest(body)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given(parsers.parse('the ".cursor/agents" directory is deleted'))
def _delete_dir(world: dict[str, Any]) -> None:
    directory = world["root"] / ".cursor" / "agents"
    for child in directory.iterdir():
        child.unlink()
    directory.rmdir()


@when("the agent-config check runs")
def _run_check(world: dict[str, Any]) -> None:
    with sqlite3.connect(":memory:") as conn:
        world["drifts"] = check_config_drift(world["root"], conn)


@then(parsers.parse('"{relpath}" is reported as orphaned'))
def _reported(world: dict[str, Any], relpath: str) -> None:
    assert relpath in [d.file for d in _orphans(world)]


@then(parsers.parse('"{relpath}" is not reported as orphaned'))
def _not_reported(world: dict[str, Any], relpath: str) -> None:
    assert relpath not in [d.file for d in _orphans(world)]


@then(
    parsers.parse(
        "one orphan finding is reported for each role adapter the manifest "
        'records under "{directory}"'
    )
)
def _one_each(world: dict[str, Any], directory: str) -> None:
    recorded = {
        relpath
        for relpath in _manifest(world)
        if relpath.startswith(f"{directory}/") and relpath.endswith(".md")
    }
    assert recorded
    assert {d.file for d in _orphans(world)} == recorded


def _reason_for(world: dict[str, Any], relpath: str) -> str:
    reasons = [d.reason for d in _orphans(world) if d.file == relpath]
    assert reasons, f"no orphan finding for {relpath}"
    return reasons[0]


@then(
    parsers.parse('the finding for "{relpath}" says it already differs from what Beadloom wrote')
)
def _says_differs(world: dict[str, Any], relpath: str) -> None:
    assert "already differs" in _reason_for(world, relpath).lower()


@then(parsers.parse('the finding for "{relpath}" says nothing compares it any more'))
def _says_uncompared(world: dict[str, Any], relpath: str) -> None:
    reason = _reason_for(world, relpath)
    assert "already differs" not in reason.lower()
    assert ORPHAN_MARKER in reason


@then(parsers.parse('every orphan finding carries severity "{severity}"'))
def _severity(world: dict[str, Any], severity: str) -> None:
    findings = _orphans(world)
    assert findings
    assert all(d.severity == severity for d in findings)


@then("no orphan finding offers --fix as its remedy")
def _not_fixable(world: dict[str, Any]) -> None:
    findings = _orphans(world)
    assert findings
    assert all(not d.fixable for d in findings)


@then("the check does not exit non-zero because of them")
def _does_not_block(world: dict[str, Any]) -> None:
    assert not [d for d in _orphans(world) if d.severity == "error"]


@then("no orphan finding is reported")
def _none(world: dict[str, Any]) -> None:
    assert not _orphans(world), [d.file for d in _orphans(world)]
