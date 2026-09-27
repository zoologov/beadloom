"""The mutmut glue the mutation workflow runs (BDL-074 D1, `beadloom-vr0b`).

`.github/scripts/mutmut_adapter.py` is this repository's own tooling and is never
shipped: it turns the product's runner-independent answer — the functions a
change touched, by node, with the tests bound to each — into what mutmut 3.7
takes, and turns what mutmut wrote back into counter names the product reads.

**Every mutmut shape it reads is pinned here**, in the precedent of
`tests/mutmut_copy.py`: the mutant names (`<module>.x_<func>__mutmut_<N>`,
`<module>.xǁ<Class>ǁ<method>__mutmut_<N>`) and the `.meta` file's
`exit_code_by_key`, both copied from output mutmut 3.7.0 produced on this
repository on 2026-09-26. The one test that needs mutmut itself — that the exit
codes are classified by mutmut's own table — skips where the runner is not
installed, which is every CI leg but the mutation workflow's.
"""

from __future__ import annotations

import importlib.util
import json
import random
import subprocess
import sys
from typing import TYPE_CHECKING, ClassVar

import pytest

from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

if sys.version_info >= (3, 11):
    from tomllib import loads as toml_loads
else:
    from tomli import loads as toml_loads

ADAPTER = REPO_ROOT / ".github" / "scripts" / "mutmut_adapter.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mutmut_adapter", ADAPTER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


adapter = _load()

#: Names in the shape mutmut 3.7.0 writes them into `.meta`.
POSTING = "src/ledger/posting.py"
POST_1 = "ledger.posting.x_post__mutmut_1"
POST_2 = "ledger.posting.x_post__mutmut_2"
REVERSE_1 = "ledger.posting.x_reverse__mutmut_1"
DEPOSIT_1 = "ledger.posting.xǁAccountǁdeposit__mutmut_1"
INIT_1 = "ledger.posting.xǁAccountǁ__init____mutmut_1"
PACKAGE = "src/ledger/__init__.py"
PACKAGE_1 = "ledger.x__remediation_for__mutmut_1"

#: mutmut 3.7.0's own classification of the exit codes these fixtures use
#: (`__main__.py:82-104`); the one test that reads the real table checks it.
STATUS = {0: "survived", 1: "killed", 36: "timeout", 33: "no tests", None: "not checked"}


def _meta(exit_codes: dict[str, int | None]) -> str:
    """A `.meta` file in the shape mutmut 3.7.0 writes (`mutation/data.py:144-155`)."""
    return json.dumps(
        {
            "exit_code_by_key": exit_codes,
            "hash_by_function_name": {},
            "type_check_error_by_key": {},
            "durations_by_key": {},
            "estimated_durations_by_key": {},
        }
    )


def _mutants(root: Path, metas: dict[str, dict[str, int | None]]) -> Path:
    for source, codes in metas.items():
        path = root / "mutants" / f"{source}.meta"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_meta(codes), encoding="utf-8")
    return root


_ALL = {
    POSTING: {POST_1: None, POST_2: None, REVERSE_1: None, DEPOSIT_1: None, INIT_1: None},
    PACKAGE: {PACKAGE_1: None},
}


class TestAMutantNameNamesItsFunction:
    @pytest.mark.parametrize(
        ("name", "function"),
        [
            (POST_1, "post"),
            (DEPOSIT_1, "Account.deposit"),
            (INIT_1, "Account.__init__"),
            (PACKAGE_1, "_remediation_for"),
        ],
    )
    def test_the_two_shapes_mutmut_writes(self, name: str, function: str) -> None:
        assert adapter.function_of(name) == function

    @pytest.mark.parametrize("name", ["ledger.posting.post", "ledger.posting.y_post__mutmut_1"])
    def test_a_shape_it_does_not_know_is_an_error_rather_than_a_guess(self, name: str) -> None:
        with pytest.raises(adapter.AdapterShapeError):
            adapter.function_of(name)


class TestTheMetaFilesAreReadAsMutmutWritesThem:
    def test_each_source_file_maps_to_its_mutant_names(self, tmp_path: Path) -> None:
        metas = adapter.read_metas(_mutants(tmp_path, _ALL))
        assert set(metas) == {POSTING, PACKAGE}
        assert list(metas[PACKAGE]) == [PACKAGE_1]

    def test_a_meta_without_its_exit_codes_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "mutants" / f"{POSTING}.meta"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"durations_by_key": {}}), encoding="utf-8")
        with pytest.raises(adapter.AdapterShapeError, match="exit_code_by_key"):
            adapter.read_metas(tmp_path)


