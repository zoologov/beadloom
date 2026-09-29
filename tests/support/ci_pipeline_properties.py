"""The properties a CI pipeline file is held to, one function per property.

Each property is asserted over two kinds of file. A template the package ships
to adopters is the product, so its test is a product test; this repository's own
pipeline is its own configuration, so the same assertion over it is a self-check
(BDL-074 A3). The two tests live in different folders -- the self-check under
``tests/self_check/config/`` -- and share the body written here, so neither copies
it (BDL-074 F3, `beadloom-2mj3.8`).

A function is named after the test that runs it, without ``test_``. It takes the
file and asserts; :func:`held_to` binds it to the rows one module runs it over.
The files themselves, and the facts several properties share, are in
:mod:`tests.support.ci_workflows`.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.support.ci_workflows import (
    PAT_FALLBACK_CHECKOUT,
    PAT_FALLBACK_GH_TOKEN,
    VERIFY_JOBS,
    load_yaml,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

#: The interpreter legs the consolidated ``tests`` job runs, on both platforms.
MATRIX_LEGS = ["3.10", "3.11", "3.12", "3.13"]


def _file_name(path: Path) -> str:
    return path.name


def held_to(check: Callable[[Path], None], rows: Sequence[Path]) -> Callable[[Path], None]:
    """A test running *check* over each of *rows*, the row's id its file name.

    A module binds the result as ``test_<name of check> = held_to(...)``, and
    pytest names a collected test by that binding, so the id is the one a test
    written out by hand would carry.
    """

    @pytest.mark.parametrize("path", rows, ids=_file_name)
    def test(path: Path) -> None:
        check(path)

    return test


# --------------------------------------------------------------------------- #
# BDL-049: the trunk-based trigger model, the loop guard and the PAT wiring
# --------------------------------------------------------------------------- #


def ci_config_is_valid_yaml(path: Path) -> None:
    """Every CI artifact parses (no tabs / indentation breakage)."""
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)


def github_triggers_on_pull_request_not_push_main(path: Path) -> None:
    """on: pull_request -> main/master; push:main removed; dispatch kept."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    # YAML 1.1 parses the bare key ``on`` as boolean True.
    on = doc.get("on", doc.get(True))
    assert "pull_request" in on
    pr = on["pull_request"]
    assert set(pr["types"]) >= {"opened", "synchronize", "reopened"}
    assert pr["branches"] == ["main", "master"]
    assert "workflow_dispatch" in on
    assert "push" not in on


