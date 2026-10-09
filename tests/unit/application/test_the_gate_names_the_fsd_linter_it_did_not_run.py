"""The gate names Steiger among what it did not run (BDL-080 S2b, RFC D3).

Steiger is Feature-Sliced Design's own linter: it judges a frontend's slices file
by file, where ``beadloom lint`` judges the graph. The gate runs neither the style
linters nor Steiger, and its ``Not run by this gate:`` block names what the
project's pipeline runs that the gate did not — so a pipeline that runs Steiger,
directly or through the ``lint:fsd`` script ``beadloom init`` writes, has it named
there with its command and the job that runs it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.gate_coverage import derive_gate_coverage, gate_coverage_lines

if TYPE_CHECKING:
    from pathlib import Path

_FSD_LINTER = "the FSD linter"


def _pipeline_with(project_root: Path, *commands: str) -> None:
    workflows = project_root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    steps = "".join(f"      - run: {command}\n" for command in commands)
    (workflows / "ci.yml").write_text(
        f"jobs:\n  site-build:\n    runs-on: ubuntu-latest\n    steps:\n{steps}",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "command",
    [
        "npx steiger .vitepress/theme",
        "npm run lint:fsd",
        "pnpm run lint:fsd",
        "yarn lint:fsd",
        "steiger ./src",
    ],
)
def test_a_pipeline_that_runs_steiger_has_it_named_with_its_command(
    tmp_path: Path, command: str
) -> None:
    _pipeline_with(tmp_path, "npm ci", command)

    coverage = derive_gate_coverage(tmp_path, performed=("reindex", "lint", "sync-check"))

    named = {item.duty: item.command for item in coverage.not_performed}
    assert named == {_FSD_LINTER: command}


def test_the_block_reads_the_fsd_linter_beside_the_job_that_runs_it(tmp_path: Path) -> None:
    _pipeline_with(tmp_path, "npm ci && npm run lint:fsd")

    lines = gate_coverage_lines(derive_gate_coverage(tmp_path, performed=("lint",)))

    assert lines == [
        "Not run by this gate:",
        f"  {_FSD_LINTER} — `npm run lint:fsd` (.github/workflows/ci.yml: site-build)",
    ]


@pytest.mark.parametrize("command", ["npm ci", "npm run lint", "npm run build", "npm test"])
def test_an_npm_command_that_is_not_steiger_performs_no_duty_here(
    tmp_path: Path, command: str
) -> None:
    _pipeline_with(tmp_path, command)

    coverage = derive_gate_coverage(tmp_path, performed=("lint",))

    assert coverage.declared == ()
