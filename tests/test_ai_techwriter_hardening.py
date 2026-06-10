"""Holistic hardening pass for the BDL-047 (F4.1) AI tech-writer surface.

Complements the per-bead TDD suites by closing the remaining uncovered
branches and the subtle invariants the F4.1 review flagged: mid-retry budget
exhaustion, the bounded-fixpoint termination guarantee (can't loop forever),
the publisher branch/title/body edge shapes, ``_as_int`` / ``_coerce_int``
coercion edges, and the run-record/no-op honesty contract.

Everything stays deterministic: Goose, the model, git, and the network are all
behind seams (``FakeAgentRunner`` / ``FakePublisher``) or patched
``run_command``; the clock is injected (``now_ts``). No network, no model calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from tools.ai_techwriter import commands, runner, runs_store, scope, seams
from tools.ai_techwriter.commands import CommandResult
from tools.ai_techwriter.models import ContextPacket, DriftItem, HarnessConfig, HarnessResult
from tools.ai_techwriter.runner import _body, _title, run_harness
from tools.ai_techwriter.seams import (
    FakeAgentRunner,
    FakePublisher,
    GitHubPublisher,
    GitLabPublisher,
    GooseAgentRunner,
    _as_int,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tools.ai_techwriter.provider import ProviderConfig

NOW = "2026-06-10T00:00:00+00:00"


# --------------------------------------------------------------------------- #
# Shared fixtures (mirror the harness TDD wiring, kept local to this file)
# --------------------------------------------------------------------------- #


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / "docs").mkdir()
    return tmp_path


def _stale_report(*refs: tuple[str, str, str, str]) -> dict[str, object]:
    pairs: list[dict[str, object]] = [
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
    """Returns a queued sequence of sync-check reports (last repeats forever)."""

    def __init__(self, reports: list[dict[str, object]]) -> None:
        self._reports = reports
        self.calls = 0

    def __call__(self, project_root: Path) -> dict[str, object]:
        idx = min(self.calls, len(self._reports) - 1)
        self.calls += 1
        return self._reports[idx]


@pytest.fixture()
def patch_substrate(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, object]]:
    state: dict[str, object] = {
        "scope": _ScriptedScope([_CLEAN]),
        "ci_ok": True,
        "sync_update_calls": [],
    }

    def fake_sync_check(project_root: Path) -> dict[str, object]:
        report: dict[str, object] = state["scope"](project_root)  # type: ignore[operator]
        return report

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
    monkeypatch.setattr("tools.ai_techwriter.packet.beadloom_docs_polish_json", fake_polish)
    monkeypatch.setattr(runner, "beadloom_docs_polish_json", fake_polish)
    monkeypatch.setattr("tools.ai_techwriter.packet.beadloom_ctx_json", fake_ctx)
    monkeypatch.setattr("tools.ai_techwriter.packet.beadloom_why", fake_why)
    monkeypatch.setattr(runner, "beadloom_sync_update", fake_sync_update)
    monkeypatch.setattr(runner, "beadloom_ci", fake_ci)
    yield state


def _packet() -> ContextPacket:
    return ContextPacket(
        ref_id="graph",
        doc_path="docs/graph.md",
        current_content="old",
        drift_reason="symbols_changed (src/g.py)",
        docs_polish_json={"ref_id": "graph"},
        ctx={"focus": "graph"},
        why="why graph",
    )


# --------------------------------------------------------------------------- #
# runner: budget exhausted MID-RETRY (not at the very start)
# --------------------------------------------------------------------------- #


def test_budget_exceeded_mid_retry_flags_without_extra_agent_calls(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """A doc whose first attempt fails to go fresh would normally retry; if the
    token budget is already spent by that first attempt, the retry loop must
    abort with a 'budget exceeded mid-retry' flag and NOT call the agent again.
    """
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # Stays stale forever => the per-doc loop wants to retry.
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py"))]
    )
    # First attempt spends 120 tokens; cap is 120 => the 2nd attempt is blocked
    # by the mid-retry budget guard (before building another packet).
    cfg = HarnessConfig(per_doc_retries=3, max_total_tokens=120)
    agent = FakeAgentRunner(
        project_root=project, write_marker=None, input_tokens=100, output_tokens=20
    )
    result = run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW, config=cfg
    )
    assert len(agent.calls) == 1  # no second attempt — budget guard fired first
    assert result.flagged is True
    assert any("budget exceeded mid-retry" in r for r in result.flagged_reasons)


# --------------------------------------------------------------------------- #
# runner: fixpoint is BOUNDED — the can't-loop-forever guarantee
# --------------------------------------------------------------------------- #


def test_fixpoint_terminates_even_if_scope_is_adversarially_infinite(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """The subtle invariant: a scope that NEVER goes clean must still terminate
    and flag — never hang. With a *stable* (never-shrinking) stale set the
    no-progress guard fires BEFORE the round-cap: it stops as soon as a round
    re-baselines the identical set the previous round already re-baselined.
    """
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")

    class _AlwaysStale:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, project_root: Path) -> dict[str, object]:
            self.calls += 1
            # graph clears after the per-doc re-check, but a sibling is ALWAYS
            # stale => the fixpoint can never reach 0.
            if self.calls == 2:  # per-doc re-check sees graph fresh
                return _CLEAN
            return _stale_report(("sib", "docs/sib.md", "hash_changed", "src/s.py"))

    always = _AlwaysStale()
    patch_substrate["scope"] = always
    cfg = HarnessConfig(max_fixpoint_rounds=5, per_doc_retries=0)
    result = run_harness(
        project,
        agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(),
        now_ts=NOW,
        config=cfg,
    )
    assert result.flagged is True
    # No-progress: round 1 sees {sib}, round 2 sees the identical {sib} again
    # (re-baselining cleared nothing) => break at round 2, NOT the full cap.
    assert result.fixpoint_rounds == 2
    assert any("fixpoint not reached after 5 rounds" in r for r in result.flagged_reasons)
    # Bounded scope consultation: initial scope + per-doc recheck + the two
    # fixpoint reads before the no-progress break. The key property is FINITE.
    assert always.calls <= 2 + 2 + 1


def test_fixpoint_runs_full_round_cap_when_set_keeps_shrinking(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """No-progress must NOT mis-fire while the stale set is still shrinking:
    a scope that drops one ref per round (so each round's set differs from the
    last) keeps going until it reaches 0, never tripping the guard early."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # per-doc: graph stale -> recheck fresh; then fixpoint rounds shrink
    # {a,b,c} -> {b,c} -> {c} -> {} (each round's set differs => progress).
    scripted = [
        _stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py")),
        _CLEAN,  # per-doc re-check
        _stale_report(
            ("a", "docs/a.md", "hash_changed", "src/a.py"),
            ("b", "docs/b.md", "hash_changed", "src/b.py"),
            ("c", "docs/c.md", "hash_changed", "src/c.py"),
        ),
        _stale_report(
            ("b", "docs/b.md", "hash_changed", "src/b.py"),
            ("c", "docs/c.md", "hash_changed", "src/c.py"),
        ),
        _stale_report(("c", "docs/c.md", "hash_changed", "src/c.py")),
        _CLEAN,
    ]
    patch_substrate["scope"] = _ScriptedScope(scripted)
    cfg = HarnessConfig(max_fixpoint_rounds=10, per_doc_retries=0)
    result = run_harness(
        project,
        agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(),
        now_ts=NOW,
        config=cfg,
    )
    assert result.flagged is False
    assert result.fixpoint_rounds == 3  # ran every shrinking round, then clean


