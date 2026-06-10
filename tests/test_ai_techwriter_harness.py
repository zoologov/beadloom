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
    AgentResult,
    ContextPacket,
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
    """Returns a queued sequence of sync-check reports (last repeats).

    Records the ``since`` ref passed on every call so tests can assert the
    harness threads ``--since`` through every drift check (BUG-I).
    """

    def __init__(self, reports: list[dict[str, object]]) -> None:
        self._reports = reports
        self.calls = 0
        self.since_args: list[str | None] = []

    def __call__(self, project_root: Path, since: str | None = None) -> dict[str, object]:
        idx = min(self.calls, len(self._reports) - 1)
        self.calls += 1
        self.since_args.append(since)
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

    def fake_sync_check(
        project_root: Path, *, since: str | None = None
    ) -> dict[str, object]:
        return state["scope"](project_root, since)  # type: ignore[operator]

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
    monkeypatch.setattr(runner, "beadloom_docs_polish_json", fake_polish)
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
    # ref stays stale forever => retries exhausted. The agent DOES edit (writes a
    # marker) but the drift never clears, so this exercises the "edited but still
    # stale after N attempts" path (distinct from the BUG-H no-edit path).
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py"))]
    )
    cfg = HarnessConfig(per_doc_retries=2)
    agent = FakeAgentRunner(project_root=project)
    publisher = FakePublisher()
    result = run_harness(
        project, agent=agent, publisher=publisher, now_ts=NOW, config=cfg
    )
    # 1 initial + 2 retries = 3 agent calls
    assert len(agent.calls) == 3
    assert result.flagged is True
    assert any("still stale" in r for r in result.flagged_reasons)
    # The doc WAS edited (agent produced rewritten paths) so it is honestly listed.
    assert result.docs_refreshed == ["docs/graph.md"]
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


