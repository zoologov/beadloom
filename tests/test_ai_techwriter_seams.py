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
    GitHubPRBranchPublisher,
    GitHubPublisher,
    GitLabPRBranchPublisher,
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


def test_goose_runner_coerces_string_token_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Numeric-string token counts in the usage report are coerced to ints."""
    usage = json.dumps({"input_tokens": "42", "output_tokens": "9", "model": "m"})
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(0, usage, "")
    )
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.input_tokens == 42
    assert res.output_tokens == 9


def test_goose_runner_rejects_garbage_token_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-numeric / negative / boolean token values fall back to 0 (never crash).

    Exercises the ``_as_int`` guards: a negative int clamps to 0, a non-digit
    string and a bool both become 0 — the run-record stays honest, never
    carries garbage, and the run never raises on a malformed usage report.
    """
    usage = json.dumps(
        {"input_tokens": -5, "output_tokens": "lots", "model": "m"}
    )
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(0, usage, "")
    )
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.input_tokens == 0  # negative clamped
    assert res.output_tokens == 0  # non-digit string rejected


def test_goose_runner_bool_token_value_is_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JSON ``true`` (a bool, which is an int subclass) must coerce to 0."""
    usage = json.dumps({"input_tokens": True, "output_tokens": 0, "model": "m"})
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(0, usage, "")
    )
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.input_tokens == 0


def test_goose_runner_non_list_rewritten_paths_falls_back_to_doc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ``rewritten_paths`` that is not a list falls back to the packet doc path."""
    usage = json.dumps({"rewritten_paths": "docs/x.md", "model": "m"})
    monkeypatch.setattr(
        seams, "run_command", lambda args, *, cwd, env=None: CommandResult(0, usage, "")
    )
    runner = GooseAgentRunner(
        project_root=Path("/x"), recipe_path=Path("r.yaml"), provider=qwen_provider()
    )
    res = runner.run(_packet())
    assert res.rewritten_paths == ("docs/graph.md",)


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
    # BUG-J: the bot's deterministic refresh branch is force-pushed so a
    # lingering branch from a prior run can't block it with a non-fast-forward.
    assert git_calls[3][:4] == ["git", "push", "--force", "--set-upstream"]
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


# --------------------------------------------------------------------------- #
# BUG-J force-push + pr_url backfill
# --------------------------------------------------------------------------- #


def test_push_branch_uses_force(monkeypatch: pytest.MonkeyPatch) -> None:
    """BUG-J: the push must be a ``--force`` push of the bot's refresh branch."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        return CommandResult(0, "https://github.com/o/r/pull/1\n", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    GitHubPublisher().publish(
        project_root=Path("/x"), branch="ai/x", title="T", body="B", flagged=False
    )
    push = next(c for c in seen if c[:2] == ["git", "push"])
    assert "--force" in push
    assert push == ["git", "push", "--force", "--set-upstream", "origin", "ai/x"]


def _seed_repo_with_origin(work: Path, bare: Path) -> str:
    """Seed a 'main' checkout (one commit) + a bare origin; return base HEAD."""
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
    return base_head


def test_push_succeeds_over_preexisting_remote_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BUG-J real-git: a lingering remote refresh branch must NOT block the run.

    Pre-create the deterministic refresh branch on origin (with unrelated
    history, as a stale prior run would leave it). With the force-push the new
    run still publishes and the branch head advances to the new proposal commit.
    """
    work = tmp_path / "work"
    work.mkdir()
    bare = tmp_path / "origin.git"
    _seed_repo_with_origin(work, bare)

    branch = "ai-techwriter/refresh-graph"
    # A prior run left an unmergeable branch on origin (divergent history).
    _git_out(work, "checkout", "-b", branch)
    (work / "docs" / "graph.md").write_text("STALE prior proposal\n", encoding="utf-8")
    _git_out(work, "add", "-A")
    _git_out(work, "commit", "-m", "stale prior run")
    _git_out(work, "push", "-u", "origin", branch)
    stale_head = _git_out(bare, "rev-parse", branch).strip()
    # Back on main; drop the LOCAL branch so the run starts from a fresh
    # checkout state — the lingering branch exists only on origin (the BUG-J
    # scenario: a prior run's branch persists remotely, e.g. an open PR).
    _git_out(work, "checkout", "main")
    _git_out(work, "branch", "-D", branch)
    # The new run's working state: agent edit + run-record.
    (work / "docs" / "graph.md").write_text("old\nrefreshed by AI\n", encoding="utf-8")
    (work / ".beadloom").mkdir()
    (work / ".beadloom" / "ai_techwriter_runs.json").write_text("[]\n", encoding="utf-8")

    real_run = commands.run_command

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "gh":
            return CommandResult(0, "https://github.com/o/r/pull/42\n", "")
        return real_run(args, cwd=cwd)

    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPublisher().publish(
        project_root=work, branch=branch, title="docs: refresh", body="B", flagged=False
    )
    assert url == "https://github.com/o/r/pull/42"
    new_head = _git_out(bare, "rev-parse", branch).strip()
    assert new_head != stale_head  # the force-push moved the branch head.
    doc_in_commit = _git_out(bare, "show", f"{new_head}:docs/graph.md")
    assert "refreshed by AI" in doc_in_commit


