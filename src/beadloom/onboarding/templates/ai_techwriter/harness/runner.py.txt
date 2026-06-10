"""The deterministic orchestrator (RFC Q3 loop).

    discover -> per-doc { agent (seam) -> sync-update -> re-check + retry }
    -> global fixpoint -> gate (beadloom ci) -> publish (seam) -> emit record.

Everything here is deterministic given the injected seams (agent, publisher)
and clock (``now_ts``). The agent and publisher are the only non-deterministic
/ network-touching parts and are passed in.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from tools.ai_techwriter.commands import (
    beadloom_ci,
    beadloom_docs_polish_json,
    beadloom_sync_update,
)
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
    from collections.abc import Sequence

    from tools.ai_techwriter.seams import AgentRunner, ReviewPublisher

logger = logging.getLogger(__name__)

_BRANCH_PREFIX = "ai-techwriter/refresh-"
#: Max length of the slug *after* the prefix (keeps the full ref git/FS-safe).
_BRANCH_SLUG_MAX = 60
#: Above this many distinct docs, the per-doc slug pile is meaningless noise —
#: collapse to a deterministic count-based slug (``refresh-<n>-docs``) instead.
_BRANCH_MANY_DOCS = 5
#: Disambiguating segments are filesystem/git-safe lowercase ``a-z0-9-`` tokens.
_SLUG_UNSAFE = re.compile(r"[^a-z0-9]+")


def _doc_slug(doc_path: str) -> str:
    """A git/FS-safe disambiguating slug for one doc: ``parent-stem``.

    Using the parent directory + stem (not the bare stem) is what fixes BUG-E:
    many ``SPEC.md`` files no longer collapse into ``SPEC-SPEC-SPEC`` — each
    becomes e.g. ``graph-diff`` (``.../graph-diff/SPEC.md``). A bare-stem-only
    doc (no informative parent, e.g. ``README.md`` at the doc root) falls back
    to just the stem.
    """
    path = Path(doc_path)
    parent = path.parent.name
    stem = path.stem
    raw = f"{parent}-{stem}" if parent and parent not in {".", "docs"} else stem
    return _SLUG_UNSAFE.sub("-", raw.lower()).strip("-")


def _branch_name(docs_refreshed: Sequence[str]) -> str:
    """Deterministic, git/FS-safe branch name for the refreshed docs (BUG-E).

    * Empty -> ``refresh-docs``.
    * Many docs (> :data:`_BRANCH_MANY_DOCS`) -> ``refresh-<n>-docs`` (the
      per-doc slug pile would be noise and risk overflowing the cap).
    * Otherwise the deduped, sorted (order-independent) per-doc slugs joined by
      ``-``, capped at :data:`_BRANCH_SLUG_MAX` chars on a segment boundary.
    """
    count = len(docs_refreshed)
    if count == 0:
        return f"{_BRANCH_PREFIX}docs"
    if count > _BRANCH_MANY_DOCS:
        return f"{_BRANCH_PREFIX}{count}-docs"
    slugs = sorted({slug for p in docs_refreshed if (slug := _doc_slug(p))})
    slug = _cap_segments(slugs) or "docs"
    return f"{_BRANCH_PREFIX}{slug}"


def _cap_segments(slugs: list[str]) -> str:
    """Join *slugs* with ``-``, dropping whole segments to fit the length cap."""
    out: list[str] = []
    used = 0
    for seg in slugs:
        extra = len(seg) + (1 if out else 0)
        if used + extra > _BRANCH_SLUG_MAX:
            break
        out.append(seg)
        used += extra
    return "-".join(out)


def run_harness(
    project_root: Path,
    *,
    agent: AgentRunner,
    publisher: ReviewPublisher,
    now_ts: str,
    config: HarnessConfig | None = None,
    since: str | None = None,
) -> HarnessResult:
    """Drive one full AI tech-writer run; return a structured result.

    *now_ts* is the injected timestamp stored in the run-record (never read
    from the wall clock here), mirroring ``site.py``'s ``now_ts``.

    *since* (a git ref — the push's parent commit) is the AUTHORITATIVE drift
    baseline for the whole loop (BUG-I). It governs not only the *initial* scope
    discovery but every subsequent drift check — the per-doc freshness re-check
    AND the global fixpoint — so "is this doc still drifted relative to the
    parent?" is answered against the SAME baseline the scope used. On a fresh CI
    checkout the stored sync_state is always clean, so verifying against the
    stored state (the old behaviour) would falsely declare success; threading
    *since* through verification is what makes the loop actually prove the
    per-push drift was resolved. ``beadloom ci`` (:func:`_run_gate`) remains an
    additional gate, but the ``--since`` re-check is authoritative for this loop.
    """
    cfg = config or HarnessConfig()
    result = HarnessResult(model="")

    stale = discover_scope(project_root, since=since)
    if not stale:
        logger.info("ai-techwriter: 0 stale docs — no-op")
        result.no_op = True
        result.gate_passed = True
        return result

    _repair_each_doc(project_root, stale, agent=agent, cfg=cfg, result=result, since=since)
    _run_fixpoint(project_root, cfg=cfg, result=result, since=since)
    _run_gate(project_root, result=result)
    # Emit the run-record BEFORE publishing: the publisher's commit stages the
    # record file (``.beadloom/ai_techwriter_runs.json``) so it rides in the
    # PR/MR — the record must exist on disk before the commit. (The 0-stale
    # no-op above returns early: no record, no PR.)
    _emit_record(project_root, now_ts=now_ts, cfg=cfg, result=result)
    _publish(project_root, publisher=publisher, result=result)
    return result


def _repair_each_doc(
    project_root: Path,
    stale: list[DriftItem],
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    result: HarnessResult,
    since: str | None,
) -> None:
    """Per-doc loop: agent -> sync-update -> re-check, with bounded retry.

    A doc is added to ``result.docs_refreshed`` ONLY when the agent actually
    produced an edit for it (BUG-H) — a failed/empty agent run (goose rc!=0 →
    empty :class:`AgentResult`) never marks the doc refreshed.
    """
    # Fetch the whole ``docs polish`` report ONCE and reuse it across every doc
    # (RFC Q4 design intent), instead of re-shelling per doc in build_packet.
    polish_report: dict[str, object] | None = beadloom_docs_polish_json(project_root)
    for item in stale:
        if _budget_exceeded(cfg, result):
            result.flagged = True
            result.flagged_reasons.append(f"budget exceeded before repairing {item.ref_id}")
            return
        edited = _repair_one_doc(
            project_root,
            item,
            agent=agent,
            cfg=cfg,
            result=result,
            polish_report=polish_report,
            since=since,
        )
        if edited and item.doc_path not in result.docs_refreshed:
            result.docs_refreshed.append(item.doc_path)


def _repair_one_doc(
    project_root: Path,
    item: DriftItem,
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    result: HarnessResult,
    polish_report: dict[str, object] | None,
    since: str | None,
) -> bool:
    """Repair one doc with retry <= per_doc_retries.

    Returns True iff the agent produced a real edit for this doc (non-empty
    rewritten paths) — that, not mere stored-state freshness, is what marks the
    doc refreshed (BUG-H). Freshness is verified against *since* (the parent
    commit), the authoritative baseline (BUG-I); a doc that never goes
    fresh-since-ref after all attempts is flagged. An agent run that produced no
    edit at all across every attempt is flagged as an agent failure.
    """
    attempts = cfg.per_doc_retries + 1
    edited = False
    for attempt in range(attempts):
        if _budget_exceeded(cfg, result):
            result.flagged = True
            result.flagged_reasons.append(f"budget exceeded mid-retry for {item.ref_id}")
            return edited
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
        if not agent_result.rewritten_paths:
            # goose rc!=0 → empty result: no edit produced, nothing to verify.
            logger.warning("agent produced no edit for %s (attempt %d)", item.ref_id, attempt + 1)
            continue
        edited = True
        beadloom_sync_update(project_root, item.ref_id)
        if _ref_is_fresh(project_root, item.ref_id, since=since):
            return True
        logger.info("ref %s still stale after attempt %d", item.ref_id, attempt + 1)
    if not edited:
        result.flagged = True
        result.flagged_reasons.append(f"agent failed for {item.ref_id} after {attempts} attempts")
    else:
        result.flagged = True
        result.flagged_reasons.append(f"{item.ref_id} still stale after {attempts} attempts")
    return edited


def _ref_is_fresh(project_root: Path, ref_id: str, *, since: str | None) -> bool:
    """True if *ref_id* has no stale pairs in a sync-check against *since*.

    Verifies against the same ``--since`` baseline the scope used (BUG-I), so a
    fresh-checkout stored-state re-baseline cannot mask unresolved per-push drift.
    """
    return ref_id not in {item.ref_id for item in discover_scope(project_root, since=since)}


def _run_fixpoint(
    project_root: Path, *, cfg: HarnessConfig, result: HarnessResult, since: str | None
) -> None:
    """Global fixpoint: re-baseline newly re-staled siblings until stable 0.

    Terminates on whichever fires first (RFC Q3 "no-progress / round-cap"):

    * **natural**: the stale set reaches 0 (clean) — success;
    * **no-progress**: re-baselining a round leaves the *same* stale ref-id set
      it started with (the set stopped shrinking and ``sync-update`` cleared
      nothing) — flag immediately, no point spending the remaining rounds;
    * **round-cap**: ``max_fixpoint_rounds`` exhausted — flag.
    """
    prev_refs: set[str] | None = None
    for round_no in range(cfg.max_fixpoint_rounds):
        stale = discover_scope(project_root, since=since)
        if not stale:
            return
        result.fixpoint_rounds = round_no + 1
        cur_refs = {item.ref_id for item in stale}
        for item in stale:
            beadloom_sync_update(project_root, item.ref_id)
        if cur_refs == prev_refs:
            # No-progress: this round saw the identical stale set the previous
            # round re-baselined, yet it is still stale — further rounds cannot
            # help. Flag now rather than burning the remaining round budget.
            _flag_fixpoint_stuck(result, cfg, stale)
            return
        prev_refs = cur_refs
    remaining = discover_scope(project_root, since=since)
    if remaining:
        _flag_fixpoint_stuck(result, cfg, remaining)


def _flag_fixpoint_stuck(
    result: HarnessResult, cfg: HarnessConfig, remaining: list[DriftItem]
) -> None:
    """Flag a fixpoint that never reached a clean state (no-progress / cap)."""
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
    branch = _branch_name(result.docs_refreshed)
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
