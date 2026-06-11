"""Thin CLI entrypoint CI invokes around the one harness (RFC Q5).

``python -m tools.ai_techwriter --platform github|gitlab [--dry-run]``

This is the single entrypoint BOTH CI wrappers call — only the trigger, the
secret naming, and the ``--platform`` flag differ (GitHub workflow vs GitLab
job). The wrapper itself is deliberately *thin*: it only assembles the seams
(provider, Goose agent, the platform PR/MR publisher), injects a real
timestamp, and delegates the whole deterministic loop to
:func:`tools.ai_techwriter.runner.run_harness`.

The builders (:func:`_build_agent`, :func:`_build_publisher`, :func:`_default_now`)
and ``run_harness`` are injectable (via the Click context ``obj``) so the
arg-wiring is unit-testable with every non-deterministic / network-touching
seam faked — no Goose, no model, no git, no network.

Exit codes (for CI visibility) — driven by the harness *verdict* (BDL-050,
:func:`tools.ai_techwriter.runner.classify_verdict`), NOT by the bare
``result.flagged``. The discriminator between a genuine doc failure and an
infra failure is whether the model ever produced output (``tokens > 0``):

* ``0`` — **ok**: no-op (0 stale) **or** a clean green run (gate green); **or**
  **infra**: the agent never ran (``tokens == 0`` — a dead self-hosted runner,
  a provider 5xx / timeout, or an exhausted quota). An infra failure is *not* a
  doc problem, so it MUST NOT block the PR — instead the entrypoint emits a
  GitHub ``::warning::`` annotation and posts a best-effort PR/MR note saying the
  docs were NOT checked on this push.
* ``1`` — **flagged**: the model ran (``tokens > 0``) but the docs still aren't
  clean (post-refresh ``beadloom ci`` red, fixpoint not reached, or budget
  exceeded mid-work). A real "needs human" → the CI required check goes red.

So the required ``ai-techwriter`` check is red ONLY on a genuine ``flagged``
verdict; dead infra / an exhausted \\$30 quota never freezes merges.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, cast

import click

from tools.ai_techwriter.models import HarnessConfig, HarnessResult
from tools.ai_techwriter.provider import ProviderConfig, default_recipe_path, qwen_provider
from tools.ai_techwriter.runner import (
    VERDICT_FLAGGED,
    VERDICT_INFRA,
    classify_verdict,
)
from tools.ai_techwriter.runner import run_harness as _real_run_harness
from tools.ai_techwriter.seams import (
    CommentPublisher,
    GitHubPRBranchPublisher,
    GitHubPublisher,
    GitLabPRBranchPublisher,
    GitLabPublisher,
    GooseAgentRunner,
    ReviewPublisher,
)

if TYPE_CHECKING:
    from tools.ai_techwriter.seams import AgentRunner

#: The PR/MR note + CI annotation copy for the BDL-050 ``infra`` verdict. Kept as
#: a constant so the annotation and the comment carry the identical message.
_INFRA_MESSAGE = (
    "could not run (infra) — docs were NOT checked on this PR; "
    "re-run before relying on freshness"
)

#: Supported CI platforms (RFC Q5 table) — both first-class.
PLATFORMS = ("github", "gitlab")

#: Publish targets (BDL-049). ``branch-pr`` is the original behaviour (cut a new
#: branch + open a PR/MR) — kept for ``workflow_dispatch`` / manual runs with no
#: PR context. ``pr-branch`` commits the refresh onto the EXISTING PR head
#: branch + posts a comment (the ``on: pull_request`` path).
TARGETS = ("branch-pr", "pr-branch")

#: Type of the injectable run_harness seam (mirrors runner.run_harness).
RunHarness = Callable[..., HarnessResult]


def _default_now() -> str:
    """Real wall-clock timestamp (ISO-8601 UTC) stored in the run-record.

    Injected into the harness as ``now_ts`` so the record is honest; the
    harness itself never reads the clock (deterministic given the seam).
    """
    return datetime.now(timezone.utc).isoformat()


def _build_agent(project_root: Path, provider: ProviderConfig) -> AgentRunner:
    """Construct the real Goose agent seam (recipe + provider + project root).

    No model call happens here — only object construction. The key is resolved
    from the env (``QWEN_API_KEY``) lazily inside the runner, on the CI box that
    holds the secret.
    """
    return GooseAgentRunner(
        project_root=project_root,
        recipe_path=default_recipe_path(),
        provider=provider,
    )


def _build_publisher(platform: str, target: str) -> ReviewPublisher:
    """Map ``(platform, target)`` to its publish adapter (the only platform seam).

    ``branch-pr`` keeps the original branch-cutting publishers (manual /
    ``workflow_dispatch`` use, no PR context); ``pr-branch`` selects the
    commit-onto-the-PR-head-branch publishers (BDL-049, ``on: pull_request``).
    """
    if target == "pr-branch":
        if platform == "gitlab":
            return GitLabPRBranchPublisher()
        return GitHubPRBranchPublisher()
    if platform == "gitlab":
        return GitLabPublisher()
    return GitHubPublisher()


def _resolve(ctx: click.Context, key: str, default: object) -> object:
    """Pull an injected seam from the Click context ``obj`` (else the default)."""
    obj = ctx.obj if isinstance(ctx.obj, dict) else {}
    return obj.get(key, default)


@click.command()
@click.option(
    "--platform",
    type=click.Choice(PLATFORMS),
    required=True,
    help="CI platform whose PR/MR adapter to use (github or gitlab).",
)
@click.option(
    "--project-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd,
    help="Repo root to operate on (defaults to the current directory).",
)
@click.option(
    "--since",
    default=None,
    help="Baseline = code state at this git ref (the push's parent commit). "
    "Drift is measured against it so a fresh CI checkout still detects per-push "
    "drift. An all-zero SHA (force-push / first-push) is treated as unset.",
)
@click.option(
    "--target",
    type=click.Choice(TARGETS),
    default="branch-pr",
    help="Publish target: 'branch-pr' (default) cuts a new branch + opens a "
    "PR/MR (manual / workflow_dispatch); 'pr-branch' commits the refresh onto "
    "the existing PR head branch + posts a comment (on: pull_request).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Report the wiring and exit WITHOUT running the harness (no model/PR).",
)
@click.pass_context
def main(
    ctx: click.Context,
    platform: str,
    project_root: Path,
    since: str | None,
    target: str,
    dry_run: bool,
) -> None:
    """Run the AI tech-writer harness for one CI platform.

    Thin wrapper: assemble seams → inject a real timestamp → run_harness.
    """
    now = cast("Callable[[], str]", _resolve(ctx, "now", _default_now))
    run = cast("RunHarness", _resolve(ctx, "run_harness", _real_run_harness))
    since_ref = _normalize_since(since)

    if dry_run:
        click.echo(f"dry-run: platform={platform} project-root={project_root}")
        click.echo(f"dry-run: since={since_ref or '(stored sync_state)'} target={target}")
        click.echo("dry-run: would wire qwen_provider + GooseAgentRunner + publisher")
        return

    provider = qwen_provider()
    agent = _build_agent(project_root, provider)
    publisher = cast(
        "ReviewPublisher",
        _resolve(ctx, "publisher", _build_publisher(platform, target)),
    )
    config = HarnessConfig(platform=platform)

    result = run(
        project_root,
        agent=agent,
        publisher=publisher,
        now_ts=now(),
        config=config,
        since=since_ref,
    )
    _report(result, project_root=project_root, publisher=publisher)


def _normalize_since(since: str | None) -> str | None:
    """Drop empty / all-zero SHAs (force-push / first-push sentinel) to None.

    CI passes ``github.event.before`` / ``$CI_COMMIT_BEFORE_SHA``, which is an
    all-zero SHA on a first push or a force-push. The shell guard in the wrapper
    already falls back to ``HEAD~1`` for that case, but this is a defensive
    second line: an unusable baseline becomes the default (stored-state) path
    rather than an error.
    """
    if since is None:
        return None
    stripped = since.strip()
    if not stripped or set(stripped) == {"0"}:
        return None
    return stripped


def _report(
    result: HarnessResult, *, project_root: Path, publisher: ReviewPublisher
) -> None:
    """Echo the outcome; map the verdict to an exit code (BDL-050).

    ``ok``/``infra`` → exit 0 (a clean run, a no-op, or "couldn't run"); only a
    genuine ``flagged`` verdict (the model ran, ``tokens > 0``, docs still dirty)
    raises ``Exit(1)`` so the required CI check goes red. On ``infra`` we also
    emit a loud GitHub ``::warning::`` annotation + a best-effort PR/MR note so a
    skipped check is visible (a human re-runs before trusting freshness).
    """
    if result.no_op:
        click.echo("ai-techwriter: 0 stale docs — no-op (exit 0)")
        return
    summary = (
        f"ai-techwriter: {len(result.docs_refreshed)} doc(s) refreshed, "
        f"gate={'green' if result.gate_passed else 'FAILED'}, pr={result.pr_url or '(none)'}"
    )
    click.echo(summary)
    verdict = classify_verdict(result)
    if verdict == VERDICT_INFRA:
        _report_infra(result, project_root=project_root, publisher=publisher)
        return
    if verdict == VERDICT_FLAGGED:
        click.echo("ai-techwriter: flagged — needs human attention:")
        for reason in result.flagged_reasons:
            click.echo(f"  ⚠ {reason}")
        raise click.exceptions.Exit(1)


def _report_infra(
    result: HarnessResult, *, project_root: Path, publisher: ReviewPublisher
) -> None:
    """Surface an ``infra`` verdict WITHOUT blocking the PR (exit 0).

    Emits the GitHub Actions ``::warning::`` annotation (always) and posts a
    best-effort PR/MR note via the publisher's comment seam (only the pr-branch
    publishers implement it; if it can't, the annotation alone stands — never an
    exit-1). The run-record was already emitted honestly by the harness
    (tokens=0, the flagged_reasons).
    """
    click.echo(f"::warning title=AI tech-writer::{_INFRA_MESSAGE}")
    for reason in result.flagged_reasons:
        click.echo(f"  (infra) {reason}")
    _post_infra_comment(project_root=project_root, publisher=publisher)


def _post_infra_comment(*, project_root: Path, publisher: ReviewPublisher) -> None:
    """Best-effort PR/MR note for the infra verdict (annotation is primary)."""
    if not isinstance(publisher, CommentPublisher):
        return
    body = f"⚠ AI tech-writer {_INFRA_MESSAGE}"
    try:
        publisher.comment(project_root=project_root, body=body)
    except (RuntimeError, OSError) as exc:  # best-effort; never fail the run
        click.echo(f"ai-techwriter: infra comment skipped ({exc})")


if __name__ == "__main__":  # pragma: no cover - module-exec convenience
    main()
