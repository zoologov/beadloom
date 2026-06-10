# beadloom:feature=onboarding
"""BDL-049 BEAD-02: CI configs fire on PR (not push:main), use merge-base
``--since``, carry the loop-guard, and publish via ``--target pr-branch``.

These are static, network-free checks over the four artifacts the feature
touches: the live GitHub workflow + GitLab pipeline, and the two vendored
templates scaffolded into adopter repos. Each must (a) parse as YAML and
(b) encode the trunk-based / merge_request_event trigger model so a scaffolded
repo gets the same trunk-based behaviour as Beadloom itself.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

GH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ai-techwriter.yml"
GL_PIPELINE = REPO_ROOT / ".gitlab-ci.yml"
TEMPLATES = REPO_ROOT / "src" / "beadloom" / "onboarding" / "templates" / "ai_techwriter"
GH_TEMPLATE = TEMPLATES / "github-workflow.yml"
GL_TEMPLATE = TEMPLATES / "gitlab-ci-job.yml"

GITHUB_FILES = (GH_WORKFLOW, GH_TEMPLATE)
GITLAB_FILES = (GL_PIPELINE, GL_TEMPLATE)
ALL_FILES = GITHUB_FILES + GITLAB_FILES


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_ci_config_is_valid_yaml(path: Path) -> None:
    """Every CI artifact parses (no tabs / indentation breakage)."""
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_triggers_on_pull_request_not_push_main(path: Path) -> None:
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


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_has_cancel_in_progress_concurrency(path: Path) -> None:
    """G8: cancel-in-progress, keyed per PR."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    concurrency = doc["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    assert "pull_request.number" in concurrency["group"]


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_uses_merge_base_since_and_pr_branch_target(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "git merge-base" in text
    assert "--target pr-branch" in text
    # Fallback to the base SHA when merge-base cannot resolve.
    assert "pull_request.base.sha" in text
    # PR URL wired so the publisher can comment / record it.
    assert "PR_URL:" in text
    assert "pull_request.html_url" in text


@pytest.mark.parametrize("path", GITHUB_FILES, ids=lambda p: p.name)
def test_github_checks_out_pr_head_branch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "pull_request.head.ref" in text
    assert "fetch-depth: 0" in text


@pytest.mark.parametrize("path", GITLAB_FILES, ids=lambda p: p.name)
def test_gitlab_triggers_on_merge_request_event(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert '$CI_PIPELINE_SOURCE == "merge_request_event"' in text
    # The old push-to-main gate is gone for the ai-techwriter job.
    assert '$CI_COMMIT_BRANCH == "main"' not in text


@pytest.mark.parametrize("path", GITLAB_FILES, ids=lambda p: p.name)
def test_gitlab_uses_merge_base_since_and_pr_branch_target(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "git merge-base" in text
    assert "CI_MERGE_REQUEST_TARGET_BRANCH_NAME" in text
    assert "--platform gitlab --target pr-branch" in text
    # Env the BEAD-01 publisher reads to resolve + comment on the MR.
    assert "CI_MERGE_REQUEST_IID" in text
    assert "CI_MERGE_REQUEST_PROJECT_URL" in text


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_loop_guard_present(path: Path) -> None:
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


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_inline_shell_parses_with_bash_n(path: Path) -> None:
    """Every inline run:/script: block is syntactically valid bash."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    blocks = _inline_shell_blocks(doc)
    assert blocks, f"no inline shell found in {path.name}"
    for block in blocks:
        result = subprocess.run(
            ["bash", "-n"],  # noqa: S607 - bash resolved on PATH in CI/dev
            input=block,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f"{path.name}:\n{block}\n{result.stderr}"


def test_live_and_template_github_share_trigger_model() -> None:
    """The vendored GitHub template mirrors the live workflow's trigger model."""
    live = yaml.safe_load(GH_WORKFLOW.read_text(encoding="utf-8"))
    tmpl = yaml.safe_load(GH_TEMPLATE.read_text(encoding="utf-8"))
    live_on = live.get("on", live.get(True))
    tmpl_on = tmpl.get("on", tmpl.get(True))
    assert "pull_request" in live_on and "pull_request" in tmpl_on
    assert "push" not in live_on and "push" not in tmpl_on
