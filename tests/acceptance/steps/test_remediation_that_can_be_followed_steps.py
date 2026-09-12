"""Step implementations for `features/remediation_that_can_be_followed.feature`.

BDL-069 S1 (`beadloom-h7b3`), the second half of BDL-UX #282. Every step runs the
real command against a git repository built in a temporary directory: `init`
writes the documents, one module's name is taken back out of one of them, and the
commands under test are the ones an adopter would type next.

The repository is built by `package_lacking_a_module`, which the steps of
`beadloom-yn6i` share because they state their Given in the same words. The
package holds three code files, so its document is paired three times.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from .package_lacking_a_module import DOC_PATH, MODULE_REMOVED, build, run, stale_pairs

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/remediation_that_can_be_followed.feature")


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


@given("a git repository whose package document does not name one of its modules")
def _given_a_document_lacking_a_module(
    world: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world["project"] = build(tmp_path, monkeypatch)


def _run(world: dict[str, Any], *args: str) -> Any:
    return run(world["project"], *args)


def _gate(world: dict[str, Any]) -> dict[str, Any]:
    result = _run(world, "ci", "--format", "json")
    # `.stdout`, not `.output`: Click merges stderr into `.output`, and a notice
    # written there would turn a correct report into a JSON decode error.
    report: dict[str, Any] = json.loads(result.stdout)
    report["exit_code"] = result.exit_code
    return report


def _sync_step(report: dict[str, Any]) -> dict[str, Any]:
    steps = [step for step in report["steps"] if step["name"] == "sync-check"]
    assert len(steps) == 1, report["steps"]
    return steps[0]


def _findings_about_the_document(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        finding
        for finding in _sync_step(report)["findings"]
        if {"file": DOC_PATH} in finding.get("locations", [])
    ]


def _stale_pairs(world: dict[str, Any]) -> list[dict[str, Any]]:
    return stale_pairs(world["project"])


@when("beadloom ci is run on the repository")
def _when_ci(world: dict[str, Any]) -> None:
    world["ci"] = _gate(world)


@when("the document is revised the way the gate's remediation says")
def _when_the_remediation_is_followed(world: dict[str, Any]) -> None:
    findings = _findings_about_the_document(world["ci"])
    assert findings, _sync_step(world["ci"])
    remediations = {finding["remediation"] for finding in findings}
    # Following the instruction means doing what it says and nothing else, so it
    # has to say both what to write and where to write it.
    for remediation in remediations:
        assert MODULE_REMOVED in remediation, remediation
        assert DOC_PATH in remediation, remediation
    readme = world["project"] / "docs" / DOC_PATH
    with readme.open("a", encoding="utf-8") as handle:
        handle.write(f"- `{MODULE_REMOVED}.py`\n")


@when("beadloom sync-update is run for every stale ref without prompts")
def _when_sync_update_all(world: dict[str, Any]) -> None:
    world["sync_update"] = _run(world, "sync-update", "--yes", "--all")


@when("beadloom sync-check is run on the repository")
def _when_sync_check(world: dict[str, Any]) -> None:
    world["sync_check"] = _run(world, "sync-check")


@then("the gate does not exit 0")
def _then_the_gate_is_red(world: dict[str, Any]) -> None:
    assert world["ci"]["exit_code"] != 0, _sync_step(world["ci"])


@then("the gate exits 0")
def _then_the_gate_is_green(world: dict[str, Any]) -> None:
    assert world["ci"]["exit_code"] == 0, _sync_step(world["ci"])


@then("no finding about that document tells the reader to re-attest it")
def _then_no_reattest_instruction(world: dict[str, Any]) -> None:
    findings = _findings_about_the_document(world["ci"])
    assert findings, _sync_step(world["ci"])
    for finding in findings:
        assert "sync-update" not in finding["remediation"], finding


@then("every finding about that document names the module the document lacks")
def _then_findings_name_the_module(world: dict[str, Any]) -> None:
    findings = _findings_about_the_document(world["ci"])
    assert findings, _sync_step(world["ci"])
    for finding in findings:
        assert MODULE_REMOVED in finding["why"], finding
        assert MODULE_REMOVED in finding["remediation"], finding


@then("the command exits 0")
def _then_sync_update_exits_zero(world: dict[str, Any]) -> None:
    result = world["sync_update"]
    assert result.exit_code == 0, result.output


@then("its output names every pair the freshness check still reports stale")
def _then_sync_update_names_what_it_left(world: dict[str, Any]) -> None:
    output = world["sync_update"].output
    left = _stale_pairs(world)
    # Anti-vacuity, and the measurement that makes the output worth reading: the
    # verdict did not move, so there is a population for the report to name.
    assert len(left) > 1, left
    for pair in left:
        assert f"{pair['doc_path']} <-> {pair['code_path']}" in output, (pair, output)


@then("its output says re-attesting cannot clear the reason those pairs are stale")
def _then_sync_update_says_why(world: dict[str, Any]) -> None:
    output = world["sync_update"].output
    assert "re-attesting cannot clear missing_modules" in output, output


@then("every stale line names the code file of its pair")
def _then_each_line_names_its_code_file(world: dict[str, Any]) -> None:
    lines = [ln for ln in world["sync_check"].output.splitlines() if "[stale]" in ln]
    stale = _stale_pairs(world)
    assert len(stale) > 1, stale
    assert len(lines) == len(stale), (lines, stale)
    for pair in stale:
        assert any(f"{pair['doc_path']} <-> {pair['code_path']}" in line for line in lines), (
            pair,
            lines,
        )


@then("no two stale lines are the same")
def _then_lines_are_distinct(world: dict[str, Any]) -> None:
    lines = [ln for ln in world["sync_check"].output.splitlines() if "[stale]" in ln]
    assert len(lines) > 1, lines
    assert len(set(lines)) == len(lines), lines


@then("the gate's summary counts stale pairs, as many as sync-check reports in JSON")
def _then_summary_counts_pairs(world: dict[str, Any]) -> None:
    stale = _stale_pairs(world)
    documents = {pair["doc_path"] for pair in stale}
    # The count is only informative when pairs and documents differ.
    assert len(stale) > len(documents), (stale, documents)
    summary = _sync_step(_gate(world))["summary"]
    assert summary.startswith(f"{len(stale)} stale pair(s)"), summary
