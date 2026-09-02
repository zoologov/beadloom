"""`init` reports one verdict per tree, in every mode and through either entry point.

BDL-067 `.15`, covering `.14`. The measurement this module exists for: **112 tests
across seven files of this epic were green while the defect `.14` fixed was live on
two modes.** Every one of them pinned `--mode bootstrap`, and the defect lived in
`--mode both`. `tests/test_init_branches_that_reach_the_bootstrap.py` read `init`'s
source and confirmed that the branch took a verdict, which was true and not the
question: the verdict was there and it was BLIND, judging an index written before the
run's last graph file. A syntactic check answers "could this branch report"; only
running the command answers "does it report".

So the axis here is the one the epic never varied. The cases run over
`--mode {bootstrap, import, both}` — read off the flag's own `click.Choice` rather
than written out, so a fourth mode joins the parametrisation on the day it is
declared — and over the two entry points that choose a mode: the `--yes` flag and the
wizard's first prompt.

THE ASSERTION THE REVIEW OF `.13` NAMED, and the one that would have caught `.14`
with no sabotage at all, is `TestTheWizardAndTheFlagAgree`. Measured on the pre-`.14`
tree over a project with a flat `src/index.ts` and two documents the classifier
cannot place:

    beadloom init --yes --mode both   -> rc 0, then `lint --strict` rc 1
    the wizard answering `both`       -> rc 1, then `lint --strict` rc 1

Two halves of one command disagreeing about one tree. Neither half needed to be known
correct for the pair to be a defect, which is why the agreement is asserted directly
rather than inferred from an expected exit code. The wizard re-indexed after its last
writer and `--yes` did not, and `.14` moved the reindex so that both do.

The fixture is a project that is not us (`orders-web`, a flat `src/index.ts` plus
`docs/` the classifier reads as domains), so a verdict that worked by recognising
Beadloom's own tree would fail these. Nothing is patched in the unsabotaged cases:
the real bootstrap, the real `import_docs`, the real `generate_rules` and the real
linter all run.

THE DIVERGENCE THIS MODULE ONCE ONLY RECORDED IS NOW ASSERTED AWAY. Until `.18`,
`--yes --mode both` generated the doc skeletons inside its bootstrap block and
imported afterwards, so it classified the documents it had written seconds earlier
and its graph gained `architecture` and two `readme` nodes the wizard's graph did not
have. The paragraph that stood here reported that, said both graphs passed their own
rules, and routed the question to the review. The review decided it: one command with
one declared mode must not leave two different graphs, and a graph whose nodes are
named after Beadloom's own scaffolding is not a description of the adopter's project
(BDL-UX #216). `non_interactive_init` now generates the skeletons last, in the
wizard's order, and `TestTheWizardAndTheFlagImportTheSameDocuments` asserts node-set
equality where this paragraph used to explain its absence.

The verdict was green on both sides of that divergence, which is why it needed its own
assertion: `.14` gives every imported node a `part_of` edge to the root, so the wrong
graph was structurally valid. An epic that hides a defect it did not create has done
the thing it exists to stop, so `TestNoRunImportsTheScaffoldingItWrote` states the
claim over one entry point at a time and does not depend on the other agreeing.
"""

from __future__ import annotations

import ast
import inspect
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from beadloom.application.gate import lint_step
from beadloom.onboarding.scanner import init_flow
from beadloom.services.cli import main
from tests.adopter_project import typescript_project

# The divergences are the sibling module's, imported rather than re-written: two
# copies of a sabotage drift, and the point of these cases is that the same
# divergence is met by every mode and both entry points.
from tests.test_init_verdict_over_its_own_rules import (
    INIT_FLOW_BINDING,
    THE_ADDED_ORPHAN,
    THE_MODES,
    THE_RULE,
    _a_bootstrap_that_forgets_the_edge,
    _an_import_that_adds_an_orphan,
    _lint_strict,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

#: Documents whose text matches none of `classify_doc`'s patterns, so each falls
#: through to the `other` branch and is written as a `domain` node in
#: `imported.yml` — the second writer, and the one `--mode bootstrap` never runs.
UNCLASSIFIABLE_DOCS = {
    "payments.md": "# Payments\n\nHow money moves through the shop.\n",
    "billing.md": "# Billing\n\nWho is charged, and when.\n",
}

#: The two graph files `init` can write, by the name each writer gives it.
THE_BOOTSTRAP_FILE = "services.yml"
THE_IMPORT_FILE = "imported.yml"


def _the_modes_the_wizard_offers() -> frozenset[str]:
    """Every mode the wizard can be answered with, read off `init_flow`'s source.

    `interactive_init` asks its mode question four times over, with a different
    `choices` list depending on whether the project has code, docs or neither.
    The union of those lists is what a human can answer, and it has to cover what
    the flag offers or the two entry points cannot be compared at all.
    """
    source = Path(inspect.getfile(init_flow)).read_text(encoding="utf-8")
    offered: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "ask"):
            continue
        asks_for_the_mode = any(
            isinstance(arg, ast.Constant) and arg.value == "Choose init mode"
            for arg in node.args
        )
        if not asks_for_the_mode:
            continue
        for keyword in node.keywords:
            if keyword.arg == "choices" and isinstance(keyword.value, ast.List):
                offered.update(
                    element.value
                    for element in keyword.value.elts
                    if isinstance(element, ast.Constant)
                    and isinstance(element.value, str)
                )
    return frozenset(offered)