def github_has_cancel_in_progress_concurrency(path: Path) -> None:
    """G8: cancel-in-progress, keyed per PR."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    concurrency = doc["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    assert "pull_request.number" in concurrency["group"]


def github_uses_merge_base_since_and_pr_branch_target(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "git merge-base" in text
    assert "--target pr-branch" in text
    # Fallback to the base SHA when merge-base cannot resolve.
    assert "pull_request.base.sha" in text
    # PR URL wired so the publisher can comment / record it.
    assert "PR_URL:" in text
    assert "pull_request.html_url" in text


def github_checks_out_pr_head_branch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "pull_request.head.ref" in text
    assert "fetch-depth: 0" in text


def gitlab_triggers_on_merge_request_event(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert '$CI_PIPELINE_SOURCE == "merge_request_event"' in text
    # The old push-to-main gate is gone for the ai-techwriter job.
    assert '$CI_COMMIT_BRANCH == "main"' not in text


def gitlab_uses_merge_base_since_and_pr_branch_target(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "git merge-base" in text
    assert "CI_MERGE_REQUEST_TARGET_BRANCH_NAME" in text
    assert "--platform gitlab --target pr-branch" in text
    # Env the BEAD-01 publisher reads to resolve + comment on the MR.
    assert "CI_MERGE_REQUEST_IID" in text
    assert "CI_MERGE_REQUEST_PROJECT_URL" in text


def loop_guard_present(path: Path) -> None:
    """Belt-and-suspenders loop-guard: author + [skip ai-techwriter] subject."""
    text = path.read_text(encoding="utf-8")
    assert "beadloom-ai-techwriter" in text
    assert "skip ai-techwriter" in text
    assert "git log -1" in text


def _inline_shell_blocks(doc: object) -> list[str]:
    """Collect every inline shell snippet from a parsed CI doc (run:/script:)."""
    blocks: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "run" and isinstance(value, str):
                    blocks.append(value)
                elif key == "script" and isinstance(value, list):
                    blocks.append("\n".join(str(s) for s in value))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    return blocks


def inline_shell_parses_with_bash_n(path: Path) -> None:
    """Every inline run:/script: block is syntactically valid bash."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    blocks = _inline_shell_blocks(doc)
    assert blocks, f"no inline shell found in {path.name}"
    for block in blocks:
        result = subprocess.run(
            ["bash", "-n"],  # noqa: S607 - bash resolved on PATH in CI/dev
            input=block,
            # The child speaks UTF-8 by contract (our own CLI, a JSON payload, a shell
            # block from a YAML file); `text=True` would have decoded it with the
            # image's locale instead (BDL-061.42).
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f"{path.name}:\n{block}\n{result.stderr}"


def _gh_steps(path: Path) -> list[dict[str, object]]:
    """The ordered step list of the single ai-techwriter job in a GH workflow."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    job = jobs["ai-techwriter"]
    steps = job["steps"]
    assert isinstance(steps, list)
    return [s for s in steps if isinstance(s, dict)]


def github_loop_guard_sets_skip_flag_before_work(path: Path) -> None:
    """The loop-guard runs as an EARLY step and sets AI_TW_SKIP in the env file.

    It must come before the install/harness steps so it can short-circuit the
    agent's own ``synchronize`` re-trigger.
    """
    steps = _gh_steps(path)
    guard_idx = next(
        i
        for i, s in enumerate(steps)
        if isinstance(s.get("run"), str) and "AI_TW_SKIP=1" in s["run"]
    )
    # The guard reads the head commit author + subject (belt-and-suspenders).
    guard = steps[guard_idx]["run"]
    assert isinstance(guard, str)
    assert "git log -1" in guard
    assert "beadloom-ai-techwriter" in guard
    assert "[skip ai-techwriter]" in guard
    assert "GITHUB_ENV" in guard
    # The harness step (the model + commit) comes AFTER the guard.
    harness_idx = next(
        i
        for i, s in enumerate(steps)
        if isinstance(s.get("run"), str) and "beadloom.ai_agents.ai_techwriter" in s["run"]
    )
    assert guard_idx < harness_idx


def github_every_post_guard_step_is_gated_on_skip(path: Path) -> None:
    """Every step that does work (after the guard) is gated by AI_TW_SKIP != '1'.

    Without the gate the agent's own refresh push would still install + run the
    model on the next ``synchronize`` (the loop). Each working step's ``if:``
    must reference the skip flag.
    """
    steps = _gh_steps(path)
    guard_idx = next(
        i
        for i, s in enumerate(steps)
        if isinstance(s.get("run"), str) and "AI_TW_SKIP=1" in s["run"]
    )
    post_guard = steps[guard_idx + 1 :]
    assert post_guard, "there must be work steps after the guard"
    for step in post_guard:
        cond = step.get("if")
        assert isinstance(cond, str), f"missing if-gate on step {step.get('name')}"
        assert "AI_TW_SKIP" in cond, f"step {step.get('name')} not gated on AI_TW_SKIP"


def github_pr_path_and_dispatch_path_are_mutually_exclusive(path: Path) -> None:
    """The pr-branch harness step is PR-only; the branch-pr step is dispatch-only.

    So a single trigger never runs both publish targets.
    """
    steps = _gh_steps(path)
    pr_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target pr-branch" in s["run"]
    )
    dispatch_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target branch-pr" in s["run"]
    )
    assert "pull_request" in str(pr_step.get("if"))
    assert "workflow_dispatch" in str(dispatch_step.get("if"))


def github_dispatch_path_keeps_branch_pr_target(path: Path) -> None:
    """workflow_dispatch (no PR context) keeps the original branch-PR publish."""
    text = path.read_text(encoding="utf-8")
    assert "--target branch-pr" in text


def github_grants_contents_and_pull_request_write(path: Path) -> None:
    """The pr-branch publisher needs contents:write (push) + pull-requests:write
    (comment) — both must be granted."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    perms = doc["permissions"]
    assert perms["contents"] == "write"
    assert perms["pull-requests"] == "write"


def github_checkout_uses_pat_with_token_fallback(path: Path) -> None:
    """``actions/checkout`` persists the credential ``git push`` uses; it must be
    the PAT (so the agent's push triggers ``beadloom-gate``) with a fallback to
    the default token (variant-C: PAT-less repos still check out + work)."""
    steps = _gh_steps(path)
    checkout = next(
        s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")
    )
    with_block = checkout.get("with")
    assert isinstance(with_block, dict), "checkout must declare a with: block"
    token = str(with_block.get("token", ""))
    assert PAT_FALLBACK_CHECKOUT in token, token


def github_pr_path_gh_token_uses_pat_with_token_fallback(path: Path) -> None:
    """The pr-branch harness step's ``GH_TOKEN`` must use the PAT (so ``gh`` push
    + ``gh pr comment`` authenticate as the PAT) with a fallback to GITHUB_TOKEN."""
    steps = _gh_steps(path)
    pr_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target pr-branch" in s["run"]
    )
    env = pr_step.get("env")
    assert isinstance(env, dict)
    gh_token = str(env.get("GH_TOKEN", ""))
    assert PAT_FALLBACK_GH_TOKEN in gh_token, gh_token


