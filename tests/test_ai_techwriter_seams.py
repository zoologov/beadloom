"""Tests for the real seam impls + subprocess wrappers (mocked, no network).

GooseAgentRunner / GitHubPublisher / GitLabPublisher are exercised by patching
``run_command`` so no real ``goose`` / ``gh`` / ``glab`` / ``git`` is invoked.
"""

from __future__ import annotations

import json
import subprocess
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


def _git_out(cwd: Path, *args: str) -> str:
    """Run a real ``git`` subcommand in *cwd* (test helper, never raises silently)."""
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    ).stdout


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
    # BUG-C: the packet is NEVER inlined on argv (ARG_MAX blows on real docs).
    # It is written to a temp file and only the FILE PATH is passed as a param.
    assert not any(a.startswith("packet=") for a in args)
    packet_file_params = [a for a in args if a.startswith("packet_file=")]
    assert len(packet_file_params) == 1
    packet_path = packet_file_params[0].split("=", 1)[1]
    # No argv token carries the (potentially huge) packet JSON payload.
    assert not any('"current_content"' in a for a in args)
    # generous runaway hard caps are wired (safety net, not a quality knob)
    assert "--max-turns" in args
    # the temp packet file is cleaned up after the run (no leak).
    assert not Path(packet_path).exists()
    # provider config wired via env; the key is the resolved secret value
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["GOOSE_PROVIDER"] == "openai"
    assert env["GOOSE_MODEL"] == "qwen3.7-plus"
    assert env["OPENAI_API_KEY"] == "k-from-secret"


