"""Typed, immutable data structures for the AI tech-writer harness.

Pure data — no I/O, no subprocess. Every structure that crosses a seam (agent,
publisher, run-record store) is defined here so the contract is explicit and
mypy-checked end to end.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DriftItem:
    """One stale doc ref discovered by ``beadloom sync-check --json``.

    A ref may have several drifting code files; ``reasons`` is the set of drift
    kinds reported for it (symbols_changed / hash_changed / untracked).
    """

    ref_id: str
    doc_path: str
    reasons: tuple[str, ...]
    code_files: tuple[str, ...]

    def reason_summary(self) -> str:
        """A compact, human-readable drift summary for prompts / PR bodies."""
        reasons = ", ".join(self.reasons) if self.reasons else "stale"
        files = ", ".join(self.code_files) if self.code_files else "(no code files)"
        return f"{reasons} ({files})"


@dataclass(frozen=True)
class ContextPacket:
    """The per-doc input handed to the agent seam.

    Mirrors RFC Q4: everything the agent needs to rewrite one drifted doc,
    assembled deterministically by the harness.
    """

    ref_id: str
    doc_path: str
    current_content: str
    drift_reason: str
    docs_polish_json: dict[str, object]
    ctx: dict[str, object]
    why: str


@dataclass(frozen=True)
class AgentResult:
    """What the agent reports back after rewriting one doc.

    Token counts come from the model API's ``usage`` field — fact, not
    estimate (RFC Observability / G9).
    """

    rewritten_paths: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    model: str


@dataclass(frozen=True)
class GateResult:
    """Outcome of the ``beadloom ci`` acceptance gate."""

    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class PublishResult:
    """Outcome of the PR/MR publish seam."""

    url: str
    flagged: bool


@dataclass(frozen=True)
class RunRecord:
    """Append-only run-record (G9), persisted to the runs store.

    ``ts`` is injected (never ``now()``) so the record is deterministic in
    tests; token counts are facts taken from :class:`AgentResult`.
    """

    ts: str
    platform: str
    docs_refreshed: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    model: str
    gate: str
    pr_url: str

    def to_json(self) -> dict[str, object]:
        """Serialise to the on-disk record shape (stable key order)."""
        return {
            "ts": self.ts,
            "platform": self.platform,
            "docs_refreshed": list(self.docs_refreshed),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model": self.model,
            "gate": self.gate,
            "pr_url": self.pr_url,
        }


@dataclass(frozen=True)
class HarnessConfig:
    """Budget / caps + run identity (RFC Q3 / Q5).

    Caps act only as a runaway safety net (RFC Q2): exceeding any of them
    yields a *flagged* PR/MR, never a stuck job.
    """

    platform: str = "github"
    per_doc_retries: int = 2
    max_fixpoint_rounds: int = 10
    max_total_turns: int = 50
    max_total_tokens: int = 2_000_000


@dataclass
class HarnessResult:
    """Everything the harness produced, for the CI wrapper / observability.

    Mutable accumulator: the orchestrator fills it as it progresses.
    """

    no_op: bool = False
    docs_refreshed: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    gate_passed: bool = False
    flagged: bool = False
    flagged_reasons: list[str] = field(default_factory=list)
    pr_url: str = ""
    total_turns: int = 0
    fixpoint_rounds: int = 0
    run_record: RunRecord | None = None
