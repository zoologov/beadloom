"""The mutmut glue this repository's mutation workflow runs (BDL-074 D1). Never shipped.

Beadloom owns no mutation runner (BDL-061 CONTEXT Q5). The product answers the
runner-independent questions — which functions a change touched, the node owning
each, the tests the binding ties to that node, and the score a run's counters
make — and this script is where those answers meet mutmut 3.7, as it is:

``select``
    Write the per-run ``pytest_add_cli_args_test_selection`` into
    ``pyproject.toml``, each kind of test file chosen by what it is (BDL-074 G1):
    the files the binding ties to the changed nodes; the acceptance step files
    whose loaded scenarios carry a changed node's ``@node:`` tag; and the pool's
    UNPLACED files — the FALLBACK, for files outside every kind folder that may
    exercise the node while the binding cannot say. Self-checks are never chosen:
    they test this repository's files, not the changed code. The fallback shrinks
    as unplaced files are laid out and is empty once none is left in the pool
    (59 of the 167 unplaced files were in it on 2026-09-28, measured). Then prepare the
    mutants and take the EXACT names of the changed functions' mutants from
    ``mutants/*.meta`` (a glob ending ``__mutmut_*`` makes mutmut's clean run
    fall back to the whole selection, BDL-073). Given ``--budget``, a change
    with more mutants than that is measured in part: whole functions, the
    largest first, each one that still fits, and every function left out is
    named with its count and written to ``--left-out`` (``beadloom-af99.17``).
``sample``
    Prepare the mutants and draw a seeded random sample of exact names from the
    whole declared scope.
``counters``
    Classify exactly the selected names with mutmut's own exit-code table, and
    write the counters and the survivors the product reads.
``judge``
    Tell a run that judged every selected mutant from one that left some
    unjudged while every step exited 0, and name what a capped run left out.

**Preparing the mutants uses mutmut's command line only.** mutmut has no
command that generates mutants and stops, and its generation functions moved
between 3.7.0 and 3.8.0. What both versions do is generate, run the stats pass
over the selection, SAVE the stats, and then refuse a name filter that matches
nothing. So preparation is ``mutmut run <a name no mutant has>``, followed by a
check that the stats and the ``.meta`` files exist: the stats it saved are
reused by the run that follows, so the stats pass is paid once, as it would be
anyway.

Every mutmut shape read here is named where it is read and pinned by
``tests/self_check/config/test_mutation_adapter.py``, which also runs the
installed mutmut end to end on a two-function project. Run it from the
repository root: mutmut works in ``./mutants`` relative to the current
directory.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

#: Where mutmut 3.7 writes the mutated copy and one ``<source>.meta`` per file.
MUTANTS = "mutants"
META_SUFFIX = ".meta"

#: The key of the per-run test selection in ``[tool.mutmut]``.
SELECTION_KEY = "pytest_add_cli_args_test_selection"

#: A mutant name ends ``__mutmut_<N>`` (mutmut 3.7 ``utils/format_utils.py:61-67``).
_MUTANT_SUFFIX = re.compile(r"__mutmut_\d+$")

#: mutmut's separator in a method's mangled name, ``xǁ<Class>ǁ<method>``
#: (``mutation/trampoline_templates.py:1``).
_CLASS_SEPARATOR = "ǁ"

#: The prefix of a top-level function's mangled name, ``x_<function>``.
_FUNCTION_PREFIX = "x_"

#: A name no mutant has: ``mutmut run`` generates, runs and saves the stats pass,
#: then refuses a filter that matches nothing (3.7.0 and 3.8.0 alike).
_NO_SUCH_MUTANT = "beadloom_adapter.x_no_such_function__mutmut_0"

#: What the stats pass leaves behind, and what preparing is checked by.
_STATS_FILE = "mutmut-stats.json"

#: The children preparing uses; the ceiling every invocation here holds to.
_PREPARE_CHILDREN = 2

#: Where mutmut keeps its exit-code classification: 3.8.0, then 3.7.0.
_STATUS_TABLE_HOMES = ("mutmut.stats", "mutmut.__main__")

#: How many lines of mutmut's own output a failed preparation quotes.
_QUOTED_LINES = 15

#: The array that holds the selection, as this repository's pyproject spells it.
_SELECTION_ARRAY = re.compile(
    rf"^{SELECTION_KEY}\s*=\s*\[[^\]]*\]", flags=re.MULTILINE | re.DOTALL
)

#: The counter names written, in mutmut's own ``export-cicd-stats`` spelling
#: (``__main__.py:1174-1191``) plus the two classes it counts and does not export.
_COUNTER_NAMES = (
    "killed",
    "survived",
    "no_tests",
    "skipped",
    "suspicious",
    "timeout",
    "check_was_interrupted_by_user",
    "segfault",
    "caught_by_type_check",
    "not_checked",
)


class AdapterShapeError(RuntimeError):
    """mutmut wrote something in a shape this adapter was not written against."""


@dataclass(frozen=True)
class PickedNames:
    """The exact mutant names of a change, and how many each function contributed."""

    names: tuple[str, ...]
    counts: tuple[tuple[str, str, int], ...]


#: The recorded kind of a self-check file in the plan's ``other_kinds`` counts.
_SELF_CHECK_KIND = "self_check"


@dataclass(frozen=True)
class ChosenTests:
    """The tests a per-change run is given, and where each part came from."""

    bound: tuple[str, ...]
    acceptance: tuple[str, ...]
    fallback: tuple[str, ...]
    unplaced: int

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(sorted({*self.bound, *self.acceptance, *self.fallback}))


#: One function a capped run left out: its source path, its name, its mutants.
Left = tuple[str, str, int]


@dataclass(frozen=True)
class Budgeted:
    """What a run measures within its budget of mutants, and what it leaves out."""

    measured: PickedNames
    left: tuple[Left, ...]
    budget: int | None


@dataclass(frozen=True)
class Counted:
    """Counters over exactly the selected names, and the survivors among them."""

    counters: dict[str, int]
    survivors: tuple[dict[str, str], ...]


def function_of(name: str) -> str:
    """The function a mutant name belongs to: ``function`` or ``Class.method``."""
    mangled = _MUTANT_SUFFIX.sub("", name)
    if mangled == name:
        raise AdapterShapeError(f"{name!r} does not end in __mutmut_<N>")
    local = mangled.rpartition(".")[2]
    if local.startswith(f"x{_CLASS_SEPARATOR}"):
        parts = local.split(_CLASS_SEPARATOR)
        if len(parts) == 3 and all(parts[1:]):
            return f"{parts[1]}.{parts[2]}"
    elif local.startswith(_FUNCTION_PREFIX) and len(local) > len(_FUNCTION_PREFIX):
        return local[len(_FUNCTION_PREFIX) :]
    raise AdapterShapeError(f"{name!r} is in no mutant-name shape mutmut 3.7 writes")


def read_metas(root: Path) -> dict[str, dict[str, int | None]]:
    """Every ``.meta`` under ``<root>/mutants``: source path -> exit code by mutant name."""
    base = root / MUTANTS
    metas: dict[str, dict[str, int | None]] = {}
    for path in sorted(base.rglob(f"*.py{META_SUFFIX}")):
        source = path.relative_to(base).as_posix().removesuffix(META_SUFFIX)
        metas[source] = _exit_codes(path)
    return metas


def _exit_codes(path: Path) -> dict[str, int | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    codes = data.get("exit_code_by_key") if isinstance(data, dict) else None
    if not isinstance(codes, dict):
        raise AdapterShapeError(f"{path} holds no exit_code_by_key object")
    return {str(name): code for name, code in codes.items()}


def names_for_functions(
    functions: Iterable[Mapping[str, object]], metas: Mapping[str, Mapping[str, int | None]]
) -> PickedNames:
    """The exact names of each changed function's mutants, in the plan's order."""
    names: list[str] = []
    counts: list[tuple[str, str, int]] = []
    for function in functions:
        path, wanted = str(function["path"]), str(function["name"])
        own = [name for name in metas.get(path, {}) if function_of(name) == wanted]
        names.extend(own)
        counts.append((path, wanted, len(own)))
    return PickedNames(names=tuple(dict.fromkeys(names)), counts=tuple(counts))


def budgeted_names(
    functions: Sequence[Mapping[str, object]],
    metas: Mapping[str, Mapping[str, int | None]],
    budget: int | None,
) -> Budgeted:
    """The change's names within *budget* mutants: whole functions, the largest first.

    A change within the budget, or with none, is measured whole. Otherwise each
    function is taken, largest first and in the plan's order among equals, when
    its mutants still fit what is left of the budget; a function they do not fit
    gives way to smaller ones, and is left out with its count. A function with no
    mutant costs nothing and is always measured.
    """
    everything = names_for_functions(functions, metas)
    if budget is None or len(everything.names) <= budget:
        return Budgeted(measured=everything, left=(), budget=budget)
    room = budget
    taken: set[int] = set()
    for index in sorted(range(len(everything.counts)), key=lambda k: -everything.counts[k][2]):
        count = everything.counts[index][2]
        if count <= room:
            taken.add(index)
            room -= count
    chosen = [function for index, function in enumerate(functions) if index in taken]
    left = tuple(count for index, count in enumerate(everything.counts) if index not in taken)
    return Budgeted(measured=names_for_functions(chosen, metas), left=left, budget=budget)


def describe_left(left: Sequence[Left]) -> str:
    """The remainder a capped run did not measure, as one clause; empty for none."""
    if not left:
        return ""
    mutants = sum(count for _, _, count in left)
    named = ", ".join(f"{function} ({count})" for _, function, count in left)
    return f"{mutants} mutant(s) of {len(left)} function(s) not measured, over the budget: {named}"


def write_left(path: Path, left: Sequence[Left]) -> None:
    """Write the remainder one function per line: path, name and count, tab-separated."""
    path.write_text(
        "".join(f"{source}\t{name}\t{count}\n" for source, name, count in left), encoding="utf-8"
    )


def read_left(path: Path) -> tuple[Left, ...]:
    """The remainder :func:`write_left` wrote; a line in another shape is an error."""
    left: list[Left] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3 or not parts[2].isdigit():
            raise AdapterShapeError(f"{path}: {line!r} is not path<TAB>function<TAB>count")
        left.append((parts[0], parts[1], int(parts[2])))
    return tuple(left)


def tests_for_change(plan: Mapping[str, object], pool: Sequence[str]) -> ChosenTests:
    """The changed nodes' bound and tag-selected tests, plus the pool's unplaced files."""
    nodes = [node for node in _json_list(plan.get("nodes")) if isinstance(node, dict)]
    bound = {str(test) for node in nodes for test in _json_list(node.get("bound_tests"))}
    acceptance = {
        str(test) for node in nodes for test in _json_list(node.get("acceptance_tests"))
    } - bound
    unplaced = {str(test) for test in _json_list(plan.get("unplaced_tests"))}
    fallback = {test for test in pool if test in unplaced} - bound - acceptance
    return ChosenTests(
        bound=tuple(sorted(bound)),
        acceptance=tuple(sorted(acceptance)),
        fallback=tuple(sorted(fallback)),
        unplaced=len(unplaced),
    )


def describe_tests(chosen: ChosenTests, plan: Mapping[str, object]) -> str:
    """The population line: every kind chosen, and the self-checks left out."""
    kinds = plan.get("other_kinds")
    self_checks = kinds.get(_SELF_CHECK_KIND, 0) if isinstance(kinds, dict) else 0
    return (
        f"Tests: {len(chosen.files)} file(s) — {len(chosen.bound)} bound to the changed "
        f"node(s), {len(chosen.acceptance)} acceptance step file(s) by the @node tags of "
        f"their scenarios, {len(chosen.fallback)} of {chosen.unplaced} unplaced file(s) "
        f"from the pool as the FALLBACK; {self_checks} self-check file(s) excluded, "
        f"because they test this repository's files rather than the changed code"
    )


def _json_list(value: object) -> list[object]:
    """*value* when the plan holds a list there, else nothing."""
    return list(value) if isinstance(value, list) else []


def with_selection(pyproject: str, tests: Sequence[str]) -> str:
    """*pyproject* with its per-run selection replaced by *tests* and nothing else."""
    entries = "".join(f'    "{test}",\n' for test in tests)
    replacement = f"{SELECTION_KEY} = [\n{entries}]"
    rewritten, count = _SELECTION_ARRAY.subn(lambda _: replacement, pyproject, count=1)
    if count != 1:
        raise AdapterShapeError(f"pyproject.toml has no `{SELECTION_KEY} = [...]` array")
    return rewritten


def sample_names(
    metas: Mapping[str, Mapping[str, int | None]], size: int, seed: str
) -> tuple[str, ...]:
    """*size* names drawn from the whole scope: sorted names, ``random.Random(seed)``."""
    everything = sorted(name for names in metas.values() for name in names)
    if size >= len(everything):
        return tuple(everything)
    return tuple(sorted(random.Random(seed).sample(everything, size)))  # noqa: S311 - a sample, not a secret


def count_names(
    names: Sequence[str],
    metas: Mapping[str, Mapping[str, int | None]],
    status_of: Mapping[int | None, str],
) -> Counted:
    """Classify exactly *names*; a name no ``.meta`` holds is an error, not a zero."""
    source_of = {name: source for source, codes in metas.items() for name in codes}
    counters = dict.fromkeys(_COUNTER_NAMES, 0)
    survivors: list[dict[str, str]] = []
    for name in names:
        if name not in source_of:
            raise AdapterShapeError(f"{name} is in no .meta file under {MUTANTS}/")
        status = status_of.get(metas[source_of[name]][name], "suspicious").replace(" ", "_")
        counters[status] = counters.get(status, 0) + 1
        if status == "survived":
            survivors.append({"path": source_of[name], "mutant": name})
    counters["total"] = len(names)
    return Counted(counters=counters, survivors=tuple(survivors))


def mutmut_status_table() -> Mapping[int | None, str]:
    """mutmut's own exit-code classification, read from the installed runner.

    Importing it loads mutmut's configuration from the current directory, so
    call it from the project root.
    """
    import importlib

    for home in _STATUS_TABLE_HOMES:
        try:
            module = importlib.import_module(home)
        except ImportError:
            continue
        table = getattr(module, "status_by_exit_code", None)
        if table is not None:
            return dict(table)
    raise AdapterShapeError(f"no status_by_exit_code in {_STATUS_TABLE_HOMES}")


def runner_executable() -> str:
    """The ``mutmut`` beside this interpreter, else the one on PATH."""
    beside = Path(sys.executable).with_name("mutmut")
    if beside.is_file():
        return str(beside)
    found = shutil.which("mutmut")
    if found is None:
        raise AdapterShapeError("mutmut is not installed (the `mutation` extra)")
    return found


def judge(selected: int, stats: Path, left: Sequence[Left] = ()) -> tuple[str, str]:
    """``judged`` when every selected mutant has a verdict, else ``silent`` and why.

    *left* is what a capped run did not measure: the verdict is over the selected
    mutants alone, and the detail names the remainder whatever the verdict.
    """
    verdict, detail = _verdict(selected, stats)
    remainder = describe_left(left)
    return verdict, f"{detail}; {remainder}" if remainder else detail


def _verdict(selected: int, stats: Path) -> tuple[str, str]:
    """The verdict over the selected mutants and its reason."""
    try:
        data = json.loads(stats.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    if not isinstance(data, dict):
        return "silent", "the counters were never written, so this run judged nothing"
    total, unrun = data.get("total"), data.get("not_checked")
    if not isinstance(total, int) or not isinstance(unrun, int):
        return "silent", "the counters carry no mutant total or no not-checked count"
    if selected == 0 or total == 0:
        return "silent", "0 mutants were selected, so there was nothing to judge"
    if total != selected:
        return "silent", f"the counters cover {total} of {selected} selected mutants"
    if unrun:
        return "silent", (
            f"{unrun} of {selected} selected mutants never ran, so the score is a "
            f"ratio over the part the run reached"
        )
    if data.get("check_was_interrupted_by_user"):
        return "silent", "the run was interrupted, so its counters cover part of it"
    shown = ("killed", "survived", "timeout", "no_tests")
    classes = ", ".join(f"{name} {data.get(name, 0)}" for name in shown)
    return "judged", f"{total} mutant(s) judged: {classes}"


def prepare_mutants(root: Path) -> Path:
    """Generate the mutants and run the stats pass, through mutmut's command line.

    The run is ASKED to stop: it names a mutant that does not exist, so mutmut
    refuses the filter after saving its stats. Preparation is judged by what it
    left, not by its exit code: the stats file and at least one ``.meta``. A
    stats pass that failed leaves no stats file and is reported with mutmut's
    own last lines.
    """
    result = subprocess.run(  # noqa: S603 - the installed runner, a fixed argv
        [runner_executable(), "run", "--max-children", str(_PREPARE_CHILDREN), _NO_SUCH_MUTANT],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    mutants = root / MUTANTS
    if not (mutants / _STATS_FILE).is_file() or not any(mutants.rglob(f"*.py{META_SUFFIX}")):
        tail = "\n".join((result.stdout + result.stderr).splitlines()[-_QUOTED_LINES:])
        raise AdapterShapeError(
            f"mutmut left no {_STATS_FILE} or no .meta, so its stats pass over the "
            f"selection did not complete (exit {result.returncode}):\n{tail}"
        )
    return root


def _pool(pyproject: str) -> list[str]:
    if sys.version_info >= (3, 11):
        from tomllib import loads
    else:
        from tomli import loads

    entries = loads(pyproject)["tool"]["mutmut"][SELECTION_KEY]
    return [str(entry) for entry in entries]


def _say(text: str) -> None:
    """One line of this command's output, which is what the workflow shows."""
    sys.stdout.write(f"{text}\n")


