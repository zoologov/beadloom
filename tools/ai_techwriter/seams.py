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
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from tools.ai_techwriter.commands import run_command
from tools.ai_techwriter.models import AgentResult, ContextPacket
from tools.ai_techwriter.runs_store import load_runs, runs_store_path

if TYPE_CHECKING:
    from tools.ai_techwriter.provider import ProviderConfig

logger = logging.getLogger(__name__)

#: Bot identity stamped on the auto-commit. Set inline on the ``git commit`` so
#: CI runners without a global git config can still commit (no network, no user
#: config required). A noreply address keeps the bot out of contributor stats.
_BOT_NAME = "beadloom-ai-techwriter"
_BOT_EMAIL = "beadloom-ai-techwriter@users.noreply.github.com"

#: BDL-049 loop-guard token. The pr-branch refresh commit message STARTS with
#: this so the workflow's early-skip step (and a belt-and-suspenders author
#: check) can tell the agent's own push apart from a human push and NOT
#: re-trigger the ``pull_request: synchronize`` run (an otherwise-infinite loop).
_SKIP_TOKEN = "[skip ai-techwriter]"  # noqa: S105 - loop-guard token, not a secret

#: BDL-049 pr-branch mode: CI env vars the workflow injects so the publisher can
#: resolve the pre-existing PR/MR (no chicken-and-egg — the PR already exists).
#: GitHub passes the full PR URL; GitLab passes the MR IID + project URL.
_GH_PR_URL_ENV = "PR_URL"
_GL_MR_IID_ENV = "CI_MERGE_REQUEST_IID"
_GL_MR_PROJECT_URL_ENV = "CI_MERGE_REQUEST_PROJECT_URL"

#: Paths staged into the auto-commit: the agent's doc edits AND the G9
#: run-record (``.beadloom/ai_techwriter_runs.json`` is tracked — only the
#: ``.beadloom/*.db`` files are gitignored). Staging the run-record guarantees a
#: non-empty commit even when 0 docs changed (flagged-needs-human case), so
#: ``git commit`` never fails on "nothing to commit".
_STAGED_PATHS = ("docs", ".beadloom/ai_techwriter_runs.json")


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


@runtime_checkable
class CommentPublisher(Protocol):
    """A publisher that can post a standalone comment on the existing PR/MR.

    BDL-050 ``infra`` path: when the agent never ran (tokens==0) there is no
    refresh to publish, but the entrypoint still wants to leave a best-effort
    "could not run — docs were NOT checked" note on the PR/MR. The pr-branch
    publishers (which already resolve the pre-existing PR/MR from the CI env)
    implement this; other publishers simply do not, so the caller skips it.
    """

    def comment(self, *, project_root: Path, body: str) -> bool:
        """Post *body* on the pre-existing PR/MR; return True iff it was posted."""
        ...