class TestTheChangedFunctionsBecomeExactNames:
    def test_each_changed_function_gets_every_mutant_of_its_own(self, tmp_path: Path) -> None:
        metas = adapter.read_metas(_mutants(tmp_path, _ALL))
        functions = [
            {"path": POSTING, "name": "post"},
            {"path": POSTING, "name": "Account.deposit"},
        ]
        picked = adapter.names_for_functions(functions, metas)
        assert picked.names == (POST_1, POST_2, DEPOSIT_1)
        assert picked.counts == ((POSTING, "post", 2), (POSTING, "Account.deposit", 1))

    def test_no_name_is_a_glob(self, tmp_path: Path) -> None:
        """A glob ending `__mutmut_*` makes mutmut's clean run fall back to the whole
        selection (BDL-073); exact names are the reason this adapter reads `.meta`."""
        metas = adapter.read_metas(_mutants(tmp_path, _ALL))
        picked = adapter.names_for_functions([{"path": POSTING, "name": "post"}], metas)
        assert not any("*" in name for name in picked.names)

    def test_a_function_mutmut_generated_nothing_for_is_counted_as_zero(
        self, tmp_path: Path
    ) -> None:
        metas = adapter.read_metas(_mutants(tmp_path, _ALL))
        picked = adapter.names_for_functions([{"path": POSTING, "name": "absent"}], metas)
        assert picked.names == ()
        assert picked.counts == ((POSTING, "absent", 0),)


class TestTheTestsARunIsGiven:
    PLAN: ClassVar[dict[str, object]] = {
        "nodes": [
            {"node": "posting", "functions": ["post"], "bound_tests": ["tests/unit/p/test_a.py"]}
        ],
        "unbound_tests": ["tests/test_flat.py", "tests/test_unpooled.py"],
    }

    def test_the_bound_tests_and_the_pools_unbound_files(self) -> None:
        pool = ["tests/test_flat.py", "tests/unit/other/test_b.py"]
        chosen = adapter.tests_for_change(self.PLAN, pool)
        assert chosen.bound == ("tests/unit/p/test_a.py",)
        assert chosen.fallback == ("tests/test_flat.py",)
        assert chosen.files == ("tests/test_flat.py", "tests/unit/p/test_a.py")

    def test_a_pool_file_bound_to_another_node_is_left_out(self) -> None:
        """The binding says it tests something else; the pool is only asked about
        the files the binding cannot place."""
        chosen = adapter.tests_for_change(self.PLAN, ["tests/unit/other/test_b.py"])
        assert "tests/unit/other/test_b.py" not in chosen.files

    def test_an_unbound_file_outside_the_pool_is_not_added(self) -> None:
        """The pool was derived by coverage and runs in `mutants/`; an unbound file
        outside it may not (the whole suite does not fit that room)."""
        chosen = adapter.tests_for_change(self.PLAN, [])
        assert chosen.files == ("tests/unit/p/test_a.py",)


_PYPROJECT = """\
[tool.other]
x = 1

[tool.mutmut]
source_paths = ["src/pkg"]
pytest_add_cli_args_test_selection = [
    "tests/test_a.py",
    "tests/test_b.py",
]
also_copy = [
    "docs",
]
"""


