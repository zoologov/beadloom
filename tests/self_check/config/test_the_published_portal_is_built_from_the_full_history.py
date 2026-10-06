# beadloom:feature=site-generation
"""The portal this repository publishes is indexed from the full history.

BDL-078 ``beadloom-btkd.9``, from T's finding F1 (``beadloom-q63p``).
``deploy-site.yml`` reindexes and regenerates the portal on GitHub's runner, and
the activity on every node's card is measured on the history that job checked
out. ``actions/checkout`` fetches one commit unless told otherwise, and git shows
that one commit as adding every file. MEASURED on a clone of this repository one
commit deep: all 130 nodes read "1 commit", their changed lines were the size of
their files, and three activity levels were populated where the full history
populates five.

A static, network-free check over the YAML.
"""

from __future__ import annotations

from typing import Any

import yaml

from tests.support.repository_root import REPO_ROOT

DEPLOY_SITE = REPO_ROOT / ".github" / "workflows" / "deploy-site.yml"


def _build_steps() -> list[dict[str, Any]]:
    workflow = yaml.safe_load(DEPLOY_SITE.read_text(encoding="utf-8"))
    steps: list[dict[str, Any]] = workflow["jobs"]["build"]["steps"]
    return steps


def test_the_deploy_job_checks_out_the_full_history_before_it_reindexes() -> None:
    steps = _build_steps()
    checkout = next(
        i
        for i, step in enumerate(steps)
        if str(step.get("uses", "")).startswith("actions/checkout@")
    )
    reindexing = next(
        i for i, step in enumerate(steps) if "beadloom reindex" in str(step.get("run"))
    )
    assert checkout < reindexing
    # 0 is "all history" to actions/checkout; its default, 1, is a single commit.
    assert steps[checkout].get("with", {}).get("fetch-depth") == 0, steps[checkout]