def _outputs(path: str | None, **values: object) -> None:
    if path is None:
        return
    with Path(path).open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")


def _select(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    plan = payload.get("change", payload)
    names_out = Path(args.names_out)
    if plan.get("empty", not plan.get("functions")):
        names_out.write_text("", encoding="utf-8")
        _outputs(args.github_output, mutants=0)
        _say("Population: empty — the change touches no function of the declared scope")
        return 0
    root = Path.cwd()
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    chosen = tests_for_change(plan, _pool(text))
    if not chosen.files:
        _say(
            "Refused: no test to run the change's mutants against — the binding ties "
            "no test to the changed nodes, no scenario names them, and no pool file "
            "is left unplaced. An empty selection would run the whole suite, which "
            "does not fit mutants/."
        )
        return 1
    pyproject.write_text(with_selection(text, chosen.files), encoding="utf-8")
    _say(describe_tests(chosen, plan))
    functions = list(plan["functions"])
    budgeted = budgeted_names(functions, read_metas(prepare_mutants(root)), args.budget)
    picked = budgeted.measured
    for path, function, count in picked.counts:
        _say(f"  {function} ({path}): {count} mutant(s)")
    for path, function, count in budgeted.left:
        _say(f"  not measured: {function} ({path}), {count} mutant(s)")
    names_out.write_text("".join(f"{name}\n" for name in picked.names), encoding="utf-8")
    if args.left_out:
        write_left(Path(args.left_out), budgeted.left)
    unmeasured = sum(count for _, _, count in budgeted.left)
    _outputs(
        args.github_output,
        mutants=len(picked.names),
        tests=len(chosen.files),
        unmeasured=unmeasured,
    )
    _say(_population(budgeted))
    return 0


def _population(budgeted: Budgeted) -> str:
    """The population line: what is measured and, for a capped run, what is not."""
    picked = budgeted.measured
    if not budgeted.left:
        if not picked.names:
            return "Population: 0 mutants — mutmut generated none for the changed functions"
        return f"Population: {len(picked.names)} mutant(s) of {len(picked.counts)} function(s)"
    unmeasured = sum(count for _, _, count in budgeted.left)
    whole = len(picked.names) + unmeasured
    functions = len(picked.counts) + len(budgeted.left)
    return (
        f"Population: {len(picked.names)} of {whole} mutant(s) of {functions} function(s) "
        f"measured, in {len(picked.counts)} function(s) — the budget of {budgeted.budget} "
        f"mutants this job's time holds; {describe_left(budgeted.left)}"
    )


def _sample(args: argparse.Namespace) -> int:
    metas = read_metas(prepare_mutants(Path.cwd()))
    population = sum(len(names) for names in metas.values())
    names = sample_names(metas, args.size, args.seed)
    Path(args.names_out).write_text("\n".join(names) + "\n", encoding="utf-8")
    _outputs(args.github_output, population=population, size=len(names), seed=args.seed)
    _say(f"Sample: {len(names)} of {population} mutants, seed {args.seed!r}")
    return 0


def _read_names(path: str) -> tuple[str, ...]:
    return tuple(line for line in Path(path).read_text(encoding="utf-8").split() if line)


def _counters(args: argparse.Namespace) -> int:
    counted = count_names(_read_names(args.names), read_metas(Path.cwd()), mutmut_status_table())
    Path(args.stats_out).write_text(json.dumps(counted.counters, indent=2), encoding="utf-8")
    survivors = json.dumps(list(counted.survivors), indent=2)
    Path(args.survivors_out).write_text(survivors, encoding="utf-8")
    _say(", ".join(f"{name} {value}" for name, value in counted.counters.items() if value))
    return 0


def _judge(args: argparse.Namespace) -> int:
    left = read_left(Path(args.left)) if args.left else ()
    verdict, detail = judge(len(_read_names(args.names)), Path(args.stats), left)
    _say(f"verdict={verdict}")
    _say(f"detail={detail}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    select = commands.add_parser("select", help="exact names of a change's mutants")
    select.add_argument("--plan", required=True)
    select.add_argument("--names-out", required=True)
    select.add_argument("--github-output")
    select.add_argument("--budget", type=int, help="the most mutants the run measures")
    select.add_argument("--left-out", help="where the functions over the budget are written")
    select.set_defaults(handler=_select)

    sample = commands.add_parser("sample", help="a seeded random sample of the scope")
    sample.add_argument("--size", type=int, required=True)
    sample.add_argument("--seed", required=True)
    sample.add_argument("--names-out", required=True)
    sample.add_argument("--github-output")
    sample.set_defaults(handler=_sample)

    counters = commands.add_parser("counters", help="counters over exactly the names run")
    counters.add_argument("--names", required=True)
    counters.add_argument("--stats-out", required=True)
    counters.add_argument("--survivors-out", required=True)
    counters.set_defaults(handler=_counters)

    verdict = commands.add_parser("judge", help="judged or silent, for the announcement")
    verdict.add_argument("--names", required=True)
    verdict.add_argument("--stats", required=True)
    verdict.add_argument("--left", help="the functions a capped run did not measure")
    verdict.set_defaults(handler=_judge)

    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
