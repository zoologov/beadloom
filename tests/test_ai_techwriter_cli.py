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
    GitHubPublisher,
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
    ) -> HarnessResult:
        self.calls.append(
            {
                "project_root": project_root,
                "agent": agent,
                "publisher": publisher,
                "now_ts": now_ts,
                "config": config,
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
    """A flagged run (needs human) signals via a non-zero exit for CI visibility."""
    spy = _SpyHarness(
        HarnessResult(
            docs_refreshed=["docs/a.md"],
            gate_passed=False,
            flagged=True,
            flagged_reasons=["beadloom ci failed"],
            pr_url="u",
        )
    )
    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--platform", "github", "--project-root", str(project)],
        obj={"run_harness": spy, "now": lambda: "T"},
    )
    assert result.exit_code != 0
    assert "needs human" in result.output.lower() or "flagged" in result.output.lower()


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
    assert isinstance(cli._build_publisher("github"), GitHubPublisher)
    assert isinstance(cli._build_publisher("gitlab"), GitLabPublisher)


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
