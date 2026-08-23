"""What Beadloom writes into a project that is **not** Beadloom (BDL-UX #183).

Four slices of scrutiny read ``- **Current version:** 2.2.0`` in this
repository's composed ``CLAUDE.md`` and passed over it, because here the line is
true by coincidence: we are Beadloom, so the tool's version and the project's
version are the same string. Every test below points a renderer at a project
whose facts *cannot* coincide with ours.

The suite has two halves on purpose. The specific half asserts the version each
fixture declares. The general half — :func:`beadloom_local_facts_in` — sweeps
the whole composed artifact for any identifier of *this* repository, so the next
fact that leaks by the same route fails here instead of shipping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.doctor import get_actual_version
from beadloom.onboarding.agentic_flow_setup import composed_claude_md
from beadloom.onboarding.flow_config import build_flow_config
from beadloom.onboarding.scanner.claude_md import (
    _render_project_info_section,
    refresh_claude_md,
)
from tests.adopter_project import (
    beadloom_local_facts_in,
    hatch_dynamic_project,
    poetry_project,
    python_project,
    rust_project,
    typescript_project,
    undeclared_version_project,
)

if TYPE_CHECKING:
    from pathlib import Path


def _config(architecture: str = "ddd", stack: str = "python") -> object:
    return build_flow_config(
        {"tools": ["claude"], "architecture": [architecture], "stack": [stack]}
    )


class TestTheAdoptersVersionIsTheAdoptersOwn:
    """The rendered version must come from the project, or not be rendered."""

    def test_typescript_project_renders_its_own_version(self, tmp_path: Path) -> None:
        project = typescript_project(tmp_path / "orders-web")

        rendered = _render_project_info_section(project.root)

        assert f"- **Current version:** {project.version}" in rendered
        assert get_actual_version() not in rendered

    def test_rust_project_renders_its_own_version(self, tmp_path: Path) -> None:
        project = rust_project(tmp_path / "ledger-core")

        rendered = _render_project_info_section(project.root)

        assert f"- **Current version:** {project.version}" in rendered

    def test_python_project_that_is_not_beadloom_renders_its_own_version(
        self, tmp_path: Path
    ) -> None:
        project = python_project(tmp_path / "invoice-svc")

        rendered = _render_project_info_section(project.root)

        assert f"- **Current version:** {project.version}" in rendered
        assert get_actual_version() not in rendered

    def test_poetry_version_is_read_too(self, tmp_path: Path) -> None:
        project = poetry_project(tmp_path / "warehouse")

        rendered = _render_project_info_section(project.root)

        assert f"- **Current version:** {project.version}" in rendered

    def test_a_dynamic_version_is_still_a_declared_version(
        self, tmp_path: Path
    ) -> None:
        project = hatch_dynamic_project(tmp_path / "pipeline")

        rendered = _render_project_info_section(project.root)

        assert f"- **Current version:** {project.version}" in rendered

    def test_this_repository_can_read_its_own_declared_version(self) -> None:
        """The dogfood leg — and the one case where being right proves little."""
        from pathlib import Path as _Path

        from beadloom import __version__
        from beadloom.onboarding.scanner.project_facts import detect_project_version

        repo = _Path(__file__).resolve().parents[1]

        assert detect_project_version(repo) == __version__

    def test_an_undeclared_version_renders_nothing_not_ours(
        self, tmp_path: Path
    ) -> None:
        """*Unknown is not zero* — and it is certainly not somebody else's number."""
        project = undeclared_version_project(tmp_path / "gateway")

        rendered = _render_project_info_section(project.root)

        assert "Current version" not in rendered
        assert get_actual_version() not in rendered


