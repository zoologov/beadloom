"""Tests for the idempotent `main` branch-protection helper (BDL-049 / BEAD-03).

The helper configures GitHub branch protection on ``main`` via ``gh api`` so that
the trunk-based flow is enforced: a PR is required (no direct push), ``beadloom
ci`` is a *required status check*, ``enforce_admins: true`` (strict trunk-based —
even admins go through PRs and cannot bypass the gate), 0 required reviews so the
solo owner can still self-merge once the gate is green, and ``restrictions:
null`` (no push-restriction allow-list).

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

    def test_payload_enforces_admins_with_no_restrictions(self) -> None:
        """Strict trunk-based: even admins go through PRs (``enforce_admins:
        true``), but there is no push-restriction allow-list. Owner is not
        locked out — with 0 required reviews + the always-on ``beadloom-gate``
        check the owner can still self-merge their own PR once the gate is
        green; they just cannot direct-push or bypass the gate."""
        payload = build_protection_payload()
        assert payload["enforce_admins"] is True
        assert payload["restrictions"] is None

    def test_payload_required_status_checks_strict_with_default_contexts(self) -> None:
        payload = build_protection_payload()
        checks = payload["required_status_checks"]
        assert checks["strict"] is True
        assert checks["contexts"] == list(DEFAULT_STATUS_CHECK_CONTEXTS)

    def test_default_contexts_are_the_consolidated_ci_check_runs(self) -> None:
        """BDL-050: the default required checks are the consolidated ``ci.yml``
        job check-run names — ``gate``, the four ``tests (3.x)`` matrix legs,
        ``site-build`` and ``ai-techwriter``. All run on EVERY PR (no ``paths:``
        filter — the matrix is un-filtered now), so requiring them under
        ``strict`` never stalls a PR. They must match ``ci.yml``'s job names +
        matrix legs EXACTLY."""
        assert DEFAULT_STATUS_CHECK_CONTEXTS == (
            "gate",
            "tests (3.10)",
            "tests (3.11)",
            "tests (3.12)",
            "tests (3.13)",
            "site-build",
            "ai-techwriter",
        )
        payload = build_protection_payload()
        assert payload["required_status_checks"]["contexts"] == [
            "gate",
            "tests (3.10)",
            "tests (3.11)",
            "tests (3.12)",
            "tests (3.13)",
            "site-build",
            "ai-techwriter",
        ]

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


class TestDefaultRunner:
    """The default :class:`GhRunner` shells out to the real ``gh`` CLI.

    We mock ``subprocess.run`` so nothing touches GitHub: the test asserts the
    argv + stdin are forwarded faithfully and stdout is returned (BDL-050
    hardening — previously the default-runner branch was uncovered).
    """

    def test_default_runner_forwards_argv_and_stdin(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import subprocess

        from beadloom.onboarding import branch_protection as bp

        seen: dict[str, object] = {}

        class _Completed:
            stdout = '{"ok": true}'

        def fake_run(argv: list[str], **kwargs: object) -> _Completed:
            seen["argv"] = argv
            seen["input"] = kwargs.get("input")
            seen["check"] = kwargs.get("check")
            return _Completed()

        monkeypatch.setattr(subprocess, "run", fake_run)
        # No ``runner=`` → the production _subprocess_runner default is exercised.
        req = bp.apply_branch_protection("acme", "widget")
        assert seen["argv"] == ["gh", *req.gh_args()]
        assert seen["input"] == req.payload_json()
        assert seen["check"] is True


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
        """The printed payload is strict trunk-based + owner-safe: 0 reviews,
        ``enforce_admins: true`` (even admins go through PRs), strict required
        checks, no restrictions (owner still self-merges via the gate)."""
        result = CliRunner().invoke(
            main,
            ["setup-branch-protection", "--repo", "acme/widget", "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.split("--- payload (stdin) ---", 1)[1])
        assert payload["required_pull_request_reviews"] == {
            "required_approving_review_count": 0
        }
        assert payload["enforce_admins"] is True
        assert payload["restrictions"] is None
        assert payload["required_status_checks"]["strict"] is True

    def test_dry_run_default_check_is_the_consolidated_ci_set(self) -> None:
        """BDL-050: without ``--check``, the required checks default to the
        consolidated ``ci.yml`` job set (``gate`` + the four ``tests (3.x)``
        legs + ``site-build`` + ``ai-techwriter``) — all un-filtered, so
        ``strict`` never stalls a PR."""
        result = CliRunner().invoke(
            main,
            ["setup-branch-protection", "--repo", "acme/widget", "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.split("--- payload (stdin) ---", 1)[1])
        assert payload["required_status_checks"]["contexts"] == [
            "gate",
            "tests (3.10)",
            "tests (3.11)",
            "tests (3.12)",
            "tests (3.13)",
            "site-build",
            "ai-techwriter",
        ]

    def test_dry_run_check_option_overrides_default_exactly(self) -> None:
        """Repeated ``--check`` replaces the default with exactly those contexts."""
        result = CliRunner().invoke(
            main,
            [
                "setup-branch-protection",
                "--repo",
                "acme/widget",
                "--check",
                "a",
                "--check",
                "b",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.split("--- payload (stdin) ---", 1)[1])
        assert payload["required_status_checks"]["contexts"] == ["a", "b"]

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
