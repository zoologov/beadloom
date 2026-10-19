"""The gate's coverage report reads the pipeline the room census reads (BDL-083 S2a, RFC D6).

BDL-UX #332: on the monorepo fixture `ci` reported "this project declares no pipeline"
while its `.gitlab-ci.yml` runs `uv run pytest tests` and `npm run lint:fsd`, because the
report read `.github/workflows` and nothing else. It now takes its files from
:func:`beadloom.application.rooms.pipeline_sources`, so the two derivations read one
declaration and cannot disagree about which.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.gate_coverage import derive_gate_coverage, gate_coverage_lines

if TYPE_CHECKING:
    from pathlib import Path

_PIPELINE = (
    "backend-tests:\n"
    "  image: python:3.12-slim\n"
    "  script:\n"
    "    - cd backend && uv run pytest tests\n"
    "frontend-tests:\n"
    "  image: node:22-slim\n"
    "  script: [npm ci, npm run lint:fsd]\n"
)


def _gitlab(root: Path, body: str = _PIPELINE) -> None:
    (root / ".gitlab-ci.yml").write_text(body, encoding="utf-8")


def test_the_verifications_of_a_gitlab_pipeline_are_read(tmp_path: Path) -> None:
    # Arrange
    _gitlab(tmp_path)

    # Act
    coverage = derive_gate_coverage(tmp_path, performed=["lint"])

    # Assert
    found = {(v.duty, v.command, v.source) for v in coverage.not_performed}
    assert found == {
        ("the test suite", "uv run pytest tests", ".gitlab-ci.yml: backend-tests"),
        ("the FSD linter", "npm run lint:fsd", ".gitlab-ci.yml: frontend-tests"),
    }
    assert coverage.inspected == 1


def test_a_gitlab_mirror_beside_github_workflows_is_not_read(tmp_path: Path) -> None:
    # Arrange
    _gitlab(tmp_path)
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: uv run mypy src\n",
        encoding="utf-8",
    )

    # Act
    coverage = derive_gate_coverage(tmp_path, performed=[])

    # Assert
    assert [v.source for v in coverage.declared] == [".github/workflows/ci.yml: t"]
    assert coverage.inspected == 1


def test_an_unreadable_gitlab_pipeline_is_unresolved(tmp_path: Path) -> None:
    # Arrange
    _gitlab(tmp_path, "tests: [unclosed\n")

    # Act
    coverage = derive_gate_coverage(tmp_path, performed=[])

    # Assert
    assert [u.source for u in coverage.unresolved] == [".gitlab-ci.yml"]


def test_no_pipeline_names_both_files_it_looked_for(tmp_path: Path) -> None:
    # Act
    lines = gate_coverage_lines(derive_gate_coverage(tmp_path, performed=[]))

    # Assert
    assert "this project declares no pipeline" in lines[1]
    assert ".github/workflows" in lines[1]
    assert ".gitlab-ci.yml" in lines[1]
