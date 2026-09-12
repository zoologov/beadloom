"""BDL-069 S4, `beadloom-dibq` — the `readme-pair` step in the Gate.

The leg holds a project's DECLARED document pairs against each other and blocks
when their shapes diverge. It is modelled on `issue-log`, the step beside it,
and the modelling is the point: a project that declares no pair is a NAMED skip,
so the upgrade that ships this step turns nobody's green tree red. That is the
binding constraint of the epic and the first thing asserted here.

What the leg adds over the comparison it calls is the POPULATION in its line.
`check_document_pairs` answers whether the shapes agree; a gate step that says
only `0 finding(s)` is a green that could mean two pairs agreed or that a typo
in the declaration left nothing to compare. So the line names the pairs it held
and the blocks it compared, and the tests below read those numbers rather than
the verdict alone.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from beadloom.application.gate import run_ci_gate
from beadloom.onboarding.scanner import generate_agents_md

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from beadloom.application.gate import GateResult, GateStep

#: A three-block document: one heading and two paragraphs.
SOURCE = "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n"
#: Its follower, in the other language, block for block.
FOLLOWER = "# Zagolovok\n\nPervyi abzats.\n\nVtoroi abzats.\n"
#: The same follower with the second paragraph gone — the 2026-09-10 shape.
FOLLOWER_SHORT = "# Zagolovok\n\nPervyi abzats.\n"


def _project(root: Path, *, declaration: str | None) -> None:
    """A project whose every other gate step passes, declaring *declaration* or nothing."""
    (root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(root)
    if declaration is None:
        return
    config = root / ".beadloom" / "config.yml"
    existing = config.read_text(encoding="utf-8") if config.is_file() else ""
    config.write_text(existing + declaration, encoding="utf-8")


def _declare(*pairs: tuple[str, str]) -> str:
    entries = "".join(f"  - source: {s}\n    follower: {f}\n" for s, f in pairs)
    return "\ndocument_pairs:\n" + entries


def _pair(root: Path, source: str, follower: str, *, name: str = "README") -> None:
    (root / f"{name}.md").write_text(source, encoding="utf-8")
    (root / f"{name}.ru.md").write_text(follower, encoding="utf-8")


def _step(root: Path, name: str = "readme-pair") -> tuple[GateStep, GateResult]:
    result = run_ci_gate(root, fail_on=None, hub_exports=[], no_reindex=False)
    return next(step for step in result.steps if step.name == name), result


# ---------------------------------------------------------------------------
# The constraint: no adopter's Gate changes verdict on upgrade
# ---------------------------------------------------------------------------


def test_a_project_that_declares_no_pair_skips_the_step(tmp_path: Path) -> None:
    """A skip that says why, never a silent pass — and never a red on upgrade."""
    _project(tmp_path, declaration=None)
    step, result = _step(tmp_path)
    assert step.skipped is True
    assert step.status == "SKIP"
    assert "no document pair" in step.summary.lower()
    assert "document_pairs" in step.summary
    assert step.findings == []
    assert result.ok is True


@pytest.mark.parametrize(
    ("label", "declaration"),
    [
        ("a config declaring other things", "\ndocs_audit:\n  ignore: []\n"),
        ("an empty list", "\ndocument_pairs: []\n"),
        ("a key with no entries", "\ndocument_pairs:\n"),
    ],
)
def test_a_config_that_names_no_pair_leaves_the_verdict_where_it_was(
    tmp_path: Path, label: str, declaration: str
) -> None:
    """Three shapes an adopter's existing config can have; none of them is judged."""
    _project(tmp_path, declaration=declaration)
    step, result = _step(tmp_path)
    assert step.skipped is True, label
    assert result.ok is True, label


# ---------------------------------------------------------------------------
# The leg itself
# ---------------------------------------------------------------------------


