"""Mockable seams: the agent (Goose) and the review publisher (PR/MR).

These two interfaces wall off the only non-deterministic / network-touching
parts of the harness:

* :class:`AgentRunner` — the per-doc rewrite (Goose + model). The harness
  depends only on the protocol; :class:`GooseAgentRunner` is the real (thin)
  subprocess wiring, :class:`FakeAgentRunner` is the test double.
* :class:`ReviewPublisher` — branch + open a PR (GitHub) or MR (GitLab) via a
  platform adapter. :class:`FakePublisher` is the test double.

The real Goose recipe wiring lands in BEAD-03; here we define only the
invocation contract + a thin subprocess call.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from tools.ai_techwriter.commands import run_command
from tools.ai_techwriter.models import AgentResult, ContextPacket

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@runtime_checkable
class AgentRunner(Protocol):
    """Rewrite one drifted doc from its context packet.

    Implementations MUST write the rewritten doc(s) to disk and report the
    paths touched plus the model's real token usage.
    """

    def run(self, packet: ContextPacket) -> AgentResult:
        """Repair the doc described by *packet*; return the result."""
        ...


@runtime_checkable
class ReviewPublisher(Protocol):
    """Branch + push + open a PR/MR for human review (never auto-merge)."""

    def publish(
        self,
        *,
        project_root: Path,
        branch: str,
        title: str,
        body: str,
        flagged: bool,
    ) -> str:
        """Open the review request; return its URL."""
        ...


class GooseAgentRunner:
    """Real agent seam: shells out to Goose with a recipe + the packet.

    Thin by design — the recipe/provider wiring is BEAD-03. Here we only define
    the invocation contract: pass the packet as JSON on a recipe param, run
    Goose headless, and read back a small JSON usage report it emits.
    """

    def __init__(
        self,
        *,
        project_root: Path,
        recipe_path: Path,
        model: str,
    ) -> None:
        self._project_root = project_root
        self._recipe_path = recipe_path
        self._model = model

    def run(self, packet: ContextPacket) -> AgentResult:
        """Invoke Goose headless on *packet*; parse its usage report."""
        packet_json = json.dumps(_packet_payload(packet))
        result = run_command(
            [
                "goose",
                "run",
                "--recipe",
                str(self._recipe_path),
                "--params",
                f"packet={packet_json}",
            ],
            cwd=self._project_root,
        )
        if not result.ok:
            raise RuntimeError(
                f"goose run failed (rc={result.returncode}): {result.stderr[:500]}"
            )
        return _parse_goose_usage(result.stdout, default_model=self._model, packet=packet)


def _packet_payload(packet: ContextPacket) -> dict[str, object]:
    """Serialise a packet to the Goose recipe parameter shape."""
    return {
        "ref_id": packet.ref_id,
        "doc_path": packet.doc_path,
        "current_content": packet.current_content,
        "drift_reason": packet.drift_reason,
        "docs_polish_json": packet.docs_polish_json,
        "ctx": packet.ctx,
        "why": packet.why,
    }


def _parse_goose_usage(
    stdout: str, *, default_model: str, packet: ContextPacket
) -> AgentResult:
    """Parse the JSON usage line Goose emits (last JSON object in stdout)."""
    usage: dict[str, object] = {}
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                usage = candidate
                break
    paths = usage.get("rewritten_paths")
    rewritten = tuple(str(p) for p in paths) if isinstance(paths, list) else (packet.doc_path,)
    return AgentResult(
        rewritten_paths=rewritten,
        input_tokens=_as_int(usage.get("input_tokens")),
        output_tokens=_as_int(usage.get("output_tokens")),
        model=str(usage.get("model") or default_model),
    )


def _as_int(value: object) -> int:
    """Best-effort non-negative int from an untyped JSON value."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


class GitHubPublisher:
    """Open a PR via ``gh pr create`` after pushing the branch."""

    def publish(
        self,
        *,
        project_root: Path,
        branch: str,
        title: str,
        body: str,
        flagged: bool,
    ) -> str:
        """Push *branch* and open a GitHub PR; return its URL."""
        _push_branch(project_root, branch)
        args = ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body]
        if flagged:
            args += ["--label", "needs-human"]
        result = run_command(args, cwd=project_root)
        if not result.ok:
            raise RuntimeError(f"gh pr create failed (rc={result.returncode}): {result.stderr}")
        return result.stdout.strip()


class GitLabPublisher:
    """Open an MR via ``glab mr create`` after pushing the branch."""

    def publish(
        self,
        *,
        project_root: Path,
        branch: str,
        title: str,
        body: str,
        flagged: bool,
    ) -> str:
        """Push *branch* and open a GitLab MR; return its URL."""
        _push_branch(project_root, branch)
        args = [
            "glab",
            "mr",
            "create",
            "--source-branch",
            branch,
            "--title",
            title,
            "--description",
            body,
            "--yes",
        ]
        if flagged:
            args += ["--label", "needs-human"]
        result = run_command(args, cwd=project_root)
        if not result.ok:
            raise RuntimeError(f"glab mr create failed (rc={result.returncode}): {result.stderr}")
        return result.stdout.strip()


def _push_branch(project_root: Path, branch: str) -> None:
    """Push *branch* to origin (create the upstream ref)."""
    result = run_command(["git", "push", "--set-upstream", "origin", branch], cwd=project_root)
    if not result.ok:
        raise RuntimeError(f"git push failed (rc={result.returncode}): {result.stderr}")


class FakeAgentRunner:
    """Test double for :class:`AgentRunner`.

    Records the packets it was handed, optionally writes deterministic content
    to the touched docs, and can be configured per-call to fail (to exercise
    the per-doc retry loop). Reports fixed token usage so run-records are
    deterministic.
    """

    def __init__(
        self,
        *,
        project_root: Path | None = None,
        model: str = "fake-model",
        input_tokens: int = 100,
        output_tokens: int = 50,
        write_marker: str | None = "<!-- refreshed -->",
        fail_first_n: int = 0,
    ) -> None:
        self._project_root = project_root
        self._model = model
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._write_marker = write_marker
        self._fail_first_n = fail_first_n
        self.calls: list[ContextPacket] = []

    def run(self, packet: ContextPacket) -> AgentResult:
        """Record the call; optionally fail or write a marker; return usage."""
        self.calls.append(packet)
        if len(self.calls) <= self._fail_first_n:
            raise RuntimeError("FakeAgentRunner: simulated agent failure")
        if self._project_root is not None and self._write_marker is not None:
            target = self._project_root / packet.doc_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                f"{packet.current_content}\n{self._write_marker}\n", encoding="utf-8"
            )
        return AgentResult(
            rewritten_paths=(packet.doc_path,),
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            model=self._model,
        )


class FakePublisher:
    """Test double for :class:`ReviewPublisher`.

    Records the publish call and returns a deterministic URL; never touches
    git or the network.
    """

    def __init__(self, *, url: str = "https://example.test/pr/1") -> None:
        self._url = url
        self.published: list[dict[str, object]] = []

    def publish(
        self,
        *,
        project_root: Path,
        branch: str,
        title: str,
        body: str,
        flagged: bool,
    ) -> str:
        """Record the publish call; return the configured URL."""
        self.published.append(
            {
                "project_root": str(project_root),
                "branch": branch,
                "title": title,
                "body": body,
                "flagged": flagged,
            }
        )
        return self._url