def test_fixpoint_clean_on_first_round_records_zero_rounds(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """When the per-doc loop already left the repo clean, the fixpoint returns
    immediately (no rounds counted) — the natural-termination branch."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [
            _stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")),
            _CLEAN,  # per-doc re-check: fresh
            _CLEAN,  # fixpoint round-0 read: already clean -> early return
        ]
    )
    result = run_harness(
        project, agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(), now_ts=NOW,
    )
    assert result.flagged is False
    assert result.fixpoint_rounds == 0


# --------------------------------------------------------------------------- #
# runner: model-attribution edge (agent reports empty model => result.model
# stays the last non-empty value)
# --------------------------------------------------------------------------- #


def test_empty_agent_model_does_not_overwrite_recorded_model(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """If the agent returns a falsy model string, the harness must NOT clobber
    ``result.model`` with '' (the 114->116 branch)."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py")), _CLEAN]
    )
    agent = FakeAgentRunner(project_root=project, model="")  # falsy model
    result = run_harness(project, agent=agent, publisher=FakePublisher(), now_ts=NOW)
    # No model reported anywhere => stays the HarnessResult default "".
    assert result.model == ""
    assert result.run_record is not None
    assert result.run_record.model == ""


# --------------------------------------------------------------------------- #
# runner: PR title/body/branch edge shapes
# --------------------------------------------------------------------------- #