def test_a_declared_pair_that_corresponds_passes_and_names_its_population(
    tmp_path: Path,
) -> None:
    _pair(tmp_path, SOURCE, FOLLOWER)
    _project(tmp_path, declaration=_declare(("README.md", "README.ru.md")))
    step, result = _step(tmp_path)
    assert step.passed is True
    assert step.status == "PASS"
    assert result.ok is True
    assert "1 pair(s) held" in step.summary
    assert "3 block(s) compared" in step.summary
    assert "0 finding(s)" in step.summary
    assert "README.md <-> README.ru.md" in step.summary


def test_a_pair_whose_shapes_diverge_fails_the_gate(tmp_path: Path) -> None:
    _pair(tmp_path, SOURCE, FOLLOWER_SHORT)
    _project(tmp_path, declaration=_declare(("README.md", "README.ru.md")))
    step, result = _step(tmp_path)
    assert step.passed is False
    assert step.status == "FAIL"
    assert result.ok is False
    assert [f["rule"] for f in step.findings] == ["unpaired-block"]
    assert step.findings[0]["severity"] == "error"
    assert step.findings[0]["kind"] == "readme-pair"
    assert "1 finding(s)" in step.summary


def test_a_finding_names_the_file_and_the_line_it_is_about(tmp_path: Path) -> None:
    """A finding an agent can act on names the document, not only the pair."""
    _pair(tmp_path, SOURCE, FOLLOWER_SHORT)
    _project(tmp_path, declaration=_declare(("README.md", "README.ru.md")))
    step, _ = _step(tmp_path)
    locations = step.findings[0]["locations"]
    assert locations == [{"file": "README.md", "line": 5}]
    assert "Title" in str(step.findings[0]["why"])
    assert step.findings[0]["remediation"]


def test_a_declared_file_that_cannot_be_read_fails_and_names_it(tmp_path: Path) -> None:
    """The declaration is the project's own; a path that resolves to nothing is a defect.

    The precedent is `issue-log`, which fails on a declared log that is missing
    rather than passing over it. A declaration nothing reads is the false green
    this epic is made of: the step would report `0 finding(s)` having compared
    no document at all.
    """
    (tmp_path / "README.md").write_text(SOURCE, encoding="utf-8")
    _project(tmp_path, declaration=_declare(("README.md", "README.ru.md")))
    step, result = _step(tmp_path)
    assert step.passed is False
    assert result.ok is False
    assert [f["locations"] for f in step.findings] == [[{"file": "README.ru.md"}]]
    assert "UNREADABLE: README.ru.md" in step.summary


def test_a_pair_that_holds_no_block_at_all_warns_rather_than_passing(
    tmp_path: Path,
) -> None:
    """Two readable empty files: no finding, and nothing checked — WARN, not PASS."""
    _pair(tmp_path, "", "")
    _project(tmp_path, declaration=_declare(("README.md", "README.ru.md")))
    step, result = _step(tmp_path)
    assert step.passed is True
    assert step.not_verified is True
    assert step.status == "WARN"
    assert result.ok is True
    assert "NOT COMPARED" in step.summary


def test_the_line_does_not_qualify_a_pair_that_has_nothing_to_qualify(
    tmp_path: Path,
) -> None:
    """NOT VERIFIED RED: a line that qualifies every pair is one a reader stops reading."""
    _pair(tmp_path, SOURCE, FOLLOWER)
    _project(tmp_path, declaration=_declare(("README.md", "README.ru.md")))
    step, _ = _step(tmp_path)
    assert "NOT COMPARED" not in step.summary
    assert "UNREADABLE" not in step.summary


def test_the_line_names_several_pairs_and_stops_at_a_readable_number(
    tmp_path: Path,
) -> None:
    """Four declared pairs: the counts cover all four, the naming stops at three."""
    names = ("A", "B", "C", "D")
    for name in names:
        _pair(tmp_path, SOURCE, FOLLOWER, name=name)
    _project(
        tmp_path,
        declaration=_declare(*((f"{n}.md", f"{n}.ru.md") for n in names)),
    )
    step, result = _step(tmp_path)
    assert result.ok is True
    assert "4 pair(s) held" in step.summary
    assert "12 block(s) compared" in step.summary
    assert "D.md <-> D.ru.md" not in step.summary
    assert "1 more pair(s) not named here" in step.summary