def test_pr_url_backfilled_into_record_recommitted_and_repushed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After create, the last run-record entry gets the URL + is re-pushed.

    Real-git: only ``gh pr create`` is mocked. The store starts with an entry
    whose ``pr_url`` is empty; after publish the entry carries the returned URL
    AND that URL-bearing record is present in the pushed branch's tree.
    """
    work = tmp_path / "work"
    work.mkdir()
    bare = tmp_path / "origin.git"
    _seed_repo_with_origin(work, bare)

    (work / "docs" / "graph.md").write_text("old\nrefreshed by AI\n", encoding="utf-8")
    (work / ".beadloom").mkdir()
    store = work / ".beadloom" / "ai_techwriter_runs.json"
    store.write_text(json.dumps([{"ts": "t0", "pr_url": ""}]) + "\n", encoding="utf-8")

    real_run = commands.run_command

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "gh":
            return CommandResult(0, "https://github.com/o/r/pull/77\n", "")
        return real_run(args, cwd=cwd)

    monkeypatch.setattr(seams, "run_command", fake_run)
    branch = "ai-techwriter/refresh-graph"
    url = GitHubPublisher().publish(
        project_root=work, branch=branch, title="docs: refresh", body="B", flagged=False
    )
    assert url == "https://github.com/o/r/pull/77"

    # The on-disk store's last entry now carries the URL.
    records = json.loads(store.read_text(encoding="utf-8"))
    assert records[-1]["pr_url"] == "https://github.com/o/r/pull/77"
    # The pushed branch head carries the URL-bearing record (amend + re-push).
    head = _git_out(bare, "rev-parse", branch).strip()
    record_in_commit = _git_out(bare, "show", f"{head}:.beadloom/ai_techwriter_runs.json")
    assert "https://github.com/o/r/pull/77" in record_in_commit


def test_backfill_failure_does_not_fail_the_run(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A failing post-create amend/push must NOT fail the run.

    The first push (pre-create) succeeds; ``gh`` returns the URL; the SECOND
    push (post-amend) fails. ``publish`` still returns the URL and logs a
    warning rather than raising.
    """
    push_calls = {"n": 0}

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "gh":
            return CommandResult(0, "https://github.com/o/r/pull/9\n", "")
        if args[:2] == ["git", "push"]:
            push_calls["n"] += 1
            if push_calls["n"] >= 2:
                return CommandResult(1, "", "non-fast-forward")
        return CommandResult(0, "", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    # A non-empty store so the backfill proceeds to the amend + second push.
    monkeypatch.setattr(seams, "load_runs", lambda root: [{"ts": "t0", "pr_url": ""}])
    monkeypatch.setattr(seams, "runs_store_path", lambda root: Path("/dev/null"))
    with caplog.at_level("WARNING"):
        url = GitHubPublisher().publish(
            project_root=Path("/x"), branch="ai/x", title="T", body="B", flagged=False
        )
    assert url == "https://github.com/o/r/pull/9"
    assert any("backfill pr_url" in r.message for r in caplog.records)


def test_record_pr_url_noop_when_store_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No store / empty store: backfill is a no-op (no amend, no second push)."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if args[0] == "gh":
            return CommandResult(0, "https://github.com/o/r/pull/3\n", "")
        return CommandResult(0, "", "")

    monkeypatch.setattr(seams, "run_command", fake_run)
    monkeypatch.setattr(seams, "load_runs", lambda root: [])
    url = GitHubPublisher().publish(
        project_root=Path("/x"), branch="ai/x", title="T", body="B", flagged=False
    )
    assert url == "https://github.com/o/r/pull/3"
    # Exactly one push (pre-create); no amend, no second push.
    assert sum(1 for c in seen if c[:2] == ["git", "push"]) == 1
    assert not any("--amend" in c for c in seen)


# --------------------------------------------------------------------------- #
# BDL-049: pr-branch publish mode (commit onto the PR head branch + comment)
# --------------------------------------------------------------------------- #


def _has_staged_docs(args: list[str]) -> bool:
    """True for the ``git diff --cached --quiet -- docs`` probe call."""
    return args[:4] == ["git", "diff", "--cached", "--quiet"]


def test_github_pr_branch_commits_to_current_branch_no_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pr-branch mode commits onto the CURRENT branch (no ``git checkout -b``)."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")  # docs changed → commit
        return CommandResult(0, "", "")

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/5")
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPRBranchPublisher().publish(
        project_root=Path("/x"),
        branch="ignored-branch",
        title="docs: AI tech-writer refresh (2 doc(s))",
        body="B",
        flagged=False,
    )
    # pr_url is resolved from the CI env (the PR pre-exists), NOT from gh.
    assert url == "https://github.com/o/r/pull/5"
    git_calls = [c for c in seen if c[0] == "git"]
    # Never cuts a new branch — stays on the runner's PR-head checkout.
    assert not any(c[:3] == ["git", "checkout", "-b"] for c in git_calls)
    assert not any("checkout" in c for c in git_calls)
    # Commit message starts with the loop-guard token.
    commit_call = next(c for c in git_calls if "commit" in c)
    msg = commit_call[commit_call.index("-m") + 1]
    assert msg.startswith("[skip ai-techwriter]")
    assert "docs: AI tech-writer refresh (2 doc(s))" in msg
    # Bot identity inlined (CI without global git config still commits).
    assert any("user.name=beadloom-ai-techwriter" in a for a in commit_call)
    # Push is a PLAIN push of the current branch (HEAD), NOT a force-push.
    push_call = next(c for c in git_calls if c[:2] == ["git", "push"])
    assert "--force" not in push_call
    assert push_call == ["git", "push", "origin", "HEAD"]