def test_title_flagged_prefix_and_clean_form() -> None:
    clean = HarnessResult(docs_refreshed=["docs/a.md"])
    assert _title(clean) == "docs: AI tech-writer refresh (1 doc(s))"
    flagged = HarnessResult(docs_refreshed=["docs/a.md"], flagged=True)
    assert _title(flagged).startswith("⚠ needs human")


def test_body_lists_none_when_no_docs_refreshed_and_flagged_reasons() -> None:
    """A flagged run with zero refreshed docs still produces an honest body:
    the '(none)' docs marker + the flagged-reasons section + token line."""
    result = HarnessResult(
        docs_refreshed=[], flagged=True, flagged_reasons=["beadloom ci failed (rc=1)"],
        gate_passed=False, input_tokens=10, output_tokens=5,
    )
    body = _body(result)
    assert "- (none)" in body
    assert "Gate (`beadloom ci`): FAILED" in body
    assert "Needs human attention" in body
    assert "beadloom ci failed (rc=1)" in body
    assert "Tokens: in=10 out=5" in body


def test_branch_with_no_docs_refreshed_falls_back_to_refresh_docs(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """A gate-failed run that refreshed NOTHING yields the readable fallback
    branch ``ai-techwriter/refresh-docs`` (BEAD-11 fix for the BEAD-08 finding).

    The bug was operator precedence in ``runner._publish``::

        branch = _BRANCH_PREFIX + "-".join(sorted(stems))[:60] or "...docs"

    ``+`` bound before ``or``, so for an empty ``docs_refreshed`` the left
    operand was the non-empty ``"ai-techwriter/refresh-"`` and the ``or`` never
    fired — producing a dangling ``ai-techwriter/refresh-`` with a trailing
    hyphen. The fix parenthesizes the slug so ``or`` scopes to it; with zero
    docs the slug is empty so the ``"docs"`` fallback applies.
    """
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py"))]
    )
    patch_substrate["ci_ok"] = False
    cfg = HarnessConfig(per_doc_retries=0)
    publisher = FakePublisher()
    result = run_harness(
        project, agent=FakeAgentRunner(project_root=project, write_marker=None),
        publisher=publisher, now_ts=NOW, config=cfg,
    )
    assert result.docs_refreshed == []
    branch = str(publisher.published[0]["branch"])
    assert branch == "ai-techwriter/refresh-docs"  # readable fallback, no trailing hyphen


def test_duplicate_doc_path_refreshed_only_once(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """Two stale refs that share one doc_path must list that doc once in
    docs_refreshed (no double-counting in the run-record)."""
    (project / "docs" / "shared.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [
            _stale_report(
                ("a", "docs/shared.md", "hash_changed", "src/a.py"),
                ("b", "docs/shared.md", "symbols_changed", "src/b.py"),
            ),
            _CLEAN,
        ]
    )
    result = run_harness(
        project, agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(), now_ts=NOW,
    )
    assert result.docs_refreshed == ["docs/shared.md"]


# --------------------------------------------------------------------------- #
# seams: _as_int coercion edges (bool, str-digit, negative, junk)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, 0),  # bool is NOT counted as an int (usage misuse guard)
        (False, 0),
        (5, 5),
        (-7, 0),  # negative clamped to 0
        ("42", 42),  # digit string parsed
        ("-3", 0),  # non-digit string (has '-') => 0
        ("nope", 0),
        (None, 0),
        (3.9, 0),  # floats are not ints here
    ],
)
def test_as_int_coercion_matrix(value: object, expected: int) -> None:
    assert _as_int(value) == expected


