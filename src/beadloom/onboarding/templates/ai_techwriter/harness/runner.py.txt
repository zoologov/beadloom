"""The deterministic orchestrator (RFC Q3 loop).

    discover -> per-doc { agent (seam) -> sync-update -> re-check + retry }
    -> global fixpoint -> gate (beadloom ci) -> publish (seam) -> emit record.

Everything here is deterministic given the injected seams (agent, publisher)
and clock (``now_ts``). The agent and publisher are the only non-deterministic
/ network-touching parts and are passed in.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tools.ai_techwriter.commands import beadloom_ci, beadloom_sync_update
from tools.ai_techwriter.models import (
    DriftItem,
    HarnessConfig,
    HarnessResult,
    RunRecord,
)
from tools.ai_techwriter.packet import build_packet
from tools.ai_techwriter.runs_store import append_run
from tools.ai_techwriter.scope import discover_scope

if TYPE_CHECKING:
    from tools.ai_techwriter.seams import AgentRunner, ReviewPublisher

logger = logging.getLogger(__name__)

_BRANCH_PREFIX = "ai-techwriter/refresh-"


def run_harness(
    project_root: Path,
    *,
    agent: AgentRunner,
    publisher: ReviewPublisher,
    now_ts: str,
    config: HarnessConfig | None = None,
) -> HarnessResult:
    """Drive one full AI tech-writer run; return a structured result.

    *now_ts* is the injected timestamp stored in the run-record (never read
    from the wall clock here), mirroring ``site.py``'s ``now_ts``.
    """
    cfg = config or HarnessConfig()
    result = HarnessResult(model="")

    stale = discover_scope(project_root)
    if not stale:
        logger.info("ai-techwriter: 0 stale docs — no-op")
        result.no_op = True
        result.gate_passed = True
        return result

    _repair_each_doc(project_root, stale, agent=agent, cfg=cfg, result=result)
    _run_fixpoint(project_root, cfg=cfg, result=result)
    _run_gate(project_root, result=result)
    _publish(project_root, publisher=publisher, result=result)
    _emit_record(project_root, now_ts=now_ts, cfg=cfg, result=result)
    return result


def _repair_each_doc(
    project_root: Path,
    stale: list[DriftItem],
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    result: HarnessResult,
) -> None:
    """Per-doc loop: agent -> sync-update -> re-check, with bounded retry."""
    polish_report: dict[str, object] | None = None
    for item in stale:
        if _budget_exceeded(cfg, result):
            result.flagged = True
            result.flagged_reasons.append(f"budget exceeded before repairing {item.ref_id}")
            return
        ok = _repair_one_doc(
            project_root, item, agent=agent, cfg=cfg, result=result, polish_report=polish_report
        )
        if ok and item.doc_path not in result.docs_refreshed:
            result.docs_refreshed.append(item.doc_path)


def _repair_one_doc(
    project_root: Path,
    item: DriftItem,
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    result: HarnessResult,
    polish_report: dict[str, object] | None,
) -> bool:
    """Repair one doc with retry <= per_doc_retries; True if it went fresh."""
    attempts = cfg.per_doc_retries + 1
    for attempt in range(attempts):
        if _budget_exceeded(cfg, result):
            result.flagged = True
            result.flagged_reasons.append(f"budget exceeded mid-retry for {item.ref_id}")
            return False
        packet = build_packet(project_root, item, polish_report=polish_report)
        result.total_turns += 1
        try:
            agent_result = agent.run(packet)
        except (RuntimeError, OSError) as exc:
            logger.warning("agent failed for %s (attempt %d): %s", item.ref_id, attempt + 1, exc)
            continue
        result.input_tokens += agent_result.input_tokens
        result.output_tokens += agent_result.output_tokens
        if agent_result.model:
            result.model = agent_result.model
        beadloom_sync_update(project_root, item.ref_id)
        if _ref_is_fresh(project_root, item.ref_id):
            return True
        logger.info("ref %s still stale after attempt %d", item.ref_id, attempt + 1)
    result.flagged = True
    result.flagged_reasons.append(f"{item.ref_id} still stale after {attempts} attempts")
    return False


def _ref_is_fresh(project_root: Path, ref_id: str) -> bool:
    """True if *ref_id* has no stale pairs in a fresh sync-check."""
    return ref_id not in {item.ref_id for item in discover_scope(project_root)}


def _run_fixpoint(
    project_root: Path, *, cfg: HarnessConfig, result: HarnessResult
) -> None:
    """Global fixpoint: re-baseline newly re-staled siblings until stable 0.

    Bounded by ``max_fixpoint_rounds`` and no-progress detection (the
    re-stale-siblings invariant is bounded — RFC Q3).
    """
    for round_no in range(cfg.max_fixpoint_rounds):
        stale = discover_scope(project_root)
        if not stale:
            return
        result.fixpoint_rounds = round_no + 1
        for item in stale:
            beadloom_sync_update(project_root, item.ref_id)
        # No-progress guard: if the set did not shrink AND re-baselining didn't
        # clear it, the next round handles it; the round-cap bounds the loop.
    remaining = discover_scope(project_root)
    if remaining:
        result.flagged = True
        result.flagged_reasons.append(
            f"fixpoint not reached after {cfg.max_fixpoint_rounds} rounds: "
            + ", ".join(d.ref_id for d in remaining)
        )


def _run_gate(project_root: Path, *, result: HarnessResult) -> None:
    """Run ``beadloom ci``; record pass/fail (failure => flagged)."""
    gate = beadloom_ci(project_root)
    result.gate_passed = gate.ok
    if not gate.ok:
        result.flagged = True
        result.flagged_reasons.append(f"beadloom ci failed (rc={gate.returncode})")


def _publish(
    project_root: Path, *, publisher: ReviewPublisher, result: HarnessResult
) -> None:
    """Open the PR/MR (flagged iff the run is not clean-green)."""
    branch = _BRANCH_PREFIX + "-".join(
        sorted(Path(p).stem for p in result.docs_refreshed)
    )[:60] or f"{_BRANCH_PREFIX}docs"
    title = _title(result)
    body = _body(result)
    result.pr_url = publisher.publish(
        project_root=project_root,
        branch=branch,
        title=title,
        body=body,
        flagged=result.flagged,
    )


def _title(result: HarnessResult) -> str:
    """PR/MR title, flagged-prefixed when human attention is needed."""
    base = f"docs: AI tech-writer refresh ({len(result.docs_refreshed)} doc(s))"
    return f"⚠ needs human — {base}" if result.flagged else base


def _body(result: HarnessResult) -> str:
    """PR/MR body listing refreshed docs and any unresolved problems."""
    lines = ["Refreshed by the AI tech-writer harness.", "", "## Docs refreshed"]
    lines += [f"- {p}" for p in result.docs_refreshed] or ["- (none)"]
    lines += ["", f"Gate (`beadloom ci`): {'green' if result.gate_passed else 'FAILED'}"]
    if result.flagged:
        lines += ["", "## ⚠ Needs human attention"]
        lines += [f"- {r}" for r in result.flagged_reasons]
    lines += ["", f"Tokens: in={result.input_tokens} out={result.output_tokens}"]
    return "\n".join(lines)


def _emit_record(
    project_root: Path, *, now_ts: str, cfg: HarnessConfig, result: HarnessResult
) -> None:
    """Append the G9 run-record (ts injected; tokens are facts)."""
    record = RunRecord(
        ts=now_ts,
        platform=cfg.platform,
        docs_refreshed=tuple(result.docs_refreshed),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=result.model,
        gate="flagged" if result.flagged else "green",
        pr_url=result.pr_url,
    )
    append_run(project_root, record)
    result.run_record = record


def _budget_exceeded(cfg: HarnessConfig, result: HarnessResult) -> bool:
    """True when turns or total tokens exceed the runaway hard ceiling."""
    if result.total_turns >= cfg.max_total_turns:
        return True
    return result.input_tokens + result.output_tokens >= cfg.max_total_tokens
