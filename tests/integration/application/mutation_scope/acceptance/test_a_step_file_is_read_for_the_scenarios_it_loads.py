"""An acceptance step file is placed under the nodes its loaded scenarios name (BDL-074 G1).

A step file binds to no node by its path; the scenarios it loads do, through their
``@node:`` tags. So the file is read for the feature paths it hands to pytest-bdd's
``scenarios(...)`` / ``scenario(...)``, and those features for their tags. Only a
literal path is followed: a computed one is not guessed at.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.mutation_scope.acceptance import acceptance_files_by_node

if TYPE_CHECKING:
    from pathlib import Path

STEPS = "tests/acceptance/steps/test_steps.py"


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _feature(node: str) -> str:
    return f"Feature: f\n\n  @node:{node}\n  Scenario: s\n    Given g\n"


class TestTheFeaturesAStepFileLoads:
    def test_the_nodes_of_a_loaded_feature_select_the_step_file(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tests/acceptance/features/a.feature": _feature("ledger"),
                STEPS: 'from pytest_bdd import scenarios\nscenarios("../features/a.feature")\n',
            },
        )

        assert acceptance_files_by_node(tmp_path, [STEPS]) == {"ledger": (STEPS,)}

    def test_a_folder_handed_to_scenarios_loads_every_feature_under_it(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            {
                "tests/acceptance/features/a.feature": _feature("ledger"),
                "tests/acceptance/features/deep/b.feature": _feature("vault"),
                STEPS: 'from pytest_bdd import scenarios\nscenarios("../features")\n',
            },
        )

        assert acceptance_files_by_node(tmp_path, [STEPS]) == {
            "ledger": (STEPS,),
            "vault": (STEPS,),
        }

    def test_a_single_scenario_binding_loads_its_feature(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tests/acceptance/features/a.feature": _feature("ledger"),
                STEPS: (
                    "from pytest_bdd import scenario\n\n"
                    '@scenario("../features/a.feature", "s")\n'
                    "def test_s() -> None:\n    pass\n"
                ),
            },
        )

        assert acceptance_files_by_node(tmp_path, [STEPS]) == {"ledger": (STEPS,)}


class TestWhatIsNotGuessed:
    def test_a_computed_path_is_not_followed(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            {
                "tests/acceptance/features/a.feature": _feature("ledger"),
                STEPS: (
                    "from pytest_bdd import scenarios\n"
                    'FEATURE = "../features/a.feature"\nscenarios(FEATURE)\n'
                ),
            },
        )

        assert acceptance_files_by_node(tmp_path, [STEPS]) == {}

    def test_a_step_file_that_does_not_parse_selects_nothing(self, tmp_path: Path) -> None:
        _write(tmp_path, {STEPS: "scenarios(\n"})

        assert acceptance_files_by_node(tmp_path, [STEPS]) == {}

    def test_a_missing_feature_or_step_file_selects_nothing(self, tmp_path: Path) -> None:
        _write(tmp_path, {STEPS: 'from pytest_bdd import scenarios\nscenarios("gone.feature")\n'})

        assert acceptance_files_by_node(tmp_path, [STEPS, "tests/acceptance/x.py"]) == {}