def test_goose_runner_writes_full_packet_to_temp_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BUG-C: the full packet (doc content + ctx + why + polish JSON) must be
    written to the temp file the recipe reads — argv only carries the path."""
    captured: dict[str, object] = {}

    def fake_run(
        args: list[str], *, cwd: Path, env: dict[str, str] | None = None
    ) -> CommandResult:
        path = next(a.split("=", 1)[1] for a in args if a.startswith("packet_file="))
        # The file must exist (with its full payload) WHILE goose runs.
        captured["payload"] = json.loads(Path(path).read_text(encoding="utf-8"))
        return CommandResult(0, "{}", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    runner.run(_packet())
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["ref_id"] == "graph"
    assert payload["doc_path"] == "docs/graph.md"
    assert payload["current_content"] == "old"
    assert payload["why"] == "why graph"


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
    git_calls = [c for c in seen if c[0] == "git"]
    assert git_calls[0][1] == "checkout"
    assert git_calls[1][1] == "add"
    assert "commit" in git_calls[2]
    assert git_calls[3][1] == "push"
    gh_call = next(c for c in seen if c[0] == "gh")
    assert gh_call[:3] == ["gh", "pr", "create"]
    # BUG-D: no --label needs-human (the title already prefixes "⚠ needs human";
    # the repo need not own a 'needs-human' label).
    assert "--label" not in gh_call
    assert "needs-human" not in gh_call


def test_github_publisher_raises_on_pr_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "git":
            return CommandResult(0, "", "")
        return CommandResult(1, "", "gh boom")

    monkeypatch.setattr(seams, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="gh pr create failed"):
        GitHubPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )


def test_github_publisher_raises_on_push_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        # commit steps succeed; only the push fails.
        if args[:2] == ["git", "push"]:
            return CommandResult(1, "", "push denied")
        return CommandResult(0, "", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
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
        project_root=Path("/x"), branch="ai/y", title="T", body="B", flagged=True
    )
    assert url == "https://gitlab.com/o/r/-/merge_requests/5"
    mr_call = next(c for c in seen if c[0] == "glab")
    assert mr_call[:3] == ["glab", "mr", "create"]
    assert "--source-branch" in mr_call
    # BUG-D: even when flagged, no --label needs-human (title prefixes it).
    assert "--label" not in mr_call
    assert "needs-human" not in mr_call


def test_gitlab_publisher_raises_on_mr_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "git":
            return CommandResult(0, "", "")
        return CommandResult(1, "", "glab boom")

    monkeypatch.setattr(seams, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="glab mr create failed"):
        GitLabPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )


def test_github_publisher_commits_before_push(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUG-A unit guard: the publisher must commit (checkout -b/add/commit)
    BEFORE it pushes, otherwise the branch carries main's HEAD (empty PR)."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        return CommandResult(0, "https://github.com/o/r/pull/7\n", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    GitHubPublisher().publish(
        project_root=Path("/x"), branch="ai/x", title="docs: refresh", body="B", flagged=False
    )
    git_calls = [c for c in seen if c[0] == "git"]
    # Order: checkout -b, add, commit, then push — push is strictly last.
    assert git_calls[0][:3] == ["git", "checkout", "-b"]
    assert git_calls[1][:3] == ["git", "add", "--"]
    assert "commit" in git_calls[2]
    assert git_calls[3][:3] == ["git", "push", "--set-upstream"]
    # The run-record path is staged alongside docs (so it rides in the commit).
    add_call = git_calls[1]
    assert "docs" in add_call
    assert ".beadloom/ai_techwriter_runs.json" in add_call
    # A bot identity is set inline (CI without global git config still commits).
    commit_call = git_calls[2]
    assert any("user.name=beadloom-ai-techwriter" in a for a in commit_call)
    assert any(a.startswith("user.email=") for a in commit_call)


def test_publisher_real_git_commit_and_push_carries_doc_and_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real-git regression (the gap that let BUG-A through).

    Exercises the REAL ``git checkout -b / add / commit / push`` against a
    local bare ``origin`` (no network); only the final ``gh pr create`` is
    mocked. Asserts the pushed branch has a NEW commit whose tree contains both
    the agent's doc edit AND the run-record.
    """
    work = tmp_path / "work"
    work.mkdir()
    bare = tmp_path / "origin.git"

    # Seed a repo on a 'main' checkout with one commit + a bare origin.
    _git_out(work, "init", "-b", "main")
    _git_out(work, "config", "user.name", "seed")
    _git_out(work, "config", "user.email", "seed@example.test")
    (work / "docs").mkdir()
    (work / "docs" / "graph.md").write_text("old\n", encoding="utf-8")
    _git_out(work, "add", "-A")
    _git_out(work, "commit", "-m", "seed")
    base_head = _git_out(work, "rev-parse", "HEAD").strip()
    _git_out(bare.parent, "init", "--bare", str(bare))
    _git_out(work, "remote", "add", "origin", str(bare))
    _git_out(work, "push", "-u", "origin", "main")

    # The agent left an uncommitted doc edit; the harness wrote the run-record.
    (work / "docs" / "graph.md").write_text("old\nrefreshed by AI\n", encoding="utf-8")
    (work / ".beadloom").mkdir()
    (work / ".beadloom" / "ai_techwriter_runs.json").write_text("[]\n", encoding="utf-8")

    # Mock ONLY the final gh create; everything git is the real subprocess.
    real_run = commands.run_command

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "gh":
            return CommandResult(0, "https://github.com/o/r/pull/99\n", "")
        return real_run(args, cwd=cwd)

    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPublisher().publish(
        project_root=work,
        branch="ai-techwriter/refresh-graph",
        title="docs: AI tech-writer refresh",
        body="B",
        flagged=False,
    )
    assert url == "https://github.com/o/r/pull/99"

    # The pushed branch exists on origin and is a NEW commit (not main's HEAD).
    pushed_head = _git_out(bare, "rev-parse", "ai-techwriter/refresh-graph").strip()
    assert pushed_head != base_head

    # The commit's tree contains both the doc edit and the run-record.
    tree = _git_out(bare, "show", "--stat", "--format=", pushed_head)
    assert "docs/graph.md" in tree
    assert ".beadloom/ai_techwriter_runs.json" in tree
    doc_in_commit = _git_out(bare, "show", f"{pushed_head}:docs/graph.md")
    assert "refreshed by AI" in doc_in_commit
