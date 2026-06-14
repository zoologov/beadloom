# beadloom:domain=ai_agents
# beadloom:feature=ai-techwriter
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
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.ai_agents.ai_techwriter.backoff import RateLimitError, retry_with_backoff
from beadloom.ai_agents.ai_techwriter.commands import (
    beadloom_ci,
    beadloom_docs_polish_json,
    beadloom_sync_update,
)
from beadloom.ai_agents.ai_techwriter.models import (
    AgentResult,
    ContextPacket,
    DriftItem,
    HarnessConfig,
    HarnessResult,
    RunRecord,
)
from beadloom.ai_agents.ai_techwriter.packet import build_packet
from beadloom.ai_agents.ai_techwriter.runs_store import append_run
from beadloom.ai_agents.ai_techwriter.scope import discover_scope

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from beadloom.ai_agents.ai_techwriter.seams import AgentRunner, ReviewPublisher

logger = logging.getLogger(__name__)

#: The three CI verdicts (BDL-050). ``ok`` / ``flagged`` gate as before; ``infra``
#: is the new "couldn't run" bucket that must NOT block a PR (a dead self-hosted
#: runner / an exhausted model quota is not a doc problem).
VERDICT_OK = "ok"
VERDICT_FLAGGED = "flagged"
VERDICT_INFRA = "infra"


def classify_verdict(result: HarnessResult) -> str:
    """Classify a finished run into ``ok`` / ``flagged`` / ``infra`` (BDL-050).

    The discriminator between a genuine doc problem and an infra failure is
    **whether the model ever produced output** (``input_tokens + output_tokens``):

    * **ok** — a 0-stale no-op OR a clean run (``not flagged``). Nothing to gate.
    * **flagged** (BLOCK) — ``flagged`` AND the agent produced tokens
      (``> 0``): the model ran but the docs aren't clean (post-refresh
      ``beadloom ci`` red, fixpoint not reached, or budget exceeded mid-work).
      A real "needs human" → the CI required check goes red.
    * **infra** (DON'T block) — ``flagged`` AND **no tokens at all** (``== 0``):
      every agent attempt failed before producing a single token (process /
      goose error, provider 5xx / timeout, exhausted quota). It *couldn't run*,
      so blocking the PR would freeze all merges on dead infra.

    Conservative by construction: ``tokens == 0`` ⇒ ``infra``; *any* token ⇒
    the ``flagged`` verdict stands. A misclassified ``infra`` is made loud by the
    CI annotation, so a human re-runs rather than silently shipping stale docs.
    """
    if not result.flagged:
        return VERDICT_OK
    if result.input_tokens + result.output_tokens > 0:
        return VERDICT_FLAGGED
    return VERDICT_INFRA


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
    sleep: Callable[[float], None] = time.sleep,
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

    _repair_each_doc(
        project_root, stale, agent=agent, cfg=cfg, result=result, since=since, sleep=sleep
    )
    _run_fixpoint(project_root, cfg=cfg, result=result, since=since)
    _run_gate(project_root, result=result)
    # Emit the run-record BEFORE publishing: the publisher's commit stages the
    # record file (``.beadloom/ai_techwriter_runs.json``) so it rides in the
    # PR/MR — the record must exist on disk before the commit. (The 0-stale
    # no-op above returns early: no record, no PR.)
    _emit_record(project_root, now_ts=now_ts, cfg=cfg, result=result)
    _publish(project_root, publisher=publisher, result=result)
    return result


@dataclass
class _DocWork:
    """Per-doc, session-isolated accumulator (no shared :class:`HarnessResult`).

    Each Goose session writes ONLY into its own ``_DocWork``; the harness folds
    them back into the single :class:`HarnessResult` in deterministic stale
    order (:func:`_fold_doc`), so the aggregate is identical whether the pool
    ran the sessions sequentially (``max_parallel=1``) or concurrently.
    """

    ref_id: str
    doc_path: str
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    edited: bool = False
    flagged_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Budget:
    """Folded-so-far totals captured at submit time (the per-doc budget snapshot).

    A session checks its own accumulation PLUS this prior snapshot against the
    runaway caps, mirroring the sequential mid-retry guard against the shared
    result — but without touching shared state, so it is thread-safe.
    """

    prior_turns: int
    prior_tokens: int


def _repair_each_doc(
    project_root: Path,
    stale: list[DriftItem],
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    result: HarnessResult,
    since: str | None,
    sleep: Callable[[float], None],
) -> None:
    """Bounded-parallel per-doc repair, folded deterministically into *result*.

    Replaces the old sequential loop with a :class:`ThreadPoolExecutor` capped
    at ``cfg.max_parallel`` (default 3, RAM-aware for the 8GB VPS): each doc gets
    its OWN Goose session (its own :class:`_DocWork`), wrapped in 429/5xx
    exponential back-off. Sessions are submitted in stale order, gated by the
    same between-doc budget check as before (computed from the folded-so-far
    totals), then their results are folded back IN ORDER — so the per-doc
    outcomes, the token/turn aggregate, and the verdict are IDENTICAL to the
    sequential behaviour for the same (mocked) sessions.
    """
    # Fetch the whole ``docs polish`` report ONCE and reuse it across every doc
    # (RFC Q4 design intent), instead of re-shelling per doc in build_packet.
    polish_report: dict[str, object] | None = beadloom_docs_polish_json(project_root)
    workers = max(cfg.max_parallel, 1)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        _dispatch_and_fold(
            pool,
            project_root,
            stale,
            agent=agent,
            cfg=cfg,
            result=result,
            polish_report=polish_report,
            since=since,
            sleep=sleep,
        )


def _dispatch_and_fold(
    pool: ThreadPoolExecutor,
    project_root: Path,
    stale: list[DriftItem],
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    result: HarnessResult,
    polish_report: dict[str, object] | None,
    since: str | None,
    sleep: Callable[[float], None],
) -> None:
    """Submit docs into a bounded window (<= ``max_parallel``) + fold IN ORDER.

    At most ``cfg.max_parallel`` sessions are in flight at once (the pool size
    plus this window cap guarantee it); the FIFO queue is folded in stale order
    so the aggregate is order-deterministic. The between-doc budget gate is the
    same as the old sequential one (computed from the folded-so-far totals);
    once it fires we stop submitting and flag, exactly as before.
    """
    window = max(cfg.max_parallel, 1)
    pending: deque[Future[_DocWork]] = deque()
    for item in stale:
        if _budget_exceeded(cfg, result):
            _budget_stop(result, item.ref_id, pending)
            return
        budget = _Budget(prior_turns=result.total_turns, prior_tokens=_total_tokens(result))
        pending.append(
            pool.submit(
                _repair_one_doc,
                project_root,
                item,
                agent=agent,
                cfg=cfg,
                polish_report=polish_report,
                since=since,
                budget=budget,
                sleep=sleep,
            )
        )
        if len(pending) >= window:
            _fold_doc(result, pending.popleft().result())
    _drain(pending, result)
    _flag_if_budget_overrun(cfg, result)


def _flag_if_budget_overrun(cfg: HarnessConfig, result: HarnessResult) -> None:
    """Flag a runaway-cap overrun detected only after folding the window.

    The between-doc pre-submit guard catches overruns deterministically when the
    folded-so-far total already exceeds a cap (the sequential / ``max_parallel=1``
    case). When several sessions ran concurrently in one window their combined
    usage can cross a cap only once all are folded — surface that honestly here
    (idempotent: never double-adds a budget reason).
    """
    if not _budget_exceeded(cfg, result):
        return
    if any("budget exceeded" in reason for reason in result.flagged_reasons):
        return
    result.flagged = True
    result.flagged_reasons.append("budget exceeded")


def _budget_stop(
    result: HarnessResult, ref_id: str, pending: deque[Future[_DocWork]]
) -> None:
    """Flag a budget-exceeded stop: fold the in-flight window, then flag + halt.

    Mirrors the sequential between-doc budget guard: the runaway cap tripped, so
    no further docs are submitted. The already-submitted window is still folded
    (its sessions ran) so the run-record stays honest.
    """
    _drain(pending, result)
    result.flagged = True
    result.flagged_reasons.append(f"budget exceeded before repairing {ref_id}")


def _drain(pending: deque[Future[_DocWork]], result: HarnessResult) -> None:
    """Fold every still-pending session in FIFO (stale) order."""
    while pending:
        _fold_doc(result, pending.popleft().result())


def _fold_doc(result: HarnessResult, work: _DocWork) -> None:
    """Merge one session's isolated :class:`_DocWork` into the shared result.

    Deterministic given the call order: tokens/turns accumulate, a real edit
    appends the doc once (BUG-H), and any per-doc flag reason is carried over.
    """
    result.total_turns += work.turns
    result.input_tokens += work.input_tokens
    result.output_tokens += work.output_tokens
    if work.model:
        result.model = work.model
    if work.edited and work.doc_path not in result.docs_refreshed:
        result.docs_refreshed.append(work.doc_path)
    if work.flagged_reasons:
        result.flagged = True
        result.flagged_reasons.extend(work.flagged_reasons)


