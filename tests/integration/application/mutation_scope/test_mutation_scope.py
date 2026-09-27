"""The mutation-SCOPE check (BDL-061 S4b, CONTEXT Q5).

Beadloom does not own a mutation runner. Owning one would break
tool-agnosticism, so what ships is the role duty (`.13`), the scope convention,
and this: the check that a declared target lies inside the configured source
paths. **The failure worth catching is a declared target that runs zero
mutants** — a scope that names a moved package, a deleted module or a directory
holding no source file at all reports a strong-looking mutation score computed
over nothing.

Everything here is ``warn``. A project that declares no ``mutation:`` block is
not failing a check it never opted into, and that is stated by a test rather
than left to be assumed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.mutation_scope import (
    MUTATION_OUTSIDE_SOURCE,
    MUTATION_TARGET_MISSING,
    MUTATION_ZERO_MUTANTS,
    check_mutation_scope,
    load_mutation_targets,
)

if TYPE_CHECKING:
    from pathlib import Path


def _project(
    tmp_path: Path,
    *,
    targets: list[str] | None,
    scan_paths: tuple[str, ...] = ("src",),
) -> Path:
    (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
    flow = "tools:\n- claude\narchitecture:\n- ddd\nstack:\n- python\n"
    if targets is not None:
        flow += "mutation:\n  targets:\n"
        flow += "".join(f"  - {t}\n" for t in targets)
    (tmp_path / ".beadloom" / "flow.yml").write_text(flow, encoding="utf-8")
    config = "languages:\n- .py\nscan_paths:\n"
    config += "".join(f"- {p}\n" for p in scan_paths)
    (tmp_path / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
    return tmp_path


def _source(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("def f() -> int:\n    return 1\n", encoding="utf-8")


class TestTargetsAreRead:
    def test_a_project_with_no_mutation_block_declares_no_targets(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, targets=None)
        assert load_mutation_targets(root) == ()

    def test_declared_targets_are_read_in_order(self, tmp_path: Path) -> None:
        root = _project(tmp_path, targets=["src/a/", "src/b.py"])
        assert load_mutation_targets(root) == ("src/a/", "src/b.py")

    def test_a_project_with_no_flow_config_declares_no_targets(
        self, tmp_path: Path
    ) -> None:
        assert load_mutation_targets(tmp_path) == ()


class TestAValidScopeIsSilent:
    def test_a_target_inside_the_source_paths_with_code_reports_nothing(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, targets=["src/core/"])
        _source(root, "src/core/rules.py")
        assert check_mutation_scope(root) == []

    def test_a_single_file_target_reports_nothing(self, tmp_path: Path) -> None:
        root = _project(tmp_path, targets=["src/core/rules.py"])
        _source(root, "src/core/rules.py")
        assert check_mutation_scope(root) == []

    def test_a_project_that_declares_no_targets_reports_nothing(
        self, tmp_path: Path
    ) -> None:
        """Not opting in is not a violation — the check ships as ``warn`` and
        must not turn a green project red on upgrade."""
        root = _project(tmp_path, targets=None)
        _source(root, "src/core/rules.py")
        assert check_mutation_scope(root) == []


class TestTheFailureWorthCatching:
    def test_a_target_outside_the_configured_source_paths_is_reported(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, targets=["tests/"], scan_paths=("src",))
        _source(root, "tests/test_x.py")
        findings = check_mutation_scope(root)
        assert [f.check for f in findings] == [MUTATION_OUTSIDE_SOURCE]
        assert "tests/" in findings[0].target
        assert "src" in findings[0].why

    def test_a_target_that_does_not_exist_is_reported(self, tmp_path: Path) -> None:
        root = _project(tmp_path, targets=["src/moved/"])
        _source(root, "src/core/rules.py")
        findings = check_mutation_scope(root)
        assert [f.check for f in findings] == [MUTATION_TARGET_MISSING]
        assert "zero mutants" in findings[0].why

    def test_a_target_holding_no_source_file_is_reported(
        self, tmp_path: Path
    ) -> None:
        """A directory of markdown runs zero mutants and scores 100%."""
        root = _project(tmp_path, targets=["src/docs/"])
        (root / "src" / "docs").mkdir(parents=True)
        (root / "src" / "docs" / "notes.md").write_text("hi\n", encoding="utf-8")
        findings = check_mutation_scope(root)
        assert [f.check for f in findings] == [MUTATION_ZERO_MUTANTS]

    def test_a_target_of_the_wrong_language_is_reported(self, tmp_path: Path) -> None:
        """The languages the project indexes decide what a mutant could be."""
        root = _project(tmp_path, targets=["src/web/"])
        (root / "src" / "web").mkdir(parents=True)
        (root / "src" / "web" / "app.ts").write_text("export {};\n", encoding="utf-8")
        findings = check_mutation_scope(root)
        assert [f.check for f in findings] == [MUTATION_ZERO_MUTANTS]

    def test_a_single_file_target_of_the_wrong_language_is_reported(
        self, tmp_path: Path
    ) -> None:
        """The file branch, not the directory one — measured by sabotage S12,
        which made a file target mutable whatever its suffix and reddened
        nothing, because every wrong-language case here was a directory."""
        root = _project(tmp_path, targets=["src/web/app.ts"])
        (root / "src" / "web").mkdir(parents=True)
        (root / "src" / "web" / "app.ts").write_text("export {};\n", encoding="utf-8")
        findings = check_mutation_scope(root)
        assert [f.check for f in findings] == [MUTATION_ZERO_MUTANTS]

    def test_each_bad_target_is_reported_once_and_names_itself(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, targets=["src/gone/", "tests/", "src/ok/"])
        _source(root, "src/ok/rules.py")
        findings = check_mutation_scope(root)
        assert sorted(f.target for f in findings) == ["src/gone/", "tests/"]

    def test_a_finding_is_a_warn_and_carries_a_remediation(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, targets=["src/gone/"])
        finding = check_mutation_scope(root)[0]
        assert finding.severity == "warn"
        assert finding.remediation


class TestSurfacedByConfigCheck:
    def test_config_check_reports_the_scope_finding(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        root = _project(tmp_path, targets=["src/gone/"])
        _source(root, "src/core/rules.py")

        result = CliRunner().invoke(main, ["config-check", "--project", str(root)])

        assert "src/gone/" in result.output
        assert "mutation" in result.output.lower()

    def test_the_gate_reports_it_without_blocking(self, tmp_path: Path) -> None:
        from beadloom.application.gate import _step_config_check

        root = _project(tmp_path, targets=["src/gone/"])
        _source(root, "src/core/rules.py")

        step = _step_config_check(root)

        assert any(
            f.get("rule") == MUTATION_TARGET_MISSING for f in step.findings
        ), step.findings


class TestForAProjectThatIsNotBeadloom:
    def test_an_adopters_own_scan_paths_decide_what_is_inside(
        self, tmp_path: Path
    ) -> None:
        """``src`` is Beadloom's layout, not everybody's — a project whose code
        lives in ``lib/`` must not have its whole scope reported."""
        root = _project(tmp_path, targets=["lib/core/"], scan_paths=("lib",))
        _source(root, "lib/core/rules.py")
        assert check_mutation_scope(root) == []
