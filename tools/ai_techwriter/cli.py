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

Exit codes (for CI visibility):

* ``0`` — no-op (0 stale) **or** a clean green run (PR/MR opened, gate green).
* ``1`` — a *flagged* run (a PR/MR was opened but it needs human attention:
  the gate failed or the budget was exceeded). The PR/MR is the deliverable;
  the non-zero exit just surfaces "needs human" in the CI run, never a crash.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, cast

import click

from tools.ai_techwriter.models import HarnessConfig, HarnessResult
from tools.ai_techwriter.provider import ProviderConfig, default_recipe_path, qwen_provider
from tools.ai_techwriter.runner import run_harness as _real_run_harness
from tools.ai_techwriter.seams import (
    GitHubPRBranchPublisher,
    GitHubPublisher,
    GitLabPRBranchPublisher,
    GitLabPublisher,
    GooseAgentRunner,
    ReviewPublisher,
)

if TYPE_CHECKING:
    from tools.ai_techwriter.seams import AgentRunner

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
    publisher = _build_publisher(platform, target)
    config = HarnessConfig(platform=platform)

    result = run(
        project_root,
        agent=agent,
        publisher=publisher,
        now_ts=now(),
        config=config,
        since=since_ref,
    )
    _report(result)


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


def _report(result: HarnessResult) -> None:
    """Echo a one-line outcome; raise Exit(1) for a flagged run."""
    if result.no_op:
        click.echo("ai-techwriter: 0 stale docs — no-op (exit 0)")
        return
    summary = (
        f"ai-techwriter: {len(result.docs_refreshed)} doc(s) refreshed, "
        f"gate={'green' if result.gate_passed else 'FAILED'}, pr={result.pr_url or '(none)'}"
    )
    click.echo(summary)
    if result.flagged:
        click.echo("ai-techwriter: flagged — needs human attention:")
        for reason in result.flagged_reasons:
            click.echo(f"  ⚠ {reason}")
        raise click.exceptions.Exit(1)


if __name__ == "__main__":  # pragma: no cover - module-exec convenience
    main()
