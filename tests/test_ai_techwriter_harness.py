"""Tests for the BDL-047 AI tech-writer harness (tools/ai_techwriter).

Goose + model + PR/MR are behind seams (FakeAgentRunner / FakePublisher) and
the subprocess wrappers are patched, so nothing here touches Goose, the model,
or the network. The clock is injected (``now_ts``) for deterministic records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from tools.ai_techwriter import commands, runner, runs_store, scope
from tools.ai_techwriter.models import (
    DriftItem,
    HarnessConfig,
    RunRecord,
)
from tools.ai_techwriter.packet import build_packet, select_polish_for_ref
from tools.ai_techwriter.runner import run_harness
from tools.ai_techwriter.scope import parse_scope
from tools.ai_techwriter.seams import (
    AgentRunner,
    FakeAgentRunner,
    FakePublisher,
    ReviewPublisher,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

NOW = "2026-06-10T00:00:00+00:00"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A minimal project root with a docs/ dir + .beadloom/."""
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / "docs").mkdir()
    return tmp_path


def _stale_report(*refs: tuple[str, str, str, str]) -> dict[str, object]:
    """Build a sync-check --json report. Each ref => (ref_id, doc, reason, code)."""
    pairs: list[dict[str, object]] = []
    for ref_id, doc, reason, code in refs:
        pairs.append(
            {
                "status": "stale",
                "ref_id": ref_id,
                "doc_path": doc,
                "code_path": code,
                "reason": reason,
            }
        )
    return {"summary": {"total": len(pairs), "ok": 0, "stale": len(pairs)}, "pairs": pairs}


_CLEAN = {"summary": {"total": 0, "ok": 0, "stale": 0}, "pairs": []}


class _ScriptedScope:
    """Returns a queued sequence of sync-check reports (last repeats)."""

    def __init__(self, reports: list[dict[str, object]]) -> None:
        self._reports = reports
        self.calls = 0

    def __call__(self, project_root: Path) -> dict[str, object]:
        idx = min(self.calls, len(self._reports) - 1)
        self.calls += 1
        return self._reports[idx]


@pytest.fixture()
def patch_substrate(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, object]]:
    """Patch all beadloom subprocess wrappers used by the harness.

    Yields a dict the test mutates: ``scope`` (a _ScriptedScope), ``ci_ok``,
    plus counters for sync-update calls.
    """
    state: dict[str, object] = {
        "scope": _ScriptedScope([_CLEAN]),
        "ci_ok": True,
        "sync_update_calls": [],
    }

    def fake_sync_check(project_root: Path) -> dict[str, object]:
        return state["scope"](project_root)  # type: ignore[operator]

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
    monkeypatch.setattr("tools.ai_techwriter.packet.beadloom_ctx_json", fake_ctx)
    monkeypatch.setattr("tools.ai_techwriter.packet.beadloom_why", fake_why)
    monkeypatch.setattr(runner, "beadloom_sync_update", fake_sync_update)
    monkeypatch.setattr(runner, "beadloom_ci", fake_ci)
    yield state


# --------------------------------------------------------------------------- #
# Scope parsing
# --------------------------------------------------------------------------- #


def test_parse_scope_groups_by_ref_collecting_reasons_and_files() -> None:
    report = _stale_report(
        ("graph", "domains/graph/README.md", "symbols_changed", "src/g/a.py"),
        ("graph", "domains/graph/README.md", "hash_changed", "src/g/b.py"),
        ("doc-sync", "domains/doc-sync/README.md", "untracked", "src/d/c.py"),
    )
    items = parse_scope(report)
    assert [i.ref_id for i in items] == ["graph", "doc-sync"]
    graph = items[0]
    assert graph.reasons == ("hash_changed", "symbols_changed")
    assert graph.code_files == ("src/g/a.py", "src/g/b.py")
    assert "symbols_changed" in graph.reason_summary()


