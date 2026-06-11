"""Tests for the BDL-047 AI tech-writer CLI entrypoint (tools/ai_techwriter/cli).

The CLI is the thin wrapper CI invokes (``python -m tools.ai_techwriter``). All
non-deterministic / network-touching seams (the Goose agent, the PR/MR
publisher, and ``run_harness`` itself) are faked or injected, so nothing here
touches Goose, the model, git, or the network. The timestamp is produced by an
injected clock for deterministic assertions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner
from tools.ai_techwriter import cli
from tools.ai_techwriter.models import HarnessConfig, HarnessResult
from tools.ai_techwriter.seams import (
    GitHubPRBranchPublisher,
    GitHubPublisher,
    GitLabPRBranchPublisher,
    GitLabPublisher,
)

if TYPE_CHECKING:
    from pathlib import Path


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


class _SpyHarness:
    """Records the kwargs run_harness was called with; returns a canned result."""

    def __init__(self, result: HarnessResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __call__(
        self,
        project_root: Path,
        *,
        agent: object,
        publisher: object,
        now_ts: str,
        config: HarnessConfig | None = None,
        since: str | None = None,
    ) -> HarnessResult:
        self.calls.append(
            {
                "project_root": project_root,
                "agent": agent,
                "publisher": publisher,
                "now_ts": now_ts,
                "config": config,
                "since": since,
            }
        )
        return self.result


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A minimal project root."""
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / "docs").mkdir()
    return tmp_path


# --------------------------------------------------------------------------- #
# Argument wiring
# --------------------------------------------------------------------------- #


def test_no_op_when_nothing_stale_exits_zero(project: Path) -> None:
    """0 stale → run_harness returns no_op → clean exit 0."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "2026-06-10T00:00:00+00:00"},
    )
    assert result.exit_code == 0, result.output
    assert spy.calls, "run_harness should have been invoked"
    assert spy.calls[0]["now_ts"] == "2026-06-10T00:00:00+00:00"


def test_since_threaded_into_harness(project: Path) -> None:
    """--since <ref> is passed straight through to run_harness."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project), "--since", "abc123"],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert spy.calls[0]["since"] == "abc123"


def test_since_defaults_to_none(project: Path) -> None:
    """No --since → run_harness gets since=None (stored-state baseline)."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert spy.calls[0]["since"] is None


def test_since_zero_sha_normalized_to_none(project: Path) -> None:
    """An all-zero SHA (force-push / first-push) falls back to None."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project), "--since", "0" * 40],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert spy.calls[0]["since"] is None


def test_github_platform_wires_github_publisher(project: Path) -> None:
    """--platform github → GitHubPublisher + platform='github' in config."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    call = spy.calls[0]
    assert isinstance(call["publisher"], GitHubPublisher)
    config = call["config"]
    assert isinstance(config, HarnessConfig)
    assert config.platform == "github"


def test_gitlab_platform_wires_gitlab_publisher(project: Path) -> None:
    """--platform gitlab → GitLabPublisher + platform='gitlab' in config."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "gitlab", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    call = spy.calls[0]
    assert isinstance(call["publisher"], GitLabPublisher)
    config = call["config"]
    assert isinstance(config, HarnessConfig)
    assert config.platform == "gitlab"