def github_dispatch_path_does_not_use_pat(path: Path) -> None:
    """The workflow_dispatch (branch-pr) path has no PR to re-gate, so it stays
    on the default token — the PAT wiring is PR-path-only."""
    steps = _gh_steps(path)
    dispatch_step = next(
        s
        for s in steps
        if isinstance(s.get("run"), str) and "--target branch-pr" in s["run"]
    )
    env = dispatch_step.get("env")
    assert isinstance(env, dict)
    gh_token = str(env.get("GH_TOKEN", ""))
    assert "AI_TW_PAT" not in gh_token, gh_token
    assert "secrets.GITHUB_TOKEN" in gh_token


def gitlab_pr_path_uses_pat_with_job_token_fallback(path: Path) -> None:
    """GitLab mirror: CI_JOB_TOKEN pushes also do not trigger pipelines, so the
    MR pr-branch push/comment authenticates with an access-token CI/CD variable
    (AI_TW_PAT) with a fallback to CI_JOB_TOKEN / the default."""
    text = path.read_text(encoding="utf-8")
    assert "AI_TW_PAT" in text
    # The fallback to the job token keeps PAT-less projects working.
    assert "CI_JOB_TOKEN" in text


# --------------------------------------------------------------------------- #
# BDL-050: the consolidated pipeline shape, mirrored across GitHub and GitLab
# --------------------------------------------------------------------------- #


def github_has_all_consolidated_jobs(path: Path) -> None:
    """gate / tests / site-build / ai-techwriter are all declared as jobs."""
    jobs = load_yaml(path)["jobs"]
    assert isinstance(jobs, dict)
    for name in (*VERIFY_JOBS, "ai-techwriter"):
        assert name in jobs, f"{path.name} missing job {name}"


def github_tests_matrix_covers_3_10_to_3_13(path: Path) -> None:
    """The ``tests`` job runs the un-filtered 3.10-3.13 matrix (no paths filter)."""
    jobs = load_yaml(path)["jobs"]
    assert isinstance(jobs, dict)
    tests = jobs["tests"]
    assert isinstance(tests, dict)
    versions = tests["strategy"]["matrix"]["python-version"]
    assert [str(v) for v in versions] == MATRIX_LEGS
    assert "paths" not in tests


def github_ai_techwriter_needs_the_three_verify_jobs(path: Path) -> None:
    """ai-techwriter is gated on gate + tests + site-build (no tokens on red)."""
    jobs = load_yaml(path)["jobs"]
    assert isinstance(jobs, dict)
    atw = jobs["ai-techwriter"]
    assert isinstance(atw, dict)
    assert set(atw["needs"]) == set(VERIFY_JOBS)


def gitlab_declares_verify_and_docs_stages(path: Path) -> None:
    """The consolidated GitLab pipeline declares the verify -> docs stages."""
    doc = load_yaml(path)
    assert doc["stages"] == ["verify", "docs"]


def gitlab_verify_stage_jobs(path: Path) -> None:
    """gate / tests / site-build all sit in the verify stage."""
    doc = load_yaml(path)
    for name in VERIFY_JOBS:
        job = doc[name]
        assert isinstance(job, dict)
        assert job["stage"] == "verify"


def gitlab_tests_matrix_covers_3_10_to_3_13(path: Path) -> None:
    """The GitLab ``tests`` job mirrors the 3.10-3.13 matrix via parallel:matrix."""
    doc = load_yaml(path)
    tests = doc["tests"]
    assert isinstance(tests, dict)
    versions = tests["parallel"]["matrix"][0]["PYTHON_VERSION"]
    assert [str(v) for v in versions] == MATRIX_LEGS


def gitlab_ai_techwriter_in_docs_stage_needs_verify_jobs(path: Path) -> None:
    """ai-techwriter sits in docs stage and ``needs`` the three verify jobs."""
    doc = load_yaml(path)
    atw = doc["ai-techwriter"]
    assert isinstance(atw, dict)
    assert atw["stage"] == "docs"
    assert set(atw["needs"]) == set(VERIFY_JOBS)


def gitlab_ai_techwriter_runs_on_merge_request(path: Path) -> None:
    """The ai-techwriter MR rule fires on a merge_request_event (verdict gates)."""
    doc = load_yaml(path)
    atw = doc["ai-techwriter"]
    assert isinstance(atw, dict)
    rules_text = yaml.safe_dump(atw["rules"])
    assert 'merge_request_event' in rules_text


# --------------------------------------------------------------------------- #
# BDL-051 S2: the harness moved into the package
# --------------------------------------------------------------------------- #


def references_new_module_not_tools(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "beadloom.ai_agents.ai_techwriter" in text
    assert "tools.ai_techwriter" not in text