#: `THE_MODES` — every mode `init` accepts, read off the flag's own
#: `click.Choice` — is imported from the sibling module above rather than derived
#: a second time here. BDL-067 `.17` moved the derivation there because it needs
#: the same axis and this module already imports from it; two derivations of one
#: fact are two things that can disagree.

#: The modes that run the bootstrap, and therefore the modes in which `init`
#: writes `rules.yml` and takes a verdict. Written here and bound to behaviour by
#: `test_the_modes_that_write_the_bootstrap_file_are_the_ones_declared`, so the
#: constant cannot quietly fall behind `init_flow`'s `mode in (...)` conditions.
THE_MODES_THAT_BOOTSTRAP = ("bootstrap", "both")

#: The modes that run `import_docs` — the second writer of `domain` nodes.
THE_MODES_THAT_IMPORT = ("import", "both")


@dataclass(frozen=True)
class InitEntryPoint:
    """One way of telling `init` which mode to run.

    The two are not two spellings of one path: `--yes` runs `non_interactive_init`
    and the wizard runs `interactive_init`, and until `.14` those two functions
    re-indexed at different points, which is exactly why a mode has to be run
    through both before it is called covered.
    """

    #: How it is spelled, for the test id.
    name: str
    #: Whether the mode is chosen by answering a prompt rather than by a flag.
    through_the_wizard: bool

    def argv(self, mode: str) -> tuple[str, ...]:
        return () if self.through_the_wizard else ("--yes", "--mode", mode)

    def prompts(self, mode: str) -> tuple[str, ...]:
        """The wizard's answers: the mode, then the graph review if one is shown.

        The review prompt appears only when the run produced nodes to review,
        which is the modes that bootstrap. `edit` is the one answer that takes no
        verdict and it is covered by the sibling module, so the answer here is
        always `yes`.
        """
        if not self.through_the_wizard:
            return ()
        if mode in THE_MODES_THAT_BOOTSTRAP:
            return (mode, "yes")
        return (mode,)


THE_ENTRY_POINTS = (
    InitEntryPoint("--yes", through_the_wizard=False),
    InitEntryPoint("wizard", through_the_wizard=True),
)

THE_FLAG, THE_WIZARD = THE_ENTRY_POINTS