def _repair_one_doc(
    project_root: Path,
    item: DriftItem,
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    polish_report: dict[str, object] | None,
    since: str | None,
    budget: _Budget,
    sleep: Callable[[float], None],
) -> _DocWork:
    """Repair one doc in its own session (retry <= per_doc_retries); return its work.

    Pure w.r.t. the shared :class:`HarnessResult`: it accumulates into a fresh
    :class:`_DocWork` so it is thread-safe in the pool. ``work.edited`` is True
    iff the agent produced a real edit (non-empty rewritten paths) — that, not
    mere stored-state freshness, is what marks the doc refreshed (BUG-H).
    Freshness is verified against *since* (BUG-I). 429/5xx back-off is applied
    per attempt; a doc that never goes fresh, or never edits, is flagged.
    """
    work = _DocWork(ref_id=item.ref_id, doc_path=item.doc_path)
    attempts = cfg.per_doc_retries + 1
    for attempt in range(attempts):
        if _doc_budget_exceeded(cfg, budget, work):
            work.flagged_reasons.append(f"budget exceeded mid-retry for {item.ref_id}")
            return work
        if _run_one_attempt(
            project_root, item, agent=agent, cfg=cfg, polish_report=polish_report,
            since=since, work=work, attempt=attempt, sleep=sleep,
        ):
            return work
    _flag_doc_outcome(work, item, attempts)
    return work


def _run_one_attempt(
    project_root: Path,
    item: DriftItem,
    *,
    agent: AgentRunner,
    cfg: HarnessConfig,
    polish_report: dict[str, object] | None,
    since: str | None,
    work: _DocWork,
    attempt: int,
    sleep: Callable[[float], None],
) -> bool:
    """One agent->sync-update->re-check attempt; True iff the doc went fresh."""
    packet = build_packet(project_root, item, polish_report=polish_report)
    work.turns += 1
    agent_result = _call_agent_with_backoff(agent, packet, cfg=cfg, sleep=sleep, attempt=attempt)
    if agent_result is None:
        return False  # no edit produced this attempt (failure / give-up / empty)
    work.input_tokens += agent_result.input_tokens
    work.output_tokens += agent_result.output_tokens
    if agent_result.model:
        work.model = agent_result.model
    if not agent_result.rewritten_paths:
        logger.warning("agent produced no edit for %s (attempt %d)", item.ref_id, attempt + 1)
        return False
    work.edited = True
    beadloom_sync_update(project_root, item.ref_id)
    if _ref_is_fresh(project_root, item.ref_id, since=since):
        return True
    logger.info("ref %s still stale after attempt %d", item.ref_id, attempt + 1)
    return False


def _call_agent_with_backoff(
    agent: AgentRunner,
    packet: ContextPacket,
    *,
    cfg: HarnessConfig,
    sleep: Callable[[float], None],
    attempt: int,
) -> AgentResult | None:
    """Run the agent with 429/5xx exponential back-off; None on give-up/failure.

    A :class:`RateLimitError` (provider 429/5xx) retries with exponential
    back-off inside this single attempt's budget; exhausting it (or any other
    ``RuntimeError`` / ``OSError``) is logged and treated as a no-edit attempt
    (return None) — exactly as a failed sequential agent run was.
    """

    def _call() -> AgentResult:
        return agent.run(packet)

    try:
        return retry_with_backoff(
            _call, attempts=cfg.backoff_attempts, base=cfg.backoff_base, sleep=sleep
        )
    except RateLimitError as exc:
        logger.warning(
            "agent rate-limited for %s (attempt %d): %s", packet.ref_id, attempt + 1, exc
        )
        return None
    except (RuntimeError, OSError) as exc:
        logger.warning("agent failed for %s (attempt %d): %s", packet.ref_id, attempt + 1, exc)
        return None


def _flag_doc_outcome(work: _DocWork, item: DriftItem, attempts: int) -> None:
    """Record the per-doc flag reason after the retry budget is spent."""
    if not work.edited:
        work.flagged_reasons.append(f"agent failed for {item.ref_id} after {attempts} attempts")
    else:
        work.flagged_reasons.append(f"{item.ref_id} still stale after {attempts} attempts")


def _doc_budget_exceeded(cfg: HarnessConfig, budget: _Budget, work: _DocWork) -> bool:
    """True when this session's own usage + the submit-time snapshot trips a cap."""
    if budget.prior_turns + work.turns >= cfg.max_total_turns:
        return True
    used = budget.prior_tokens + work.input_tokens + work.output_tokens
    return used >= cfg.max_total_tokens


def _total_tokens(result: HarnessResult) -> int:
    """Tokens accumulated into the shared result so far."""
    return result.input_tokens + result.output_tokens


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