class TestTheStackLineIsReadNotRecognised:
    """The Stack bullet used to be matched against Beadloom's OWN dependencies.

    ``sqlite``/``click``/``rich``/``tree-sitter`` were literals in the renderer,
    and the language floor was the literal ``"Python 3.10+"`` — our number. A
    project on ``>=3.12`` was described with ours; a project using anything else
    got nothing.
    """

    def test_the_python_floor_is_the_projects_own(self, tmp_path: Path) -> None:
        project = python_project(tmp_path / "invoice-svc")
        (project.root / "pyproject.toml").write_text(
            '[project]\nname = "invoice-svc"\nversion = "3.7.0"\n'
            'requires-python = ">=3.12"\ndependencies = ["fastapi", "sqlalchemy"]\n',
            encoding="utf-8",
        )
        (project.root / ".beadloom").mkdir()
        (project.root / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n", encoding="utf-8"
        )

        rendered = _render_project_info_section(project.root)

        assert "Python (>=3.12)" in rendered
        assert "3.10" not in rendered

    def test_the_projects_own_declared_dependencies_are_named(
        self, tmp_path: Path
    ) -> None:
        project = python_project(tmp_path / "invoice-svc")
        (project.root / ".beadloom").mkdir()
        (project.root / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n", encoding="utf-8"
        )

        rendered = _render_project_info_section(project.root)

        assert "fastapi" in rendered
        assert "sqlalchemy" in rendered
        # Never ours, whatever the project happens to use.
        assert "tree-sitter" not in rendered