def test_fixpoint_no_progress_flags_before_round_cap(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # graph clears in per-doc loop, but a sibling stays stale forever with the
    # IDENTICAL stale set => the no-progress guard flags at round 2, before the
    # round cap (3) is reached.
    sib = _stale_report(("doc-sync", "docs/doc-sync.md", "hash_changed", "src/d.py"))
    reports = [
        _stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")),
        _CLEAN,  # per-doc re-check: graph fresh
    ] + [sib] * 30  # fixpoint never stabilises, same set each round
    patch_substrate["scope"] = _ScriptedScope(reports)
    cfg = HarnessConfig(max_fixpoint_rounds=3)
    result = run_harness(
        project, agent=FakeAgentRunner(project_root=project),
        publisher=FakePublisher(), now_ts=NOW, config=cfg,
    )
    assert result.fixpoint_rounds == 2  # no-progress break, not the cap
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
    # The record is committed INSIDE the PR (emitted before publish), so it
    # cannot yet know its own PR URL: the on-disk record has an empty pr_url.
    # The live PR URL is still surfaced on the in-memory result for the CI log.
    assert rec["pr_url"] == ""
    assert result.run_record is not None
    assert result.pr_url == "https://x/pr/9"


def test_emit_record_runs_before_publish(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """BUG-B regression: the run-record must exist on disk BEFORE the publisher
    commits, so it rides in the PR. We assert the record file already exists at
    the moment ``publish`` is invoked."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")), _CLEAN]
    )

    seen_at_publish: dict[str, bool] = {}

    class _OrderProbePublisher(FakePublisher):
        def publish(self, **kwargs: object) -> str:  # type: ignore[override]
            seen_at_publish["record_existed"] = runs_store.runs_store_path(project).exists()
            return super().publish(**kwargs)  # type: ignore[arg-type]

    result = run_harness(
        project,
        agent=FakeAgentRunner(project_root=project),
        publisher=_OrderProbePublisher(),
        now_ts=NOW,
    )
    assert result.no_op is False
    assert seen_at_publish["record_existed"] is True


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


# --------------------------------------------------------------------------- #
# BUG-E: branch-name dedup / disambiguation
# --------------------------------------------------------------------------- #


def test_branch_name_dedupes_duplicate_stems() -> None:
    """BUG-E: many ``SPEC.md`` files must NOT produce refresh-SPEC-SPEC-SPEC.

    Disambiguate with the parent-dir + stem and dedupe, so the slug is stable
    and filesystem/git-safe.
    """
    docs = [
        "docs/domains/graph/features/graph-diff/SPEC.md",
        "docs/domains/context-oracle/features/search/SPEC.md",
        "docs/domains/doc-sync/features/docs-audit/SPEC.md",
    ]
    branch = runner._branch_name(docs)
    assert branch.startswith("ai-techwriter/refresh-")
    assert "SPEC-SPEC-SPEC" not in branch
    # Each doc contributes a DISTINCT, identifiable segment (parent-dir + stem).
    assert "graph-diff" in branch
    assert "search" in branch or "docs-audit" in branch


def test_branch_name_is_deterministic_and_bounded() -> None:
    docs = [f"docs/d{i}/SPEC.md" for i in range(40)]
    a = runner._branch_name(docs)
    b = runner._branch_name(list(reversed(docs)))
    assert a == b  # order-independent (deterministic)
    assert len(a) <= len("ai-techwriter/refresh-") + 60
    assert "SPEC-SPEC" not in a


def test_branch_name_collapses_when_too_many_docs() -> None:
    docs = [f"docs/domains/d{i}/README.md" for i in range(30)]
    branch = runner._branch_name(docs)
    # Falls back to a count-based slug rather than an unbounded stem pile.
    assert "30-docs" in branch


def test_branch_name_empty_falls_back_to_docs() -> None:
    assert runner._branch_name([]) == "ai-techwriter/refresh-docs"


def test_runs_store_load_handles_missing_and_empty(project: Path) -> None:
    assert runs_store.load_runs(project) == []
    runs_store.runs_store_path(project).write_text("", encoding="utf-8")
    assert runs_store.load_runs(project) == []
    runs_store.runs_store_path(project).write_text("{}", encoding="utf-8")
    assert runs_store.load_runs(project) == []


# --------------------------------------------------------------------------- #
# BUG-H: a failed/empty agent run must NOT be recorded as a refresh / green
# --------------------------------------------------------------------------- #


class _EmptyAgentRunner:
    """An agent whose run always returns an EMPTY result (no rewritten paths).

    Models the live BUG-H case: ``goose run failed: Invalid recipe`` →
    ``GooseAgentRunner`` returns ``_empty_result`` (rc!=0, no raise). The harness
    must treat this as "no edit produced" — never mark the doc refreshed/green.
    """

    def __init__(self, *, model: str = "qwen-empty") -> None:
        self._model = model
        self.calls: list[ContextPacket] = []

    def run(self, packet: ContextPacket) -> AgentResult:
        self.calls.append(packet)
        return AgentResult(
            rewritten_paths=(), input_tokens=0, output_tokens=0, model=self._model
        )


def test_empty_agent_result_does_not_mark_doc_refreshed_or_green(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """BUG-H: every agent attempt returns an empty result (goose rc!=0). Even if
    a fresh-checkout sync-check would report clean, the doc must NOT be counted
    as refreshed, the run must be flagged, and the gate must NOT be green."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # The sync-check is CLEAN after the (no-op) attempt — the G12 blindness that
    # would falsely declare success on a fresh CI checkout.
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")), _CLEAN]
    )
    cfg = HarnessConfig(per_doc_retries=2)
    agent = _EmptyAgentRunner()
    publisher = FakePublisher()
    result = run_harness(
        project, agent=agent, publisher=publisher, now_ts=NOW, config=cfg
    )
    assert result.docs_refreshed == []  # no false refresh
    assert result.flagged is True
    assert any("agent" in r.lower() and "graph" in r for r in result.flagged_reasons)
    # Run-record honestly reflects the failure: no docs, gate flagged.
    assert result.run_record is not None
    assert result.run_record.docs_refreshed == ()
    assert result.run_record.gate == "flagged"
    assert publisher.published[0]["flagged"] is True


def test_agent_failure_then_real_edit_marks_doc_refreshed(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """BUG-H mirror: when the agent ACTUALLY produces an edit, the doc IS marked
    refreshed and the run is green — the honest-success path still works."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")), _CLEAN]
    )
    agent = FakeAgentRunner(project_root=project, model="qwen-test")
    result = run_harness(project, agent=agent, publisher=FakePublisher(), now_ts=NOW)
    assert result.docs_refreshed == ["docs/graph.md"]
    assert result.flagged is False
    assert result.run_record is not None
    assert result.run_record.gate == "green"


# --------------------------------------------------------------------------- #
# BUG-I: --since is threaded through the fixpoint + verification, and is the
# AUTHORITATIVE drift check for this loop.
# --------------------------------------------------------------------------- #


def test_since_is_threaded_through_every_drift_check(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """BUG-I: ``--since <ref>`` governs not only the initial scope discovery but
    EVERY subsequent drift check (per-doc re-verify + fixpoint), so a fresh CI
    checkout cannot mask per-push drift in the verification path."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    scripted = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py")), _CLEAN]
    )
    patch_substrate["scope"] = scripted
    agent = FakeAgentRunner(project_root=project)
    run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW, since="abc123"
    )
    # Every sync-check (discovery, per-doc re-check, fixpoint) used the same ref.
    assert scripted.since_args  # at least one call happened
    assert all(s == "abc123" for s in scripted.since_args)


def test_doc_still_drifted_since_ref_after_repair_flags_not_green(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    """BUG-I: the AUTHORITATIVE check is ``--since <ref>``. If the doc is still
    drifted relative to the parent commit after repair+retries — even though the
    agent 'edited' and a stored-baseline check would be clean — the run is
    flagged, never green."""
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    # --since always reports graph stale (still drifted relative to parent).
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "symbols_changed", "src/g.py"))]
    )
    cfg = HarnessConfig(per_doc_retries=2)
    agent = FakeAgentRunner(project_root=project)  # writes a marker each call
    publisher = FakePublisher()
    result = run_harness(
        project, agent=agent, publisher=publisher, now_ts=NOW, config=cfg, since="parent-sha"
    )
    # The agent DID produce an edit each attempt, so the doc is honestly listed
    # as refreshed — but the AUTHORITATIVE --since check never goes clean, so the
    # run is flagged, not green.
    assert result.docs_refreshed == ["docs/graph.md"]
    assert result.flagged is True
    assert any("still" in r and "graph" in r for r in result.flagged_reasons)
    assert result.run_record is not None
    assert result.run_record.gate == "flagged"