def test_parse_scope_ignores_ok_pairs_and_malformed() -> None:
    report = {
        "pairs": [
            {"status": "ok", "ref_id": "x", "reason": "ok"},
            "not-a-dict",
            {"status": "stale", "ref_id": "", "reason": "hash_changed"},
            {"status": "stale", "ref_id": "y", "doc_path": "d.md", "reason": "untracked"},
        ]
    }
    items = parse_scope(report)
    assert [i.ref_id for i in items] == ["y"]


def test_parse_scope_no_pairs_key_returns_empty() -> None:
    assert parse_scope({"summary": {}}) == []


# --------------------------------------------------------------------------- #
# Packet building
# --------------------------------------------------------------------------- #


def test_select_polish_for_ref_returns_node_or_empty() -> None:
    report = {"nodes": [{"ref_id": "a", "summary": "A"}, {"ref_id": "b"}]}
    assert select_polish_for_ref(report, "a") == {"ref_id": "a", "summary": "A"}
    assert select_polish_for_ref(report, "zzz") == {}
    assert select_polish_for_ref({}, "a") == {}


def test_build_packet_assembles_all_fields(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    doc = project / "docs" / "graph.md"
    doc.write_text("old content", encoding="utf-8")
    item = DriftItem(
        ref_id="graph",
        doc_path="docs/graph.md",
        reasons=("symbols_changed",),
        code_files=("src/g/a.py",),
    )
    packet = build_packet(project, item)
    assert packet.ref_id == "graph"
    assert packet.current_content == "old content"
    assert "symbols_changed" in packet.drift_reason
    assert packet.docs_polish_json == {"ref_id": "graph", "summary": "graph node"}
    assert packet.ctx == {"focus": "graph"}
    assert packet.why == "why graph"


# --------------------------------------------------------------------------- #
# Harness: no-op
# --------------------------------------------------------------------------- #


def test_zero_stale_is_clean_noop(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    agent = FakeAgentRunner()
    publisher = FakePublisher()
    result = run_harness(project, agent=agent, publisher=publisher, now_ts=NOW)
    assert result.no_op is True
    assert result.gate_passed is True
    assert agent.calls == []
    assert publisher.published == []
    # no run-record on a no-op
    assert runs_store.load_runs(project) == []


# --------------------------------------------------------------------------- #
# Harness: green path
# --------------------------------------------------------------------------- #


def test_green_path_refreshes_doc_and_opens_normal_pr(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # round 1: stale graph; after sync-update everything is clean.
    patch_substrate["scope"] = _ScriptedScope(
        [
            _stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")),
            _CLEAN,
        ]
    )
    agent = FakeAgentRunner(project_root=project, model="qwen-test")
    publisher = FakePublisher(url="https://example.test/pr/42")

    result = run_harness(project, agent=agent, publisher=publisher, now_ts=NOW)

    assert result.no_op is False
    assert result.gate_passed is True
    assert result.flagged is False
    assert result.docs_refreshed == ["docs/graph.md"]
    assert result.pr_url == "https://example.test/pr/42"
    assert len(agent.calls) == 1
    assert publisher.published[0]["flagged"] is False
    assert "needs human" not in str(publisher.published[0]["title"])
    # doc was rewritten by the agent
    assert "<!-- refreshed -->" in (project / "docs" / "graph.md").read_text()


# --------------------------------------------------------------------------- #
# Harness: per-doc retry
# --------------------------------------------------------------------------- #


def test_per_doc_retry_recovers_after_one_agent_failure(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [
            _stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py")),
            _CLEAN,
        ]
    )
    agent = FakeAgentRunner(project_root=project, fail_first_n=1)
    result = run_harness(project, agent=agent, publisher=FakePublisher(), now_ts=NOW)
    # first attempt raised, second succeeded => 2 calls, doc refreshed, not flagged
    assert len(agent.calls) == 2
    assert result.flagged is False
    assert result.docs_refreshed == ["docs/graph.md"]


def test_per_doc_retry_exhausted_flags_pr(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # ref stays stale forever => retries exhausted
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py"))]
    )
    cfg = HarnessConfig(per_doc_retries=2)
    agent = FakeAgentRunner(project_root=project, write_marker=None)
    publisher = FakePublisher()
    result = run_harness(
        project, agent=agent, publisher=publisher, now_ts=NOW, config=cfg
    )
    # 1 initial + 2 retries = 3 agent calls
    assert len(agent.calls) == 3
    assert result.flagged is True
    assert any("still stale" in r for r in result.flagged_reasons)
    assert publisher.published[0]["flagged"] is True
    assert "needs human" in str(publisher.published[0]["title"])


# --------------------------------------------------------------------------- #
# Harness: fixpoint (re-stale siblings + round cap)
# --------------------------------------------------------------------------- #


def test_fixpoint_rebaselines_restale_siblings_then_stabilises(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # Per-doc loop sees ref fresh after attempt (call 2 = clean for graph re-check),
    # but the global fixpoint then sees a re-staled sibling once, then clean.
    sib = _stale_report(("doc-sync", "docs/doc-sync.md", "hash_changed", "src/d.py"))
    patch_substrate["scope"] = _ScriptedScope(
        [
            _stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")),
            _CLEAN,  # per-doc re-check: graph fresh
            sib,  # fixpoint round 1: sibling re-staled
            _CLEAN,  # fixpoint round 2: clean
        ]
    )
    agent = FakeAgentRunner(project_root=project)
    result = run_harness(project, agent=agent, publisher=FakePublisher(), now_ts=NOW)
    assert result.flagged is False
    assert result.fixpoint_rounds >= 1
    # sibling was re-baselined via sync-update
    assert "doc-sync" in patch_substrate["sync_update_calls"]  # type: ignore[operator]


def test_fixpoint_round_cap_flags_when_never_stable(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # graph clears in per-doc loop, but a sibling stays stale forever => cap hit
    sib = _stale_report(("doc-sync", "docs/doc-sync.md", "hash_changed", "src/d.py"))
    reports = [
        _stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")),
        _CLEAN,  # per-doc re-check: graph fresh
    ] + [sib] * 30  # fixpoint never stabilises
    patch_substrate["scope"] = _ScriptedScope(reports)
    cfg = HarnessConfig(max_fixpoint_rounds=3)
    result = run_harness(
        project, agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(), now_ts=NOW, config=cfg,
    )
    assert result.fixpoint_rounds == 3
    assert result.flagged is True
    assert any("fixpoint not reached" in r for r in result.flagged_reasons)


# --------------------------------------------------------------------------- #
# Harness: gate
# --------------------------------------------------------------------------- #


def test_gate_failure_flags_pr(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py")), _CLEAN]
    )
    patch_substrate["ci_ok"] = False
    publisher = FakePublisher()
    result = run_harness(
        project, agent=FakeAgentRunner(project_root=project),
        publisher=publisher, now_ts=NOW,
    )
    assert result.gate_passed is False
    assert result.flagged is True
    assert any("beadloom ci failed" in r for r in result.flagged_reasons)
    assert publisher.published[0]["flagged"] is True


# --------------------------------------------------------------------------- #
# Harness: budget exceed
# --------------------------------------------------------------------------- #


def test_budget_turn_cap_flags(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "a.md").write_text("old", encoding="utf-8")
    (project / "docs" / "b.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [
            _stale_report(
                ("a", "docs/a.md", "hash_changed", "src/a.py"),
                ("b", "docs/b.md", "hash_changed", "src/b.py"),
            )
        ]
    )
    # max_total_turns=1 => after the first agent turn, budget is exceeded
    cfg = HarnessConfig(max_total_turns=1, per_doc_retries=0)
    result = run_harness(
        project, agent=FakeAgentRunner(project_root=project, write_marker=None),
        publisher=FakePublisher(), now_ts=NOW, config=cfg,
    )
    assert result.flagged is True
    assert any("budget exceeded" in r for r in result.flagged_reasons)


def test_budget_token_cap_flags(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "a.md").write_text("old", encoding="utf-8")
    (project / "docs" / "b.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [
            _stale_report(
                ("a", "docs/a.md", "hash_changed", "src/a.py"),
                ("b", "docs/b.md", "hash_changed", "src/b.py"),
            ),
            _CLEAN,
        ]
    )
    cfg = HarnessConfig(max_total_tokens=120, per_doc_retries=0)
    agent = FakeAgentRunner(project_root=project, input_tokens=100, output_tokens=50)
    result = run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW, config=cfg
    )
    # first doc: 150 tokens > 120 cap => second doc skipped, flagged
    assert result.flagged is True
    assert any("budget exceeded" in r for r in result.flagged_reasons)


# --------------------------------------------------------------------------- #
# Run-record emission (G9)
# --------------------------------------------------------------------------- #


def test_run_record_emitted_with_injected_ts_and_fact_tokens(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")), _CLEAN]
    )
    agent = FakeAgentRunner(
        project_root=project, model="qwen3.7-plus", input_tokens=1234, output_tokens=567
    )
    result = run_harness(
        project, agent=agent, publisher=FakePublisher(url="https://x/pr/9"), now_ts=NOW
    )
    runs = runs_store.load_runs(project)
    assert len(runs) == 1
    rec = runs[0]
    assert rec["ts"] == NOW
    assert rec["platform"] == "github"
    assert rec["docs_refreshed"] == ["docs/graph.md"]
    assert rec["input_tokens"] == 1234
    assert rec["output_tokens"] == 567
    assert rec["model"] == "qwen3.7-plus"
    assert rec["gate"] == "green"
    assert rec["pr_url"] == "https://x/pr/9"
    assert result.run_record is not None


def test_run_record_appends_not_overwrites(project: Path) -> None:
    existing = RunRecord(
        ts="2026-01-01T00:00:00+00:00",
        platform="gitlab",
        docs_refreshed=("docs/old.md",),
        input_tokens=1,
        output_tokens=2,
        model="m",
        gate="green",
        pr_url="https://x/mr/1",
    )
    runs_store.append_run(project, existing)
    runs_store.append_run(
        project,
        RunRecord(
            ts=NOW, platform="github", docs_refreshed=("docs/new.md",),
            input_tokens=3, output_tokens=4, model="m2", gate="flagged", pr_url="u",
        ),
    )
    runs = runs_store.load_runs(project)
    assert [r["ts"] for r in runs] == ["2026-01-01T00:00:00+00:00", NOW]


def test_run_record_to_json_shape() -> None:
    rec = RunRecord(
        ts=NOW, platform="gitlab", docs_refreshed=("a.md", "b.md"),
        input_tokens=10, output_tokens=20, model="qwen", gate="flagged",
        pr_url="https://x/mr/7",
    )
    assert rec.to_json() == {
        "ts": NOW,
        "platform": "gitlab",
        "docs_refreshed": ["a.md", "b.md"],
        "input_tokens": 10,
        "output_tokens": 20,
        "model": "qwen",
        "gate": "flagged",
        "pr_url": "https://x/mr/7",
    }


# --------------------------------------------------------------------------- #
# Seam protocol conformance
# --------------------------------------------------------------------------- #


def test_fakes_satisfy_protocols() -> None:
    assert isinstance(FakeAgentRunner(), AgentRunner)
    assert isinstance(FakePublisher(), ReviewPublisher)


def test_runs_store_load_handles_missing_and_empty(project: Path) -> None:
    assert runs_store.load_runs(project) == []
    runs_store.runs_store_path(project).write_text("", encoding="utf-8")
    assert runs_store.load_runs(project) == []
    runs_store.runs_store_path(project).write_text("{}", encoding="utf-8")
    assert runs_store.load_runs(project) == []
