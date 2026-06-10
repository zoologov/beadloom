"""Tests for the real seam impls + subprocess wrappers (mocked, no network).

GooseAgentRunner / GitHubPublisher / GitLabPublisher are exercised by patching
``run_command`` so no real ``goose`` / ``gh`` / ``glab`` / ``git`` is invoked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tools.ai_techwriter import commands, seams
from tools.ai_techwriter.commands import CommandResult
from tools.ai_techwriter.models import ContextPacket
from tools.ai_techwriter.provider import qwen_provider
from tools.ai_techwriter.seams import (
    GitHubPublisher,
    GitLabPublisher,
    GooseAgentRunner,
)


def _packet() -> ContextPacket:
    return ContextPacket(
        ref_id="graph",
        doc_path="docs/graph.md",
        current_content="old",
        drift_reason="symbols_changed (src/g.py)",
        docs_polish_json={"ref_id": "graph"},
        ctx={"focus": "graph"},
        why="why graph",
    )


# --------------------------------------------------------------------------- #
# command wrappers
# --------------------------------------------------------------------------- #


def test_sync_check_json_parses_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"summary": {"stale": 0}, "pairs": []}

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        assert args == ["beadloom", "sync-check", "--json"]
        return CommandResult(2, json.dumps(payload), "")

    monkeypatch.setattr(commands, "run_command", fake_run)
    assert commands.beadloom_sync_check_json(Path("/x")) == payload


def test_sync_check_json_raises_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands, "run_command", lambda args, *, cwd: CommandResult(1, "", "boom"))
    with pytest.raises(RuntimeError, match="no JSON"):
        commands.beadloom_sync_check_json(Path("/x"))


def test_ctx_json_returns_empty_on_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands, "run_command", lambda args, *, cwd: CommandResult(0, "", ""))
    assert commands.beadloom_ctx_json(Path("/x"), "graph") == {}


def test_command_result_ok() -> None:
    assert CommandResult(0, "", "").ok is True
    assert CommandResult(1, "", "").ok is False


def test_run_command_invokes_real_subprocess(tmp_path: Path) -> None:
    # Exercise the one real subprocess seam with a harmless, portable command.
    res = commands.run_command(["python", "-c", "print('hi')"], cwd=tmp_path)
    assert res.ok is True
    assert res.stdout.strip() == "hi"


def test_run_command_captures_nonzero_without_raising(tmp_path: Path) -> None:
    res = commands.run_command(["python", "-c", "import sys; sys.exit(3)"], cwd=tmp_path)
    assert res.returncode == 3
    assert res.ok is False


def test_sync_check_json_raises_on_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        commands, "run_command", lambda args, *, cwd: CommandResult(0, "[1,2]", "")
    )
    with pytest.raises(RuntimeError, match="not an object"):
        commands.beadloom_sync_check_json(Path("/x"))


def test_docs_polish_json_parses_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        commands,
        "run_command",
        lambda args, *, cwd: CommandResult(0, '{"nodes": []}', ""),
    )
    assert commands.beadloom_docs_polish_json(Path("/x")) == {"nodes": []}


def test_docs_polish_json_raises_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands, "run_command", lambda args, *, cwd: CommandResult(1, "", ""))
    with pytest.raises(RuntimeError, match="no JSON"):
        commands.beadloom_docs_polish_json(Path("/x"))


def test_ctx_json_returns_empty_on_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands, "run_command", lambda args, *, cwd: CommandResult(0, "42", ""))
    assert commands.beadloom_ctx_json(Path("/x"), "graph") == {}


def test_sync_update_and_ci_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        return CommandResult(0, "", "")

    monkeypatch.setattr(commands, "run_command", fake_run)
    commands.beadloom_sync_update(Path("/x"), "graph")
    commands.beadloom_ci(Path("/x"))
    assert ["beadloom", "sync-update", "graph", "--yes"] in seen
    assert ["beadloom", "ci"] in seen


def test_why_wrapper_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        commands, "run_command", lambda args, *, cwd: CommandResult(0, "impact text", "")
    )
    assert commands.beadloom_why(Path("/x"), "graph") == "impact text"


# --------------------------------------------------------------------------- #
# GooseAgentRunner
# --------------------------------------------------------------------------- #


def test_goose_runner_parses_usage_report(monkeypatch: pytest.MonkeyPatch) -> None:
    usage_line = json.dumps(
        {
            "rewritten_paths": ["docs/graph.md"],
            "input_tokens": 900,
            "output_tokens": 300,
            "model": "qwen3.7-plus",
        }
    )

    def fake_run(
        args: list[str], *, cwd: Path, env: dict[str, str] | None = None
    ) -> CommandResult:
        assert args[0] == "goose"
        return CommandResult(0, f"thinking...\n{usage_line}\n", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("recipe.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.rewritten_paths == ("docs/graph.md",)
    assert res.input_tokens == 900
    assert res.output_tokens == 300
    assert res.model == "qwen3.7-plus"


def test_goose_runner_builds_command_with_recipe_provider_and_caps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        args: list[str], *, cwd: Path, env: dict[str, str] | None = None
    ) -> CommandResult:
        captured["args"] = args
        captured["env"] = env
        return CommandResult(0, "{}", "")

    monkeypatch.setenv("QWEN_API_KEY", "k-from-secret")
    monkeypatch.setattr(seams, "run_command", fake_run)
    runner = GooseAgentRunner(
        project_root=Path("/x"),
        recipe_path=Path("/x/tools/ai_techwriter/recipe.yaml"),
        provider=qwen_provider(),
    )
    runner.run(_packet())
    args = captured["args"]
    assert isinstance(args, list)
    assert args[:2] == ["goose", "run"]
    assert "--recipe" in args
    assert "/x/tools/ai_techwriter/recipe.yaml" in args
    # the per-doc packet is passed as a recipe param
    assert any(a.startswith("packet=") for a in args)
    # generous runaway hard caps are wired (safety net, not a quality knob)
    assert "--max-turns" in args
    # provider config wired via env; the key is the resolved secret value
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["GOOSE_PROVIDER"] == "openai"
    assert env["GOOSE_MODEL"] == "qwen3.7-plus"
    assert env["OPENAI_API_KEY"] == "k-from-secret"


def test_goose_runner_defaults_when_no_usage_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        seams,
        "run_command",
        lambda args, *, cwd, env=None: CommandResult(0, "no json here", ""),
    )
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.rewritten_paths == ("docs/graph.md",)
    assert res.input_tokens == 0
    # falls back to the provider's configured model
    assert res.model == "qwen3.7-plus"


def test_goose_runner_skips_non_object_and_invalid_json_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A trailing JSON array (not an object) and a malformed line are both
    # skipped; the earlier usage object is the one parsed.
    usage = json.dumps({"input_tokens": 5, "output_tokens": 2, "model": "m2"})
    stdout = f"{usage}\n{{not json}}\n[1, 2, 3]\n"
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(0, stdout, "")
    )
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.input_tokens == 5
    assert res.model == "m2"
    # no rewritten_paths key => falls back to the packet's doc path
    assert res.rewritten_paths == ("docs/graph.md",)


def test_goose_runner_returns_empty_result_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A failed/empty agent run must NOT crash the harness: it returns an empty
    # result (no rewritten paths) so the fixpoint treats the doc as still stale
    # and retries / flags it.
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(1, "", "kaboom")
    )
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.rewritten_paths == ()
    assert res.input_tokens == 0
    assert res.output_tokens == 0
    assert res.model == "qwen3.7-plus"


# --------------------------------------------------------------------------- #
# Publishers
# --------------------------------------------------------------------------- #


def test_github_publisher_pushes_and_creates_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if args[:2] == ["git", "push"]:
            return CommandResult(0, "", "")
        return CommandResult(0, "https://github.com/o/r/pull/3\n", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPublisher().publish(
        project_root=Path("/x"), branch="ai/x", title="T", body="B", flagged=True
    )
    assert url == "https://github.com/o/r/pull/3"
    assert seen[0][:2] == ["git", "push"]
    gh_call = seen[1]
    assert gh_call[:3] == ["gh", "pr", "create"]
    assert "--label" in gh_call and "needs-human" in gh_call


def test_github_publisher_raises_on_pr_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[:2] == ["git", "push"]:
            return CommandResult(0, "", "")
        return CommandResult(1, "", "gh boom")

    monkeypatch.setattr(seams, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="gh pr create failed"):
        GitHubPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )


def test_github_publisher_raises_on_push_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd: CommandResult(1, "", "push denied")
    )
    with pytest.raises(RuntimeError, match="git push failed"):
        GitHubPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )


def test_gitlab_publisher_pushes_and_creates_mr(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if args[:2] == ["git", "push"]:
            return CommandResult(0, "", "")
        return CommandResult(0, "https://gitlab.com/o/r/-/merge_requests/5\n", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitLabPublisher().publish(
        project_root=Path("/x"), branch="ai/y", title="T", body="B", flagged=False
    )
    assert url == "https://gitlab.com/o/r/-/merge_requests/5"
    mr_call = seen[1]
    assert mr_call[:3] == ["glab", "mr", "create"]
    assert "--source-branch" in mr_call
    assert "--label" not in mr_call  # not flagged


def test_gitlab_publisher_raises_on_mr_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[:2] == ["git", "push"]:
            return CommandResult(0, "", "")
        return CommandResult(1, "", "glab boom")

    monkeypatch.setattr(seams, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="glab mr create failed"):
        GitLabPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )
