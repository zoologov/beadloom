"""One table over `init`'s entry points, its modes and the renderer that will run.

BDL-067 `.19`, covering `.17` and `.18`. THE MEASUREMENT THIS MODULE EXISTS FOR:
the suite already enumerates BRANCHES (`.7`) and then MODES (`.15`), and the fifth
review still returned four majors — three of them on axes no enumeration covered.
Which branch withdraws the completion claim, which renderer the quoted `ci` line
matches, and which run wrote the failing node are three questions, and every
enumeration in this epic answered one of them while holding the other two fixed.

So this is not a third one-axis enumeration. Every module before it varies one axis
with the rest constant; this one varies the CELL and measures the rest:

    `.7`   varies the branch, at one mode, over the source rather than the command.
    `.15`  varies the mode, over two entry points, with one divergence per writer.
    `.17`  varies the ATTRIBUTION CORNER, one entry point per corner.
    here   varies (entry point x mode), and measures the corner, the withdrawal and
           the renderer in each cell.

WHAT IS NOT REPEATED HERE. The corner axis is `.17`'s and is not re-enumerated: the
cells below reach three of its four corners as a consequence of what each run does,
and `(graph theirs, rules ours)` is reached by no cell and stays `.17`'s alone. The
`--yes` re-init exclusion is `.17`'s too and is restated below only as this table's
applicability predicate, over all four entry points rather than over `--yes`. The
sabotage, the modes, the renderer list, the bindings, the graph reader and the
bootstrapping-mode list are imported from the two sibling modules rather than
written again, so a reword moves one place.

THE AXES, AND WHY THEY ARE NOT A RAW CROSS. `init` has four branches that write a
graph file, and `tests/test_init_branches_that_reach_the_bootstrap.py` finds them in
the command's own source: `('non_interactive',)`, `('bootstrap',)`, `('import_path',)`
and the fallthrough wizard. Two of them take a `--mode`; the other two declare one
mode each by which writers they call, and that claim is checked against the writers
found under their guard rather than asserted. Eight cells, and a fifth branch or a
fourth mode fails `TestTheTableIsTheCommandsOwnShape` instead of going untested.

THE INVARIANTS, one per class, asserted in every cell the arrangement reaches:

  1. No run that wrote a graph file terminates 0 over a graph failing the rules on
     disk (`TestNoCellReportsSuccessOverAFailingTree`).
  2. A success claim is withdrawn wherever one was made before a failing verdict
     (`TestEveryCellWithdrawsTheClaimItMade`).
  3. The bug-report request appears exactly where THIS run wrote both the rules and
     the graph file the failing node came from (`TestTheBugReportIsAskedForWhereThe
     RunWroteBoth`). Whether the run wrote them is MEASURED off the directory by
     this module's own digest, not read from the report and not taken from the
     product's instrument -- see `_the_graph_directory_now`.
  4. The shape quoted from `beadloom ci` matches what `ci` emits in every renderer
     it can choose (`TestEveryCellPromisesWhatEveryRendererPrints`).
  5. The entry points that offer one declared mode leave one graph
     (`TestTheEntryPointsLeaveOneGraphForOneDeclaredMode`).

THE FINDING THIS TABLE PRODUCED, and what closed it. On a tree that already carried a
graph file an earlier run left, `beadloom init --bootstrap` and the wizard answering
`bootstrap` left DIFFERENT graphs. Measured on a project with `.beadloom/_graph/
legacy.yml` holding one service root and one domain `ledger`:

    only `--bootstrap` left:  ledger with no `docs:` field
    only the wizard left:     ledger with docs: ['docs/domains/ledger/README.md'],
                              and that file, and `ledger` in the Domains table of
                              docs/architecture.md

The cause was one argument. The `--bootstrap` branch called `generate_skeletons(root,
result["nodes"], result["edges"])`; the other callers call `generate_skeletons(root)`
with no node list, so they write skeletons for every node on disk. That is BDL-UX #216
-- the divergence `.18` closed on `non_interactive_init` -- standing on the third
entry point. This table recorded it rather than asserting it away, because closing it
was a behaviour change and `.19` was a test bead; the review of `.20` raised it as a
major and BDL-067 `.21` closed it by taking the parameter off the function rather than
by editing the third call site, since a document about the whole tree that can be
handed part of the tree is a defect one caller at a time. The case that measures it is
`test_every_branch_leaves_the_same_thing_on_a_tree_it_did_not_start`, and the case that
prevents the next caller is `test_the_skeleton_writer_cannot_be_handed_a_subset_of_the
_tree`. Both were measured red before the parameter came off: the docs differed by
`docs/domains/ledger/README.md` and the architecture document by whether it named
`ledger` at all.

RED PROVED, not asserted. Each invariant was measured against a tree without the fix
it covers, one single-edit mutant of `services/commands/setup.py` at a time, and each
mutant is the shape the code had before `.17`:

    the withdrawal printed only where this run wrote the rules
        -> 10 failures, all five cells of the inherited arrangement
    one boolean about `rules.yml` choosing both halves of the headline
        -> 4 failures, the two cells where the two facts disagree
    the report quoting `gate_step_line` instead of stating the step's two facts
        -> 10 failures, one per cell, under `rich` and under no other renderer
    the `--import` branch deferring its verdict
        -> 7 failures, all in the `--import` cell, across four of the five classes

INVARIANT 5 at `--mode both` was measured against the tree at `52f52ae^` -- `.18`
reverted, everything else present -- where `--yes` and the wizard leave graphs that
differ by three nodes, and it fails there and passes here. The module as a whole
cannot be imported at `8d87735^`: `_ATTRIBUTION`, `_GRAPH_HALF` and `_RULES_HALF` do
not exist before `.17`, which is a proof of binding and not a proof of any one case,
which is why the mutants above were run instead.

WHAT CANNOT FAIL AGAINST A PRE-FIX TREE, declared because a case that guards the
future is worth keeping and worth not mistaking for evidence:

  - `TestTheTableIsTheCommandsOwnShape` and `TestTheCellsNoArrangementReaches` are
    claims about `init`'s shape and about this table's own coverage. They fail on a
    fifth branch, a fourth mode, a one-mode branch that grew a second writer, or a
    cell quietly losing its arrangement -- none of which any pre-fix tree has.
  - `TestWhichBranchesCanMeetAFileTheyDidNotWrite` measures re-init behaviour that
    `.17` and `.18` did not touch. It is the applicability predicate, and it guards
    the predicate rather than the fix.
  - `TestTheTableExercisesBothAnswersOfBothHalves` is anti-vacuity for INVARIANT 3
    over the table. It survives the one-boolean mutant, because that mutant keeps
    both answers occurring while attaching them to the wrong cells -- which is what
    the per-cell cases catch and this one deliberately does not.
  - `test_the_renderer_prints_the_two_facts_the_report_promised` is about
    `_format_gate`, not about `init`. Every renderer already printed the step's name
    and summary before `.17`; what `.17` changed is what the report says about them.
    It is the half that makes "quotes no renderer's line" a promise rather than a
    prohibition, and it fails if a renderer stops printing the summary.
  - INVARIANT 5 at `bootstrap` and at `import` passes at `52f52ae^` as well: those
    two modes agreed before `.18` and still do. Only `both` distinguishes the fix;
    the other two guard the third branch against the next divergence.

The fixture is a project that is not us (`orders-web`, a flat `src/index.ts` plus two
documents the classifier cannot place), so a verdict that worked by recognising
Beadloom's own tree would fail these.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.application.gate import GateResult, GateStep, lint_step
from beadloom.onboarding.doc_generator import generate_skeletons
from beadloom.services.cli import main
from beadloom.services.commands.federation import _format_gate
from beadloom.services.commands.setup import (
    _ATTRIBUTION,
    _GRAPH_HALF,
    _RULES_HALF,
    WITHDRAWN_COMPLETION_CLAIM,
)

# Every axis and every instrument below is the siblings', imported rather than
# rewritten. Two derivations of one fact drift, and this epic has already paid
# for that twice: `.6` for two bindings counted as two branches, and `.17` for a
# `THE_MODES` that had begun to exist in two modules.
from tests.test_init_agrees_across_its_modes import (
    THE_BOOTSTRAP_FILE,
    THE_MODES_THAT_BOOTSTRAP,
    _a_project_with_code_and_docs,
    _graph_on_disk,
)
from tests.test_init_branches_that_reach_the_bootstrap import (
    THE_GRAPH_COMMIT_POINT,
    _call_sites_in,
    _callables_that_reach,
    _the_commands_source,
)
from tests.test_init_report_says_whose_failure_it_is import (
    A_DOMAIN_RULE_THE_ADOPTER_WROTE,
)
from tests.test_init_verdict_over_its_own_rules import (
    THE_BRANCHES,
    THE_BUG_REPORT_REQUEST,
    THE_FAILURE_REPORT,
    THE_GATE_FORMATS,
    THE_MODES,
    THE_RULE,
    _a_bootstrap_that_forgets_the_edge,
    _lint_strict,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from _pytest.tmpdir import TempPathFactory

#: The rules file, by the name every cell has to be judged against. The only
#: constant this module declares for itself: the two sibling modules spell it as
#: part of a path, and what is needed here is the bare file name the digest keys
#: on.
THE_RULES_FILE = "rules.yml"

#: A graph file no writer in the product knows about, holding what an earlier run
#: can leave: a root the import step can attach to, and one domain with no
#: parent. Named `legacy.yml` so that neither `bootstrap_project` (which writes
#: `services.yml`) nor `import_docs` (which writes `imported.yml`) rewrites it as
#: a whole -- what may still touch it is `generate_skeletons`, and whether it did
#: is the fact this table measures rather than assumes.
THE_INHERITED_FILE = "legacy.yml"

#: The unparented domain in it, which is the node every cell of the inherited
#: arrangement is red over. Named for the file it sits in rather than
#: `THE_INHERITED_ORPHAN`, which is `.17`'s name for a different node in a
#: different file: one name for two nodes is how a reader stops noticing which
#: one a case is about.
THE_ORPHAN_IN_THE_INHERITED_FILE = "ledger"

AN_INHERITED_GRAPH = {
    "nodes": [
        {
            "ref_id": "orders-web",
            "kind": "service",
            "summary": "The root an earlier run wrote.",
        },
        {
            "ref_id": THE_ORPHAN_IN_THE_INHERITED_FILE,
            "kind": "domain",
            "summary": "Left by an earlier run, with no parent.",
        },
    ]
}

@dataclass(frozen=True)
class EntryPoint:
    """One branch of `init` that writes a graph file, and the modes it declares.

    `guard` is the branch's identity as `init`'s own source spells it, and it is
    what binds this table to `tests/test_init_branches_that_reach_the_bootstrap.
    py`'s enumerator. A branch is not a binding and not a flag spelling: `.6`
    exists because two bindings were counted as two branches for four waves while
    the branch a human adopter meets first went unjudged.
    """

    #: How it is spelled on the command line, for the test id. The three that
    #: reach the bootstrap use the names `THE_BRANCHES` uses, so the sabotage
    #: binding can be looked up there instead of restated here.
    name: str
    #: The `if` conditions the branch sits under, outermost first, as the source
    #: spells them. The empty tuple is the fallthrough wizard.
    guard: tuple[str, ...]
    #: Every mode this branch can be asked for. Two branches take `--mode` and
    #: offer whatever the flag offers; the other two declare one mode each, and
    #: `test_a_fixed_mode_branch_declares_the_mode_its_writers_are` checks that
    #: declaration against the writers found under the guard.
    modes: tuple[str, ...]
    #: Whether this branch can WRITE a graph file in a run that also meets one
    #: it did not write. `--yes` is the one that cannot, and it fails both halves
    #: rather than one: without `--force` `non_interactive_init` returns
    #: `skipped`, so the inherited file survives a run that wrote nothing, and
    #: with `--force` the directory is deleted before anything runs. Measured
    #: over every branch in `TestWhichBranchesCanMeetAFileTheyDidNotWrite`, as
    #: the conjunction rather than as either half.
    can_meet_a_file_it_did_not_write: bool

    def argv(self, mode: str, project_root: Path) -> tuple[str, ...]:
        if self.name == "--yes":
            return ("--yes", "--mode", mode)
        if self.name == "--bootstrap":
            return ("--bootstrap",)
        if self.name == "--import":
            return ("--import", str(project_root / "docs"))
        return ()

    def prompts(self, mode: str, *, reinit: bool) -> tuple[str, ...]:
        """The wizard's answers, in order; empty for the branches that ask none.

        The re-init answer comes first when `.beadloom/` is already there:
        `overwrite` keeps the directory and the files inside it, which is what
        makes the wizard able to meet a rules file it did not write. The graph
        review is asked only when the run produced nodes to review, so only the
        modes that bootstrap answer it, and the answer is always `yes` -- `edit`
        is the one answer that takes no verdict and it is the sibling module's.
        """
        if self.name != "wizard":
            return ()
        answers = ["overwrite"] if reinit else []
        answers.append(mode)
        if mode in THE_MODES_THAT_BOOTSTRAP:
            answers.append("yes")
        return tuple(answers)


#: Every branch of `init` that writes a graph file, with the modes it offers.
#: `--bootstrap` and `--import` are branches with one mode rather than flags with
#: none: each calls exactly one node-creating writer, and that is what makes the
#: cell count 8 rather than 12.
THE_ENTRY_POINTS = (
    EntryPoint(
        "--yes", ("non_interactive",), THE_MODES, can_meet_a_file_it_did_not_write=False
    ),
    EntryPoint(
        "--bootstrap", ("bootstrap",), ("bootstrap",), can_meet_a_file_it_did_not_write=True
    ),
    EntryPoint(
        "--import", ("import_path",), ("import",), can_meet_a_file_it_did_not_write=True
    ),
    EntryPoint("wizard", (), THE_MODES, can_meet_a_file_it_did_not_write=True),
)

#: The branches whose mode is fixed by the flag rather than chosen, and the
#: writer each one's declared mode implies. `bootstrap_project` is the writer of
#: `services.yml` and `import_docs` the writer of `imported.yml`; a branch whose
#: guard reaches neither, or both, is not the single-mode branch it is listed as.
THE_WRITER_A_MODE_IMPLIES = {
    "bootstrap": "bootstrap_project",
    "import": "import_docs",
}

#: The binding of `bootstrap_project` each branch reaches, taken from the sibling
#: module's `THE_BRANCHES` rather than restated: the wizard and `--yes` share one
#: and `--bootstrap` has its own, which is the confusion `.6` was written for and
#: the one `.17` found still sitting in the acceptance fixture.
THE_BINDING_OF = {branch.name: branch.binding for branch in THE_BRANCHES}


@dataclass(frozen=True)
class Cell:
    """One (entry point, mode) the command offers."""

    entry: EntryPoint
    mode: str

    @property
    def name(self) -> str:
        return f"{self.entry.name}-{self.mode}"

    @property
    def writes_its_own_rules(self) -> bool:
        """Whether this cell's run authors `rules.yml`.

        Only `bootstrap_project` writes rules, so only the modes that bootstrap
        can contradict a rule of their own. The list is the sibling module's, and
        it checks itself against the files each mode leaves.
        """
        return self.mode in THE_MODES_THAT_BOOTSTRAP


#: The table: every mode every branch offers.
THE_TABLE = tuple(
    Cell(entry, mode) for entry in THE_ENTRY_POINTS for mode in entry.modes
)


def _the_graph_directory_now(project_root: Path) -> dict[str, str]:
    """Digest every graph YAML under `.beadloom/_graph/`, by file name.

    Deliberately NOT `setup._graph_files_now`, which is the product's own
    instrument and is what the report's attribution is computed from. A check
    that reuses the instrument under test agrees with it by construction and
    cannot fail when it is wrong, which is the whole reason the report's
    attribution is measured here rather than read back.

    Two limitations, stated because a digest that says nothing about them is a
    check somebody will over-read. A rewrite that reproduces the previous bytes
    exactly reads as "not written" -- true of an idempotent patch -- and a file
    that cannot be read is skipped rather than counted as changed.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    digests: dict[str, str] = {}
    if not graph_dir.is_dir():
        return digests
    for path in sorted(graph_dir.glob("*.yml")):
        try:
            digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return digests


@dataclass(frozen=True)
class Arrangement:
    """A tree that fails its rules, and which file the failing node is in.

    Two of them, and they differ in whose the contradiction is rather than in
    what breaks: the rule is `domain-needs-parent` and the violation is a domain
    with no `part_of` edge in both. What varies is who wrote them, which is the
    fact the report has to get right and the only one an adopter can check.
    """

    #: How it is spelled, for the test id.
    name: str
    #: Builds the tree the run will meet. Returns the project root.
    arrange: Callable[[Path], Path]
    #: The sabotage, if any, applied for the duration of the run.
    sabotage: Callable[[pytest.MonkeyPatch, Cell], None] | None
    #: The graph file holding the node that fails. Declared by the arrangement
    #: because the arrangement puts it there; whether THIS RUN wrote that file is
    #: measured, never declared.
    the_file_the_failing_node_is_in: str
    #: Whether `.beadloom/` is already there when the run starts, which is the
    #: wizard's extra prompt and the reason `--yes` cannot reach this one.
    reinit: bool
    #: The cells this arrangement can make red.
    applies_to: Callable[[Cell], bool]


def _a_virgin_project(tmp_path: Path) -> Path:
    return _a_project_with_code_and_docs(tmp_path)


def _a_project_carrying_an_earlier_runs_graph(tmp_path: Path) -> Path:
    """The same project, plus a rules file and a graph file it did not write.

    Nothing is patched. `bootstrap_project` leaves the rules file alone because
    one is already there, `import_docs` writes `imported.yml` and attaches its
    nodes to the single service root this file provides, and `ledger` is left
    unparented by every writer because no writer knows about the file it is in.
    """
    project = _a_project_with_code_and_docs(tmp_path)
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    # `.17`'s hand-written `domain-needs-parent`, imported rather than written a
    # second time: it is the same requirement `generate_rules` emits, so what
    # this fixture varies is who wrote it and nothing else, and two copies of one
    # rules file would drift into varying more than that.
    (graph_dir / THE_RULES_FILE).write_text(
        A_DOMAIN_RULE_THE_ADOPTER_WROTE, encoding="utf-8"
    )
    (graph_dir / THE_INHERITED_FILE).write_text(
        yaml.safe_dump(AN_INHERITED_GRAPH, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return project


def _the_bootstrap_forgets_the_edge(monkeypatch: pytest.MonkeyPatch, cell: Cell) -> None:
    """The sibling module's sabotage, on the binding this cell's branch reaches."""
    _a_bootstrap_that_forgets_the_edge(monkeypatch, THE_BINDING_OF[cell.entry.name])


THE_ARRANGEMENTS = (
    Arrangement(
        name="ours",
        arrange=_a_virgin_project,
        sabotage=_the_bootstrap_forgets_the_edge,
        the_file_the_failing_node_is_in=THE_BOOTSTRAP_FILE,
        reinit=False,
        applies_to=lambda cell: cell.writes_its_own_rules,
    ),
    Arrangement(
        name="theirs",
        arrange=_a_project_carrying_an_earlier_runs_graph,
        sabotage=None,
        the_file_the_failing_node_is_in=THE_INHERITED_FILE,
        reinit=True,
        applies_to=lambda cell: cell.entry.can_meet_a_file_it_did_not_write,
    ),
)

#: Every (cell, arrangement) that can produce a red tree. Filtered rather than
#: skipped, for `.15`'s reason: a skip is a case reporting itself as not run, and
#: the cells no arrangement reaches are asserted as a set in
#: `TestTheCellsNoArrangementReaches` instead of disappearing quietly.
THE_RED_RUNS = tuple(
    (cell, arrangement)
    for cell in THE_TABLE
    for arrangement in THE_ARRANGEMENTS
    if arrangement.applies_to(cell)
)

RED_RUN_IDS = [f"{cell.name}-{arr.name}" for cell, arr in THE_RED_RUNS]


@dataclass(frozen=True)
class RunOutcome:
    """One completed run, and the two facts the report's attribution rests on."""

    project_root: Path
    exit_code: int
    output: str
    #: Whether this run wrote the file holding the node that fails.
    wrote_the_failing_graph_file: bool
    #: Whether this run wrote `rules.yml`.
    wrote_the_rules_file: bool
    #: Whether this run wrote any graph file at all. A run that wrote none did
    #: not meet the tree it was pointed at -- it refused it.
    wrote_a_graph_file: bool

    @property
    def corner(self) -> tuple[bool, bool]:
        return (self.wrote_the_failing_graph_file, self.wrote_the_rules_file)


def _answering(cell: Cell, *, reinit: bool) -> Any:
    from contextlib import nullcontext
    from unittest.mock import patch

    prompts = cell.entry.prompts(cell.mode, reinit=reinit)
    if not prompts:
        return nullcontext()

    class _Answers:
        def __enter__(self) -> None:
            self._prompt = patch("rich.prompt.Prompt.ask", side_effect=list(prompts))
            # Accepted rather than declined: `--yes` has no such prompt and always
            # generates, so a declining wizard would be compared against a run
            # that did strictly more work (`.18`).
            self._confirm = patch("rich.prompt.Confirm.ask", return_value=True)
            self._prompt.start()
            self._confirm.start()

        def __exit__(self, *exc: object) -> None:
            self._confirm.stop()
            self._prompt.stop()

    return _Answers()


def _perform(project_root: Path, cell: Cell, arrangement: Arrangement) -> RunOutcome:
    """Run one cell over one arrangement, measuring what it wrote as it goes."""
    before = _the_graph_directory_now(project_root)
    with pytest.MonkeyPatch.context() as monkeypatch:
        if arrangement.sabotage is not None:
            arrangement.sabotage(monkeypatch, cell)
        with _answering(cell, reinit=arrangement.reinit):
            result = CliRunner().invoke(
                main,
                [
                    "init",
                    *cell.entry.argv(cell.mode, project_root),
                    "--project",
                    str(project_root),
                ],
            )
    after = _the_graph_directory_now(project_root)

    def written(name: str) -> bool:
        return before.get(name) != after.get(name)

    return RunOutcome(
        project_root=project_root,
        exit_code=result.exit_code,
        output=str(result.output),
        wrote_the_failing_graph_file=written(arrangement.the_file_the_failing_node_is_in),
        wrote_the_rules_file=written(THE_RULES_FILE),
        wrote_a_graph_file=any(
            before.get(name) != after.get(name) for name in before | after
        ),
    )


@pytest.fixture(scope="module")
def red_runs(tmp_path_factory: TempPathFactory) -> Iterator[dict[str, RunOutcome]]:
    """Every red run in the table, performed once and read many times.

    Module-scoped because a cell costs a full `init` -- a bootstrap, an import, a
    doc generation and a reindex -- and the cases below read the same completed
    run from several angles. Each case reads an immutable record and a tree
    nothing writes to afterwards, so order still does not matter; what is shared
    is the cost, not the state.
    """
    performed: dict[str, RunOutcome] = {}
    for (cell, arrangement), run_id in zip(THE_RED_RUNS, RED_RUN_IDS, strict=True):
        root = arrangement.arrange(tmp_path_factory.mktemp(run_id.replace("-", "_")))
        performed[run_id] = _perform(root, cell, arrangement)
    yield performed


@pytest.fixture(scope="module")
def failing_steps(red_runs: dict[str, RunOutcome]) -> dict[str, GateStep]:
    """The Gate's own step for each red tree, which is what `ci` will render."""
    return {
        run_id: lint_step(outcome.project_root) for run_id, outcome in red_runs.items()
    }


class TestTheTableIsTheCommandsOwnShape:
    """The axes are derived and bound, so a fifth branch fails instead of hiding.

    A hand-written axis is the shape this epic came from: a comment calling two
    bindings "the two ways `init` reaches the bootstrap" was believed for four
    waves. Every claim the table makes about `init`'s shape is checked against
    `init`'s source here before anything is run over it.
    """

    def test_the_entry_points_are_the_branches_that_write_a_graph_file(self) -> None:
        """`.7`'s enumerator finds the branches; this table must be those branches."""
        import beadloom

        writing = _callables_that_reach(beadloom, THE_GRAPH_COMMIT_POINT)
        sites = _call_sites_in(_the_commands_source(), writing)

        assert {site.guard for site in sites} == {
            entry.guard for entry in THE_ENTRY_POINTS
        }, sorted({site.guard for site in sites})

    def test_the_axis_is_not_empty(self) -> None:
        """Anti-vacuity: a derivation that found nothing would collect no cases."""
        assert len(THE_ENTRY_POINTS) == 4, THE_ENTRY_POINTS
        assert len(THE_TABLE) == 8, [cell.name for cell in THE_TABLE]

    def test_every_mode_the_flag_offers_has_a_cell(self) -> None:
        """A fourth `--mode` joins the table on the day it is declared."""
        assert {cell.mode for cell in THE_TABLE} == set(THE_MODES), THE_MODES

    @pytest.mark.parametrize(
        "entry",
        [e for e in THE_ENTRY_POINTS if len(e.modes) == 1],
        ids=[e.name for e in THE_ENTRY_POINTS if len(e.modes) == 1],
    )
    def test_a_fixed_mode_branch_declares_the_mode_its_writers_are(
        self, entry: EntryPoint
    ) -> None:
        """`--bootstrap` is mode `bootstrap` because of what it calls, not by name.

        A branch listed with one mode is a claim that it runs that mode's writer
        and not the other's. Read off the call sites under its guard, so a branch
        that grew a second writer stops being a one-mode cell here rather than
        being tested as one.
        """
        import beadloom

        writing = _callables_that_reach(beadloom, THE_GRAPH_COMMIT_POINT)
        under_the_guard = {
            site.callee
            for site in _call_sites_in(_the_commands_source(), writing)
            if site.guard == entry.guard
        }
        (mode,) = entry.modes

        assert THE_WRITER_A_MODE_IMPLIES[mode] in under_the_guard, under_the_guard
        others = set(THE_WRITER_A_MODE_IMPLIES.values()) - {
            THE_WRITER_A_MODE_IMPLIES[mode]
        }
        assert not (others & under_the_guard), under_the_guard

    def test_every_branch_that_can_be_sabotaged_has_a_known_binding(self) -> None:
        """The `ours` arrangement patches a binding, so every cell it reaches needs one."""
        needed = {
            cell.entry.name
            for cell, arrangement in THE_RED_RUNS
            if arrangement.sabotage is not None
        }

        assert needed <= set(THE_BINDING_OF), sorted(needed - set(THE_BINDING_OF))


class TestWhichBranchesCanMeetAFileTheyDidNotWrite:
    """`can_meet_a_file_it_did_not_write` is a claim about `init`, measured like one.

    It is this table's applicability predicate: the `theirs` arrangement puts a
    graph file on disk before the run, and the arrangement is only about a branch
    that then WRITES one of its own beside it. So the measurement is the
    conjunction -- the inherited file is still there afterwards AND this run wrote
    a graph file -- and not either half, because `--yes` satisfies the first half
    for the wrong reason: it refuses the tree and writes nothing, leaving the file
    untouched by doing no work at all.

    The `--yes` row restates in one case what
    `TestWhyTheYesBranchCannotMeetAnAdoptersRulesFile` establishes in two (the
    `skipped` return and the `--force` delete). The other three rows are asserted
    nowhere else, and running all four is what makes the predicate checked over
    the axis rather than for the one branch somebody remembered.
    """

    @pytest.mark.parametrize(
        "entry", THE_ENTRY_POINTS, ids=[e.name for e in THE_ENTRY_POINTS]
    )
    def test_the_branch_meets_the_inherited_file_exactly_where_the_table_says(
        self, tmp_path: Path, entry: EntryPoint
    ) -> None:
        project = _a_project_carrying_an_earlier_runs_graph(tmp_path)
        inherited = project / ".beadloom" / "_graph" / THE_INHERITED_FILE
        # Anti-vacuity: the claim below is about a file that was there to survive.
        assert inherited.is_file()

        outcome = _perform(project, Cell(entry, entry.modes[0]), THE_ARRANGEMENTS[1])
        met = inherited.is_file() and outcome.wrote_a_graph_file

        assert met == entry.can_meet_a_file_it_did_not_write, (
            f"{entry.name}: the inherited file is "
            f"{'still there' if inherited.is_file() else 'gone'} and this run "
            f"{'wrote' if outcome.wrote_a_graph_file else 'wrote no'} graph file, "
            f"and the table says can_meet_a_file_it_did_not_write="
            f"{entry.can_meet_a_file_it_did_not_write}"
        )


class TestTheCellsNoArrangementReaches:
    """The empty cells are named, so an untested cell is a decision and not a gap.

    One cell of the eight has no red arrangement at all. `--yes --mode import`
    writes no `rules.yml` -- only `bootstrap_project` writes rules, and that mode
    does not run it -- and it cannot meet one either, because
    `non_interactive_init` returns `skipped` over an existing `.beadloom/` and
    `--force` deletes it. So there is no tree on which that cell can fail its
    rules, and its green is structural rather than lucky. The two halves of that
    reason are asserted in the sibling modules
    (`TestAnImportOnlyRunOnAVirginProjectNamesNoParent` and
    `TestWhyTheYesBranchCannotMeetAnAdoptersRulesFile`); what is asserted here is
    that the set has not silently grown.
    """

    def test_exactly_one_cell_has_no_red_arrangement(self) -> None:
        reached = {cell.name for cell, _ in THE_RED_RUNS}
        unreached = sorted(cell.name for cell in THE_TABLE if cell.name not in reached)

        assert unreached == ["--yes-import"], unreached


@pytest.mark.parametrize(("cell", "arrangement"), THE_RED_RUNS, ids=RED_RUN_IDS)
class TestNoCellReportsSuccessOverAFailingTree:
    """INVARIANT 1. A run that wrote a graph file does not exit 0 over a red tree.

    Stated over the tree the run leaves rather than over the run's own output:
    the claim is agreement with the command the adopter types next, which is what
    BDL-UX #192 was reported as and what `.14` found a verdict failing to do
    while looking present in the source.
    """

    def test_the_tree_the_run_leaves_actually_fails_its_rules(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        """Anti-vacuity: every claim below is about a tree that is red."""
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]

        assert _lint_strict(outcome.project_root) != 0, outcome.output

    def test_the_run_does_not_exit_zero(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]

        assert outcome.exit_code != 0, outcome.output

    def test_it_names_the_rule_the_gate_will_name(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        """Not "something is wrong" -- the string the adopter reads again next."""
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]

        assert THE_RULE in outcome.output, outcome.output


@pytest.mark.parametrize(("cell", "arrangement"), THE_RED_RUNS, ids=RED_RUN_IDS)
class TestEveryCellWithdrawsTheClaimItMade:
    """INVARIANT 2. Wherever a claim was made before a red verdict, it is withdrawn.

    The sibling module asserts this over three branches at one mode and over one
    divergence. Here it is asserted in every cell of the table, which is where
    the axes it holds fixed live: `--yes --mode both`, the `--import` branch and
    every cell of the inherited arrangement are cells no branch enumeration
    reached, and two of the three majors the fifth review returned were about
    which branch does what.
    """

    def test_the_cell_claimed_something_before_the_withdrawal(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        """Anti-vacuity: a run that announced nothing needs no withdrawal."""
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]

        withdrawn = outcome.output.find(WITHDRAWN_COMPLETION_CLAIM)
        assert withdrawn != -1, outcome.output
        announced = [
            line for line in outcome.output[:withdrawn].splitlines() if line.strip()
        ]
        assert announced, (
            f"the {cell.name} cell printed nothing before the withdrawal, so there "
            "is no claim for it to withdraw and this case asserts nothing"
        )

    def test_the_claim_is_withdrawn_before_the_failure_is_reported(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]

        withdrawn = outcome.output.find(WITHDRAWN_COMPLETION_CLAIM)
        reported = outcome.output.find(THE_FAILURE_REPORT)

        assert withdrawn != -1, outcome.output
        assert reported != -1, outcome.output
        assert withdrawn < reported, outcome.output


@pytest.mark.parametrize(("cell", "arrangement"), THE_RED_RUNS, ids=RED_RUN_IDS)
class TestTheBugReportIsAskedForWhereTheRunWroteBoth:
    """INVARIANT 3. The request follows what THIS run wrote, measured off the disk.

    The corner is not declared per cell. Both halves of it are measured by
    digesting `.beadloom/_graph/` before and after the run with this module's own
    hash -- see `_the_graph_directory_now` for why it is not the product's
    instrument -- and the report is then required to agree with the measurement.
    So the case holds whatever a cell turns out to do, and it FAILS if the report
    and the tree disagree, which is the defect the review of `.16` measured: a
    bug report asked for against `import_docs` in a run where `import_docs` had
    not executed.
    """

    def test_the_headline_names_whose_graph_and_whose_rules(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]
        graph_is_ours, rules_are_ours = outcome.corner

        assert _GRAPH_HALF[graph_is_ours] in outcome.output, outcome.output
        assert _RULES_HALF[rules_are_ours] in outcome.output, outcome.output
        assert _GRAPH_HALF[not graph_is_ours] not in outcome.output, outcome.output
        assert _RULES_HALF[not rules_are_ours] not in outcome.output, outcome.output

    def test_the_attribution_sentence_is_the_one_the_measurement_chooses(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]

        assert _ATTRIBUTION[outcome.corner] in outcome.output, outcome.output
        wrong = [
            sentence
            for corner, sentence in _ATTRIBUTION.items()
            if corner != outcome.corner and sentence in outcome.output
        ]
        assert wrong == [], (outcome.corner, wrong, outcome.output)

    def test_the_request_appears_only_where_this_run_wrote_both(
        self,
        red_runs: dict[str, RunOutcome],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        outcome = red_runs[f"{cell.name}-{arrangement.name}"]

        asked = THE_BUG_REPORT_REQUEST in outcome.output
        assert asked == (outcome.corner == (True, True)), (
            outcome.corner,
            outcome.output,
        )


class TestTheTableExercisesBothAnswersOfBothHalves:
    """Anti-vacuity for the invariant above, over the table rather than per case.

    A table in which every run wrote everything would satisfy INVARIANT 3 with
    one branch of the report ever taken, and would call the "only" in "only where
    this run wrote both" untested. These two cases fail if the arrangements stop
    producing both answers.
    """

    def test_both_answers_of_each_half_occur(
        self, red_runs: dict[str, RunOutcome]
    ) -> None:
        corners = [outcome.corner for outcome in red_runs.values()]

        assert {graph for graph, _ in corners} == {True, False}, corners
        assert {rules for _, rules in corners} == {True, False}, corners

    def test_the_request_is_both_made_and_refused_somewhere(
        self, red_runs: dict[str, RunOutcome]
    ) -> None:
        asked = {
            THE_BUG_REPORT_REQUEST in outcome.output for outcome in red_runs.values()
        }

        assert asked == {True, False}


@pytest.mark.parametrize(("cell", "arrangement"), THE_RED_RUNS, ids=RED_RUN_IDS)
class TestEveryCellPromisesWhatEveryRendererPrints:
    """INVARIANT 4. The quoted shape survives whichever renderer `ci` chooses.

    The sibling module ranges over `ci`'s formats in ONE cell. The defect it was
    written for was a promise scoped to one rendering -- `init` promised
    `[FAIL] lint: 2 error(s), 0 warning(s)` and `ci` in a non-TTY shell printed
    `::notice::lint FAIL: 2 error(s), 0 warning(s)` -- and a promise is made once
    per cell, so the axis it needs is the product. The report states the step's
    NAME and its SUMMARY, which is what all three renderers read off the step,
    and quotes none of their spellings.
    """

    def test_the_report_states_the_step_name_and_its_summary(
        self,
        red_runs: dict[str, RunOutcome],
        failing_steps: dict[str, GateStep],
        cell: Cell,
        arrangement: Arrangement,
    ) -> None:
        run_id = f"{cell.name}-{arrangement.name}"
        outcome, step = red_runs[run_id], failing_steps[run_id]

        # Anti-vacuity: a green step is a promise about nothing.
        assert not step.passed, outcome.output
        assert step.name in outcome.output, outcome.output
        assert step.summary in outcome.output, outcome.output

    @pytest.mark.parametrize("fmt", THE_GATE_FORMATS, ids=list(THE_GATE_FORMATS))
    def test_the_renderer_prints_the_two_facts_the_report_promised(
        self,
        red_runs: dict[str, RunOutcome],
        failing_steps: dict[str, GateStep],
        cell: Cell,
        arrangement: Arrangement,
        fmt: str,
    ) -> None:
        run_id = f"{cell.name}-{arrangement.name}"
        step = failing_steps[run_id]

        rendered = _format_gate(GateResult(steps=[step]), fmt)

        assert step.name in rendered, (fmt, rendered)
        assert step.summary in rendered, (fmt, rendered)

    @pytest.mark.parametrize("fmt", THE_GATE_FORMATS, ids=list(THE_GATE_FORMATS))
    def test_the_report_quotes_no_renderer_s_own_step_line(
        self,
        red_runs: dict[str, RunOutcome],
        failing_steps: dict[str, GateStep],
        cell: Cell,
        arrangement: Arrangement,
        fmt: str,
    ) -> None:
        """A quoted spelling belongs to one renderer and is false under the others."""
        run_id = f"{cell.name}-{arrangement.name}"
        outcome, step = red_runs[run_id], failing_steps[run_id]

        rendered = _format_gate(GateResult(steps=[step]), fmt)
        lines_about_the_step = [
            line.strip() for line in rendered.splitlines() if step.name in line.strip()
        ]
        # Anti-vacuity: a renderer that never mentions the step would make the
        # claim below hold over an empty list.
        assert lines_about_the_step, (fmt, rendered)

        quoted = [line for line in lines_about_the_step if line in outcome.output]
        assert quoted == [], (fmt, quoted, outcome.output)


#: Every mode more than one branch offers, which is every mode: `--yes` and the
#: wizard offer all three, and `--bootstrap` and `--import` add a third branch to
#: two of them. Derived rather than listed, so a mode only one branch offered
#: would drop out of the comparison instead of being compared against itself.
THE_MODES_MORE_THAN_ONE_BRANCH_OFFERS = tuple(
    mode
    for mode in THE_MODES
    if len([entry for entry in THE_ENTRY_POINTS if mode in entry.modes]) > 1
)

#: The modes more than one branch can run over a tree that already carries a
#: graph file. Narrower than the tuple above, and derived from the same two
#: facts rather than written down: `--yes` refuses such a tree (`skipped`) or
#: deletes it (`--force`), so for a mode only `--yes` and the wizard offer there
#: is one branch left and nothing to compare. `test_which_modes_have_two
#: _branches_that_can_re_run` states which modes those are, so a mode leaving or
#: joining this set is visible rather than silently untested.
THE_MODES_MORE_THAN_ONE_BRANCH_CAN_RE_RUN = tuple(
    mode
    for mode in THE_MODES
    if len(
        [
            entry
            for entry in THE_ENTRY_POINTS
            if mode in entry.modes and entry.can_meet_a_file_it_did_not_write
        ]
    )
    > 1
)


class TestTheEntryPointsLeaveOneGraphForOneDeclaredMode:
    """INVARIANT 5. One command, one declared mode, one graph -- over all branches.

    `.18` closed this between `--yes` and the wizard for `--mode both`, where the
    two left graphs describing different things (BDL-UX #216), and asserted it
    over the IMPORTED graph. Two things are new here. The claim is stated over
    the WHOLE graph on disk -- every node and every edge, from whichever file
    wrote it -- so a divergence outside `imported.yml` is caught too. And the
    population is every branch offering the mode rather than the two that take
    `--mode`: `--bootstrap` and `--import` are how an adopter runs one mode
    without naming it, and nothing asserted that they leave what the other two
    leave.

    Stated over the graph rather than over a verdict, because the divergence
    `.18` closed was green on both sides and would have passed any comparison of
    exit codes.

    THE LIMIT THIS CLASS DECLARED, now closed. Until BDL-067 `.21` every case
    here ran on a VIRGIN tree, and the invariant was false on a tree that already
    carried a graph file: the wizard wrote a README for the inherited node and
    patched its `docs:` field, `--bootstrap` did neither, because the two called
    `generate_skeletons` with different arguments. That was BDL-UX #216 standing
    on the third entry point, and `.21` closed it by removing the argument rather
    than by fixing the call -- `generate_skeletons` no longer accepts a node
    list, so the whole-tree document it renders cannot be rendered from a subset
    of the tree by any caller. The last case below is that measurement, and it is
    stated over the tree the divergence needed: the inherited one.
    """

    def _graph_left_by(self, tmp_path: Path, entry: EntryPoint, mode: str) -> Any:
        project = _a_project_with_code_and_docs(tmp_path, name="orders-web")
        with _answering(Cell(entry, mode), reinit=False):
            result = CliRunner().invoke(
                main,
                [
                    "init",
                    *entry.argv(mode, project),
                    "--project",
                    str(project),
                ],
            )
        assert result.exit_code == 0, result.output
        nodes, edges = _graph_on_disk(project)
        return (
            sorted(json.dumps(node, sort_keys=True) for node in nodes),
            sorted(json.dumps(edge, sort_keys=True) for edge in edges),
        )

    def _left_by(
        self,
        tmp_path: Path,
        entry: EntryPoint,
        mode: str,
        *,
        arrange: Any,
        reinit: bool,
    ) -> Any:
        """Everything one branch leaves behind: the graph, the docs, the rc.

        Unlike `_graph_left_by` this does not require a green run. On the
        inherited tree every branch is red -- `ledger` has no parent and the
        rules file says it must -- and what is being compared is what the
        branches LEAVE, which the exit code does not answer.
        """
        project = arrange(tmp_path)
        with _answering(Cell(entry, mode), reinit=reinit):
            result = CliRunner().invoke(
                main, ["init", *entry.argv(mode, project), "--project", str(project)]
            )
        nodes, edges = _graph_on_disk(project)
        architecture = project / "docs" / "architecture.md"
        return {
            "rc": result.exit_code,
            "nodes": sorted(json.dumps(node, sort_keys=True) for node in nodes),
            "edges": sorted(json.dumps(edge, sort_keys=True) for edge in edges),
            "docs": sorted(
                str(path.relative_to(project))
                for path in (project / "docs").rglob("*.md")
            ),
            "the inherited node is in the architecture document": (
                THE_ORPHAN_IN_THE_INHERITED_FILE
                in architecture.read_text(encoding="utf-8")
                if architecture.is_file()
                else None
            ),
        }

    def test_every_mode_is_offered_by_more_than_one_branch(self) -> None:
        """Anti-vacuity: a mode with one branch would be compared against itself."""
        assert set(THE_MODES_MORE_THAN_ONE_BRANCH_OFFERS) == set(THE_MODES), (
            THE_MODES_MORE_THAN_ONE_BRANCH_OFFERS
        )

    def test_two_of_the_modes_are_offered_by_a_third_branch(self) -> None:
        """The axis this class adds: a mode run without `--mode` at all."""
        three = tuple(
            mode
            for mode in THE_MODES
            if len([e for e in THE_ENTRY_POINTS if mode in e.modes]) > 2
        )

        assert three == ("bootstrap", "import"), three

    @pytest.mark.parametrize(
        "mode",
        THE_MODES_MORE_THAN_ONE_BRANCH_OFFERS,
        ids=list(THE_MODES_MORE_THAN_ONE_BRANCH_OFFERS),
    )
    def test_every_branch_offering_the_mode_leaves_the_same_graph(
        self, tmp_path: Path, mode: str
    ) -> None:
        offering = [entry for entry in THE_ENTRY_POINTS if mode in entry.modes]
        left = {
            entry.name: self._graph_left_by(tmp_path / entry.name.strip("-"), entry, mode)
            for entry in offering
        }
        # Anti-vacuity: an empty graph would make every branch agree cheaply.
        assert all(nodes for nodes, _ in left.values()), left

        first, *rest = offering
        for entry in rest:
            assert left[entry.name] == left[first.name], (
                mode,
                entry.name,
                first.name,
                left,
            )

    def test_the_skeleton_writer_cannot_be_handed_a_subset_of_the_tree(self) -> None:
        """The fix, stated over the signature rather than over the call sites.

        `generate_skeletons` renders `docs/architecture.md`, a document about the
        WHOLE graph. While it accepted a node list, a caller could hand it part
        of the tree and get a whole-tree document describing that part — and one
        caller of four did, which is what the case below measured. Fixing the
        call site would have left the next caller free to make the same mistake:
        `.18` fixed one and the review of `.20` found the third still open,
        quoting `.18`'s own comment stating the rule it had not applied there.

        A case over the call sites would have to be re-derived whenever a fifth
        appears. A renderer that takes only the project root cannot be handed a
        subset by any caller, including one written tomorrow.
        """
        parameters = list(inspect.signature(generate_skeletons).parameters)

        assert parameters == ["project_root"], (
            "`generate_skeletons` renders a whole-tree document and has grown a "
            f"way to be given part of the tree: {parameters}"
        )

    def test_which_modes_have_two_branches_that_can_re_run(self) -> None:
        """The population of the case below, stated so its absence is visible.

        `both` is offered by `--yes` and the wizard only, and `--yes` cannot meet
        a file it did not write, so no two branches run `both` over an inherited
        tree and there is nothing to compare there. `bootstrap` and `import` each
        have a third entry point, which is exactly where the divergence was.
        """
        assert THE_MODES_MORE_THAN_ONE_BRANCH_CAN_RE_RUN == ("bootstrap", "import"), (
            THE_MODES_MORE_THAN_ONE_BRANCH_CAN_RE_RUN
        )

    @pytest.mark.parametrize(
        "mode",
        THE_MODES_MORE_THAN_ONE_BRANCH_CAN_RE_RUN,
        ids=list(THE_MODES_MORE_THAN_ONE_BRANCH_CAN_RE_RUN),
    )
    def test_every_branch_leaves_the_same_thing_on_a_tree_it_did_not_start(
        self, tmp_path: Path, mode: str
    ) -> None:
        """The case the class's stated limit named, run on the tree it named.

        MEASURED before the fix, by the review of `.20`, on two identical trees
        each carrying `.beadloom/_graph/legacy.yml`: only the wizard's tree
        gained `docs/domains/ledger/README.md`, only the wizard's tree listed
        `ledger` in the Domains table of `docs/architecture.md`, and only the
        wizard's `legacy.yml` gained a `docs:` field on that node. One declared
        mode, two entry points, two different trees.

        The docs are compared as well as the graph because that is where the
        divergence showed first: `generate_skeletons` renders `architecture.md`
        from the nodes it is given, so a caller that hands it a subset of the
        tree gets a whole-tree document describing part of the tree.
        """
        offering = [
            entry
            for entry in THE_ENTRY_POINTS
            if mode in entry.modes and entry.can_meet_a_file_it_did_not_write
        ]
        # Anti-vacuity: one branch would be compared against itself. `--yes` is
        # excluded for a measured reason and not for a stated one -- it returns
        # `skipped` over an existing `.beadloom/` and deletes the directory under
        # `--force`, so it never MEETS an inherited file, which is what
        # `TestWhichBranchesCanMeetAFileTheyDidNotWrite` establishes.
        assert len(offering) > 1, offering
        left = {
            entry.name: self._left_by(
                tmp_path / entry.name.strip("-"),
                entry,
                mode,
                arrange=_a_project_carrying_an_earlier_runs_graph,
                reinit=True,
            )
            for entry in offering
        }
        # And an empty graph would make every branch agree cheaply.
        assert all(outcome["nodes"] for outcome in left.values()), left

        first, *rest = offering
        for entry in rest:
            assert left[entry.name] == left[first.name], (
                mode,
                entry.name,
                first.name,
                left,
            )