def test_github_pr_branch_posts_pr_comment_not_pr_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pr-branch mode posts a PR comment; it never runs ``gh pr create``."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/8")
    monkeypatch.setattr(seams, "run_command", fake_run)
    GitHubPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="summary body", flagged=False
    )
    gh_calls = [c for c in seen if c[0] == "gh"]
    assert gh_calls, "a gh pr comment must be posted"
    assert all("create" not in c for c in gh_calls)
    comment = gh_calls[0]
    assert comment[:3] == ["gh", "pr", "comment"]
    assert "https://github.com/o/r/pull/8" in comment
    assert "--body" in comment
    assert comment[comment.index("--body") + 1] == "summary body"


def test_github_pr_branch_zero_docs_skips_empty_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """0 docs changed → no empty commit and no push (record + comment only)."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(0, "", "")  # nothing staged under docs → no-op
        return CommandResult(0, "", "")

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/2")
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
    )
    assert url == "https://github.com/o/r/pull/2"
    git_calls = [c for c in seen if c[0] == "git"]
    assert not any("commit" in c for c in git_calls), "no empty commit on a 0-doc no-op"
    assert not any(c[:2] == ["git", "push"] for c in git_calls), "nothing to push"
    # The comment is still posted (the run happened).
    assert any(c[0] == "gh" for c in seen)


def test_github_pr_branch_comment_failure_does_not_fail_run(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A failing PR comment is best-effort: the run still succeeds (commit is it)."""

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "gh":
            return CommandResult(1, "", "gh comment boom")
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/4")
    monkeypatch.setattr(seams, "run_command", fake_run)
    with caplog.at_level("WARNING"):
        url = GitHubPRBranchPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )
    assert url == "https://github.com/o/r/pull/4"
    assert any("comment" in r.message.lower() for r in caplog.records)