class GooseAgentRunner:
    """Real agent seam: shells out to Goose with a recipe + provider + packet.

    Builds the headless ``goose run`` invocation from the shipped recipe (tool
    allow-list + the tech-writer instructions), the :class:`ProviderConfig`
    (Qwen3.7-Plus over an OpenAI-compatible endpoint; key resolved from env, set
    on the child process, never inlined), and the per-doc context packet. Parses
    the JSON usage report Goose emits into an :class:`AgentResult`.

    A failed / empty run is handled gracefully: an empty :class:`AgentResult`
    (no rewritten paths) is returned so the harness's fixpoint treats the doc as
    still stale and retries / flags it — it never crashes the run.
    """

    def __init__(
        self,
        *,
        project_root: Path,
        recipe_path: Path,
        provider: ProviderConfig,
    ) -> None:
        self._project_root = project_root
        self._recipe_path = recipe_path
        self._provider = provider

    def run(self, packet: ContextPacket) -> AgentResult:
        """Invoke Goose headless on *packet*; parse its usage report.

        BUG-C: the packet (full doc content + ctx + why + docs-polish JSON) is
        tens of KB on real docs and blows ``ARG_MAX`` if inlined on argv
        (``[Errno 7] Argument list too long``). It is written to a temp file and
        only the FILE PATH is passed to Goose (``--params packet_file=<path>``);
        the recipe instructs the agent to read it via the allowed read-only FS
        tool. The temp file is always cleaned up, even on error.
        """
        packet_json = json.dumps(_packet_payload(packet))
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            prefix="ai_techwriter_packet_",
            delete=False,
        ) as handle:
            handle.write(packet_json)
            packet_file = Path(handle.name)
        try:
            args = self._build_command(packet_file)
            env = self._provider.goose_env(api_key=self._provider.resolve_api_key())
            result = run_command(args, cwd=self._project_root, env=env)
        finally:
            packet_file.unlink(missing_ok=True)
        if not result.ok:
            logger.warning(
                "goose run failed (rc=%d): %s",
                result.returncode,
                result.stderr[:500],
            )
            return _empty_result(self._provider.model)
        return _parse_goose_usage(result.stdout, default_model=self._provider.model, packet=packet)

    def _build_command(self, packet_file: Path) -> list[str]:
        """Construct the headless ``goose run`` argv (recipe + packet FILE + caps).

        Only the *path* to the packet file goes on argv — never the payload — so
        the invocation stays well under ``ARG_MAX`` regardless of doc size.
        """
        return [
            "goose",
            "run",
            "--recipe",
            str(self._recipe_path),
            "--params",
            f"packet_file={packet_file}",
            "--max-turns",
            str(self._provider.max_turns),
            "--no-session",
        ]


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


def _parse_goose_usage(stdout: str, *, default_model: str, packet: ContextPacket) -> AgentResult:
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


def _empty_result(model: str) -> AgentResult:
    """An empty result: no docs written, no tokens — 'still stale' to the loop."""
    return AgentResult(
        rewritten_paths=(),
        input_tokens=0,
        output_tokens=0,
        model=model,
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
        """Push *branch* and open a GitHub PR; return its URL.

        BUG-D: no ``--label needs-human``. A flagged run already prefixes the
        title with "⚠ needs human", so the label is redundant — and dropping it
        removes the dependency on the target repo owning that label (``gh pr
        create`` errors out with "could not add label: 'needs-human' not found"
        otherwise). *flagged* still drives the title prefix upstream.
        """
        del flagged  # title already encodes the flagged state; no label needed.
        _commit_changes(project_root, branch, title)
        _push_branch(project_root, branch)
        args = ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body]
        result = run_command(args, cwd=project_root)
        if not result.ok:
            raise RuntimeError(f"gh pr create failed (rc={result.returncode}): {result.stderr}")
        url = result.stdout.strip()
        _backfill_pr_url(project_root, branch, url)
        return url


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
        """Push *branch* and open a GitLab MR; return its URL.

        BUG-D: no ``--label needs-human`` (same rationale as the GitHub path —
        the title already prefixes "⚠ needs human" and the target project need
        not own that label). *flagged* still drives the title prefix upstream.
        """
        del flagged  # title already encodes the flagged state; no label needed.
        _commit_changes(project_root, branch, title)
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
        result = run_command(args, cwd=project_root)
        if not result.ok:
            raise RuntimeError(f"glab mr create failed (rc={result.returncode}): {result.stderr}")
        url = result.stdout.strip()
        _backfill_pr_url(project_root, branch, url)
        return url


