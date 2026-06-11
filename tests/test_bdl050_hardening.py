"""BDL-050 BEAD-04 hardening: edge cases over the consolidated-CI surface.

These tests HARDEN the W1-W2 implementation: they cover production paths the
existing suites leave uncovered and pin down a handful of FOCUS boundaries
(verdict ⇄ exit-code ⇄ infra-annotation; the fixpoint round-cap vs no-progress
distinction; branch-name overflow; the inlined pypi test job) WITHOUT duplicating
the green tests in ``test_ai_techwriter_*`` / ``test_ci_*`` / ``test_branch_protection``.

Everything is deterministic + network-free: the agent / gate / git / gh seams are
faked or patched, and the workflow checks are static ``yaml.safe_load`` over the
committed YAML.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner, Result

from beadloom.ai_agents.ai_techwriter import cli, commands, runner, scope
from beadloom.ai_agents.ai_techwriter.models import HarnessConfig, HarnessResult
from beadloom.ai_agents.ai_techwriter.runner import _branch_name, classify_verdict, run_harness
from beadloom.ai_agents.ai_techwriter.seams import FakeAgentRunner, FakePublisher

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

from pathlib import Path as _Path

REPO_ROOT = _Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

NOW = "2026-06-10T00:00:00+00:00"


# --------------------------------------------------------------------------- #
# Shared deterministic substrate (mirrors test_ai_techwriter_harness)
# --------------------------------------------------------------------------- #


def _stale_report(*refs: tuple[str, str, str, str]) -> dict[str, object]:
    pairs = [
        {
            "status": "stale",
            "ref_id": ref_id,
            "doc_path": doc,
            "code_path": code,
            "reason": reason,
        }
        for ref_id, doc, reason, code in refs
    ]
    return {"summary": {"total": len(pairs), "ok": 0, "stale": len(pairs)}, "pairs": pairs}


_CLEAN: dict[str, object] = {"summary": {"total": 0, "ok": 0, "stale": 0}, "pairs": []}


class _ScriptedScope:
    """Returns a queued sequence of sync-check reports (the last one repeats)."""

    def __init__(self, reports: list[dict[str, object]]) -> None:
        self._reports = reports
        self.calls = 0

    def __call__(self, project_root: Path, since: str | None = None) -> dict[str, object]:
        idx = min(self.calls, len(self._reports) - 1)
        self.calls += 1
        return self._reports[idx]


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / "docs").mkdir()
    return tmp_path


@pytest.fixture()
def patch_substrate(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, object]]:
    state: dict[str, object] = {
        "scope": _ScriptedScope([_CLEAN]),
        "ci_ok": True,
        "sync_update_calls": [],
    }

    def fake_sync_check(project_root: Path, *, since: str | None = None) -> dict[str, object]:
        scoped = state["scope"]
        assert isinstance(scoped, _ScriptedScope)
        return scoped(project_root, since)

    def fake_polish(project_root: Path) -> dict[str, object]:
        return {"nodes": [{"ref_id": "graph", "summary": "graph node"}]}

    def fake_ctx(project_root: Path, ref_id: str) -> dict[str, object]:
        return {"focus": ref_id}

    def fake_why(project_root: Path, ref_id: str) -> str:
        return f"why {ref_id}"

    def fake_sync_update(project_root: Path, ref_id: str) -> commands.CommandResult:
        calls = state["sync_update_calls"]
        assert isinstance(calls, list)
        calls.append(ref_id)
        return commands.CommandResult(0, "", "")

    def fake_ci(project_root: Path) -> commands.CommandResult:
        return commands.CommandResult(0 if state["ci_ok"] else 1, "", "")

    monkeypatch.setattr(scope, "beadloom_sync_check_json", fake_sync_check)
    monkeypatch.setattr(
        "beadloom.ai_agents.ai_techwriter.packet.beadloom_docs_polish_json", fake_polish
    )
    monkeypatch.setattr("beadloom.ai_agents.ai_techwriter.packet.beadloom_ctx_json", fake_ctx)
    monkeypatch.setattr("beadloom.ai_agents.ai_techwriter.packet.beadloom_why", fake_why)
    monkeypatch.setattr(runner, "beadloom_docs_polish_json", fake_polish)
    monkeypatch.setattr(runner, "beadloom_sync_update", fake_sync_update)
    monkeypatch.setattr(runner, "beadloom_ci", fake_ci)
    yield state


# --------------------------------------------------------------------------- #
# runner: fixpoint ROUND-CAP path (distinct from the no-progress break)
# --------------------------------------------------------------------------- #


def test_fixpoint_round_cap_flags_when_set_keeps_changing(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """A stale set that CHANGES every round never trips the no-progress guard, so
    it exhausts ``max_fixpoint_rounds`` and is flagged by the round-cap branch.

    This is the distinct sibling of ``test_fixpoint_no_progress_flags_before_round_cap``:
    there the set is identical each round (early break); here it differs each round
    so only the cap can stop it (runner.py round-cap flag path).
    """
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # Per-doc loop: graph stale then clean. Then the fixpoint sees a DIFFERENT
    # sibling ref each round (s1, s2, s3, ...) so cur_refs != prev_refs always.
    rounds = [
        _stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")),
        _CLEAN,  # per-doc re-check: graph fresh
    ]
    rounds += [
        _stale_report((f"sib{i}", f"docs/sib{i}.md", "hash_changed", f"src/s{i}.py"))
        for i in range(20)
    ]
    patch_substrate["scope"] = _ScriptedScope(rounds)
    cfg = HarnessConfig(max_fixpoint_rounds=3)
    result = run_harness(
        project,
        agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(),
        now_ts=NOW,
        config=cfg,
    )
    assert result.fixpoint_rounds == 3  # the cap, not an early no-progress break
    assert result.flagged is True
    assert any("fixpoint not reached after 3 rounds" in r for r in result.flagged_reasons)


def test_fixpoint_round_cap_then_final_clean_is_not_flagged(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """If the cap loop ends with a changing set but the FINAL re-check is clean,
    the run is NOT flagged (the post-loop ``remaining`` is empty → no flag).

    This pins the runner branch where the fixpoint exhausts its rounds yet the
    last ``discover_scope`` happens to be clean — success, not a stuck flag.
    """
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    rounds = [
        _stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")),
        _CLEAN,  # per-doc re-check: graph fresh
    ]
    # A DIFFERENT sibling each in-loop round (never trips no-progress), then the
    # post-loop final re-check returns clean → not flagged.
    rounds += [
        _stale_report((f"sib{i}", f"docs/sib{i}.md", "hash_changed", f"src/s{i}.py"))
        for i in range(2)
    ]
    rounds.append(_CLEAN)  # the FINAL post-cap discover_scope is clean
    patch_substrate["scope"] = _ScriptedScope(rounds)
    cfg = HarnessConfig(max_fixpoint_rounds=2)
    result = run_harness(
        project,
        agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(),
        now_ts=NOW,
        config=cfg,
    )
    assert result.flagged is False
    assert not any("fixpoint not reached" in r for r in result.flagged_reasons)


# --------------------------------------------------------------------------- #
# runner: budget exceeded MID-RETRY (inside _repair_one_doc's loop)
# --------------------------------------------------------------------------- #


def test_budget_exceeded_mid_retry_flags_that_ref(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """When a single doc's retry loop crosses the token cap, that ref is flagged
    with a 'budget exceeded mid-retry' reason (the per-doc inner-loop guard).

    The agent edits but the ref never goes fresh, so it retries; the cap is set
    just above the first turn's tokens so the cap trips on the second iteration.
    """
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # ref stays stale forever => the per-doc loop retries; cap=120 trips after the
    # first 150-token turn, inside _repair_one_doc (not the outer _repair_each_doc).
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py"))]
    )
    cfg = HarnessConfig(per_doc_retries=5, max_total_tokens=120)
    agent = FakeAgentRunner(project_root=project, input_tokens=100, output_tokens=50)
    result = run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW, config=cfg
    )
    assert result.flagged is True
    assert any("budget exceeded mid-retry for graph" in r for r in result.flagged_reasons)
    # Only one agent turn ran before the cap stopped the retries.
    assert len(agent.calls) == 1


# --------------------------------------------------------------------------- #
# runner: model is NOT overwritten when the agent reports an empty model string
# --------------------------------------------------------------------------- #


def test_empty_agent_model_does_not_clobber_prior_model(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """An agent turn that reports ``model=''`` must not blank an already-set model
    on the result (runner only assigns when ``agent_result.model`` is truthy).
    """
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")), _CLEAN]
    )
    # write_marker set => the fake edits the doc, but model="" => the assignment
    # branch is skipped and result.model stays "" (its initial value), not clobbered.
    agent = FakeAgentRunner(project_root=project, model="")
    result = run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW
    )
    assert result.model == ""
    assert result.flagged is False


# --------------------------------------------------------------------------- #
# runner: _branch_name overflow drops whole segments to fit the length cap
# --------------------------------------------------------------------------- #


def test_branch_name_drops_segments_over_length_cap() -> None:
    """With several long-slugged docs (but <= the many-docs threshold), the branch
    name caps on a SEGMENT boundary — later slugs are dropped, never truncated.
    """
    docs = [
        f"docs/{'reallylongdirectorynamesegment' + str(i)}/SPEC.md" for i in range(4)
    ]
    name = _branch_name(docs)
    assert name.startswith("ai-techwriter/refresh-")
    slug = name.removeprefix("ai-techwriter/refresh-")
    assert len(slug) <= 60
    # Dropped on a boundary: no trailing partial segment / dangling hyphen.
    assert not slug.endswith("-")
    # At least one but not all four long segments fit.
    assert 1 <= slug.count("graph") + slug.count("spec") + len(slug.split("-")) <= 4


def test_branch_name_single_doc_uses_its_slug() -> None:
    """One doc with an informative parent yields ``parent-stem`` (sanity boundary)."""
    name = _branch_name(["docs/graph-diff/SPEC.md"])
    assert name == "ai-techwriter/refresh-graph-diff-spec"


# --------------------------------------------------------------------------- #
# cli: the ::warning:: annotation is emitted ONLY on infra (never ok / flagged)
# --------------------------------------------------------------------------- #


def _invoke(
    result: HarnessResult, project: Path, publisher: object | None = None
) -> Result:
    obj: dict[str, object] = {"run_harness": lambda *a, **k: result, "now": lambda: "T"}
    if publisher is not None:
        obj["publisher"] = publisher
    return CliRunner().invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj=obj,
    )


def test_warning_not_emitted_on_clean_green_run(project: Path) -> None:
    """A clean refresh (ok) exits 0 and emits NO ::warning:: (infra annotation is
    reserved for the infra verdict only)."""
    res = HarnessResult(docs_refreshed=["docs/a.md"], gate_passed=True, pr_url="u")
    out = _invoke(res, project)
    assert out.exit_code == 0, out.output
    assert "::warning" not in out.output


def test_warning_not_emitted_on_noop(project: Path) -> None:
    """A 0-stale no-op exits 0 and emits NO ::warning::."""
    res = HarnessResult(no_op=True, gate_passed=True)
    out = _invoke(res, project)
    assert out.exit_code == 0, out.output
    assert "::warning" not in out.output


def test_infra_warning_message_text_matches_constant(project: Path) -> None:
    """The infra ::warning:: carries the exact agreed copy (docs NOT checked)."""
    res = HarnessResult(
        flagged=True,
        flagged_reasons=["provider 503"],
        input_tokens=0,
        output_tokens=0,
    )
    out = _invoke(res, project)
    assert out.exit_code == 0, out.output
    assert f"::warning title=AI tech-writer::{cli._INFRA_MESSAGE}" in out.output
    assert "(infra) provider 503" in out.output


def test_infra_no_comment_when_publisher_is_not_a_comment_publisher(project: Path) -> None:
    """A publisher WITHOUT a comment seam => infra still exits 0 (annotation only),
    no crash, no attempt to comment."""

    class _PlainPublisher:
        def publish(self, **_kwargs: object) -> str:
            return ""

    res = HarnessResult(flagged=True, flagged_reasons=["quota"], input_tokens=0, output_tokens=0)
    out = _invoke(res, project, publisher=_PlainPublisher())
    assert out.exit_code == 0, out.output
    assert "::warning title=AI tech-writer::" in out.output


# --------------------------------------------------------------------------- #
# cli: classify_verdict ⇄ exit-code parametrized truth table (end-to-end)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("res", "expected_exit", "expect_warning"),
    [
        (HarnessResult(no_op=True, gate_passed=True), 0, False),
        (HarnessResult(docs_refreshed=["d"], gate_passed=True), 0, False),
        (HarnessResult(flagged=True, input_tokens=1, output_tokens=0), 1, False),
        (HarnessResult(flagged=True, input_tokens=0, output_tokens=1), 1, False),
        (HarnessResult(flagged=True, input_tokens=0, output_tokens=0), 0, True),
    ],
    ids=["noop", "clean", "flagged-1in", "flagged-1out", "infra-0tokens"],
)
def test_verdict_exit_and_warning_table(
    project: Path, res: HarnessResult, expected_exit: int, expect_warning: bool
) -> None:
    """End-to-end: each verdict bucket maps to the right exit code, and the
    ::warning:: appears iff (and only iff) the verdict is infra."""
    out = _invoke(res, project)
    assert out.exit_code == expected_exit, out.output
    assert ("::warning" in out.output) is expect_warning


def test_classify_verdict_matches_cli_exit(project: Path) -> None:
    """The CLI exit code is a faithful function of classify_verdict (no drift)."""
    for res in (
        HarnessResult(no_op=True),
        HarnessResult(flagged=True, input_tokens=5),
        HarnessResult(flagged=True, input_tokens=0, output_tokens=0),
    ):
        verdict = classify_verdict(res)
        out = _invoke(res, project)
        if verdict == "flagged":
            assert out.exit_code == 1
        else:
            assert out.exit_code == 0


# --------------------------------------------------------------------------- #
# pypi-publish.yml: the (now-inlined) test job survives + parses (BDL-050)
# --------------------------------------------------------------------------- #

PYPI = WORKFLOWS / "pypi-publish.yml"
GITLAB_CI = REPO_ROOT / ".gitlab-ci.yml"


def test_pypi_publish_parses_clean() -> None:
    """pypi-publish.yml still ``yaml.safe_load``s after tests.yml was folded away."""
    doc = yaml.safe_load(PYPI.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert isinstance(doc["jobs"], dict)


def test_pypi_publish_has_inlined_test_job_not_workflow_call() -> None:
    """tests.yml was deleted, so the release pipeline must run pytest INLINE (no
    ``uses: ./.github/workflows/tests.yml`` workflow_call that would now 404)."""
    text = PYPI.read_text(encoding="utf-8")
    assert "workflows/tests.yml" not in text
    jobs = yaml.safe_load(text)["jobs"]
    assert "tests" in jobs
    steps = jobs["tests"]["steps"]
    runs = "\n".join(str(s.get("run", "")) for s in steps if isinstance(s, dict))
    assert "pytest" in runs


def test_gitlab_ci_parses_clean() -> None:
    """The GitLab mirror ``yaml.safe_load``s clean (no YAML-anchor breakage)."""
    doc = yaml.safe_load(GITLAB_CI.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert doc["stages"] == ["verify", "docs"]