def test_github_pr_branch_pr_url_empty_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No PR_URL in env → pr_url is empty and no comment is attempted."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.delenv("PR_URL", raising=False)
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
    )
    assert url == ""
    # Commit/push still happen; only the comment is skipped (no target).
    assert any("commit" in c for c in seen if c[0] == "git")
    assert not any(c[0] == "gh" for c in seen)


def test_github_pr_branch_raises_on_push_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real push failure (not the comment) still fails the run — the commit
    must land on the PR branch."""

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[:2] == ["git", "push"]:
            return CommandResult(1, "", "push rejected")
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/1")
    monkeypatch.setattr(seams, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="git push failed"):
        GitHubPRBranchPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )


def test_gitlab_pr_branch_commits_and_posts_mr_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitLab pr-branch: commit to current branch + ``glab mr note`` (not create)."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "12")
    monkeypatch.setenv(
        "CI_MERGE_REQUEST_PROJECT_URL", "https://gitlab.com/o/r"
    )
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitLabPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="note body", flagged=False
    )
    # Run-record URL composed from the CI MR env.
    assert url == "https://gitlab.com/o/r/-/merge_requests/12"
    glab_calls = [c for c in seen if c[0] == "glab"]
    assert glab_calls, "a glab mr note must be posted"
    assert all("create" not in c for c in glab_calls)
    note = glab_calls[0]
    assert note[:3] == ["glab", "mr", "note"]
    assert "12" in note
    git_calls = [c for c in seen if c[0] == "git"]
    assert not any("checkout" in c for c in git_calls)
    push_call = next(c for c in git_calls if c[:2] == ["git", "push"])
    assert "--force" not in push_call


def test_pr_branch_publishers_satisfy_protocol() -> None:
    """Both pr-branch publishers are drop-in ReviewPublishers (seam-compatible)."""
    assert isinstance(GitHubPRBranchPublisher(), seams.ReviewPublisher)
    assert isinstance(GitLabPRBranchPublisher(), seams.ReviewPublisher)


# --------------------------------------------------------------------------- #
# BDL-049 hardening: pr-branch edge cases (mr_url env, flagged run, comment skip)
# --------------------------------------------------------------------------- #


def test_gitlab_pr_branch_url_empty_when_project_url_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IID set but PROJECT_URL unset → the run-record MR url is empty (no guess).

    The note can still be posted (the IID identifies the MR for ``glab``), but
    the composed URL needs BOTH env vars; with one missing it must stay empty
    rather than emit a malformed ``/-/merge_requests/<iid>`` URL.
    """
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "12")
    monkeypatch.delenv("CI_MERGE_REQUEST_PROJECT_URL", raising=False)
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitLabPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
    )
    assert url == ""
    # The note is still posted (the IID alone identifies the MR for glab).
    assert any(c[:3] == ["glab", "mr", "note"] for c in seen)