def test_invalid_platform_is_rejected(project: Path) -> None:
    """An unknown --platform is rejected by the CLI (non-zero, no harness call)."""
    spy = _SpyHarness(HarnessResult(no_op=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "bitbucket", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code != 0
    assert not spy.calls


def test_platform_is_required(project: Path) -> None:
    """--platform is required."""
    spy = _SpyHarness(HarnessResult(no_op=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code != 0
    assert not spy.calls


# --------------------------------------------------------------------------- #
# Dry-run
# --------------------------------------------------------------------------- #


def test_dry_run_does_not_invoke_harness(project: Path) -> None:
    """--dry-run reports the wiring and exits 0 WITHOUT running the harness."""
    spy = _SpyHarness(HarnessResult(no_op=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project), "--dry-run"],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert not spy.calls
    assert "dry-run" in result.output.lower()
    assert "github" in result.output.lower()


# --------------------------------------------------------------------------- #
# Exit codes reflect the harness outcome
# --------------------------------------------------------------------------- #


def test_clean_green_run_exits_zero(project: Path) -> None:
    """A real (non no-op) green run exits 0."""
    spy = _SpyHarness(
        HarnessResult(docs_refreshed=["docs/a.md"], gate_passed=True, pr_url="u")
    )
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output


def test_flagged_run_exits_nonzero(project: Path) -> None:
    """A flagged run WITH model output (tokens>0) → verdict flagged → exit 1."""
    spy = _SpyHarness(
        HarnessResult(
            docs_refreshed=["docs/a.md"],
            gate_passed=False,
            flagged=True,
            flagged_reasons=["beadloom ci failed"],
            input_tokens=100,
            output_tokens=50,
            pr_url="u",
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 1
    assert "needs human" in result.output.lower() or "flagged" in result.output.lower()


# --------------------------------------------------------------------------- #
# BDL-050: verdict-driven exit codes (ok/infra → 0, flagged → 1) + infra signal
# --------------------------------------------------------------------------- #


def test_infra_verdict_exits_zero_with_warning(project: Path) -> None:
    """flagged + NO tokens (agent never ran) → verdict infra → exit 0 + ::warning::.

    A dead runner / exhausted quota must NOT block the PR; the loud GitHub
    annotation surfaces that docs were NOT checked.
    """
    spy = _SpyHarness(
        HarnessResult(
            docs_refreshed=[],
            gate_passed=False,
            flagged=True,
            flagged_reasons=["agent failed for graph after 3 attempts"],
            input_tokens=0,
            output_tokens=0,
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert "::warning title=AI tech-writer::" in result.output
    assert "docs were not checked" in result.output.lower()


def test_infra_verdict_attempts_pr_comment_via_publisher(project: Path) -> None:
    """On infra, the entrypoint posts a best-effort note via the comment seam."""
    comments: list[str] = []

    class _CommentingPublisher:
        """A publisher that satisfies ReviewPublisher + CommentPublisher."""

        def publish(self, **_kwargs: object) -> str:
            return ""

        def comment(self, *, project_root: Path, body: str) -> bool:
            del project_root
            comments.append(body)
            return True

    spy = _SpyHarness(
        HarnessResult(
            flagged=True,
            flagged_reasons=["goose run failed (rc=1)"],
            input_tokens=0,
            output_tokens=0,
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={
            "run_harness": spy,
            "now": lambda: "T",
            "publisher": _CommentingPublisher(),
        },
    )
    assert result.exit_code == 0, result.output
    assert comments, "infra path should attempt a PR/MR comment"
    assert "could not run" in comments[0].lower()


def test_infra_comment_failure_does_not_fail_run(project: Path) -> None:
    """A failing comment seam never turns an infra run into a non-zero exit."""

    class _BrokenCommentPublisher:
        def publish(self, **_kwargs: object) -> str:
            return ""

        def comment(self, *, project_root: Path, body: str) -> bool:
            del project_root, body
            raise RuntimeError("gh exploded")

    spy = _SpyHarness(
        HarnessResult(
            flagged=True,
            flagged_reasons=["provider 503"],
            input_tokens=0,
            output_tokens=0,
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={
            "run_harness": spy,
            "now": lambda: "T",
            "publisher": _BrokenCommentPublisher(),
        },
    )
    assert result.exit_code == 0, result.output
    assert "::warning title=AI tech-writer::" in result.output


def test_flagged_boundary_one_token_blocks(project: Path) -> None:
    """The tokens>0 boundary at the CLI: a single token → flagged → exit 1."""
    spy = _SpyHarness(
        HarnessResult(
            flagged=True,
            flagged_reasons=["fixpoint not reached"],
            input_tokens=0,
            output_tokens=1,
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 1, result.output
    assert "::warning" not in result.output


# --------------------------------------------------------------------------- #
# Real-seam builders (no network: we only assert on the constructed objects)
# --------------------------------------------------------------------------- #


def test_build_agent_constructs_goose_runner(project: Path) -> None:
    """The default agent builder constructs a GooseAgentRunner (no run() called)."""
    from tools.ai_techwriter.provider import qwen_provider
    from tools.ai_techwriter.seams import GooseAgentRunner

    agent = cli._build_agent(project, qwen_provider())
    assert isinstance(agent, GooseAgentRunner)


def test_build_publisher_maps_platform() -> None:
    """The publisher builder maps the platform string to the right adapter."""
    assert isinstance(cli._build_publisher("github", "branch-pr"), GitHubPublisher)
    assert isinstance(cli._build_publisher("gitlab", "branch-pr"), GitLabPublisher)


# --------------------------------------------------------------------------- #
# BDL-049: --target {branch-pr,pr-branch}
# --------------------------------------------------------------------------- #


def test_target_defaults_to_branch_pr(project: Path) -> None:
    """No --target → the existing branch-cutting GitHubPublisher (today's path)."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert isinstance(spy.calls[0]["publisher"], GitHubPublisher)


def test_target_pr_branch_wires_github_pr_branch_publisher(project: Path) -> None:
    """--target pr-branch + github → the commit-to-current-branch publisher."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--target", "pr-branch", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert isinstance(spy.calls[0]["publisher"], GitHubPRBranchPublisher)


def test_target_pr_branch_wires_gitlab_pr_branch_publisher(project: Path) -> None:
    """--target pr-branch + gitlab → the GitLab commit-to-current-branch publisher."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "gitlab", "--target", "pr-branch", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert isinstance(spy.calls[0]["publisher"], GitLabPRBranchPublisher)


def test_invalid_target_is_rejected(project: Path) -> None:
    """An unknown --target is rejected by the CLI (non-zero, no harness call)."""
    spy = _SpyHarness(HarnessResult(no_op=True))
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--target", "nope", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code != 0
    assert not spy.calls


def test_build_publisher_maps_target() -> None:
    """The publisher builder maps (platform, target) to the right adapter."""
    assert isinstance(cli._build_publisher("github", "pr-branch"), GitHubPRBranchPublisher)
    assert isinstance(cli._build_publisher("gitlab", "pr-branch"), GitLabPRBranchPublisher)


def test_default_now_is_iso_utc_string() -> None:
    """The default clock yields an ISO-8601 UTC timestamp string."""
    ts = cli._default_now()
    assert isinstance(ts, str)
    assert ts.endswith("+00:00") or ts.endswith("Z")


def test_real_run_invokes_harness_with_real_agent(project: Path) -> None:
    """End-to-end wiring (harness faked via obj, real agent builder) exits 0."""
    spy = _SpyHarness(HarnessResult(no_op=True, gate_passed=True))
    runner = CliRunner()
    # Do NOT override _build_agent here beyond the autouse fake, but force a
    # real GooseAgentRunner build to exercise that path without running it.
    result = runner.invoke(
        cli.main,
        ["--platform", "gitlab", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code == 0, result.output
    assert isinstance(spy.calls[0]["publisher"], GitLabPublisher)
