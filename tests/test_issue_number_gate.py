"""BDL-068 S6, `beadloom-0mdo.66` — the issue-log step in the Gate.

The step BLOCKS, unlike its `docs-quality` neighbour, and the reason is stated
where it is asserted: a duplicate number is not a writing-standard opinion, it
is a reference that resolves to two different entries, and the repair is a
renumber the author can perform in the same commit. CONTEXT's rule is that no
check is added that cannot fail, so the tree on which this one goes red is
exercised here and was measured on this repository before #187 was repaired.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.gate import run_ci_gate
from beadloom.onboarding.scanner import generate_agents_md

if TYPE_CHECKING:
    from pathlib import Path


def _project(root: Path, *, log: str | None) -> None:
    (root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(root)
    if log is None:
        return
    (root / "log.md").write_text(log, encoding="utf-8")
    config = root / ".beadloom" / "config.yml"
    existing = config.read_text(encoding="utf-8") if config.is_file() else ""
    config.write_text(
        existing + "\nissue_log:\n  path: log.md\n  ledger: ledger\n", encoding="utf-8"
    )


def _step(root: Path, name: str = "issue-log"):  # type: ignore[no-untyped-def]
    result = run_ci_gate(root, fail_on=None, hub_exports=[], no_reindex=False)
    return next(step for step in result.steps if step.name == name), result


def test_a_project_that_declares_no_issue_log_skips_the_step(tmp_path: Path) -> None:
    """A skip that says why, never a silent pass — and never a red on upgrade."""
    _project(tmp_path, log=None)
    step, result = _step(tmp_path)
    assert step.skipped is True
    assert "no issue log" in step.summary.lower()
    assert result.ok is True


def test_a_duplicate_number_fails_the_gate(tmp_path: Path) -> None:
    _project(tmp_path, log="187. the open one\n\n187. the closed one\n")
    step, result = _step(tmp_path)
    assert step.passed is False
    assert result.ok is False
    assert [f["rule"] for f in step.findings] == ["duplicate-number"]
    assert step.findings[0]["severity"] == "error"


def test_a_declared_log_with_no_duplicate_passes_and_states_its_unread_legs(
    tmp_path: Path,
) -> None:
    _project(tmp_path, log="7. an entry\n")
    step, result = _step(tmp_path)
    assert step.passed is True
    assert step.not_verified is True, "the ledger is empty, so two legs entered no number"
    assert result.ok is True


def test_the_step_runs_directly_after_docs_quality(tmp_path: Path) -> None:
    """Placed with the document checks, before the composed-config ones."""
    _project(tmp_path, log="7. an entry\n")
    result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
    names = [step.name for step in result.steps]
    assert names.index("issue-log") == names.index("docs-quality") + 1


def test_the_gate_line_states_how_much_of_the_log_unclaimed_number_reached(
    tmp_path: Path,
) -> None:
    """BDL-068 S6, `beadloom-l9ee`.

    On this repository the line read `240 entr(ies) uniquely numbered; 5
    claim(s), floor 262` over a log whose 235 entries below the floor
    `unclaimed-number` never entered. The step still passes -- an unreached
    population is coverage, not a finding -- but the summary now says which
    population the pass is over.
    """
    _project(tmp_path, log="5. old\n\n6. older\n\n7. also old\n\n8. the first allocated\n")
    (tmp_path / "ledger").mkdir()
    (tmp_path / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    step, result = _step(tmp_path)
    assert step.passed is True
    assert result.ok is True
    assert "3 of 4" in step.summary
    assert "unclaimed-number" in step.summary


def test_the_gate_line_does_not_qualify_a_log_its_ledger_covers_whole(
    tmp_path: Path,
) -> None:
    """NOT VERIFIED RED, for the reason its command-side twin states.

    The clause it forbids did not exist before the commit that added it. It
    guards the noise case: a summary that qualifies every log, including the
    ones with nothing to qualify, is a summary a reader stops reading.
    """
    _project(tmp_path, log="8. the only entry\n")
    (tmp_path / "ledger").mkdir()
    (tmp_path / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    step, _ = _step(tmp_path)
    assert "below floor" not in step.summary
