"""Deterministic, platform-agnostic AI tech-writer harness (BDL-047 / F4.1).

Repo tooling (NOT ``src/beadloom`` core). Orchestrates the loop:

    discover stale docs -> build per-doc packet -> invoke agent (seam)
    -> re-baseline (``beadloom sync-update``) -> global fixpoint
    -> gate (``beadloom ci``) -> publish PR/MR (seam) -> emit run-record.

Everything is deterministic except the :class:`AgentRunner` (the per-doc
rewrite) and the :class:`ReviewPublisher` (the PR/MR step), both of which are
behind mockable seams so the whole harness is unit-testable without Goose, the
model, or network access. A clock/timestamp is injected (mirroring how
``site.py`` injects ``now_ts``) so run-records are deterministic in tests.
"""

from __future__ import annotations

from tools.ai_techwriter.cli import main
from tools.ai_techwriter.models import (
    AgentResult,
    ContextPacket,
    DriftItem,
    GateResult,
    HarnessConfig,
    HarnessResult,
    PublishResult,
    RunRecord,
)
from tools.ai_techwriter.provider import (
    ProviderConfig,
    default_recipe_path,
    qwen_provider,
)
from tools.ai_techwriter.runner import run_harness
from tools.ai_techwriter.scope import discover_scope
from tools.ai_techwriter.seams import (
    AgentRunner,
    FakeAgentRunner,
    FakePublisher,
    GitHubPRBranchPublisher,
    GitHubPublisher,
    GitLabPRBranchPublisher,
    GitLabPublisher,
    GooseAgentRunner,
    ReviewPublisher,
)

__all__ = [
    "AgentResult",
    "AgentRunner",
    "ContextPacket",
    "DriftItem",
    "FakeAgentRunner",
    "FakePublisher",
    "GateResult",
    "GitHubPRBranchPublisher",
    "GitHubPublisher",
    "GitLabPRBranchPublisher",
    "GitLabPublisher",
    "GooseAgentRunner",
    "HarnessConfig",
    "HarnessResult",
    "ProviderConfig",
    "PublishResult",
    "ReviewPublisher",
    "RunRecord",
    "default_recipe_path",
    "discover_scope",
    "main",
    "qwen_provider",
    "run_harness",
]