class TestNoBeadloomFactReachesTheAdopter:
    """The sweep: no fact about *this* repository in an artifact composed for another."""

    def test_rendered_project_info_carries_no_beadloom_fact(
        self, tmp_path: Path
    ) -> None:
        for build in (typescript_project, rust_project, undeclared_version_project):
            project = build(tmp_path / build.__name__)
            rendered = _render_project_info_section(project.root)
            assert beadloom_local_facts_in(rendered) == []

    def test_composed_claude_md_carries_no_beadloom_fact(self, tmp_path: Path) -> None:
        project = typescript_project(tmp_path / "orders-web")

        text = composed_claude_md(
            _config(stack="typescript"),  # type: ignore[arg-type]  # FlowConfig built above
            project.root,
            project_name=project.name,
        )

        assert beadloom_local_facts_in(text) == []

    def test_a_non_python_adopter_is_not_told_its_test_runner_is_pytest(
        self, tmp_path: Path
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")

        text = composed_claude_md(
            _config(stack="typescript"),  # type: ignore[arg-type]
            project.root,
            project_name=project.name,
        )

        # The core is stack-neutral; it may *name* `uv run pytest` only in the
        # sentence that says so. Any other mention is a Python fact in a core
        # every adopter gets (review .11 m2's residue).
        mentions = [
            line
            for line in text.splitlines()
            if "pytest" in line and "not every project" not in line
        ]
        assert mentions == []


class TestTheDeclaredArchitectureIsTheProjectsOwn:
    """"DDD" was a constant in the renderer — this project's methodology, not theirs."""

    def test_an_fsd_project_is_not_described_as_ddd(self, tmp_path: Path) -> None:
        project = python_project(tmp_path / "shop-front")
        (project.root / ".beadloom").mkdir()
        (project.root / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [fsd]\nstack: [python]\n",
            encoding="utf-8",
        )

        rendered = _render_project_info_section(project.root)

        # Non-vacuous: the bullet must be PRESENT and must name FSD. A project
        # with no rendered architecture line would pass a bare `"DDD" not in`.
        architecture = [
            line for line in rendered.splitlines() if line.startswith("- **Architecture:**")
        ]
        assert len(architecture) == 1
        assert "FSD slices" in architecture[0]
        assert "DDD" not in rendered

    def test_a_project_declaring_no_architecture_claims_no_methodology(
        self, tmp_path: Path
    ) -> None:
        project = python_project(tmp_path / "no-flow-yml")

        rendered = _render_project_info_section(project.root)

        architecture = [
            line for line in rendered.splitlines() if line.startswith("- **Architecture:**")
        ]
        assert len(architecture) == 1
        assert "DDD" not in architecture[0]
        assert "FSD" not in architecture[0]


class TestRefreshOnAnAdopterProject:
    def test_refresh_writes_the_adopters_version_into_the_auto_region(
        self, tmp_path: Path
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        claude_dir = project.root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n## 0.1 Project: orders-web\n\n"
            "<!-- beadloom:auto-start project-info -->\n"
            "- **Current version:** 0.0.0\n"
            "<!-- beadloom:auto-end -->\n",
            encoding="utf-8",
        )

        changed = refresh_claude_md(project.root)

        assert changed == ["project-info"]
        written = (claude_dir / "CLAUDE.md").read_text(encoding="utf-8")
        assert f"- **Current version:** {project.version}" in written
        assert beadloom_local_facts_in(written) == []


class TestDoctorAuditsTheAdoptersFactsNotOurs:
    """``beadloom doctor`` reads the adopter's ``CLAUDE.md`` — against whose facts?

    The renderer was only half the leak. ``_check_agent_instructions`` audits
    four claims in *the adopter's* file (version, packages, stack, test
    framework) and compared every one of them against **Beadloom's** state:
    ``get_actual_version()``, a scan for ``src/beadloom/``, the literal keyword
    set ``{"python", "sqlite"}`` and the literal string ``pytest``. On this
    repository all four read OK by coincidence — the same coincidence as
    BDL-UX #183, one layer down.
    """

    def test_a_correct_adopter_version_claim_is_not_reported_as_drift(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.doctor import Severity, _check_agent_instructions

        project = typescript_project(tmp_path / "orders-web")
        claude_dir = project.root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            f"- **Current version:** {project.version}\n", encoding="utf-8"
        )

        checks = _check_agent_instructions(project.root)

        version = [c for c in checks if c.name == "agent_instructions_version"]
        assert [c.severity for c in version] == [Severity.OK]

    def test_an_undeclared_version_is_unverified_not_drift(
        self, tmp_path: Path
    ) -> None:
        """*Unknown is not zero* — and it is not a drift verdict either."""
        from beadloom.application.doctor import Severity, _check_agent_instructions

        project = undeclared_version_project(tmp_path / "gateway")
        claude_dir = project.root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "- **Current version:** 7.7.7\n", encoding="utf-8"
        )

        checks = _check_agent_instructions(project.root)

        version = [c for c in checks if c.name == "agent_instructions_version"]
        assert [c.severity for c in version] == [Severity.INFO]
        assert "not verified" in version[0].description

    def test_the_adopters_own_packages_are_what_the_claim_is_checked_against(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.doctor import Severity, _check_agent_instructions

        project = python_project(tmp_path / "invoice-svc")
        claude_dir = project.root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "- **Architecture:** DDD packages -- `billing/`, `ledger/`\n",
            encoding="utf-8",
        )

        checks = _check_agent_instructions(project.root)

        pkg = [c for c in checks if c.name == "agent_instructions_packages"]
        assert [c.severity for c in pkg] == [Severity.OK]

    def test_a_typescript_stack_claim_is_not_faulted_for_omitting_sqlite(
        self, tmp_path: Path
    ) -> None:
        from beadloom.application.doctor import Severity, _check_agent_instructions

        project = typescript_project(tmp_path / "orders-web")
        (project.root / ".beadloom").mkdir()
        (project.root / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [typescript]\n",
            encoding="utf-8",
        )
        claude_dir = project.root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "- **Stack:** TypeScript\n- **Tests:** vitest\n", encoding="utf-8"
        )

        checks = _check_agent_instructions(project.root)

        stack = [c for c in checks if c.name == "agent_instructions_stack"]
        tests = [c for c in checks if c.name == "agent_instructions_test_framework"]
        assert [c.severity for c in stack] == [Severity.OK]
        assert [c.severity for c in tests] == [Severity.OK]

    def test_a_stack_claim_that_contradicts_the_declared_stack_is_drift(
        self, tmp_path: Path
    ) -> None:
        """TESTS MUST BITE: the relaxed check must still fail a wrong claim."""
        from beadloom.application.doctor import Severity, _check_agent_instructions

        project = typescript_project(tmp_path / "orders-web")
        (project.root / ".beadloom").mkdir()
        (project.root / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [typescript]\n",
            encoding="utf-8",
        )
        claude_dir = project.root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text(
            "- **Stack:** Fortran 77\n- **Tests:** nosetests\n", encoding="utf-8"
        )

        checks = _check_agent_instructions(project.root)

        stack = [c for c in checks if c.name == "agent_instructions_stack"]
        tests = [c for c in checks if c.name == "agent_instructions_test_framework"]
        assert [c.severity for c in stack] == [Severity.WARNING]
        assert [c.severity for c in tests] == [Severity.WARNING]
