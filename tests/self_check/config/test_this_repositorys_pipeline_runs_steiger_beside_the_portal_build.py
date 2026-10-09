"""This repository's pipeline runs Steiger on the portal's theme, and the gate names it.

BDL-080 S2c (``beadloom-af99.8``), by the owner's ruling of 2026-10-09. Steiger,
Feature-Sliced Design's own linter, judges the theme's slices file by file; the
gate judges the graph and does not run it. RFC D3 puts it where the portal is
built — the ``site-build`` job, the only job of the pipeline that installs the
scaffold's Node dependencies — so the gate's ``Not run by this gate:`` block,
which reads the pipeline, names it with its command and its job.

The scaffold's Steiger configuration keeps the plugin's ``recommended`` set and
switches exactly one rule off, ``fsd/insignificant-slice``: the viewer was cut
into slices so that beads can run in parallel on disjoint graph nodes, not for
reuse, so a feature one widget uses is the intended shape. Any other rule
switched off fails here, because a rule turned off where no reader looks is how
a linter stops meaning anything.
"""

from __future__ import annotations

import re

import yaml

from beadloom.application.gate_coverage import derive_gate_coverage
from tests.support.repository_root import REPO_ROOT

#: The duty name the gate's block gives Steiger.
_FSD_LINTER = "the FSD linter"

#: The steps a gate run performs; none of them is Steiger.
_GATE_STEPS = (
    "reindex",
    "lint",
    "sync-check",
    "docs-audit",
    "docs-quality",
    "doc-spaces",
    "scope-check",
    "config-check",
    "doctor",
)

_STEIGER_CONFIG = REPO_ROOT / "src" / "beadloom" / "site_scaffold" / "steiger.config.js"

#: A rule's setting in a Steiger configuration: ``"fsd/<rule>": "<severity>"``.
_RULE_SETTING = re.compile(r"""["'](fsd/[a-z-]+)["']\s*:\s*["'](off|warn|error)["']""")


def test_the_site_build_job_runs_steiger_and_the_gate_names_it() -> None:
    coverage = derive_gate_coverage(REPO_ROOT, performed=_GATE_STEPS)

    named = [
        (item.command, item.source) for item in coverage.not_performed if item.duty == _FSD_LINTER
    ]
    assert named == [("npm run lint:fsd", ".github/workflows/ci.yml: site-build")]


def test_the_gitlab_mirror_of_site_build_runs_it_too() -> None:
    pipeline = yaml.safe_load((REPO_ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))

    script = " && ".join(pipeline["site-build"]["script"])

    assert "npm run lint:fsd" in script


def test_the_scaffold_keeps_the_recommended_set_with_one_rule_off() -> None:
    config = _STEIGER_CONFIG.read_text(encoding="utf-8")

    assert "fsd.configs.recommended" in config
    settings = dict(_RULE_SETTING.findall(config))
    assert settings == {"fsd/insignificant-slice": "off"}