class GitHubPRBranchPublisher:
    """BDL-049 pr-branch mode: commit the refresh onto the EXISTING PR head.

    On a ``pull_request`` run the runner is already checked out on the PR head
    branch, so instead of cutting a new branch + ``gh pr create`` (which yields
    an orphan doc-PR), this publisher commits the refreshed docs + run-record
    *onto the current branch* and posts a summary comment on the pre-existing
    PR. Code + docs become one reviewable PR; the human still merges.

    The PR URL is resolved from the CI env (:data:`_GH_PR_URL_ENV`) — reliable
    now because the PR pre-exists (no chicken-and-egg, no amend/backfill). The
    comment is best-effort: if ``gh pr comment`` fails the run still succeeds
    (the commit is the deliverable).
    """

    def publish(
        self,
        *,
        project_root: Path,
        branch: str,
        title: str,
        body: str,
        flagged: bool,
    ) -> str:
        """Commit onto the current branch + push + comment; return the PR URL.

        *branch* / *flagged* are part of the :class:`ReviewPublisher` contract
        but unused here: pr-branch mode never cuts a branch, and the title
        already encodes the flagged state.
        """
        del branch, flagged
        pr_url = os.environ.get(_GH_PR_URL_ENV, "").strip()
        if _commit_to_current_branch(project_root, title):
            _push_current_branch(project_root)
        if pr_url:
            _post_pr_comment(project_root, ["gh", "pr", "comment", pr_url, "--body", body])
        return pr_url

    def comment(self, *, project_root: Path, body: str) -> bool:
        """Best-effort note on the pre-existing PR (BDL-050 infra path).

        Resolves the PR from :data:`_GH_PR_URL_ENV` (the same env the publish
        path uses); with no PR context there is nothing to comment on, so it is
        a no-op (returns False). Never raises — the caller already has the loud
        ``::warning::`` annotation as the primary signal.
        """
        pr_url = os.environ.get(_GH_PR_URL_ENV, "").strip()
        if not pr_url:
            return False
        return _post_pr_comment(project_root, ["gh", "pr", "comment", pr_url, "--body", body])


class GitLabPRBranchPublisher:
    """BDL-049 pr-branch mode for GitLab MRs (mirror of the GitHub path).

    Commits the refresh onto the MR source branch the runner checked out and
    posts a ``glab mr note`` on the pre-existing MR instead of ``glab mr
    create``. The MR URL for the run-record is composed from the CI MR env
    (:data:`_GL_MR_PROJECT_URL_ENV` + :data:`_GL_MR_IID_ENV`); the note is
    best-effort.
    """

    def publish(
        self,
        *,
        project_root: Path,
        branch: str,
        title: str,
        body: str,
        flagged: bool,
    ) -> str:
        """Commit onto the current branch + push + MR note; return the MR URL."""
        del branch, flagged
        iid = os.environ.get(_GL_MR_IID_ENV, "").strip()
        mr_url = _gitlab_mr_url(iid)
        if _commit_to_current_branch(project_root, title):
            _push_current_branch(project_root)
        if iid:
            _post_pr_comment(project_root, ["glab", "mr", "note", iid, "--message", body])
        return mr_url

    def comment(self, *, project_root: Path, body: str) -> bool:
        """Best-effort note on the pre-existing MR (BDL-050 infra path).

        Resolves the MR IID from :data:`_GL_MR_IID_ENV`; with no MR context it
        is a no-op (returns False). Never raises — the ``::warning::`` annotation
        is the primary signal.
        """
        iid = os.environ.get(_GL_MR_IID_ENV, "").strip()
        if not iid:
            return False
        return _post_pr_comment(project_root, ["glab", "mr", "note", iid, "--message", body])


def _gitlab_mr_url(iid: str) -> str:
    """Compose the MR URL from the CI env (empty when the env is incomplete)."""
    project_url = os.environ.get(_GL_MR_PROJECT_URL_ENV, "").strip()
    if not iid or not project_url:
        return ""
    return f"{project_url.rstrip('/')}/-/merge_requests/{iid}"


def _commit_to_current_branch(project_root: Path, title: str) -> bool:
    """Stage docs + record and commit onto the CURRENT branch (no ``checkout -b``).

    Returns True iff a commit was made. When the agent produced no doc edit
    (0 docs changed) there is nothing to land, so we skip the commit entirely
    rather than create an empty/record-only commit on the PR branch (BDL-049
    no-op rule). The commit message STARTS with :data:`_SKIP_TOKEN` so the
    workflow loop-guard does not re-trigger on the agent's own push, and uses
    the inline bot identity so a CI runner without a global git config commits.
    """
    if not _has_doc_changes(project_root):
        return False
    _git(project_root, ["add", "--", *_STAGED_PATHS], "git add")
    message = f"{_SKIP_TOKEN} {title}"
    _git(
        project_root,
        [
            "-c",
            f"user.name={_BOT_NAME}",
            "-c",
            f"user.email={_BOT_EMAIL}",
            "commit",
            "-m",
            message,
        ],
        "git commit",
    )
    return True


