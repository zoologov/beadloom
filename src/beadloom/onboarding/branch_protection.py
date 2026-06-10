# beadloom:domain=onboarding
"""Idempotent ``main`` branch-protection helper (BDL-049 / BEAD-03).

Trunk-based development (CLAUDE.md §6 Git) requires ``main`` to be
branch-protected: every change integrates via a PR (no direct push) and the
``beadloom-gate`` check is a **required status check**, so the gate becomes true
enforcement (hardening BDL-048 G5) rather than advisory CI.

.. important::
   A required status-check context must match a **real GitHub check-run name
   exactly**, and must NOT be a check produced by a **path-filtered** workflow.
   A path-filtered check does not run on PRs that miss the filter, so under
   ``strict: true`` the PR — and therefore ``main`` — becomes permanently
   unmergeable. The default :data:`DEFAULT_STATUS_CHECK_CONTEXTS` is the
   always-on ``beadloom-gate`` check-run for exactly this reason.

The helper configures GitHub branch protection via ``gh api``::

    gh api --method PUT \
      -H "Accept: application/vnd.github+json" \
      repos/{owner}/{repo}/branches/main/protection \
      --input -      # the JSON payload is fed on stdin

with this payload (the protection contract):

- ``required_status_checks`` — ``strict: true`` (the branch must be up to date)
  + ``contexts`` = the **real** GitHub check-run names that run on every PR
  (default :data:`DEFAULT_STATUS_CHECK_CONTEXTS` = the always-on
  ``beadloom-gate`` check; never a path-filtered workflow's check).
- ``required_pull_request_reviews`` — ``{"required_approving_review_count": 0}``:
  a PR IS required, but the **solo owner can self-merge** (no human review
  needed). Team review later is a one-field bump.
- ``enforce_admins: true`` — **strict trunk-based**: even repo admins (the
  owner) go through PRs and CANNOT direct-push to ``main`` or bypass the gate.
  Combined with ``required_approving_review_count: 0`` + the reliable always-on
  ``beadloom-gate`` required check, the owner is NOT locked out — they can still
  self-merge their own PR once the gate is green. Escape hatch: if
  ``beadloom-gate`` ever breaks, temporarily remove protection via the API
  (``gh api --method DELETE .../protection``) and re-apply once fixed.
- ``restrictions: null`` — no push-restriction allow-list.

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

#: Default required status-check context — the **real** GitHub check-run name of
#: the always-on Beadloom gate (the ``beadloom-gate`` job in the *Beadloom Gate*
#: workflow). That workflow runs on EVERY ``pull_request`` with **no ``paths:``
#: filter**, so the check always reports — making it safe to require under
#: ``strict: true``.
#:
#: A required status-check context MUST match a real GitHub check-run name
#: EXACTLY, and you must NOT require a check produced by a **path-filtered**
#: workflow: such a check does not run on PRs that miss the path filter, so under
#: ``strict: true`` the PR (and ``main``) becomes permanently unmergeable. The
#: repo's ``Tests`` workflow (``test (3.10)``…``test (3.13)``) IS path-filtered,
#: which is exactly why those legs are NOT the default. A repo whose test checks
#: run on every PR can require them by overriding ``status_check_contexts``
#: (CLI: repeatable ``--check``).
DEFAULT_STATUS_CHECK_CONTEXTS: tuple[str, ...] = ("beadloom-gate",)

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

    PR required (no direct push), the always-on ``beadloom-gate`` check required
    (``strict``), ``enforce_admins: true`` (strict trunk-based — even admins go
    through PRs, no bypass) + 0 required reviews + ``restrictions: null`` so the
    owner is NOT locked out and can still self-merge their own PR once the gate
    is green. ``status_check_contexts`` must be **real check-run names** and must
    NOT include a path-filtered workflow's check (it would not run on every PR →
    stuck PRs under ``strict``).
    """
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": list(status_check_contexts),
        },
        "enforce_admins": True,
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
