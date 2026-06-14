"""S5 (BDL-052) — bounded-parallel sessions + 429/5xx back-off (seam-mocked).

The CI tech-writer fallback drives several Goose sessions concurrently with a
per-session exponential back-off, but its LOGIC / VERDICT / aggregation are
unchanged. These tests pin the new behaviour deterministically — NO network, no
real Goose, no real sleep (the ``sleep`` seam is injected):

* parallel result == sequential result for the same mocked sessions;
* a session retries on 429/5xx then succeeds within the attempt budget;
* a session gives up after the back-off budget is exhausted;
* the bounded pool never runs more than ``max_parallel`` sessions at once.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest

from beadloom.ai_agents.ai_techwriter import commands, runner, scope
from beadloom.ai_agents.ai_techwriter.backoff import (
    RateLimitError,
    backoff_delay,
    retry_with_backoff,
)
from beadloom.ai_agents.ai_techwriter.models import AgentResult, ContextPacket, HarnessConfig
from beadloom.ai_agents.ai_techwriter.runner import run_harness
from beadloom.ai_agents.ai_techwriter.seams import FakeAgentRunner, FakePublisher

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

NOW = "2026-06-10T00:00:00+00:00"


def _no_sleep(_seconds: float) -> None:
    """Injected sleep seam: never actually wait (deterministic + instant)."""


def _stale_report(*refs: tuple[str, str, str, str]) -> dict[str, object]:
    pairs: list[dict[str, object]] = [
        {"status": "stale", "ref_id": r, "doc_path": d, "code_path": c, "reason": reason}
        for r, d, reason, c in refs
    ]
    return {"summary": {"total": len(pairs), "ok": 0, "stale": len(pairs)}, "pairs": pairs}


_CLEAN: dict[str, object] = {"summary": {"total": 0, "ok": 0, "stale": 0}, "pairs": []}


class _ScriptedScope:
    """Returns a queued sequence of sync-check reports (last repeats), thread-safe."""

    def __init__(self, reports: list[dict[str, object]]) -> None:
        self._reports = reports
        self._lock = threading.Lock()
        self.calls = 0

    def __call__(self, project_root: Path, since: str | None = None) -> dict[str, object]:
        with self._lock:
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
    state: dict[str, object] = {"scope": _ScriptedScope([_CLEAN]), "ci_ok": True}

    def fake_sync_check(project_root: Path, *, since: str | None = None) -> dict[str, object]:
        return state["scope"](project_root, since)  # type: ignore[operator]

    def fake_polish(project_root: Path) -> dict[str, object]:
        return {"nodes": []}

    def fake_ctx(project_root: Path, ref_id: str) -> dict[str, object]:
        return {"focus": ref_id}

    def fake_why(project_root: Path, ref_id: str) -> str:
        return f"why {ref_id}"

    def fake_sync_update(project_root: Path, ref_id: str) -> commands.CommandResult:
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
# backoff helper (unit)
# --------------------------------------------------------------------------- #


def test_backoff_delay_is_exponential_and_capped() -> None:
    assert backoff_delay(0, base=1.0, max_delay=30.0) == 1.0
    assert backoff_delay(1, base=1.0, max_delay=30.0) == 2.0
    assert backoff_delay(2, base=1.0, max_delay=30.0) == 4.0
    assert backoff_delay(10, base=1.0, max_delay=30.0) == 30.0  # capped


def test_retry_with_backoff_retries_then_succeeds() -> None:
    waits: list[float] = []
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("429")
        return "ok"

    out = retry_with_backoff(flaky, attempts=4, base=1.0, sleep=waits.append)
    assert out == "ok"
    assert calls["n"] == 3
    assert waits == [1.0, 2.0]  # backed off before tries 2 and 3


def test_retry_with_backoff_gives_up_within_budget() -> None:
    calls = {"n": 0}

    def always_429() -> str:
        calls["n"] += 1
        raise RateLimitError("429")

    with pytest.raises(RateLimitError):
        retry_with_backoff(always_429, attempts=3, base=1.0, sleep=_no_sleep)
    assert calls["n"] == 3  # exactly the attempt budget, no more


def test_retry_with_backoff_passes_through_non_rate_limit() -> None:
    def boom() -> str:
        raise ValueError("not a rate limit")

    with pytest.raises(ValueError, match="not a rate limit"):
        retry_with_backoff(boom, attempts=3, sleep=_no_sleep)


# --------------------------------------------------------------------------- #
# parallel == sequential
# --------------------------------------------------------------------------- #


def _run(project: Path, state: dict[str, object], *, max_parallel: int) -> object:
    for name in ("a", "b", "c", "d"):
        (project / "docs" / f"{name}.md").write_text("old", encoding="utf-8")
    state["scope"] = _ScriptedScope(
        [
            _stale_report(
                ("a", "docs/a.md", "hash_changed", "src/a.py"),
                ("b", "docs/b.md", "hash_changed", "src/b.py"),
                ("c", "docs/c.md", "hash_changed", "src/c.py"),
                ("d", "docs/d.md", "hash_changed", "src/d.py"),
            ),
            _CLEAN,
        ]
    )
    cfg = HarnessConfig(max_parallel=max_parallel)
    agent = FakeAgentRunner(project_root=project, model="qwen-test")
    return run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW, config=cfg, sleep=_no_sleep
    )


def test_parallel_result_equals_sequential(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    seq = _run(project, patch_substrate, max_parallel=1)
    par = _run(project, patch_substrate, max_parallel=4)
    assert par.flagged is seq.flagged  # type: ignore[attr-defined]
    assert sorted(par.docs_refreshed) == sorted(seq.docs_refreshed)  # type: ignore[attr-defined]
    assert par.input_tokens == seq.input_tokens  # type: ignore[attr-defined]
    assert par.output_tokens == seq.output_tokens  # type: ignore[attr-defined]
    assert par.total_turns == seq.total_turns  # type: ignore[attr-defined]
    assert runner.classify_verdict(par) == runner.classify_verdict(seq)  # type: ignore[arg-type]


def test_docs_refreshed_preserve_stale_order(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    result = _run(project, patch_substrate, max_parallel=4)
    assert result.docs_refreshed == [  # type: ignore[attr-defined]
        "docs/a.md",
        "docs/b.md",
        "docs/c.md",
        "docs/d.md",
    ]


# --------------------------------------------------------------------------- #
# per-session back-off through the harness
# --------------------------------------------------------------------------- #


def test_session_recovers_after_429_backoff(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py")), _CLEAN]
    )
    # First two attempts 429, the third succeeds — within the 4-attempt budget.
    agent = FakeAgentRunner(project_root=project, rate_limit_first_n=2)
    result = run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW, sleep=_no_sleep
    )
    assert result.flagged is False
    assert result.docs_refreshed == ["docs/graph.md"]
    assert len(agent.calls) == 3  # 2 rate-limited + 1 success, one per-doc turn


def test_session_gives_up_after_backoff_budget(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    (project / "docs" / "graph.md").write_text("old", encoding="utf-8")
    patch_substrate["scope"] = _ScriptedScope(
        [_stale_report(("graph", "docs/graph.md", "hash_changed", "src/g.py"))]
    )
    # Always 429 → exhaust the back-off budget; per_doc_retries=0 so one attempt.
    cfg = HarnessConfig(per_doc_retries=0, backoff_attempts=3)
    agent = FakeAgentRunner(project_root=project, rate_limit_first_n=99)
    result = run_harness(
        project, agent=agent, publisher=FakePublisher(), now_ts=NOW, config=cfg, sleep=_no_sleep
    )
    assert result.flagged is True
    assert any("agent failed" in r for r in result.flagged_reasons)
    assert len(agent.calls) == 3  # exactly the back-off attempt budget for the one turn
    assert result.input_tokens == 0  # no tokens ever produced => infra-classifiable
    assert runner.classify_verdict(result) == runner.VERDICT_INFRA


# --------------------------------------------------------------------------- #
# max_parallel cap respected
# --------------------------------------------------------------------------- #


class _ConcurrencyProbe:
    """Agent double that records the peak number of concurrent ``run`` calls."""

    def __init__(self, *, project_root: Path, gate: threading.Barrier | None) -> None:
        self._project_root = project_root
        self._gate = gate
        self._lock = threading.Lock()
        self.current = 0
        self.peak = 0
        self.calls: list[ContextPacket] = []

    def run(self, packet: ContextPacket) -> AgentResult:
        with self._lock:
            self.calls.append(packet)
            self.current += 1
            self.peak = max(self.peak, self.current)
        try:
            if self._gate is not None:
                self._gate.wait(timeout=2.0)
        finally:
            with self._lock:
                self.current -= 1
        target = self._project_root / packet.doc_path
        target.write_text("refreshed", encoding="utf-8")
        return AgentResult(
            rewritten_paths=(packet.doc_path,), input_tokens=1, output_tokens=1, model="m"
        )


def test_pool_never_exceeds_max_parallel(
    project: Path, patch_substrate: dict[str, object]
) -> None:
    docs = [f"d{i}" for i in range(6)]
    for name in docs:
        (project / "docs" / f"{name}.md").write_text("old", encoding="utf-8")
    report = _stale_report(*[(n, f"docs/{n}.md", "hash_changed", f"src/{n}.py") for n in docs])
    patch_substrate["scope"] = _ScriptedScope([report, _CLEAN])
    cap = 3
    # A barrier of exactly `cap` parties only releases when `cap` sessions are
    # in flight together; if the pool ever tried to run more, peak would exceed
    # cap; if it ran fewer it would deadlock (caught by the 2s timeout).
    gate = threading.Barrier(cap)
    probe = _ConcurrencyProbe(project_root=project, gate=gate)
    cfg = HarnessConfig(max_parallel=cap)
    result = run_harness(
        project, agent=probe, publisher=FakePublisher(), now_ts=NOW, config=cfg, sleep=_no_sleep
    )
    assert probe.peak == cap  # ran exactly `cap` at a time, never more
    assert sorted(result.docs_refreshed) == sorted(f"docs/{n}.md" for n in docs)