def _the_bootstrap_forgets_the_edge(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both entry points reach the bootstrap through the one `init_flow` binding."""
    _a_bootstrap_that_forgets_the_edge(monkeypatch, INIT_FLOW_BINDING)


@dataclass(frozen=True)
class Divergence:
    """A graph a writer leaves in contradiction with the rules on disk.

    Constructed rather than awaited: `.1` and `.14` gave both node-creating
    writers a post-condition that makes an unparented domain impossible to obtain
    honestly, so a test that waited for one would pass for the reason those beads
    landed and say nothing about a future divergence.
    """

    #: How it is spelled, for the test id.
    name: str
    #: The sabotage, applied to the one binding both entry points share.
    apply: Callable[[pytest.MonkeyPatch], None]
    #: The modes that run the writer it sabotages. Outside them it would sit
    #: inert and the case would go green for the wrong reason.
    modes: tuple[str, ...]
    #: Whether it leaves an orphan under a name a test can pin.
    orphan_is_named: bool


#: One divergence per node-creating writer. `.14`'s sweep of `src/` found six
#: functions that write into `.beadloom/_graph/` and exactly two that create
#: nodes; those two are the only ones that can leave an unparented domain, so
#: those two are the ones sabotaged here. The enumeration is checked, not
#: trusted: `tests/test_init_branches_that_reach_the_bootstrap.py` rediscovers
#: the six from the source and fails on a seventh.
THE_DIVERGENCES = (
    Divergence(
        "the bootstrap forgets the edge",
        apply=_the_bootstrap_forgets_the_edge,
        modes=THE_MODES_THAT_BOOTSTRAP,
        orphan_is_named=False,
    ),
    Divergence(
        "the import adds an orphan",
        apply=_an_import_that_adds_an_orphan,
        modes=THE_MODES_THAT_IMPORT,
        orphan_is_named=True,
    ),
)


def _a_project_with_code_and_docs(tmp_path: Path, name: str = "orders-web") -> Path:
    """A flat `src/index.ts` plus documents the classifier reads as domains.

    Both writers have something to write here, which is what makes one fixture
    usable for all three modes: `--mode bootstrap` ignores the docs, `--mode
    import` ignores the code, and `--mode both` writes two graph files.
    """
    project = typescript_project(tmp_path / name).root
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for filename, text in UNCLASSIFIABLE_DOCS.items():
        (docs / filename).write_text(text, encoding="utf-8")
    return project


def _a_project_whose_skeletons_would_collide(tmp_path: Path) -> Path:
    """Two code-bearing source directories, plus documents the adopter wrote.

    The shape the review of `.16` measured. `generate_skeletons` writes
    `docs/architecture.md`, `docs/domains/orders/README.md` and
    `docs/domains/catalog/README.md`, and `import_docs` names a node after the
    file STEM — so both READMEs arrive under the single ref_id `readme`. A
    fixture with one cluster would show a run importing its own scaffolding but
    not the collision, and the collision is the part that makes the imported
    graph unrepairable rather than merely wrong: the loader keeps one node per
    ref_id, so one of the two documents is silently dropped.

    `typescript_project` is flat by construction and this shape is not, so the
    project is built here rather than adapted from it. The manifest name is the
    same, which keeps the root node's ref_id comparable with the other fixtures.
    """
    project = tmp_path / "orders-web"
    for cluster in ("orders", "catalog"):
        (project / "src" / cluster).mkdir(parents=True)
        (project / "src" / cluster / f"{cluster}.ts").write_text(
            f"export const {cluster} = [];\n", encoding="utf-8"
        )
    (project / "package.json").write_text(
        '{\n  "name": "orders-web",\n  "version": "0.4.1"\n}\n', encoding="utf-8"
    )
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for filename, text in UNCLASSIFIABLE_DOCS.items():
        (docs / filename).write_text(text, encoding="utf-8")
    return project


def _documents_under(project_root: Path) -> list[str]:
    """Every markdown file under `docs/`, by its path relative to the project."""
    docs_dir = project_root / "docs"
    if not docs_dir.is_dir():
        return []
    return sorted(
        str(path.relative_to(project_root))
        for path in docs_dir.rglob("*.md")
        if path.is_file()
    )


def _the_imported_graph(project_root: Path) -> dict[str, Any]:
    """`imported.yml` as written, or an empty mapping when no import ran."""
    path = project_root / ".beadloom" / "_graph" / THE_IMPORT_FILE
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@contextmanager
def _answering(
    prompts: tuple[str, ...], *, generate_skeletons: bool = False
) -> Iterator[None]:
    """Answer the wizard's prompts; a no-op for the entry point that asks none.

    `generate_skeletons` is the answer to the one `Confirm.ask` the wizard puts:
    "Generate doc skeletons?". Declining it keeps a case about the verdict, which
    is what every case written before `.18` wanted. `.18` compares the graph the
    two entry points leave behind, and `--yes` has no such prompt — it always
    generates — so a declining wizard would be compared against a run that did
    strictly more work, and an agreement measured there would say nothing about
    the divergence.
    """
    if not prompts:
        yield
        return
    with (
        patch("rich.prompt.Prompt.ask", side_effect=list(prompts)),
        patch("rich.prompt.Confirm.ask", return_value=generate_skeletons),
    ):
        yield


def _init(
    project_root: Path,
    entry: InitEntryPoint,
    mode: str,
    *,
    generate_skeletons: bool = False,
) -> Any:
    with _answering(entry.prompts(mode), generate_skeletons=generate_skeletons):
        return CliRunner().invoke(
            main, ["init", *entry.argv(mode), "--project", str(project_root)]
        )


def _graph_on_disk(project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every node and edge under `.beadloom/_graph/`, whichever file wrote it.

    Read off the files rather than off a writer's return value: the finding this
    module covers is that one writer's post-condition said nothing about the
    other's output, and a fixture that asked one writer what it wrote would
    repeat that mistake.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for path in sorted(graph_dir.glob("*.yml")):
        if path.name == "rules.yml":
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        nodes.extend(data.get("nodes") or [])
        edges.extend(data.get("edges") or [])
    return nodes, edges


def _unparented_domains(project_root: Path) -> list[str]:
    nodes, edges = _graph_on_disk(project_root)
    parented = {edge["src"] for edge in edges if edge["kind"] == "part_of"}
    return [
        node["ref_id"]
        for node in nodes
        if node.get("kind") == "domain" and node["ref_id"] not in parented
    ]


MODE_IDS = list(THE_MODES)
ENTRY_IDS = [entry.name for entry in THE_ENTRY_POINTS]

#: Every (entry point, mode) the command offers. The product is the axis this
#: epic never varied: six combinations, of which one file's worth of tests ran
#: exactly one.
THE_COMBINATIONS = [
    (entry, mode) for entry in THE_ENTRY_POINTS for mode in THE_MODES
]
COMBINATION_IDS = [f"{entry.name}-{mode}" for entry, mode in THE_COMBINATIONS]

#: Every (entry point, mode, divergence) where the divergence reaches a writer
#: that mode runs. Filtered rather than skipped: a skip is a case that reports
#: itself as not run, and a matrix that skips half of what it lists is the kind
#: of green this bead exists to distrust.
THE_SABOTAGED_COMBINATIONS = [
    (entry, mode, divergence)
    for entry in THE_ENTRY_POINTS
    for divergence in THE_DIVERGENCES
    for mode in THE_MODES
    if mode in divergence.modes
]

#: The subset where the run also wrote `rules.yml`, so there is a rule for the
#: divergence to contradict. `--mode import` writes none, which is why it is
#: absent here and why its green is explained in its own class rather than
#: asserted alongside these.
THE_SABOTAGED_COMBINATIONS_WITH_RULES = [
    (entry, mode, divergence)
    for entry, mode, divergence in THE_SABOTAGED_COMBINATIONS
    if mode in THE_MODES_THAT_BOOTSTRAP
]

#: The subset where the orphan carries a name a case can pin. The bootstrap
#: divergence orphans whatever the preset named the source directory, which is
#: the project's own name rather than a constant; only the import divergence
#: adds a node under a name it chose.
THE_SABOTAGED_COMBINATIONS_WITH_A_NAMED_ORPHAN = [
    (entry, mode, divergence)
    for entry, mode, divergence in THE_SABOTAGED_COMBINATIONS_WITH_RULES
    if divergence.orphan_is_named
]


def _sabotage_ids(
    combinations: list[tuple[InitEntryPoint, str, Divergence]],
) -> list[str]:
    return [
        f"{entry.name}-{mode}-{divergence.name.replace(' ', '-')}"
        for entry, mode, divergence in combinations
    ]


SABOTAGED_IDS = _sabotage_ids(THE_SABOTAGED_COMBINATIONS)
SABOTAGED_WITH_RULES_IDS = _sabotage_ids(THE_SABOTAGED_COMBINATIONS_WITH_RULES)
SABOTAGED_NAMED_ORPHAN_IDS = _sabotage_ids(THE_SABOTAGED_COMBINATIONS_WITH_A_NAMED_ORPHAN)


class TestTheParametrisationCoversWhatTheCommandOffers:
    """The axis is derived, so it is checked before anything is run over it.

    A derivation that silently returned nothing would collect zero cases and
    report a green file, which is a larger version of the defect this module is
    about: 112 green tests that could not see the mode where the bug lived.
    """

    def test_the_flag_offers_the_three_modes_this_module_runs(self) -> None:
        assert set(THE_MODES) >= {"bootstrap", "import", "both"}, THE_MODES

    def test_the_wizard_offers_every_mode_the_flag_offers(self) -> None:
        """Otherwise the pair below cannot be compared in the missing mode.

        A mode reachable only through `--yes` is a mode with one entry point, and
        the agreement that would have caught `.14` is not askable about it.
        """
        offered_by_the_wizard = _the_modes_the_wizard_offers()

        # Anti-vacuity: a parse that found no `choices` list would satisfy any
        # superset claim by way of an empty left-hand side.
        assert offered_by_the_wizard, "no mode prompt was found in init_flow's source"
        assert set(THE_MODES) <= offered_by_the_wizard, (
            f"modes the flag accepts and the wizard cannot be answered with: "
            f"{sorted(set(THE_MODES) - offered_by_the_wizard)}"
        )

    @pytest.mark.parametrize("mode", THE_MODES, ids=MODE_IDS)
    def test_the_modes_that_write_the_bootstrap_file_are_the_ones_declared(
        self, tmp_path: Path, mode: str
    ) -> None:
        """`THE_MODES_THAT_BOOTSTRAP` is bound to what the command does.

        The constant mirrors an `if mode in (...)` in two modules. Left as a
        written-down claim it would go stale the way the branch count in this
        epic's first four waves did.
        """
        project = _a_project_with_code_and_docs(tmp_path)

        _init(project, THE_FLAG, mode)

        written = (project / ".beadloom" / "_graph" / THE_BOOTSTRAP_FILE).is_file()
        assert written == (mode in THE_MODES_THAT_BOOTSTRAP)

    @pytest.mark.parametrize("mode", THE_MODES, ids=MODE_IDS)
    def test_the_modes_that_write_the_import_file_are_the_ones_declared(
        self, tmp_path: Path, mode: str
    ) -> None:
        project = _a_project_with_code_and_docs(tmp_path)

        _init(project, THE_FLAG, mode)

        written = (project / ".beadloom" / "_graph" / THE_IMPORT_FILE).is_file()
        assert written == (mode in THE_MODES_THAT_IMPORT)


@pytest.mark.parametrize(("entry", "mode"), THE_COMBINATIONS, ids=COMBINATION_IDS)
class TestEveryModeAgreesWithTheLintTheAdopterRunsNext:
    """Nothing is patched: this is the reproduction from BDL-UX #192, per mode.

    Measured on the pre-`.14` tree, `--yes --mode both` exited 0 over a tree whose
    `lint --strict` exited 1 — the adopter's very next command contradicting the
    one that had just reported success. `--mode bootstrap` was green there, which
    is why one pinned mode saw nothing.
    """

    def test_the_run_reports_success(
        self, tmp_path: Path, entry: InitEntryPoint, mode: str
    ) -> None:
        project = _a_project_with_code_and_docs(tmp_path)

        result = _init(project, entry, mode)

        assert result.exit_code == 0, result.output

    def test_the_verdict_agrees_with_lint_strict_on_the_tree_it_leaves(
        self, tmp_path: Path, entry: InitEntryPoint, mode: str
    ) -> None:
        """The claim is agreement with the Gate, not a particular number.

        Stated as an equivalence so it keeps meaning something on a fixture where
        the honest answer is red: what must never happen is one of the two
        reporting clean while the other does not.
        """
        project = _a_project_with_code_and_docs(tmp_path)

        init_rc = _init(project, entry, mode).exit_code

        assert (init_rc != 0) == (_lint_strict(project) != 0)



THE_COMBINATIONS_THAT_BOOTSTRAP = [
    (entry, mode) for entry in THE_ENTRY_POINTS for mode in THE_MODES_THAT_BOOTSTRAP
]
BOOTSTRAPPING_COMBINATION_IDS = [
    f"{entry.name}-{mode}" for entry, mode in THE_COMBINATIONS_THAT_BOOTSTRAP
]


@pytest.mark.parametrize(
    ("entry", "mode"),
    THE_COMBINATIONS_THAT_BOOTSTRAP,
    ids=BOOTSTRAPPING_COMBINATION_IDS,
)
class TestEveryDomainAnyWriterWroteCarriesAParent:
    """`.1`'s post-condition and `.14`'s, stated once over the files on disk.

    The parametrisation is the modes that bootstrap, because those are the modes
    in which the graph has a root for a `part_of` edge to point at. `--mode
    import` on a virgin project has none, names no parent by the decision `.14`
    took, and is covered by `TestAnImportOnlyRunOnAVirginProjectNamesNoParent`
    rather than by an exception written into this claim.

    Under `--mode both` this reads the output of both node-creating writers
    through one assertion, which is the shape the finding asked for: a claim
    scoped to one writer is what left the other outside the instrument.
    """

    def test_no_domain_is_left_without_a_part_of_edge(
        self, tmp_path: Path, entry: InitEntryPoint, mode: str
    ) -> None:
        project = _a_project_with_code_and_docs(tmp_path)

        _init(project, entry, mode)

        assert _unparented_domains(project) == []
        # Anti-vacuity: a graph with no domain satisfies the claim above without
        # either writer having been exercised.
        nodes, _ = _graph_on_disk(project)
        assert [n for n in nodes if n.get("kind") == "domain"], nodes


@pytest.mark.parametrize("mode", THE_MODES, ids=MODE_IDS)
class TestTheWizardAndTheFlagAgree:
    """THE ASSERTION THE REVIEW NAMED. Two entry points, one tree, one verdict.

    Each case builds the fixture twice, from the same code and the same
    documents, and runs one copy through each entry point. Neither run is
    asserted to be right: what is asserted is that they say the same thing, which
    is a claim `.14` broke without anything in the suite noticing.

    Measured against the pre-`.14` tree at `--mode both`: the wizard exited 1 and
    `--yes` exited 0, over fixtures that differ in nothing. No sabotage is
    involved — the divergence is what a virgin project with a `docs/` directory
    produced on its own.
    """

    def _two_runs(self, tmp_path: Path, mode: str) -> tuple[Any, Path, Any, Path]:
        by_flag = _a_project_with_code_and_docs(tmp_path / "flag")
        by_wizard = _a_project_with_code_and_docs(tmp_path / "wizard")
        return (
            _init(by_flag, THE_FLAG, mode),
            by_flag,
            _init(by_wizard, THE_WIZARD, mode),
            by_wizard,
        )

    def test_they_report_the_same_verdict(self, tmp_path: Path, mode: str) -> None:
        flag_result, _, wizard_result, _ = self._two_runs(tmp_path, mode)

        assert flag_result.exit_code == wizard_result.exit_code, (
            f"`init --yes --mode {mode}` exited {flag_result.exit_code} and the "
            f"wizard answering {mode!r} exited {wizard_result.exit_code} over the "
            "same project.\n--- --yes ---\n"
            f"{flag_result.output}\n--- wizard ---\n{wizard_result.output}"
        )

    def test_they_leave_the_adopter_the_same_next_lint(
        self, tmp_path: Path, mode: str
    ) -> None:
        """The trees, not only the reports: the adopter runs `lint --strict` next.

        Two runs that exited alike over trees that lint differently would agree
        about the wrong thing, and one of the two would be the blind one.
        """
        _, by_flag, _, by_wizard = self._two_runs(tmp_path, mode)

        assert (_lint_strict(by_flag) != 0) == (_lint_strict(by_wizard) != 0)

    def test_they_leave_the_same_domains_unparented(
        self, tmp_path: Path, mode: str
    ) -> None:
        """Which is none of them, except in the one mode that names no root.

        Stated as equality rather than as emptiness so the case says the same
        thing in all three modes: `--mode import` on a virgin project leaves its
        domains unparented on purpose, and what would be a defect is one entry
        point doing that and the other not.
        """
        _, by_flag, _, by_wizard = self._two_runs(tmp_path, mode)

        assert sorted(_unparented_domains(by_flag)) == sorted(
            _unparented_domains(by_wizard)
        )


THE_IMPORTING_COMBINATIONS = [
    (entry, mode) for entry in THE_ENTRY_POINTS for mode in THE_MODES_THAT_IMPORT
]
IMPORTING_COMBINATION_IDS = [
    f"{entry.name}-{mode}" for entry, mode in THE_IMPORTING_COMBINATIONS
]


@pytest.mark.parametrize(
    ("entry", "mode"), THE_IMPORTING_COMBINATIONS, ids=IMPORTING_COMBINATION_IDS
)
class TestNoRunImportsTheScaffoldingItWrote:
    """BDL-067 `.18`, BDL-UX #216. The graph describes the adopter, not us.

    Stated over one entry point at a time, so it holds whether or not the other
    one agrees: an agreement between two runs that both import their own
    scaffolding would be green and worthless. What is asserted is that every node
    in `imported.yml` names a document that was on disk before `init` ran.

    Measured on the pre-`.18` tree over `_a_project_whose_skeletons_would_collide`:
    `--yes --mode both` reported `Imported: 4 documents` and left `imported.yml`
    holding `architecture`, `readme`, `readme` and `payments` — three of the four
    written by `generate_skeletons` seconds earlier, inside the same command.
    """

    def test_every_imported_node_names_a_document_that_predates_the_run(
        self, tmp_path: Path, entry: InitEntryPoint, mode: str
    ) -> None:
        project = _a_project_whose_skeletons_would_collide(tmp_path)
        the_adopters_documents = _documents_under(project)

        _init(project, entry, mode, generate_skeletons=True)

        imported = _the_imported_graph(project).get("nodes") or []
        # Anti-vacuity: an import that wrote nothing satisfies any claim about
        # what it wrote, and `--mode import` on this fixture has documents to read.
        assert imported, "no node was imported, so nothing was checked"
        assert sorted(
            doc for node in imported for doc in (node.get("docs") or [])
        ) == the_adopters_documents

    def test_no_two_imported_nodes_share_a_ref_id(
        self, tmp_path: Path, entry: InitEntryPoint, mode: str
    ) -> None:
        """The consequence that makes the wrong import lossy rather than noisy.

        The importer names a node after the file stem, so two generated
        `README.md` files became two nodes under the ref_id `readme`. The loader
        keeps one node per ref_id, so a graph in that state has already dropped a
        document it claims to describe.
        """
        project = _a_project_whose_skeletons_would_collide(tmp_path)

        _init(project, entry, mode, generate_skeletons=True)

        ref_ids = [
            str(node["ref_id"]) for node in (_the_imported_graph(project).get("nodes") or [])
        ]
        assert ref_ids, "no node was imported, so nothing was checked"
        assert sorted(ref_ids) == sorted(set(ref_ids)), ref_ids


@pytest.mark.parametrize("mode", THE_MODES_THAT_IMPORT, ids=list(THE_MODES_THAT_IMPORT))
class TestTheWizardAndTheFlagImportTheSameDocuments:
    """One command, one declared mode, one imported graph — BDL-067 `.18`.

    `TestTheWizardAndTheFlagAgree` asserts the verdict and the parenting and says
    so in its own docstring; the node sets were left out of it because they
    differed, and the difference was recorded in this module's docstring and
    routed to the review rather than decided. The review decided it: a graph whose
    nodes are named after Beadloom's own scaffolding is not a description of the
    adopter's project, and one command with one declared mode must not leave two
    different graphs.

    Measured on the pre-`.18` tree, one project copied twice:

        init --yes --mode both      -> imported.yml: architecture, readme, readme, payments
        the wizard answering both   -> imported.yml: payments

    Both entry points generate the skeletons here. The wizard is offered them and
    accepts, because `--yes` has no such prompt and comparing it against a wizard
    that declined would compare two different amounts of work.
    """

    def _two_runs(self, tmp_path: Path, mode: str) -> tuple[Path, Path]:
        by_flag = _a_project_whose_skeletons_would_collide(tmp_path / "flag")
        by_wizard = _a_project_whose_skeletons_would_collide(tmp_path / "wizard")
        _init(by_flag, THE_FLAG, mode, generate_skeletons=True)
        _init(by_wizard, THE_WIZARD, mode, generate_skeletons=True)
        return by_flag, by_wizard

    def test_they_write_the_same_imported_graph(
        self, tmp_path: Path, mode: str
    ) -> None:
        by_flag, by_wizard = self._two_runs(tmp_path, mode)

        through_the_flag = _the_imported_graph(by_flag)
        through_the_wizard = _the_imported_graph(by_wizard)

        # Anti-vacuity: two runs that imported nothing agree about nothing.
        assert through_the_flag.get("nodes"), "the flag imported no node"
        assert through_the_flag == through_the_wizard

    def test_they_generate_the_same_documents(
        self, tmp_path: Path, mode: str
    ) -> None:
        """The other half of the same act, and the one that orders it.

        The import reads `docs/`, so two entry points can only import the same
        documents if they also leave the same ones behind. Stated separately
        because a run that generated nothing at all would satisfy the claim above
        while doing less than the adopter asked for.
        """
        by_flag, by_wizard = self._two_runs(tmp_path, mode)

        assert _documents_under(by_flag) == _documents_under(by_wizard)


@pytest.mark.parametrize("mode", THE_MODES_THAT_IMPORT, ids=list(THE_MODES_THAT_IMPORT))
class TestTheWizardAndTheFlagAgreeOverAGraphTheRulesReject:
    """The same agreement where the honest answer is red, not green.

    Without this the class above would be satisfied by two entry points that both
    report success unconditionally, which is the state `--yes` was in. The
    divergence is applied to the import step because that is the writer whose
    output the two entry points used to see differently: `--yes` re-indexed before
    it ran, the wizard after.
    """

    def test_they_report_the_same_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
    ) -> None:
        by_flag = _a_project_with_code_and_docs(tmp_path / "flag")
        by_wizard = _a_project_with_code_and_docs(tmp_path / "wizard")
        _an_import_that_adds_an_orphan(monkeypatch)

        flag_result = _init(by_flag, THE_FLAG, mode)
        wizard_result = _init(by_wizard, THE_WIZARD, mode)

        assert flag_result.exit_code == wizard_result.exit_code, (
            f"--- --yes ---\n{flag_result.output}\n"
            f"--- wizard ---\n{wizard_result.output}"
        )

    def test_each_agrees_with_the_lint_on_the_tree_it_left(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
    ) -> None:
        """Agreement between the two is not enough if both are blind together."""
        by_flag = _a_project_with_code_and_docs(tmp_path / "flag")
        by_wizard = _a_project_with_code_and_docs(tmp_path / "wizard")
        _an_import_that_adds_an_orphan(monkeypatch)

        flag_rc = _init(by_flag, THE_FLAG, mode).exit_code
        wizard_rc = _init(by_wizard, THE_WIZARD, mode).exit_code

        assert (flag_rc != 0) == (_lint_strict(by_flag) != 0)
        assert (wizard_rc != 0) == (_lint_strict(by_wizard) != 0)


@pytest.mark.parametrize(
    ("entry", "mode", "divergence"), THE_SABOTAGED_COMBINATIONS, ids=SABOTAGED_IDS
)
class TestAViolationTheRunIntroducedIsReportedInEveryModeItCanReach:
    """Each writer's divergence, met by every mode that runs that writer.

    `--mode import` writes no `rules.yml`, so a run in that mode has no rule to
    violate and the honest verdict is clean. That is asserted as an equivalence
    with `lint --strict` rather than as an exit code, and the reason is checked
    separately in `TestAnImportOnlyRunOnAVirginProjectNamesNoParent` — a green
    that is explained is a different thing from a green that is assumed.
    """

    def test_the_verdict_agrees_with_lint_strict_on_the_tree_it_leaves(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        entry: InitEntryPoint,
        mode: str,
        divergence: Divergence,
    ) -> None:
        project = _a_project_with_code_and_docs(tmp_path)
        divergence.apply(monkeypatch)

        init_rc = _init(project, entry, mode).exit_code

        assert (init_rc != 0) == (_lint_strict(project) != 0)


@pytest.mark.parametrize(
    ("entry", "mode", "divergence"),
    THE_SABOTAGED_COMBINATIONS_WITH_RULES,
    ids=SABOTAGED_WITH_RULES_IDS,
)
class TestARunThatWroteItsOwnRulesReportsTheGraphThatFailsThem:
    """Where a rule exists, the contradiction with it is reported by name.

    The pairing that matters is the one down the ids: the same divergence, met by
    `--mode bootstrap` and by `--mode both`, through `--yes` and through the
    wizard. Under `--mode both` the import step writes a second graph file after
    the bootstrap's, and until `.14` the verdict judged an index taken before it.
    """

    def test_the_command_does_not_report_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        entry: InitEntryPoint,
        mode: str,
        divergence: Divergence,
    ) -> None:
        project = _a_project_with_code_and_docs(tmp_path)
        divergence.apply(monkeypatch)

        result = _init(project, entry, mode)

        assert result.exit_code != 0, result.output

    def test_it_names_the_rule_the_gate_will_name(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        entry: InitEntryPoint,
        mode: str,
        divergence: Divergence,
    ) -> None:
        """Not "something is wrong" — the string the adopter will read again."""
        project = _a_project_with_code_and_docs(tmp_path)
        divergence.apply(monkeypatch)

        result = _init(project, entry, mode)

        assert THE_RULE in result.output, result.output


@pytest.mark.parametrize(
    ("entry", "mode", "divergence"),
    THE_SABOTAGED_COMBINATIONS_WITH_A_NAMED_ORPHAN,
    ids=SABOTAGED_NAMED_ORPHAN_IDS,
)
class TestTheReportNamesTheNodeTheSecondWriterLeftUnparented:
    """The node the adopter has to go and fix, not merely the rule it broke.

    This is the case that is red on the pre-`.14` tree through `--yes`: the
    orphan is written into `imported.yml` after the reindex the bootstrap block
    used to run, so the verdict never saw it and named nothing at all.
    """

    def test_the_orphan_is_named_in_the_report(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        entry: InitEntryPoint,
        mode: str,
        divergence: Divergence,
    ) -> None:
        project = _a_project_with_code_and_docs(tmp_path)
        divergence.apply(monkeypatch)

        result = _init(project, entry, mode)

        assert result.exit_code != 0, result.output
        assert THE_ADDED_ORPHAN in result.output, result.output


class TestAnImportOnlyRunOnAVirginProjectNamesNoParent:
    """The green above, with its reason checked instead of assumed.

    ONE reason holds it up, since BDL-067 `.17`. `--mode import` now takes the
    verdict like every other mode — the guard is what this run WROTE, not which
    writer ran — so the tree it leaves is clean for a single reason: no
    `rules.yml` is on disk, and `lint --strict` evaluates nothing. Until `.17`
    there were two, and the first of them was a carve-out whose stated reason
    ("both of the report's headlines open with *the graph this command just
    wrote*") held only until the next `init` on the same tree, which is the
    review of `.16`'s major 2.

    That leaves the green resting on one fact rather than two, so it is the fact
    this class checks. If a rules file ever reaches an import-only run, the
    verdict is there to meet it and this case is where the change is noticed.
    """

    def test_an_import_only_run_writes_no_rules_file(self, tmp_path: Path) -> None:
        project = _a_project_with_code_and_docs(tmp_path)

        result = _init(project, THE_FLAG, "import")

        assert result.exit_code == 0, result.output
        # Anti-vacuity: the run did write a graph file, so the absence of rules
        # is a fact about this mode and not about a run that did nothing.
        assert (project / ".beadloom" / "_graph" / THE_IMPORT_FILE).is_file()
        assert not (project / ".beadloom" / "_graph" / "rules.yml").exists()

    def test_it_names_no_parent_because_the_graph_it_wrote_has_no_root(
        self, tmp_path: Path
    ) -> None:
        """BDL-067 `.14`'s carve-out, on the one run that reaches it.

        `import_docs` attaches every node it writes to the graph's single root,
        and an import-only run on a virgin project has no root to attach to: no
        `service` node exists, because only the bootstrap writes one. The
        decision was to name no parent rather than guess a destination the graph
        does not contain, and it is safe because no `rules.yml` this command
        wrote is on disk to fail — which the case above measures.

        "No single root" ranges over distinct ref_ids since BDL-067 `.17`: a
        graph that names one root twice is one candidate, and the bootstrap
        produces exactly that on a project named after one of its own source
        directories (the review of `.16`, major 1). It is not this fixture's
        shape — there is no root here at all — and it is stated in
        `tests/test_import_docs_parents_what_it_writes.py`.

        Pinned here so that giving `import_docs` a guessed root, or writing rules
        into an import-only run, fails a case instead of quietly re-opening
        BDL-UX #192 on the mode that has no bootstrap.
        """
        project = _a_project_with_code_and_docs(tmp_path)

        _init(project, THE_FLAG, "import")

        nodes, _ = _graph_on_disk(project)
        assert [n for n in nodes if n.get("kind") == "service"] == [], nodes
        assert sorted(_unparented_domains(project)) == sorted(
            node["ref_id"] for node in nodes if node.get("kind") == "domain"
        )
        # Anti-vacuity: the run did write domains, so "all of them unparented" is
        # a statement about nodes rather than about an empty file.
        assert _unparented_domains(project), nodes

    def test_the_lint_the_adopter_runs_next_evaluates_no_rule(
        self, tmp_path: Path
    ) -> None:
        """So its clean report is an absence of rules, not an absence of faults."""
        from beadloom.application.reindex import incremental_reindex
        from beadloom.graph.linter import lint

        project = _a_project_with_code_and_docs(tmp_path)
        _init(project, THE_FLAG, "import")

        result = lint(project, reindex=incremental_reindex)

        assert result.rules_evaluated == 0
        assert not result.has_errors


class TestWhatABlindVerdictWouldReport:
    """Anti-vacuity for this whole module, and the ceiling of the syntactic one.

    `tests/test_init_branches_that_reach_the_bootstrap.py` asserts that a verdict
    call follows every branch that writes a graph file. `--yes --mode both`
    satisfied that and was wrong anyway, because the verdict reads the INDEX:
    `gate.lint_step` does not re-index, by design, so a graph file written after
    the run's reindex is invisible to it.

    This case demonstrates that difference on the same fixture the agreement
    cases use, which is what makes those cases claims rather than tautologies. It
    asserts nothing about `init` — `.14` fixed `init` by moving the reindex after
    the last writer — only about what the verdict's own reader can and cannot
    see.

    Declared: this case does NOT fail against the pre-`.14` tree and cannot.
    `lint_step` read the index there exactly as it does now; what changed is when
    `init` calls it. If `lint_step` is ever given a reindex of its own, this case
    goes red, and the right answer then is to retire it — the blindness it
    characterises would be gone.
    """

    def test_a_graph_file_written_after_the_reindex_is_invisible_to_the_verdict(
        self, tmp_path: Path
    ) -> None:
        project = _a_project_with_code_and_docs(tmp_path)
        assert _init(project, THE_FLAG, "both").exit_code == 0
        imported = project / ".beadloom" / "_graph" / THE_IMPORT_FILE
        data = yaml.safe_load(imported.read_text(encoding="utf-8"))
        data["nodes"].append(
            {"ref_id": THE_ADDED_ORPHAN, "kind": "domain", "summary": "No parent."}
        )
        imported.write_text(
            yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        judged_from_the_index = lint_step(project)

        assert judged_from_the_index.passed, (
            "the verdict's own reader now sees a graph file written after the "
            "reindex, so `lint_step` has gained one and the blindness this case "
            "characterises is gone — retire it rather than weakening it: "
            f"{judged_from_the_index.summary}"
        )
        assert _lint_strict(project) != 0, (
            "the tree the verdict called clean is not red, so this fixture no "
            "longer distinguishes a stale index from a fresh one and the "
            "agreement cases above would hold vacuously"
        )