def test_goose_usage_parse_coerces_string_token_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model usage line may report token counts as strings; they must be
    coerced to ints (exercises the str-digit branch end-to-end)."""
    import json

    usage = json.dumps({"input_tokens": "900", "output_tokens": "300", "model": "m"})
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(0, usage, "")
    )
    runner_obj = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=_qwen()
    )
    res = runner_obj.run(_packet())
    assert res.input_tokens == 900
    assert res.output_tokens == 300


def _qwen() -> ProviderConfig:
    from tools.ai_techwriter.provider import qwen_provider

    return qwen_provider()


def test_goose_usage_parse_handles_rewritten_paths_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A usage line with an explicit rewritten_paths list is honored verbatim
    (multi-doc rewrite), not collapsed to the packet's single doc."""
    import json

    usage = json.dumps(
        {"rewritten_paths": ["docs/a.md", "docs/b.md"], "input_tokens": 1, "output_tokens": 1}
    )
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(0, usage, "")
    )
    runner_obj = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=_qwen()
    )
    res = runner_obj.run(_packet())
    assert res.rewritten_paths == ("docs/a.md", "docs/b.md")


# --------------------------------------------------------------------------- #
# seams: GitLab publisher flagged label (the 225 branch)
# --------------------------------------------------------------------------- #


def test_gitlab_publisher_adds_needs_human_label_when_flagged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if args[:2] == ["git", "push"]:
            return CommandResult(0, "", "")
        return CommandResult(0, "https://gitlab.com/o/r/-/merge_requests/9\n", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitLabPublisher().publish(
        project_root=Path("/x"), branch="ai/z", title="T", body="B", flagged=True
    )
    assert url.endswith("/merge_requests/9")
    mr_call = seen[1]
    assert "--label" in mr_call and "needs-human" in mr_call


def test_github_publisher_no_label_when_not_flagged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if args[:2] == ["git", "push"]:
            return CommandResult(0, "", "")
        return CommandResult(0, "https://github.com/o/r/pull/1\n", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    GitHubPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
    )
    assert "--label" not in seen[1]


# --------------------------------------------------------------------------- #
# commands: docs-polish non-object guard (commands.py line 90)
# --------------------------------------------------------------------------- #


def test_docs_polish_json_raises_on_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        commands, "run_command", lambda args, *, cwd: CommandResult(0, "[1, 2]", "")
    )
    with pytest.raises(RuntimeError, match="not an object"):
        commands.beadloom_docs_polish_json(Path("/x"))


# --------------------------------------------------------------------------- #
# packet: polish_report fetched lazily when not passed in
# --------------------------------------------------------------------------- #


def test_build_packet_fetches_polish_when_not_provided(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """When the harness does not pre-fetch polish, build_packet fetches it
    itself (packet.py line 35 branch) and selects the ref slice."""
    from tools.ai_techwriter.packet import build_packet

    (project / "docs" / "graph.md").write_text("content", encoding="utf-8")
    item = DriftItem(
        ref_id="graph", doc_path="docs/graph.md",
        reasons=("hash_changed",), code_files=("src/g.py",),
    )
    packet = build_packet(project, item, polish_report=None)
    assert packet.docs_polish_json == {"ref_id": "graph", "summary": "graph node"}


def test_read_doc_returns_empty_for_missing_file(project: Path) -> None:
    """A packet for a not-yet-existing doc reads as '' (packet.py line 65)."""
    from tools.ai_techwriter.packet import read_doc

    assert read_doc(project, "docs/does-not-exist.md") == ""


# --------------------------------------------------------------------------- #
# runs_store: append-only ordering survives a corrupt store (no crash)
# --------------------------------------------------------------------------- #


def test_load_runs_drops_non_dict_rows_keeps_dicts(project: Path) -> None:
    """A store array mixing junk rows with real records keeps only the dicts
    (append-only store stays robust to partial corruption)."""
    runs_store.runs_store_path(project).write_text(
        '[{"ts": "a"}, 5, "x", null, {"ts": "b"}]', encoding="utf-8"
    )
    runs = runs_store.load_runs(project)
    assert [r["ts"] for r in runs] == ["a", "b"]


def test_append_run_on_corrupt_store_raises_not_silent(project: Path) -> None:
    """Honesty: a syntactically-corrupt runs store is surfaced (raises) on
    append rather than silently dropping prior history. The DASHBOARD tolerates
    a corrupt store (degrades to empty) but the harness emitter does not mask
    it — documenting the asymmetry so it is a conscious contract."""
    import json as _json

    from tools.ai_techwriter.models import RunRecord

    runs_store.runs_store_path(project).write_text("{ not json", encoding="utf-8")
    rec = RunRecord(
        ts=NOW, platform="github", docs_refreshed=("d.md",),
        input_tokens=1, output_tokens=2, model="m", gate="green", pr_url="u",
    )
    with pytest.raises(_json.JSONDecodeError):
        runs_store.append_run(project, rec)