def test_gitlab_pr_branch_no_iid_skips_note_and_empty_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No CI_MERGE_REQUEST_IID → no note attempted and an empty run-record URL."""
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.delenv("CI_MERGE_REQUEST_IID", raising=False)
    monkeypatch.setenv("CI_MERGE_REQUEST_PROJECT_URL", "https://gitlab.com/o/r")
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitLabPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
    )
    assert url == ""
    # Commit still lands; only the MR note is skipped (no target IID).
    assert any("commit" in c for c in seen if c[0] == "git")
    assert not any(c[0] == "glab" for c in seen)


def test_gitlab_pr_branch_trailing_slash_project_url_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A trailing slash on the project URL is stripped (no doubled ``//``)."""

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "7")
    monkeypatch.setenv("CI_MERGE_REQUEST_PROJECT_URL", "https://gitlab.com/o/r/")
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitLabPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
    )
    assert url == "https://gitlab.com/o/r/-/merge_requests/7"


def test_gitlab_pr_branch_note_failure_does_not_fail_run(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A failing ``glab mr note`` is best-effort: the run still succeeds."""

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "glab":
            return CommandResult(1, "", "glab note boom")
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("CI_MERGE_REQUEST_IID", "3")
    monkeypatch.setenv("CI_MERGE_REQUEST_PROJECT_URL", "https://gitlab.com/o/r")
    monkeypatch.setattr(seams, "run_command", fake_run)
    with caplog.at_level("WARNING"):
        url = GitLabPRBranchPublisher().publish(
            project_root=Path("/x"), branch="b", title="T", body="B", flagged=False
        )
    assert url == "https://gitlab.com/o/r/-/merge_requests/3"
    assert any("comment" in r.message.lower() for r in caplog.records)


def test_github_pr_branch_flagged_run_still_commits_and_comments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A flagged run (needs-human) still lands the commit + posts the comment.

    ``flagged`` is part of the publisher contract but the title already encodes
    the state; pr-branch mode must behave identically — the body (gate=FAILED /
    flagged reasons) is what the comment carries, and the deliverable commit
    still lands so the human reviews docs + flag together in one PR.
    """
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/13")
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPRBranchPublisher().publish(
        project_root=Path("/x"),
        branch="b",
        title="⚠ needs human: docs refresh (1 doc(s))",
        body="gate=FAILED\n- beadloom ci failed",
        flagged=True,
    )
    assert url == "https://github.com/o/r/pull/13"
    # Commit landed despite the flag.
    assert any("commit" in c for c in seen if c[0] == "git")
    # The flagged body reached the PR comment verbatim.
    comment = next(c for c in seen if c[:3] == ["gh", "pr", "comment"])
    assert comment[comment.index("--body") + 1] == "gate=FAILED\n- beadloom ci failed"


def test_github_pr_branch_commit_message_preserves_skip_token_with_special_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A title with shell/markdown specials still yields a [skip ai-techwriter] msg.

    Title is passed as an argv element (never shell-interpolated), so special
    characters must survive into the commit ``-m`` verbatim behind the token.
    """
    seen: list[list[str]] = []

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        seen.append(args)
        if _has_staged_docs(args):
            return CommandResult(1, "", "")
        return CommandResult(0, "", "")

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/1")
    monkeypatch.setattr(seams, "run_command", fake_run)
    tricky = "docs: refresh `graph.md` & $PATH; rm -rf /"
    GitHubPRBranchPublisher().publish(
        project_root=Path("/x"), branch="b", title=tricky, body="B", flagged=False
    )
    commit = next(c for c in seen if c[0] == "git" and "commit" in c)
    msg = commit[commit.index("-m") + 1]
    assert msg == f"[skip ai-techwriter] {tricky}"


def test_pr_branch_real_git_commits_onto_current_branch_with_skip_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real-git: pr-branch commits the doc edit onto the CURRENT (PR head) branch.

    Exercises real ``git add / commit / push`` against a local bare origin; only
    ``gh pr comment`` is mocked. Asserts: the commit lands on the checked-out
    PR-head branch (no new branch is created), its message starts with
    ``[skip ai-techwriter]`` (the loop-guard), it is authored by the bot, and
    the pushed branch carries the doc edit + run-record.
    """
    work = tmp_path / "work"
    work.mkdir()
    bare = tmp_path / "origin.git"
    _seed_repo_with_origin(work, bare)

    # The runner is checked out on the PR head branch (NOT main).
    pr_branch = "features/example"
    _git_out(work, "checkout", "-b", pr_branch)
    _git_out(work, "push", "-u", "origin", pr_branch)
    head_before = _git_out(bare, "rev-parse", pr_branch).strip()

    # Agent left an uncommitted doc edit; the harness wrote the run-record.
    (work / "docs" / "graph.md").write_text("old\nrefreshed by AI\n", encoding="utf-8")
    (work / ".beadloom").mkdir()
    (work / ".beadloom" / "ai_techwriter_runs.json").write_text("[]\n", encoding="utf-8")

    real_run = commands.run_command

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "gh":
            return CommandResult(0, "", "")
        return real_run(args, cwd=cwd)

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/55")
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPRBranchPublisher().publish(
        project_root=work,
        branch="ignored",
        title="docs: AI tech-writer refresh (1 doc(s))",
        body="B",
        flagged=False,
    )
    assert url == "https://github.com/o/r/pull/55"

    # No NEW branch was created — only the seed 'main' + the PR head branch exist.
    branches = {
        b.strip().lstrip("* ").strip()
        for b in _git_out(work, "branch", "--format=%(refname:short)").splitlines()
        if b.strip()
    }
    assert branches == {"main", pr_branch}

    # The PR head branch advanced by one commit on origin.
    head_after = _git_out(bare, "rev-parse", pr_branch).strip()
    assert head_after != head_before

    # The new commit carries the skip-token message + bot author + the changes.
    subject = _git_out(bare, "log", "-1", "--format=%s", pr_branch).strip()
    assert subject.startswith("[skip ai-techwriter]")
    author = _git_out(bare, "log", "-1", "--format=%an", pr_branch).strip()
    assert author == "beadloom-ai-techwriter"
    doc_in_commit = _git_out(bare, "show", f"{head_after}:docs/graph.md")
    assert "refreshed by AI" in doc_in_commit
    tree = _git_out(bare, "show", "--stat", "--format=", head_after)
    assert ".beadloom/ai_techwriter_runs.json" in tree


def test_pr_branch_real_git_zero_docs_makes_no_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real-git: a 0-doc run (only the record written) creates NO commit/push."""
    work = tmp_path / "work"
    work.mkdir()
    bare = tmp_path / "origin.git"
    _seed_repo_with_origin(work, bare)
    pr_branch = "features/example"
    _git_out(work, "checkout", "-b", pr_branch)
    _git_out(work, "push", "-u", "origin", pr_branch)
    head_before = _git_out(work, "rev-parse", "HEAD").strip()

    # No doc edit — only the run-record changed (the flagged-needs-human case).
    (work / ".beadloom").mkdir()
    (work / ".beadloom" / "ai_techwriter_runs.json").write_text("[]\n", encoding="utf-8")

    real_run = commands.run_command

    def fake_run(args: list[str], *, cwd: Path) -> CommandResult:
        if args[0] == "gh":
            return CommandResult(0, "", "")
        return real_run(args, cwd=cwd)

    monkeypatch.setenv("PR_URL", "https://github.com/o/r/pull/66")
    monkeypatch.setattr(seams, "run_command", fake_run)
    url = GitHubPRBranchPublisher().publish(
        project_root=work, branch="ignored", title="docs: refresh (0 doc(s))", body="B",
        flagged=True,
    )
    assert url == "https://github.com/o/r/pull/66"
    # HEAD did not move — no empty commit was created.
    assert _git_out(work, "rev-parse", "HEAD").strip() == head_before