def _has_doc_changes(project_root: Path) -> bool:
    """True when there are staged-or-unstaged changes under ``docs/``.

    Stages ``docs`` then probes ``git diff --cached --quiet -- docs`` (rc 0 =
    clean, rc 1 = changes). This is what implements the 0-doc no-op: a run that
    only wrote the run-record (no doc edit) must NOT produce a commit.
    """
    _git(project_root, ["add", "--", "docs"], "git add (probe)")
    probe = run_command(
        ["git", "diff", "--cached", "--quiet", "--", "docs"], cwd=project_root
    )
    return not probe.ok


def _push_current_branch(project_root: Path) -> None:
    """Push the current branch (``HEAD``) — a plain, non-force push.

    The runner is checked out on the PR head branch and we add a new commit on
    top, so a fast-forward plain push is correct (no force: this is not the
    bot-owned regenerated proposal branch of the branch-PR path).
    """
    result = run_command(["git", "push", "origin", "HEAD"], cwd=project_root)
    if not result.ok:
        raise RuntimeError(f"git push failed (rc={result.returncode}): {result.stderr}")


def _post_pr_comment(project_root: Path, args: list[str]) -> bool:
    """Post a PR/MR comment best-effort: log + swallow failure (commit is it).

    Mirrors :func:`_backfill_pr_url`'s best-effort discipline — the refresh
    commit on the PR branch is the deliverable, so a flaky ``gh``/``glab``
    comment never fails the run. Returns True iff the comment was posted (the
    BDL-050 ``infra`` path uses this to know whether the note actually landed).
    """
    result = run_command(args, cwd=project_root)
    if not result.ok:
        logger.warning(
            "could not post the PR/MR comment (rc=%d): %s",
            result.returncode,
            result.stderr[:500],
        )
    return result.ok


def _commit_changes(project_root: Path, branch: str, title: str) -> None:
    """Cut *branch* from the current checkout and commit the harness's changes.

    The agent leaves its doc rewrites as uncommitted working-tree changes and
    the harness writes the G9 run-record before publishing; neither is committed
    yet. Without this step ``_push_branch`` would push ``main``'s HEAD under a
    new branch name → an **empty** PR/MR (BUG-A). Here we:

    1. ``git checkout -b <branch>`` from the current (main) checkout,
    2. stage the doc edits **and** the run-record (:data:`_STAGED_PATHS`),
    3. ``git commit`` with an inline bot identity so CI without a global git
       config still commits.

    The staged run-record guarantees a non-empty commit even when 0 docs
    changed, so ``git commit`` never fails on "nothing to commit".
    """
    _git(project_root, ["checkout", "-b", branch], "git checkout -b")
    _git(project_root, ["add", "--", *_STAGED_PATHS], "git add")
    _git(
        project_root,
        [
            "-c",
            f"user.name={_BOT_NAME}",
            "-c",
            f"user.email={_BOT_EMAIL}",
            "commit",
            "-m",
            title,
        ],
        "git commit",
    )


def _git(project_root: Path, args: list[str], label: str) -> None:
    """Run a ``git`` subcommand in *project_root*; raise with *label* on failure."""
    result = run_command(["git", *args], cwd=project_root)
    if not result.ok:
        raise RuntimeError(f"{label} failed (rc={result.returncode}): {result.stderr}")