def test_the_step_runs_directly_after_issue_log(tmp_path: Path) -> None:
    """Placed with the document checks, beside the other opt-in declaration."""
    _project(tmp_path, declaration=None)
    result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
    names = [step.name for step in result.steps]
    assert names.index("readme-pair") == names.index("issue-log") + 1


def test_this_repository_holds_its_own_readme_pair() -> None:
    """The dogfood leg: the pair this project declares is compared on every run."""
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[1]
    if not (root / ".beadloom" / "config.yml").is_file():
        pytest.skip("not running from a checkout of this repository")
    from beadloom.application.gate_document_pairs import step_readme_pair

    step = step_readme_pair(root)
    assert step.skipped is False, "this repository declares its README pair"
    assert step.passed is True
    assert "pair(s) held" in step.summary


# ---------------------------------------------------------------------------
# The line's own count — BDL-069, `beadloom-rqma.8`
# ---------------------------------------------------------------------------


def _stated_findings(summary: str) -> int:
    """The number the readme-pair line states, read back out of the line."""
    match = re.search(r"(\d+) finding\(s\)", summary)
    assert match is not None, summary
    return int(match.group(1))


@pytest.mark.parametrize(
    ("label", "arrange"),
    [
        ("a pair that agrees", lambda root: _pair(root, SOURCE, FOLLOWER)),
        ("a pair that diverges", lambda root: _pair(root, SOURCE, FOLLOWER_SHORT)),
        (
            "a declared document nothing can read",
            lambda root: (root / "README.md").write_text(SOURCE, encoding="utf-8"),
        ),
        ("two readable documents holding no block", lambda root: _pair(root, "", "")),
    ],
)
def test_the_line_counts_the_findings_the_step_reports(
    tmp_path: Path, label: str, arrange: Callable[[Path], object]
) -> None:
    """The number in the line is the number of findings the step hands the gate.

    It counted the COMPARISON's findings, which fold over the pairs held, so a
    refused declaration and a document nothing could read were findings the step
    returned and the line did not count. The leg printed `0 finding(s)` in the
    same run in which the gate printed a finding about the leg — a check
    misstating its own population, inside the epic about checks stating theirs
    (`beadloom-qae9`, re-review MAJOR 3).
    """
    arrange(tmp_path)
    _project(tmp_path, declaration=_declare(("README.md", "README.ru.md")))
    step, _ = _step(tmp_path)
    assert _stated_findings(step.summary) == len(step.findings), f"{label}: {step.summary}"


@pytest.mark.parametrize(
    ("label", "declaration"),
    [
        ("an entry with no follower", "\ndocument_pairs:\n  - source: README.md\n"),
        (
            "an entry whose follower key is misspelled",
            "\ndocument_pairs:\n  - source: README.md\n    followr: README.ru.md\n",
        ),
        ("a scalar where the list belongs", "\ndocument_pairs: README.md\n"),
        (
            "a source resolving outside the project",
            "\ndocument_pairs:\n  - source: ../README.md\n    follower: README.ru.md\n",
        ),
    ],
)
def test_a_refused_declaration_is_counted_by_the_line_that_reports_it(
    tmp_path: Path, label: str, declaration: str
) -> None:
    """Four ways of opting in badly, each one finding, each counted in the line."""
    _pair(tmp_path, SOURCE, FOLLOWER)
    _project(tmp_path, declaration=declaration)
    step, result = _step(tmp_path)
    assert result.ok is False, label
    assert len(step.findings) == 1, label
    assert _stated_findings(step.summary) == 1, f"{label}: {step.summary}"
