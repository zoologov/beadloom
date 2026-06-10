"""Tests for the idempotent `main` branch-protection helper (BDL-049 / BEAD-03).

The helper configures GitHub branch protection on ``main`` via ``gh api`` so that
the trunk-based flow is enforced: a PR is required (no direct push), ``beadloom
ci`` is a *required status check*, ``enforce_admins: false`` + 0 required reviews
so the solo owner is never locked out, and ``restrictions: null``.

These tests NEVER touch GitHub: the ``gh`` invocation is injected as a runner
callable and mocked. We assert (a) the exact request payload the helper WOULD
send and (b) that it is safe to re-run (idempotent — a PUT is declarative, so a
second identical call sends the identical payload and succeeds).
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from beadloom.onboarding.branch_protection import (
    DEFAULT_STATUS_CHECK_CONTEXTS,
    BranchProtectionRequest,
    apply_branch_protection,
    build_protection_payload,
)
from beadloom.services.cli import main


class TestPayload:
    def test_payload_requires_pr_with_zero_reviews(self) -> None:
        payload = build_protection_payload()
        reviews = payload["required_pull_request_reviews"]
        assert reviews == {"required_approving_review_count": 0}

    def test_payload_does_not_enforce_admins_or_restrict(self) -> None:
        """Owner must never be locked out: admins not enforced, no restrictions."""
        payload = build_protection_payload()
        assert payload["enforce_admins"] is False
        assert payload["restrictions"] is None

    def test_payload_required_status_checks_strict_with_default_contexts(self) -> None:
        payload = build_protection_payload()
        checks = payload["required_status_checks"]
        assert checks["strict"] is True
        assert checks["contexts"] == list(DEFAULT_STATUS_CHECK_CONTEXTS)

    def test_payload_honors_custom_contexts(self) -> None:
        payload = build_protection_payload(status_check_contexts=("Beadloom Gate",))
        assert payload["required_status_checks"]["contexts"] == ["Beadloom Gate"]


class TestRequest:
    def test_request_targets_main_protection_endpoint(self) -> None:
        req = BranchProtectionRequest(owner="acme", repo="widget")
        argv = req.gh_args()
        assert argv[:2] == ["api", "--method"]
        assert "PUT" in argv
        assert "repos/acme/widget/branches/main/protection" in argv

    def test_request_branch_is_configurable(self) -> None:
        req = BranchProtectionRequest(owner="acme", repo="widget", branch="trunk")
        assert "repos/acme/widget/branches/trunk/protection" in req.gh_args()

    def test_request_sends_payload_on_stdin_as_json(self) -> None:
        req = BranchProtectionRequest(owner="acme", repo="widget")
        body = json.loads(req.payload_json())
        assert body == build_protection_payload()
        # Body is fed via ``--input -`` so it is read from stdin (no shell quoting).
        assert "--input" in req.gh_args()
        assert "-" in req.gh_args()


class _FakeRunner:
    """Records each invocation; returns a canned success result."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    def __call__(self, args: list[str], stdin: str) -> str:
        self.calls.append((args, stdin))
        return "{}"


class TestApply:
    def test_apply_invokes_gh_with_payload(self) -> None:
        runner = _FakeRunner()
        apply_branch_protection("acme", "widget", runner=runner)
        assert len(runner.calls) == 1
        args, stdin = runner.calls[0]
        assert args[0] == "gh"
        assert "repos/acme/widget/branches/main/protection" in args
        assert json.loads(stdin) == build_protection_payload()

    def test_apply_is_idempotent(self) -> None:
        """A declarative PUT: re-running sends the byte-identical payload."""
        runner = _FakeRunner()
        apply_branch_protection("acme", "widget", runner=runner)
        apply_branch_protection("acme", "widget", runner=runner)
        first_args, first_stdin = runner.calls[0]
        second_args, second_stdin = runner.calls[1]
        assert first_args == second_args
        assert first_stdin == second_stdin

    def test_apply_returns_request_for_inspection(self) -> None:
        runner = _FakeRunner()
        req = apply_branch_protection("acme", "widget", runner=runner)
        assert isinstance(req, BranchProtectionRequest)
        assert req.owner == "acme"
        assert req.repo == "widget"

    def test_apply_surfaces_gh_error_cleanly(self) -> None:
        """A failing ``gh`` runner (e.g. CalledProcessError) propagates unswallowed.

        The helper does not silently ignore a GitHub error — the caller sees the
        failure (a real ``gh api`` failure would raise ``CalledProcessError``;
        the helper must NOT mask it).
        """
        import subprocess

        def boom(argv: list[str], stdin: str) -> str:
            raise subprocess.CalledProcessError(1, argv, stderr="403 Forbidden")

        with pytest.raises(subprocess.CalledProcessError):
            apply_branch_protection("acme", "widget", runner=boom)

    def test_apply_honors_custom_branch_and_contexts(self) -> None:
        """A non-default branch + custom contexts flow into the sent request."""
        runner = _FakeRunner()
        req = apply_branch_protection(
            "acme",
            "widget",
            branch="trunk",
            status_check_contexts=("Beadloom Gate",),
            runner=runner,
        )
        assert req.branch == "trunk"
        args, stdin = runner.calls[0]
        assert "repos/acme/widget/branches/trunk/protection" in args
        body = json.loads(stdin)
        assert body["required_status_checks"]["contexts"] == ["Beadloom Gate"]


class TestCli:
    def test_dry_run_prints_exact_gh_call_without_invoking(self) -> None:
        """--dry-run documents the exact gh api call and does NOT touch GitHub."""
        result = CliRunner().invoke(
            main,
            ["setup-branch-protection", "--repo", "acme/widget", "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert "gh api" in result.output
        assert "repos/acme/widget/branches/main/protection" in result.output
        # The protection contract is visible in the printed payload.
        assert "required_status_checks" in result.output
        assert "enforce_admins" in result.output

    @pytest.mark.parametrize(
        "bad_repo",
        ["no-slash", "/leading", "a/b/c", "owner/", "/"],
    )
    def test_rejects_malformed_repo(self, bad_repo: str) -> None:
        result = CliRunner().invoke(
            main,
            ["setup-branch-protection", "--repo", bad_repo, "--dry-run"],
        )
        assert result.exit_code != 0

    def test_dry_run_payload_is_owner_safe_and_strict(self) -> None:
        """The printed payload is owner-safe: 0 reviews, admins not enforced,
        strict required checks, no restrictions (owner never locked out)."""
        result = CliRunner().invoke(
            main,
            ["setup-branch-protection", "--repo", "acme/widget", "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.split("--- payload (stdin) ---", 1)[1])
        assert payload["required_pull_request_reviews"] == {
            "required_approving_review_count": 0
        }
        assert payload["enforce_admins"] is False
        assert payload["restrictions"] is None
        assert payload["required_status_checks"]["strict"] is True

    def test_dry_run_honors_custom_branch_and_checks(self) -> None:
        """--branch + repeated --check flow into the dry-run gh call + payload."""
        result = CliRunner().invoke(
            main,
            [
                "setup-branch-protection",
                "--repo",
                "acme/widget",
                "--branch",
                "trunk",
                "--check",
                "Beadloom Gate",
                "--check",
                "lint",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "repos/acme/widget/branches/trunk/protection" in result.output
        payload = json.loads(result.output.split("--- payload (stdin) ---", 1)[1])
        assert payload["required_status_checks"]["contexts"] == ["Beadloom Gate", "lint"]
