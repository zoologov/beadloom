"""`beadloom mutation` — the score produced by a command (BDL-068 S3.1).

The command is the whole point of the bead: BDL-061 S4 shipped a mutation DUTY
into every composed role core and no way to produce a score, so four beads in
BDL-067 reported one by four hand methods and every result exists as prose in a
bead comment.

Every test runs the real Click command over real files. The counters are a
JSON object a runner wrote, which is the seam an adopter's own tool meets.
"""

from __future__ import annotations

import json
import platform
from typing import TYPE_CHECKING

from click.testing import CliRunner, Result

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _project(root: Path, *targets: str) -> Path:
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )
    declared = "".join(f"  - {t}\n" for t in targets)
    (root / ".beadloom" / "flow.yml").write_text(
        f"mutation:\n  targets:\n{declared}" if targets else "tools:\n- claude\n",
        encoding="utf-8",
    )
    return root


def _stats(root: Path, **values: int) -> str:
    path = root / "stats.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return str(path)


def _run(root: Path, *args: str) -> Result:
    return CliRunner().invoke(main, ["mutation", "--project", str(root), *args])


class TestTheScoreIsProduced:
    def test_a_run_over_the_declared_target_prints_the_score(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        result = _run(
            root,
            "--stats",
            _stats(root, killed=8, survived=2),
            "--target",
            "src/core/",
            "--tool",
            "a runner",
        )
        assert result.exit_code == 0, result.output
        assert "80.0%" in result.output
        assert "a runner" in result.output

    def test_the_json_carries_the_same_score_and_names_the_room(self, tmp_path: Path) -> None:
        """One computation, two renderings — a monitoring surface reads the same
        number a human does (BDL-UX #148)."""
        root = _project(tmp_path, "src/core/")
        result = _run(
            root, "--stats", _stats(root, killed=8, survived=2), "--target", "src/core/", "--json"
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["score"] == 0.8
        assert platform.python_version() in payload["room"]
        assert payload["covered"] == ["src/core/"]

    def test_the_human_output_names_the_room(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        result = _run(root, "--stats", _stats(root, killed=8, survived=2), "--target", "src/core/")
        assert platform.system() in result.output


class TestWhatMakesItExitOne:
    def test_a_run_that_produced_no_mutants(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        result = _run(
            root,
            "--stats",
            _stats(root, killed=0, survived=0, total=0),
            "--target",
            "src/core/",
        )
        assert result.exit_code == 1
        assert "mutation-run-zero-mutants" in result.output

    def test_no_run_at_all_leaves_the_declared_scope_unmeasured(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        result = _run(root)
        assert result.exit_code == 1
        assert "mutation-target-unmeasured" in result.output

    def test_a_score_under_the_declared_floor(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        result = _run(
            root,
            "--stats",
            _stats(root, killed=8, survived=2),
            "--target",
            "src/core/",
            "--min-score",
            "0.9",
        )
        assert result.exit_code == 1
        assert "0.9" in result.output

    def test_a_score_at_the_declared_floor_passes(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/")
        result = _run(
            root,
            "--stats",
            _stats(root, killed=8, survived=2),
            "--target",
            "src/core/",
            "--min-score",
            "0.8",
        )
        assert result.exit_code == 0, result.output


class TestWhatItRefusesToDo:
    def test_a_run_that_does_not_say_what_it_covered_is_not_a_run(
        self, tmp_path: Path
    ) -> None:
        """`--stats` without `--target` is refused rather than assumed to cover
        everything declared: assuming it is how a run over one module reports a
        score for a scope it never entered."""
        root = _project(tmp_path, "src/core/")
        result = _run(root, "--stats", _stats(root, killed=8, survived=2))
        assert result.exit_code == 2
        assert "--target" in result.output

    def test_a_floor_cannot_be_declared_against_a_score_that_does_not_exist(
        self, tmp_path: Path
    ) -> None:
        """A missing counter must not pass a floor by having no number to compare."""
        root = _project(tmp_path, "src/core/")
        result = _run(
            root,
            "--stats",
            _stats(root, survived=2),
            "--target",
            "src/core/",
            "--min-score",
            "0.5",
        )
        assert result.exit_code == 1
        assert "mutation-counters-missing" in result.output


class TestAProjectThatNeverOptedIn:
    def test_declaring_no_targets_is_not_a_violation(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        result = _run(root)
        assert result.exit_code == 0, result.output
        assert "no mutation scope" in result.output.lower()

class TestASliceThatDoesNotClaimTheWholeScope:
    def test_only_narrows_what_is_judged_and_prints_what_was_not(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path, "src/core/", "src/other/")
        result = _run(
            root,
            "--stats",
            _stats(root, killed=8, survived=2),
            "--target",
            "src/core/",
            "--only",
            "src/core/",
        )
        assert result.exit_code == 0, result.output
        assert "src/other/" in result.output
        assert "not judged" in result.output.lower()

    def test_the_json_carries_what_was_not_judged(self, tmp_path: Path) -> None:
        root = _project(tmp_path, "src/core/", "src/other/")
        result = _run(
            root,
            "--stats",
            _stats(root, killed=8, survived=2),
            "--target",
            "src/core/",
            "--only",
            "src/core/",
            "--json",
        )
        assert json.loads(result.stdout)["not_judged"] == ["src/other/"]

    def test_without_only_the_undeclared_half_is_a_finding(self, tmp_path: Path) -> None:
        """`--only` is what makes a slice honest; its absence judges everything."""
        root = _project(tmp_path, "src/core/", "src/other/")
        result = _run(
            root, "--stats", _stats(root, killed=8, survived=2), "--target", "src/core/"
        )
        assert result.exit_code == 1
        assert "mutation-target-unmeasured" in result.output