class TestThePerRunSelectionIsGeneratedConfiguration:
    def test_the_selection_is_replaced_and_nothing_else(self) -> None:
        text = adapter.with_selection(_PYPROJECT, ["tests/unit/test_c.py"])
        config = toml_loads(text)["tool"]
        assert config["mutmut"]["pytest_add_cli_args_test_selection"] == ["tests/unit/test_c.py"]
        assert config["mutmut"]["also_copy"] == ["docs"]
        assert config["other"] == {"x": 1}

    def test_a_file_without_the_key_is_an_error(self) -> None:
        with pytest.raises(adapter.AdapterShapeError, match="pytest_add_cli_args_test_selection"):
            adapter.with_selection("[tool.mutmut]\n", ["tests/test_c.py"])

    def test_this_repositorys_own_pyproject_can_be_rewritten(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        rewritten = adapter.with_selection(text, ["tests/test_c.py"])
        mutmut = toml_loads(rewritten)["tool"]["mutmut"]
        assert mutmut["pytest_add_cli_args_test_selection"] == ["tests/test_c.py"]
        assert mutmut["only_mutate"] == toml_loads(text)["tool"]["mutmut"]["only_mutate"]


class TestTheWeeklySampleIsSeeded:
    def test_the_same_seed_draws_the_same_names(self, tmp_path: Path) -> None:
        metas = adapter.read_metas(_mutants(tmp_path, _ALL))
        assert adapter.sample_names(metas, 3, "2026-W39") == adapter.sample_names(
            metas, 3, "2026-W39"
        )

    def test_the_draw_is_the_documented_one(self, tmp_path: Path) -> None:
        """Reproducible from the seed alone: sorted names, `random.Random(seed).sample`."""
        metas = adapter.read_metas(_mutants(tmp_path, _ALL))
        everything = sorted(name for names in metas.values() for name in names)
        expected = sorted(random.Random("2026-W39").sample(everything, 3))  # noqa: S311
        assert adapter.sample_names(metas, 3, "2026-W39") == tuple(expected)

    def test_a_sample_no_smaller_than_the_scope_is_the_scope(self, tmp_path: Path) -> None:
        metas = adapter.read_metas(_mutants(tmp_path, _ALL))
        assert len(adapter.sample_names(metas, 100, "s")) == 6


class TestTheCountersCoverExactlyTheNamesRun:
    def _metas(self, tmp_path: Path) -> dict[str, dict[str, int | None]]:
        codes = {POST_1: 1, POST_2: 0, REVERSE_1: 36, DEPOSIT_1: None, INIT_1: 1}
        return adapter.read_metas(_mutants(tmp_path, {POSTING: codes, PACKAGE: {PACKAGE_1: 0}}))

    def test_only_the_selected_names_are_counted(self, tmp_path: Path) -> None:
        counted = adapter.count_names((POST_1, POST_2, REVERSE_1), self._metas(tmp_path), STATUS)
        assert counted.counters["total"] == 3
        assert counted.counters["killed"] == 1
        assert counted.counters["survived"] == 1
        assert counted.counters["timeout"] == 1
        assert counted.counters["not_checked"] == 0

    def test_the_survivors_name_their_source_file(self, tmp_path: Path) -> None:
        counted = adapter.count_names((POST_2, PACKAGE_1), self._metas(tmp_path), STATUS)
        assert counted.survivors == (
            {"path": POSTING, "mutant": POST_2},
            {"path": PACKAGE, "mutant": PACKAGE_1},
        )

    def test_a_mutant_that_never_ran_is_not_checked(self, tmp_path: Path) -> None:
        counted = adapter.count_names((DEPOSIT_1,), self._metas(tmp_path), STATUS)
        assert counted.counters["not_checked"] == 1

    def test_a_name_no_meta_holds_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(adapter.AdapterShapeError, match=r"no \.meta"):
            adapter.count_names(("ledger.x_gone__mutmut_1",), self._metas(tmp_path), STATUS)

    def test_the_exit_codes_are_classified_by_mutmuts_own_table(self, tmp_path: Path) -> None:
        """Run in a child process from a directory shaped like a mutmut project:
        importing mutmut's table loads mutmut's configuration from the current
        directory and caches it for the life of the process."""
        pytest.importorskip("mutmut")
        (tmp_path / "src").mkdir()
        (tmp_path / "pyproject.toml").write_text(
            '[tool.mutmut]\nsource_paths = ["src"]\n', encoding="utf-8"
        )
        program = (
            "import importlib.util, json, sys\n"
            f"spec = importlib.util.spec_from_file_location('a', {str(ADAPTER)!r})\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "sys.modules['a'] = module\n"
            "spec.loader.exec_module(module)\n"
            "table = module.mutmut_status_table()\n"
            f"print(json.dumps([table[code] for code in {list(STATUS)!r}]))\n"
        )
        result = subprocess.run(  # noqa: S603 - this interpreter, a fixed program
            [sys.executable, "-c", program],
            cwd=tmp_path,
            capture_output=True,
            encoding="utf-8",
            check=True,
        )
        assert json.loads(result.stdout) == list(STATUS.values())


class TestTheJudgeTellsAJudgedRunFromASilentOne:
    def _stats(self, tmp_path: Path, **counters: int) -> Path:
        path = tmp_path / "stats.json"
        path.write_text(json.dumps(counters), encoding="utf-8")
        return path

    def test_every_selected_mutant_with_a_verdict_is_judged(self, tmp_path: Path) -> None:
        stats = self._stats(tmp_path, total=3, killed=2, survived=1, not_checked=0)
        verdict, detail = adapter.judge(3, stats)
        assert verdict == "judged"
        assert "3 mutant(s)" in detail

    def test_counters_never_written_are_silent(self, tmp_path: Path) -> None:
        verdict, detail = adapter.judge(3, tmp_path / "absent.json")
        assert verdict == "silent"
        assert "never written" in detail

    def test_an_unreadable_file_is_an_absence_and_not_a_zero(self, tmp_path: Path) -> None:
        path = tmp_path / "stats.json"
        path.write_text("not json", encoding="utf-8")
        assert adapter.judge(3, path)[0] == "silent"

    def test_counters_over_fewer_mutants_than_selected_are_silent(self, tmp_path: Path) -> None:
        verdict, detail = adapter.judge(3, self._stats(tmp_path, total=2, not_checked=0))
        assert verdict == "silent"
        assert "2 of 3" in detail

    def test_a_mutant_that_never_ran_makes_the_run_silent(self, tmp_path: Path) -> None:
        """What a killed runner leaves: the names were selected and never reached."""
        verdict, detail = adapter.judge(3, self._stats(tmp_path, total=3, not_checked=2))
        assert verdict == "silent"
        assert "2 of 3" in detail

    def test_an_interrupted_run_is_silent(self, tmp_path: Path) -> None:
        stats = self._stats(tmp_path, total=3, not_checked=0, check_was_interrupted_by_user=1)
        assert adapter.judge(3, stats)[0] == "silent"

    def test_no_selected_mutant_is_silent(self, tmp_path: Path) -> None:
        assert adapter.judge(0, self._stats(tmp_path, total=0, not_checked=0))[0] == "silent"


class TestTheCommandLine:
    def test_an_empty_change_generates_nothing_and_says_so(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def _fail(*_: object) -> None:
            raise AssertionError("an empty change must not prepare mutants")

        monkeypatch.setattr(adapter, "prepare_mutants", _fail)
        monkeypatch.chdir(tmp_path)
        plan = tmp_path / "plan.json"
        plan.write_text(json.dumps({"change": {"empty": True, "functions": []}}), encoding="utf-8")
        names = tmp_path / "names.txt"
        output = tmp_path / "out.txt"
        code = adapter.main(
            [
                "select",
                "--plan",
                str(plan),
                "--names-out",
                str(names),
                "--github-output",
                str(output),
            ]
        )
        assert code == 0
        assert names.read_text(encoding="utf-8") == ""
        assert "mutants=0" in output.read_text(encoding="utf-8")
        assert "empty" in capsys.readouterr().out

    def test_a_change_writes_its_names_and_its_selection(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(adapter, "prepare_mutants", lambda *_: _mutants(tmp_path, _ALL))
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
        plan = {
            "change": {
                "empty": False,
                "functions": [{"path": POSTING, "name": "post", "node": "posting"}],
                "nodes": [
                    {
                        "node": "posting",
                        "functions": ["post"],
                        "bound_tests": ["tests/unit/test_p.py"],
                    }
                ],
                "unbound_tests": ["tests/test_a.py"],
            }
        }
        (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        code = adapter.main(
            ["select", "--plan", "plan.json", "--names-out", "names.txt", "--github-output", "o"]
        )
        assert code == 0
        assert (tmp_path / "names.txt").read_text(encoding="utf-8").split() == [POST_1, POST_2]
        selection = toml_loads((tmp_path / "pyproject.toml").read_text(encoding="utf-8"))
        assert selection["tool"]["mutmut"]["pytest_add_cli_args_test_selection"] == [
            "tests/test_a.py",
            "tests/unit/test_p.py",
        ]
        assert "mutants=2" in (tmp_path / "o").read_text(encoding="utf-8")

    def test_a_change_with_no_test_to_run_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """An empty selection makes mutmut run the whole suite, which does not fit
        `mutants/`; a population with nothing to run it against is stated instead,
        before a stats pass is paid for."""

        def _fail(*_: object) -> None:
            raise AssertionError("a refused change must not prepare mutants")

        monkeypatch.setattr(adapter, "prepare_mutants", _fail)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
        plan = {
            "change": {
                "empty": False,
                "functions": [{"path": POSTING, "name": "post", "node": "posting"}],
                "nodes": [{"node": "posting", "functions": ["post"], "bound_tests": []}],
                "unbound_tests": [],
            }
        }
        (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        code = adapter.main(["select", "--plan", "plan.json", "--names-out", "names.txt"])
        assert code == 1
        assert "no test" in capsys.readouterr().out


_PROJECT_PYPROJECT = """\
[tool.mutmut]
source_paths = ["src/pkg"]
only_mutate = ["src/pkg/arith.py"]
pytest_add_cli_args_test_selection = [
    "tests/test_arith.py",
]
"""

_ARITH = "def add(a, b):\n    return a + b\n\n\ndef twice(a):\n    return a * 2\n"

_ARITH_TEST = (
    "from pkg.arith import add, twice\n\n\n"
    "def test_add():\n    assert add(1, 2) == 3\n\n\n"
    "def test_twice():\n    assert twice(2) >= 0\n"
)


@pytest.fixture
def arith(tmp_path: Path) -> Path:
    """A project mutmut can run over in seconds: two functions, two tests."""
    pytest.importorskip("mutmut")
    project = tmp_path / "arith"
    for relative, text in {
        "pyproject.toml": _PROJECT_PYPROJECT,
        "src/pkg/__init__.py": "",
        "src/pkg/arith.py": _ARITH,
        "tests/__init__.py": "",
        "tests/test_arith.py": _ARITH_TEST,
    }.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return project


class TestTheInstalledMutmutIsUsedAsItIs:
    """Run against the mutmut this interpreter has, whatever its version: the
    lock pins 3.7.0 for CI, and a fresh install resolves a newer one."""

    def test_preparing_generates_the_names_and_saves_the_stats(self, arith: Path) -> None:
        adapter.prepare_mutants(arith)
        metas = adapter.read_metas(arith)
        assert list(metas) == ["src/pkg/arith.py"]
        functions = {adapter.function_of(name) for name in metas["src/pkg/arith.py"]}
        assert functions == {"add", "twice"}
        assert (arith / "mutants" / "mutmut-stats.json").is_file()

    def test_a_stats_pass_that_fails_is_reported_not_taken_for_preparation(
        self, arith: Path
    ) -> None:
        (arith / "tests" / "test_arith.py").write_text(
            "def test_broken():\n    assert False\n", encoding="utf-8"
        )
        with pytest.raises(adapter.AdapterShapeError, match="stats"):
            adapter.prepare_mutants(arith)

    def test_exact_names_run_and_are_counted_by_mutmuts_own_table(self, arith: Path) -> None:
        adapter.prepare_mutants(arith)
        names = tuple(
            name
            for name in adapter.read_metas(arith)["src/pkg/arith.py"]
            if adapter.function_of(name) == "twice"
        )
        mutmut = adapter.runner_executable()
        subprocess.run(  # noqa: S603 - the installed runner, exact names
            [mutmut, "run", "--max-children", "1", *names],
            cwd=arith,
            capture_output=True,
            check=False,
        )
        (arith / "names.txt").write_text("".join(f"{n}\n" for n in names), encoding="utf-8")
        subprocess.run(  # noqa: S603 - this interpreter, the adapter, as the workflow runs it
            [
                sys.executable,
                str(ADAPTER),
                "counters",
                "--names",
                "names.txt",
                "--stats-out",
                "stats.json",
                "--survivors-out",
                "survivors.json",
            ],
            cwd=arith,
            capture_output=True,
            check=True,
        )
        counters = json.loads((arith / "stats.json").read_text(encoding="utf-8"))
        survivors = json.loads((arith / "survivors.json").read_text(encoding="utf-8"))
        assert counters["total"] == len(names)
        assert counters["not_checked"] == 0
        assert counters["killed"] + counters["survived"] == len(names)
        assert counters["survived"] >= 1, "`twice(2) >= 0` lets a mutant live"
        assert {entry["path"] for entry in survivors} == {"src/pkg/arith.py"}
        assert adapter.judge(len(names), arith / "stats.json")[0] == "judged"
