# beadloom:domain=onboarding
"""Idempotent ``main`` branch-protection helper (BDL-049 / BEAD-03).

Trunk-based development (CLAUDE.md §6 Git) requires ``main`` to be
branch-protected: every change integrates via a PR (no direct push) and the
``beadloom ci`` gate is a **required status check**, so the gate becomes true
enforcement (hardening BDL-048 G5) rather than advisory CI.

The helper configures GitHub branch protection via ``gh api``::

    gh api --method PUT \
      -H "Accept: application/vnd.github+json" \
      repos/{owner}/{repo}/branches/main/protection \
      --input -      # the JSON payload is fed on stdin

with this payload (the protection contract):

- ``required_status_checks`` — ``strict: true`` (the branch must be up to date)
  + ``contexts`` = the CI/test workflow check names (default
  :data:`DEFAULT_STATUS_CHECK_CONTEXTS`).
- ``required_pull_request_reviews`` — ``{"required_approving_review_count": 0}``:
  a PR IS required, but the **solo owner can self-merge** (no human review
  needed). Team review later is a one-field bump.
- ``enforce_admins: false`` and ``restrictions: null`` — the owner is NEVER
  locked out (admins are exempt; no push-restriction allow-list).

``PUT .../protection`` is **declarative**, so applying it twice is naturally
idempotent: the second call sends the byte-identical payload and re-settles the
same state. The ``gh`` invocation is injected (:class:`GhRunner`) so it is fully
mockable — tests assert the request WITHOUT touching GitHub.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Protocol

#: Default required status-check contexts — the Beadloom CI gate + test job, by
#: their GitHub check-run names. Override via ``status_check_contexts`` when a
#: repo names its workflow checks differently.
DEFAULT_STATUS_CHECK_CONTEXTS: tuple[str, ...] = ("beadloom ci", "tests")

#: The protected branch (trunk). Configurable, but ``main`` is the default trunk.
DEFAULT_BRANCH = "main"

#: ``Accept`` header GitHub recommends for its REST API via ``gh api``.
_ACCEPT_HEADER = "Accept: application/vnd.github+json"


class GhRunner(Protocol):
    """Runs the full ``argv`` (``["gh", ...]``) with ``stdin``; returns stdout.

    Injected/mockable: tests pass a fake that records the argv + stdin without
    touching GitHub.
    """

    def __call__(self, argv: list[str], stdin: str) -> str: ...


def build_protection_payload(
    *,
    status_check_contexts: tuple[str, ...] = DEFAULT_STATUS_CHECK_CONTEXTS,
) -> dict[str, object]:
    """Build the GitHub branch-protection request body (the protection contract).

    PR required (no direct push), ``beadloom ci`` a required check (``strict``),
    ``enforce_admins: false`` + 0 required reviews + ``restrictions: null`` so the
    solo owner is never locked out and can still self-merge.
    """
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": list(status_check_contexts),
        },
        "enforce_admins": False,
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "restrictions": None,
    }


@dataclass(frozen=True)
class BranchProtectionRequest:
    """The exact ``gh api`` request the helper WOULD send (inspectable/mockable)."""

    owner: str
    repo: str
    branch: str = DEFAULT_BRANCH
    status_check_contexts: tuple[str, ...] = DEFAULT_STATUS_CHECK_CONTEXTS

    def endpoint(self) -> str:
        """The protection REST endpoint, e.g. ``repos/o/r/branches/main/protection``."""
        return f"repos/{self.owner}/{self.repo}/branches/{self.branch}/protection"

    def payload_json(self) -> str:
        """The request body as deterministic JSON (sent on stdin via ``--input -``)."""
        payload = build_protection_payload(
            status_check_contexts=self.status_check_contexts
        )
        return json.dumps(payload, sort_keys=True)

    def gh_args(self) -> list[str]:
        """Arguments to ``gh`` (without the ``gh`` program name itself)."""
        return [
            "api",
            "--method",
            "PUT",
            "-H",
            _ACCEPT_HEADER,
            self.endpoint(),
            "--input",
            "-",
        ]


def _subprocess_runner(argv: list[str], stdin: str) -> str:
    """Default :class:`GhRunner`: shell out to the real ``gh`` CLI."""
    completed = subprocess.run(  # noqa: S603 - argv is built internally, not user shell
        argv,
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def apply_branch_protection(
    owner: str,
    repo: str,
    *,
    branch: str = DEFAULT_BRANCH,
    status_check_contexts: tuple[str, ...] = DEFAULT_STATUS_CHECK_CONTEXTS,
    runner: GhRunner | None = None,
) -> BranchProtectionRequest:
    """Configure ``branch`` protection on ``owner/repo`` via ``gh api`` (idempotent).

    Builds the declarative PUT request (see :class:`BranchProtectionRequest`) and
    runs it through ``runner`` (defaults to the real ``gh`` CLI; inject a fake in
    tests). Safe to re-run — ``PUT .../protection`` re-settles the same state.
    Returns the request that was sent, for inspection/logging.
    """
    request = BranchProtectionRequest(
        owner=owner,
        repo=repo,
        branch=branch,
        status_check_contexts=status_check_contexts,
    )
    run = runner if runner is not None else _subprocess_runner
    run(["gh", *request.gh_args()], request.payload_json())
    return request