def _push_branch(project_root: Path, branch: str) -> None:
    """Force-push *branch* to origin, creating/updating the upstream ref.

    BUG-J: the refresh branch name is deterministic (derived from the doc
    slugs), so a lingering branch from a prior run (e.g. an unmerged PR's head)
    makes a plain ``git push`` fail non-fast-forward. The refresh branch is a
    regenerated, bot-owned proposal branch, so force-pushing it is *correct* —
    it updates the open PR/MR's head to the latest proposal. Plain ``--force``
    (not ``--force-with-lease``) is right here: the branch is exclusively the
    bot's, and a lease can't be established on a fresh CI checkout that just
    created the local branch.
    """
    args = ["git", "push", "--force", "--set-upstream", "origin", branch]
    result = run_command(args, cwd=project_root)
    if not result.ok:
        raise RuntimeError(f"git push failed (rc={result.returncode}): {result.stderr}")


def _backfill_pr_url(project_root: Path, branch: str, url: str) -> None:
    """Best-effort: stamp *url* into the run-record, then amend + re-push.

    Closes the chicken-and-egg gap (the run-record is committed *before* the
    PR/MR exists, so it always carried an empty ``pr_url``). Now that the branch
    is force-pushable (BUG-J), after the PR/MR is created we: (1) write *url*
    into the latest run-record entry, (2) ``git commit --amend --no-edit`` with
    the bot identity, and (3) force-push so the PR head carries the URL.

    This is best-effort polish — the PR/MR itself is the source of truth. If any
    step fails the run is NOT failed: we log a warning and move on (the caller
    still returns the real PR/MR URL).
    """
    try:
        if not _record_pr_url(project_root, url):
            return
        _amend_commit(project_root)
        _push_branch(project_root, branch)
    except (RuntimeError, OSError) as exc:
        logger.warning(
            "could not backfill pr_url into the run-record (PR/MR already created at %s): %s",
            url,
            exc,
        )


def _record_pr_url(project_root: Path, url: str) -> bool:
    """Write *url* into the last run-record entry; return True if one was updated.

    No-op (returns False) when the store is absent/empty — there is nothing to
    stamp, so the caller skips the amend + re-push.
    """
    records = load_runs(project_root)
    if not records:
        return False
    records[-1]["pr_url"] = url
    path = runs_store_path(project_root)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return True


def _amend_commit(project_root: Path) -> None:
    """Re-include the updated run-record into HEAD via ``commit --amend``.

    Stages the run-record path and amends the existing commit (``--no-edit``,
    same message) with the same inline bot identity as :func:`_commit_changes`,
    so CI without a global git config can still amend.
    """
    _git(project_root, ["add", "--", *_STAGED_PATHS], "git add (amend)")
    _git(
        project_root,
        [
            "-c",
            f"user.name={_BOT_NAME}",
            "-c",
            f"user.email={_BOT_EMAIL}",
            "commit",
            "--amend",
            "--no-edit",
        ],
        "git commit --amend",
    )


class FakeAgentRunner:
    """Test double for :class:`AgentRunner`.

    Records the packets it was handed, optionally writes deterministic content
    to the touched docs, and can be configured per-call to fail (to exercise
    the per-doc retry loop). Reports fixed token usage so run-records are
    deterministic.

    Honest empty-result semantics (BUG-H): the fake reports
    ``rewritten_paths`` ONLY when it actually edits a doc. With
    ``write_marker=None`` (no edit written) it returns an EMPTY
    :class:`AgentResult`, mirroring the real ``GooseAgentRunner`` returning
    ``_empty_result`` on a failed ``goose run`` — so the harness treats it as
    "no edit produced", never a refresh.
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
        """Record the call; optionally fail or write a marker; return usage.

        Returns a result with non-empty ``rewritten_paths`` only when an edit is
        actually written (``write_marker`` set); otherwise an empty result with
        no rewritten paths (the no-edit / failed-agent case, BUG-H).
        """
        self.calls.append(packet)
        if len(self.calls) <= self._fail_first_n:
            raise RuntimeError("FakeAgentRunner: simulated agent failure")
        edited = self._project_root is not None and self._write_marker is not None
        if edited:
            assert self._project_root is not None  # narrowed by ``edited``
            target = self._project_root / packet.doc_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                f"{packet.current_content}\n{self._write_marker}\n", encoding="utf-8"
            )
        return AgentResult(
            rewritten_paths=(packet.doc_path,) if edited else (),
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
