"""The failure report names whose graph and whose rules, over the whole product.

BDL-067 `.17`, the review of `.16`'s major 2. The report used to choose BOTH
halves of its headline and the sentence under them from ONE boolean — whether
this run authored `rules.yml` — so the corner where the rules are ours and the
failing node is not printed the corner where both are ours. Measured by the
review over two commands on one tree: `init --yes --mode import` left unparented
domains in `imported.yml`, the wizard's re-init wrote `domain-needs-parent`, and
the report said "the graph this command just wrote" about nodes written by an
earlier run and asked the adopter to file a bug against `import_docs`, which had
not run at all.

Two facts vary independently, so the population is their product, and the cases
here are the product rather than a selection from it. The expected sentence for
each corner is read out of `setup._ATTRIBUTION` rather than spelled again, and
`test_every_corner_of_the_table_has_a_case` binds the two together: a fifth
corner, or a reworded sentence, fails here instead of leaving a corner asserted
by nobody.

Each corner is reached by ARRANGING THE TREE, never by patching the reporter.
What the report says has to follow from what is on disk, since that is the only
thing an adopter can check it against.

The fixture is a project that is not us (`orders-web`, a flat `src/index.ts`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from beadloom.services.commands.setup import (
    _ATTRIBUTION,
    _GRAPH_HALF,
    _RULES_HALF,
    _graph_file_of_each_node,
    _graph_nodes_now,
)
from tests.adopter_project import python_project, typescript_project
from tests.test_init_verdict_over_its_own_rules import (
    PACKAGE_BINDING,
    _a_bootstrap_that_forgets_the_edge,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

#: A rules file the ADOPTER wrote, requiring what the bootstrap's own generated
#: rule requires. Written by hand so that `bootstrap_project` — which never
#: rewrites a rules file already on disk — leaves it alone and the run meets a
#: rule it did not author.
A_DOMAIN_RULE_THE_ADOPTER_WROTE = """\
version: 1
rules:
  - name: domain-needs-parent
    description: Every domain must have a part_of edge
    require:
      for:
        kind: domain
      has_edge_to: {}
      edge_kind: part_of
"""

#: A rule about services, which no graph the bootstrap writes can satisfy: the
#: root service node has no parent by definition, which is why `generate_rules`
#: dropped the rule. A project carrying it by hand has a red verdict of its own.
A_SERVICE_RULE_THE_ADOPTER_WROTE = """\
version: 1
rules:
  - name: service-needs-parent
    description: Every service must have a part_of edge
    require:
      for:
        kind: service
      has_edge_to: {}
      edge_kind: part_of
"""

#: An `imported.yml` an earlier run left behind, holding one domain with no
#: parent. This is what `init --yes --mode import` writes on a virgin tree, and
#: it is written directly here so the corner does not depend on running a second
#: command whose own behaviour is under test elsewhere.
AN_IMPORT_FILE_FROM_AN_EARLIER_RUN = {
    "nodes": [
        {
            "ref_id": "payments",
            "kind": "domain",
            "summary": "Imported from payments.md",
            # `import_docs` writes this field for every node it creates, and the
            # fixture omitted it until BDL-067 `.21`. It matters: a node with no
            # doc gets a skeleton, and writing that skeleton patches `docs:` back
            # into the file the node is in — so THIS run would have written the
            # inherited file and two of the four corners would stop being the
            # corners they are named after. That is not a fixture detail, it is
            # what `.21` changed on the `--bootstrap` branch: `generate_skeletons`
            # now reads the whole tree there too, so it reaches inherited nodes
            # the way it always did from the wizard.
            "docs": ["docs/payments.md"],
        }
    ]
}

#: The node in that file, and the one every report below has to name.
THE_INHERITED_ORPHAN = "payments"

#: A rule the adopter wrote whose findings name NO node. `forbid_import`
#: violations carry `from_ref_id=None` (`graph/rules/evaluators.py`), so they
#: reach the report as a finding about a file crossing rather than about a graph
#: node — and `bootstrap_project` never rewrites a rules file already on disk, so
#: an adopter's own boundary rule survives into `init --bootstrap` and produces
#: exactly that. The review of `.20` reasoned this path out and could not stage
#: it (no tree-sitter Python grammar in that environment, so the `from:` glob
#: matched nothing and the rule went inert); it is staged here.
A_BOUNDARY_RULE_THE_ADOPTER_WROTE = """\
version: 1
rules:
  - name: no-billing-to-ledger
    description: "Billing must not import ledger directly"
    forbid_import:
      from: "src/invoice_svc/billing/**"
      to: "invoice_svc/ledger**"
"""

#: Its name, which is the whole of the line the report prints for it.
THE_BOUNDARY_RULE = "no-billing-to-ledger"


def _write_graph_file(project_root: Path, name: str, data: dict[str, Any]) -> None:
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / name).write_text(
        yaml.safe_dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _an_earlier_import_run_left_a_graph_file(project_root: Path) -> None:
    """Write `imported.yml` and the document its node points at.

    Both halves, because `import_docs` writes both: a node whose `docs:` names a
    file that is not there is not a state any writer in the product produces, and
    it is the state in which this run would rewrite the inherited file.
    """
    _write_graph_file(project_root, "imported.yml", AN_IMPORT_FILE_FROM_AN_EARLIER_RUN)
    docs = project_root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "payments.md").write_text("# Payments\n", encoding="utf-8")


def _write_rules(project_root: Path, text: str) -> None:
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "rules.yml").write_text(text, encoding="utf-8")


def _bootstrap(project_root: Path) -> Any:
    return CliRunner().invoke(
        main, ["init", "--bootstrap", "--project", str(project_root)]
    )


def _wizard(project_root: Path, *prompts: str) -> Any:
    with (
        patch("rich.prompt.Prompt.ask", side_effect=list(prompts)),
        patch("rich.prompt.Confirm.ask", return_value=False),
    ):
        return CliRunner().invoke(main, ["init", "--project", str(project_root)])


def _both_ours(project: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """A virgin bootstrap that contradicts the rules it wrote in the same run.

    Nothing is on disk beforehand, so `bootstrap_project` writes `services.yml`
    AND `rules.yml`, and the sabotage strips the edges back out. This is
    BDL-UX #192's own shape, and the only corner where Beadloom is at fault.
    """
    _a_bootstrap_that_forgets_the_edge(monkeypatch, PACKAGE_BINDING)
    return _bootstrap(project)


def _graph_ours_rules_theirs(project: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The adopter's own rule, met by the graph this run wrote.

    `service-needs-parent` is failed by the root node of any graph the bootstrap
    writes, so the failing node comes from `services.yml`, which this run wrote,
    and the rules file was already there.
    """
    _write_rules(project, A_SERVICE_RULE_THE_ADOPTER_WROTE)
    return _bootstrap(project)


def _graph_theirs_rules_ours(project: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The rule this run wrote, met by a graph file an earlier run left.

    The review's reproduction, with the earlier run's output written directly:
    `imported.yml` holds an unparented domain, no `rules.yml` is on disk, and the
    wizard's bootstrap writes `domain-needs-parent` and meets it.
    """
    _an_earlier_import_run_left_a_graph_file(project)
    return _wizard(project, "overwrite", "bootstrap", "yes")


def _neither_ours(project: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Both the rule and the failing node predate this run.

    The adopter's `domain-needs-parent` and an earlier run's `imported.yml` are
    both on disk. The bootstrap writes `services.yml`, whose own domain gets its
    parent edge and passes, so the only failing node is one this run did not
    write, under a rule this run did not write.
    """
    _write_rules(project, A_DOMAIN_RULE_THE_ADOPTER_WROTE)
    _an_earlier_import_run_left_a_graph_file(project)
    return _bootstrap(project)


#: One arrangement per corner of `(this run wrote the graph file the failing node
#: came from, this run wrote rules.yml)`. Keyed by the corner so the table and
#: the cases are checked against each other rather than kept in step by hand.
THE_CORNERS: dict[tuple[bool, bool], Callable[[Path, pytest.MonkeyPatch], Any]] = {
    (True, True): _both_ours,
    (True, False): _graph_ours_rules_theirs,
    (False, True): _graph_theirs_rules_ours,
    (False, False): _neither_ours,
}

CORNER_IDS = [
    f"graph-{'ours' if graph else 'theirs'}-rules-{'ours' if rules else 'theirs'}"
    for graph, rules in THE_CORNERS
]


def _the_report(project: Path, monkeypatch: pytest.MonkeyPatch, corner: Any) -> str:
    result = THE_CORNERS[corner](project, monkeypatch)
    assert result.exit_code != 0, (
        "the arrangement for this corner left a green tree, so the report below "
        f"was never printed and the case asserts nothing. Output: {result.output!r}"
    )
    return str(result.output)


class TestTheTableAndTheCasesAreTheSameSet:
    """The two enumerations, bound to each other.

    A corner added to `_ATTRIBUTION` with no arrangement here is a sentence
    nobody has read; an arrangement for a corner the table does not have is a
    case that cannot be checked against anything.
    """

    def test_every_corner_of_the_table_has_a_case(self) -> None:
        assert set(_ATTRIBUTION) == set(THE_CORNERS), (
            sorted(set(_ATTRIBUTION) ^ set(THE_CORNERS))
        )

    def test_the_table_is_the_full_product(self) -> None:
        """Anti-vacuity: a table with one key would make the cases agree cheaply."""
        assert set(_ATTRIBUTION) == {(True, True), (True, False), (False, True), (False, False)}

    def test_both_halves_of_the_headline_have_both_answers(self) -> None:
        assert set(_GRAPH_HALF) == {True, False}
        assert set(_RULES_HALF) == {True, False}


@pytest.mark.parametrize("corner", list(THE_CORNERS), ids=CORNER_IDS)
class TestEachCornerPrintsItsOwnSentence:
    """The report says which of the four situations the adopter is in."""

    def test_the_attribution_sentence_is_the_table_s(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corner: Any
    ) -> None:
        output = _the_report(typescript_project(tmp_path / "orders-web").root, monkeypatch, corner)

        assert _ATTRIBUTION[corner] in output, (corner, output)

    def test_no_other_corner_s_sentence_is_printed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corner: Any
    ) -> None:
        """One situation is described, not several. This is the case that bites.

        Against the pre-`.17` report, three corners printed the sentence of a
        corner they were not in, because one boolean chose it.
        """
        output = _the_report(typescript_project(tmp_path / "orders-web").root, monkeypatch, corner)

        wrong = [
            sentence
            for key, sentence in _ATTRIBUTION.items()
            if key != corner and sentence in output
        ]
        assert wrong == [], (corner, wrong, output)

    def test_the_headline_names_whose_graph_and_whose_rules(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corner: Any
    ) -> None:
        graph_is_ours, rules_are_ours = corner
        output = _the_report(typescript_project(tmp_path / "orders-web").root, monkeypatch, corner)

        assert _GRAPH_HALF[graph_is_ours] in output, (corner, output)
        assert _RULES_HALF[rules_are_ours] in output, (corner, output)
        assert _GRAPH_HALF[not graph_is_ours] not in output, (corner, output)
        assert _RULES_HALF[not rules_are_ours] not in output, (corner, output)


class TestOnlyOurOwnContradictionAsksForABugReport:
    """A bug report is asked for in one corner, and refused in the other three.

    The cost of getting this wrong falls on the adopter: a report filed against
    `import_docs` for a run in which `import_docs` did not execute is time spent
    on our attribution error. So the request is stated as a property of the
    table — present in exactly one corner — rather than checked in the one case
    somebody remembered.
    """

    THE_BUG_REPORT_REQUEST = "please report it"

    def test_exactly_one_corner_of_the_table_asks_for_one(self) -> None:
        asking = [
            key
            for key, sentence in _ATTRIBUTION.items()
            if self.THE_BUG_REPORT_REQUEST in sentence
        ]

        assert asking == [(True, True)], asking

    @pytest.mark.parametrize("corner", list(THE_CORNERS), ids=CORNER_IDS)
    def test_the_report_asks_only_where_the_table_does(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corner: Any
    ) -> None:
        output = _the_report(typescript_project(tmp_path / "orders-web").root, monkeypatch, corner)

        asked = self.THE_BUG_REPORT_REQUEST in output
        assert asked == (corner == (True, True)), (corner, output)


class TestTheInheritedOrphanIsNamedAgainstItsOwnFile:
    """The node and the file it came from, in the corners where it is not ours.

    Naming the file is `.14`'s fix; naming it in a run that did not write that
    file is what makes the sentence above checkable by the adopter.
    """

    @pytest.mark.parametrize(
        "corner", [(False, True), (False, False)], ids=["rules-ours", "neither-ours"]
    )
    def test_the_line_names_the_import_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corner: Any
    ) -> None:
        output = _the_report(typescript_project(tmp_path / "orders-web").root, monkeypatch, corner)

        named = [line for line in output.splitlines() if THE_INHERITED_ORPHAN in line]
        assert named, output
        assert all(".beadloom/_graph/imported.yml" in line for line in named), named


class TestTheWithdrawalIsNotAnAdmissionOfFault:
    """The withdrawal precedes every corner, including the three that are not ours.

    It says the check did not pass, which is true wherever the fault lies. If it
    ever came to say more than that, it would be a fifth sentence choosing itself
    from no fact at all — the shape BDL-067 `.17` exists to remove.
    """

    @pytest.mark.parametrize("corner", list(THE_CORNERS), ids=CORNER_IDS)
    def test_it_is_printed_in_every_corner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corner: Any
    ) -> None:
        from beadloom.services.commands.setup import WITHDRAWN_COMPLETION_CLAIM

        output = _the_report(typescript_project(tmp_path / "orders-web").root, monkeypatch, corner)

        assert WITHDRAWN_COMPLETION_CLAIM in output, (corner, output)


def _a_project_whose_own_boundary_rule_it_breaks(root: Path) -> Path:
    """A Python project that is not us, with one import its own rule forbids.

    Two packages under `src/invoice_svc/` and one crossing between them, so the
    adopter's `forbid_import` rule has something to match. The rule is on disk
    before `init` runs, which is what makes it theirs: `generate_rules` writes
    `rules.yml` only when there is none.
    """
    project = python_project(root).root
    ledger = project / "src" / "invoice_svc" / "ledger"
    billing = project / "src" / "invoice_svc" / "billing"
    (ledger / "entries.py").write_text("def book() -> int:\n    return 1\n", encoding="utf-8")
    (billing / "service.py").write_text(
        "from invoice_svc.ledger.entries import book\n\n\ndef charge() -> int:\n"
        "    return book()\n",
        encoding="utf-8",
    )
    _write_rules(project, A_BOUNDARY_RULE_THE_ADOPTER_WROTE)
    return project


class TestAFindingAboutNoNodeIsStillAttributed:
    """The report's coarsest grain, over the finding that has no finer one.

    Every case above is about a finding that names a node, because that is what
    a `require` rule produces and `generate_rules` writes nothing else. A
    `forbid_import` violation names a FILE and a line, and carries no node at
    all — so `_failing_rule_lines` prints the bare rule name and
    `_this_run_wrote_the_graph_that_fails` has nothing to attribute per node and
    falls back to "did this run write any graph file". Until this case, nothing
    in the suite reached either branch, and the review of `.20` recorded that as
    the one measurement it could not complete.

    The corner is `(True, False)`: this run wrote a graph file and did not write
    `rules.yml`. The corner that would misattribute — `(True, True)` with a
    node-less finding — is unreachable, because `generate_rules` writes only
    `require` rules and every finding of those names a node.
    """

    def test_the_run_is_red_on_the_adopters_own_boundary_rule(
        self, tmp_path: Path
    ) -> None:
        """The premise: the rule is live, not inert, and it fails."""
        project = _a_project_whose_own_boundary_rule_it_breaks(tmp_path)

        result = _bootstrap(project)

        assert result.exit_code == 1, result.output

    def test_the_line_is_the_bare_rule_name(self, tmp_path: Path) -> None:
        """A finding about no single node keeps the rule and names nothing else.

        An unattributed line is still true; a guessed node would not be.
        """
        project = _a_project_whose_own_boundary_rule_it_breaks(tmp_path)

        output = _bootstrap(project).output

        assert f"  {THE_BOUNDARY_RULE}\n" in output, output
        assert f"{THE_BOUNDARY_RULE}:" not in output, output

    def test_it_prints_the_corner_the_tree_is_in(self, tmp_path: Path) -> None:
        """`(True, False)` — this run wrote a graph file, the rules are theirs."""
        project = _a_project_whose_own_boundary_rule_it_breaks(tmp_path)

        output = _bootstrap(project).output

        assert _ATTRIBUTION[True, False] in output, output

    def test_no_other_corner_s_sentence_is_printed(self, tmp_path: Path) -> None:
        """The case that bites: three corners share most of their wording."""
        project = _a_project_whose_own_boundary_rule_it_breaks(tmp_path)

        output = _bootstrap(project).output

        for corner, sentence in _ATTRIBUTION.items():
            if corner != (True, False):
                assert sentence not in output, (corner, output)


class TestAGraphFileThatCannotBeReadIsSkipped:
    """`_graph_file_of_each_node` hands the adopter a report, not a traceback.

    It is reading `.beadloom/_graph/` at the moment a failure is being explained,
    and `init` can meet a hand-edited file there. A file it cannot parse costs
    one unattributed node; raising on it would replace the whole report.
    """

    def _graph_dir(self, tmp_path: Path) -> Path:
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        return graph_dir

    def test_a_readable_file_is_mapped(self, tmp_path: Path) -> None:
        """Anti-vacuity: a scan that mapped nothing would pass the two below."""
        graph_dir = self._graph_dir(tmp_path)
        (graph_dir / "services.yml").write_text(
            "nodes:\n  - ref_id: billing\n    kind: domain\n", encoding="utf-8"
        )

        assert _graph_file_of_each_node(tmp_path) == {
            "billing": ".beadloom/_graph/services.yml"
        }

    def test_a_file_that_is_not_readable_yaml_is_skipped(self, tmp_path: Path) -> None:
        graph_dir = self._graph_dir(tmp_path)
        (graph_dir / "services.yml").write_text(
            "nodes:\n  - ref_id: billing\n    kind: domain\n", encoding="utf-8"
        )
        (graph_dir / "hand-edited.yml").write_text("nodes: [oops\n", encoding="utf-8")

        assert _graph_file_of_each_node(tmp_path) == {
            "billing": ".beadloom/_graph/services.yml"
        }

    def test_a_file_that_is_not_a_mapping_is_skipped(self, tmp_path: Path) -> None:
        """Valid YAML, wrong shape — a list where a mapping was expected."""
        graph_dir = self._graph_dir(tmp_path)
        (graph_dir / "services.yml").write_text(
            "nodes:\n  - ref_id: billing\n    kind: domain\n", encoding="utf-8"
        )
        (graph_dir / "a-list.yml").write_text("- billing\n- ledger\n", encoding="utf-8")

        assert _graph_file_of_each_node(tmp_path) == {
            "billing": ".beadloom/_graph/services.yml"
        }


#: An inherited graph file holding one unparented domain and NO `docs:` field.
#: The field is the whole of the difference against `AN_INHERITED_FILE_ALREADY
#: _DOCUMENTED` below, and it is what decides whether this run touches the file:
#: `generate_skeletons` writes a README for every node that has no document and
#: patches `docs:` back into the graph file the node is in.
AN_INHERITED_FILE_WITH_NO_DOCUMENT = {
    "nodes": [
        {
            "ref_id": "ledger",
            "kind": "domain",
            "summary": "Left by an earlier run, with no parent and no document.",
        }
    ]
}

#: The same file, with the document an earlier run would have written for it.
#: This is the state `import_docs` actually leaves — it writes a `docs:` entry
#: for every node it creates — and it is why `AN_IMPORT_FILE_FROM_AN_EARLIER_RUN`
#: above carries one.
AN_INHERITED_FILE_ALREADY_DOCUMENTED = {
    "nodes": [
        {
            "ref_id": "ledger",
            "kind": "domain",
            "summary": "Left by an earlier run, with no parent.",
            "docs": ["docs/ledger.md"],
        }
    ]
}

#: The node in both of them, and the one the report names either way.
THE_INHERITED_ORPHAN_IN_THE_LEGACY_FILE = "ledger"
THE_INHERITED_FILE = "legacy.yml"


def _a_tree_carrying_an_undocumented_orphan(tmp_path: Path) -> Path:
    """A project that is not us, carrying one graph file an earlier run wrote.

    No `rules.yml`, so this run writes its own and the rules half of every corner
    below is `True`. That is deliberate: holding one half fixed leaves the
    annotation as the only thing that can move the other.
    """
    project = typescript_project(tmp_path).root
    _write_graph_file(project, THE_INHERITED_FILE, AN_INHERITED_FILE_WITH_NO_DOCUMENT)
    return project


def _a_tree_whose_orphan_already_has_its_document(tmp_path: Path) -> Path:
    """The same tree, one field further on: the node names a document that exists."""
    project = typescript_project(tmp_path).root
    _write_graph_file(project, THE_INHERITED_FILE, AN_INHERITED_FILE_ALREADY_DOCUMENTED)
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ledger.md").write_text("# Ledger\n", encoding="utf-8")
    return project


class TestWhatCountsAsWritingTheFileTheFailingNodeCameFrom:
    """The attribution instrument, over a file this run only ANNOTATED.

    BDL-067 `.22`, and the consequence `.21` reported rather than redesigned.
    `.21` gave `--bootstrap` the same call shape as the other two entry points,
    so it now runs `generate_skeletons` over the whole tree — which writes a
    README for every node with no document and patches `docs:` back into the
    graph file that node sits in, inherited files included. The instrument
    behind `_GRAPH_HALF` and `_ATTRIBUTION` asks whether the bytes of that file
    changed during the run, so "this run wrote the file the failing node came
    from" is now TRUE for a file this run neither created nor put a node in.

    MEASURED, on two trees differing by one field on one node:

        legacy.yml's node has no `docs:`  -> (True, True):  "the graph this
            command just wrote ... This is a defect in Beadloom's bootstrap
            rather than in your project — please report it"
        legacy.yml's node has `docs:`     -> (False, True): "the graph already
            in .beadloom/_graph/ ... the rule(s) this command wrote are meeting
            a graph that predates them"

    Same rule, same node, same file, two answers — and the first of them is the
    bug-report request `.17` built the table to confine to the one corner where
    Beadloom is at fault. An adopter on the first tree is asked to file a report
    about a node no writer in this run produced.

    WHAT THESE CASES ARE FOR, since the question is not this bead's to settle.
    `.21` states the attribution question is per FILE and per BYTES, and that
    per-node-CREATED is a different instrument. Both answers above are recorded
    here as the answers the product gives TODAY, so that changing the instrument
    is a test failure with a measurement attached rather than a silent re-answer
    — and so that the seventh review decides it holding both corners rather than
    one. If `.23` moves to the finer grain, the two cases below swap corners and
    say so; nothing here claims the present answer is the right one.

    THEY DID NOT SWAP, and that is the measurement `.24` owes this class. `.23`
    decided the finer grain — the graph half is now keyed on a per-node
    created-or-changed sample (`setup._graph_nodes_now`) — and `.24` implemented
    it, and BOTH cases below still print the corner they printed before. The
    reason is in `test_the_run_annotates_the_inherited_file_it_did_not_write`
    just below, which was already measuring it: on the first tree the annotation
    goes INTO the failing node itself, so `ledger` gains a `docs:` field and is a
    node this run changed at the file grain and at the node grain alike. The
    decision's stated outcome — that this corner stops asking for a bug report —
    does not follow from the grain it chose, on the pair it was decided over.

    What the finer grain does move is the case where the annotated node and the
    failing node are DIFFERENT nodes in one file, which is the common shape of an
    inherited graph file and is measured in
    `TestTheGraphHalfIsAskedOfTheNodeAndNotOfTheFile` below. Both classes are
    kept: this one records what the instrument still does, that one records what
    it now does, and an instrument change that moves either has to come to both.
    """

    def _corners_printed(self, output: str) -> list[Any]:
        return [key for key, sentence in _ATTRIBUTION.items() if sentence in output]

    def test_the_run_annotates_the_inherited_file_it_did_not_write(
        self, tmp_path: Path
    ) -> None:
        """The premise, measured: the bytes change, and only the `docs:` field.

        Without this the two cases below would rest on an assumption about what
        `generate_skeletons` touches. The node is the same node afterwards —
        same ref_id, same kind, same summary, still no parent — so nothing about
        the failure changed, only the file's bytes.
        """
        project = _a_tree_carrying_an_undocumented_orphan(tmp_path)
        path = project / ".beadloom" / "_graph" / THE_INHERITED_FILE
        before = yaml.safe_load(path.read_text(encoding="utf-8"))

        _bootstrap(project)

        after = yaml.safe_load(path.read_text(encoding="utf-8"))
        [node] = after["nodes"]
        assert node["docs"] == ["docs/domains/ledger/README.md"], after
        assert {k: v for k, v in node.items() if k != "docs"} == before["nodes"][0]

    def test_a_file_this_run_only_annotated_is_attributed_to_this_run(
        self, tmp_path: Path
    ) -> None:
        """Recorded, not endorsed: today the annotation makes the file ours.

        The report names `legacy.yml` beside the node and calls it "the graph
        this command just wrote" in the same paragraph, and asks the adopter for
        a bug report about it.
        """
        project = _a_tree_carrying_an_undocumented_orphan(tmp_path)

        output = _bootstrap(project).output

        assert self._corners_printed(output) == [(True, True)], output
        assert _GRAPH_HALF[True] in output, output
        assert f".beadloom/_graph/{THE_INHERITED_FILE}" in output, output

    def test_the_same_file_left_untouched_is_attributed_to_the_earlier_run(
        self, tmp_path: Path
    ) -> None:
        """The other side of the pair: one `docs:` field, one different answer."""
        project = _a_tree_whose_orphan_already_has_its_document(tmp_path)

        output = _bootstrap(project).output

        assert self._corners_printed(output) == [(False, True)], output
        assert _GRAPH_HALF[False] in output, output

    def test_the_two_trees_fail_the_same_rule_on_the_same_node(
        self, tmp_path: Path
    ) -> None:
        """Anti-vacuity, and the whole point of stating the pair.

        Two different sentences are only a finding if the failure underneath
        them is the same failure. Both trees are red, both name
        `domain-needs-parent` against `ledger` in `legacy.yml`, and neither of
        those nodes was written by the run that reports it. What differs is the
        attribution, and nothing else does.
        """
        annotated = _bootstrap(_a_tree_carrying_an_undocumented_orphan(tmp_path / "a"))
        untouched = _bootstrap(
            _a_tree_whose_orphan_already_has_its_document(tmp_path / "b")
        )

        the_finding = (
            f"domain-needs-parent: {THE_INHERITED_ORPHAN_IN_THE_LEGACY_FILE} "
            f"(.beadloom/_graph/{THE_INHERITED_FILE})"
        )
        assert annotated.exit_code == 1, annotated.output
        assert untouched.exit_code == 1, untouched.output
        assert the_finding in annotated.output, annotated.output
        assert the_finding in untouched.output, untouched.output
        assert self._corners_printed(annotated.output) != self._corners_printed(
            untouched.output
        )


#: The sibling that moves and the orphan that does not, in ONE file. `warehouse`
#: has a parent, so it passes every rule the bootstrap writes, and it has no
#: `docs:`, so `generate_skeletons` writes it a README and patches the field
#: back — which changes the FILE's bytes while leaving `ledger`'s node entry
#: exactly as an earlier run wrote it.
A_FILE_WHOSE_OTHER_NODE_GETS_ANNOTATED = {
    "nodes": [
        {
            "ref_id": THE_INHERITED_ORPHAN_IN_THE_LEGACY_FILE,
            "kind": "domain",
            "summary": "Left by an earlier run, with no parent.",
            "docs": ["docs/ledger.md"],
        },
        {
            "ref_id": "warehouse",
            "kind": "domain",
            "summary": "Left by the same earlier run, parented, and undocumented.",
        },
    ],
    "edges": [
        {"src": "warehouse", "dst": THE_INHERITED_ORPHAN_IN_THE_LEGACY_FILE,
         "kind": "part_of"},
    ],
}


def _a_tree_whose_annotated_node_is_not_the_failing_one(tmp_path: Path) -> Path:
    project = typescript_project(tmp_path).root
    _write_graph_file(project, THE_INHERITED_FILE, A_FILE_WHOSE_OTHER_NODE_GETS_ANNOTATED)
    docs = project / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ledger.md").write_text("# Ledger\n", encoding="utf-8")
    return project


class TestTheGraphHalfIsAskedOfTheNodeAndNotOfTheFile:
    """The attribution instrument at the grain the review of `.23` decided.

    The graph half of `_ATTRIBUTION` used to be read off the BYTES of the file
    the failing node came from, so any writer that touched that file for any
    reason made every node in it this run's. `generate_skeletons` touches
    inherited files by default — it writes a README for every node in the tree
    that has none and patches `docs:` back — so the corner that asks the adopter
    for a bug report fired on the common path.

    Decided by the review of `.23` and implemented here: the graph half is keyed
    on a before/after sample of `{ref_id: the node as written}`, taken in the
    same one place the file digests are, and "this run wrote the node" means the
    ref_id was absent before or its content differs. CREATED-OR-CHANGED rather
    than CREATED, so a node this run rewrote into failing — a `kind` or `source`
    change on a ref_id that was already there — stays ours; an instrument whose
    error direction is "hide our own defect" is what this epic exists because of.

    The byte digest is kept for the two questions it answers correctly: the
    verdict PRECONDITION (did this run change the adopter's tree at all) and the
    `rules.yml` half, since a rules file holds no nodes and the file is its grain.

    THE LIMITATION CARRIES OVER AT THE FINER GRAIN, and is re-stated because it
    is now about a node rather than a file: a file that would not parse is not in
    either sample, so a node in a file unreadable before the run and readable
    after it reads as one this run wrote, and a node whose entry is rewritten
    byte-for-byte identically reads as one it did not.
    """

    def _corners_printed(self, output: str) -> list[Any]:
        return [key for key, sentence in _ATTRIBUTION.items() if sentence in output]

    def test_the_run_annotates_the_file_without_touching_the_failing_node(
        self, tmp_path: Path
    ) -> None:
        """The premise: the file moves, the failing node's own entry does not."""
        project = _a_tree_whose_annotated_node_is_not_the_failing_one(tmp_path)
        path = project / ".beadloom" / "_graph" / THE_INHERITED_FILE
        before = yaml.safe_load(path.read_text(encoding="utf-8"))

        _bootstrap(project)

        after = yaml.safe_load(path.read_text(encoding="utf-8"))
        by_ref = {node["ref_id"]: node for node in after["nodes"]}
        assert by_ref["warehouse"]["docs"] == ["docs/domains/warehouse/README.md"], after
        assert by_ref[THE_INHERITED_ORPHAN_IN_THE_LEGACY_FILE] == before["nodes"][0]

    def test_the_failing_node_is_the_earlier_runs_though_its_file_moved(
        self, tmp_path: Path
    ) -> None:
        """The corner the decision was taken for, at the grain it was taken at.

        Under the byte instrument this printed `(True, True)` — "This is a defect
        in Beadloom's bootstrap ... please report it" — about a node no writer in
        this run produced, because a SIBLING node in the same file was annotated.
        """
        project = _a_tree_whose_annotated_node_is_not_the_failing_one(tmp_path)

        output = _bootstrap(project).output

        assert self._corners_printed(output) == [(False, True)], output
        assert _GRAPH_HALF[False] in output, output
        assert f".beadloom/_graph/{THE_INHERITED_FILE}" in output, output


class TestEachSentenceSpeaksAtTheGrainItsKeyIsReadAt:
    """A sentence and the fact that selected it cannot disagree.

    BDL-067 `.27`, the review of `.26`'s major 1. Before `.24` the graph half's
    sentences were true BY CONSTRUCTION: the corner was selected by the BYTES of
    the file the failing node came from, so a claim about that file could not
    disagree with what selected it. `.24` moved the key to the NODE — created or
    changed — and left both denials saying `graph file(s)`, so the claim became
    independent of the fact behind it, and on the very corner `.24` created it is
    false. MEASURED by the review, twice, on the tree
    `_a_tree_whose_annotated_node_is_not_the_failing_one` builds: the run rewrote
    `legacy.yml` (the sibling gained a `docs:` field and every entry was
    re-serialised) while the report said "This command did not write the graph
    file(s) named beside the node(s) above — they were already on disk". An
    adopter's `git diff` shows the file modified and the sentence denying it.

    So the property here is not a wording preference, and the fix is not to
    reword until it reads well. Each half of the key is read at one grain, and
    the sentence that half selects claims things at that grain and no other:

        graph half   `_graph_nodes_now` / `_nodes_this_run_wrote`, per ref_id
                     -> its denials are about NODES
        rules half   `_graph_files_now` / `_graph_files_this_run_wrote`, per file
                     -> its denial is about a FILE, and the file is `rules.yml`

    Restated as the property that makes the sentence uncheckable-against-nothing:
    a corner whose graph half is `False` was selected because the failing node's
    entry is byte-identical to the one that was there before the run, so "this
    command did not write the node" is again true by construction — while "this
    command did not write the file" is a claim nothing in the key supports.

    The table is checked as a table and the printed sentence is checked on the
    tree that falsifies the old one, because the epic's own history is that four
    of six defect instances were a sentence that was true of one shape while a
    neighbouring shape existed.
    """

    #: The one file a sentence may name while denying authorship: the rules half
    #: IS read at the file grain (`"rules.yml" in files_this_run_wrote`), so a
    #: claim about that file is a claim its key supports. Removed before the
    #: graph half's own claim is inspected, so that a future wording which denies
    #: both halves in one sentence is not read as a file claim about the graph.
    THE_FILE_THE_RULES_HALF_IS_READ_AT = ".beadloom/_graph/rules.yml"

    #: The corners whose graph half denies authorship. Named rather than
    #: filtered inline so the anti-vacuity case below can assert it is not empty.
    THE_CORNERS_THAT_DENY_WRITING_THE_GRAPH = tuple(
        corner for corner in _ATTRIBUTION if not corner[0]
    )

    def _the_graph_claim(self, sentence: str) -> str:
        return sentence.replace(self.THE_FILE_THE_RULES_HALF_IS_READ_AT, "")

    def test_there_are_corners_that_deny_writing_the_graph(self) -> None:
        """Anti-vacuity: an empty selection would pass both cases below."""
        assert self.THE_CORNERS_THAT_DENY_WRITING_THE_GRAPH == (
            (False, True),
            (False, False),
        ), self.THE_CORNERS_THAT_DENY_WRITING_THE_GRAPH

    def test_a_denial_the_node_key_selected_is_a_denial_about_a_node(self) -> None:
        for corner in self.THE_CORNERS_THAT_DENY_WRITING_THE_GRAPH:
            assert "node" in _ATTRIBUTION[corner], (corner, _ATTRIBUTION[corner])

    def test_no_sentence_the_node_key_selected_claims_anything_about_a_file(self) -> None:
        """The case that bites, and the one that was red when it was written.

        Both `(False, True)` and `(False, False)` said `graph file(s)` about a
        corner chosen by a node.
        """
        for corner in self.THE_CORNERS_THAT_DENY_WRITING_THE_GRAPH:
            claim = self._the_graph_claim(_ATTRIBUTION[corner])
            assert "file" not in claim, (corner, _ATTRIBUTION[corner])
            assert ".yml" not in claim, (corner, _ATTRIBUTION[corner])

    def test_the_printed_sentence_denies_only_what_the_tree_bears_out(
        self, tmp_path: Path
    ) -> None:
        """The review's measurement, as an assertion, end to end.

        The premise is measured here rather than assumed: the file the report
        names beside the failing node IS rewritten by this run, so a sentence
        denying that this command wrote that file is false about this tree. That
        the failing node's own entry did not move is measured by
        `test_the_run_annotates_the_file_without_touching_the_failing_node`
        above, on the same fixture.
        """
        project = _a_tree_whose_annotated_node_is_not_the_failing_one(tmp_path)
        path = project / ".beadloom" / "_graph" / THE_INHERITED_FILE
        before = path.read_bytes()

        output = _bootstrap(project).output

        assert path.read_bytes() != before, (
            "the premise: this run rewrote the file the report names, so a "
            "denial about that file would be false about this tree"
        )
        printed = [sentence for sentence in _ATTRIBUTION.values() if sentence in output]
        assert printed == [_ATTRIBUTION[False, True]], output
        assert "file" not in self._the_graph_claim(printed[0]), output
        assert "node" in printed[0], output


#: An inherited `services.yml` — the one graph file `bootstrap_project` rewrites
#: wholesale. Its two ref_ids are the ones the bootstrap computes for this
#: fixture (`orders-web` from `package.json`, `src` from the source dir), so the
#: run does not add nodes beside these: it REWRITES them. That is the only way a
#: node can be both older than the run and produced by it, and it is an ordinary
#: state — it is what a re-init meets on every project that has been initialised
#: once.
AN_INHERITED_FILE_THE_BOOTSTRAP_REWRITES = {
    "nodes": [
        {
            "ref_id": "orders-web",
            "kind": "service",
            "summary": "The root an earlier run wrote.",
        },
        {
            "ref_id": "src",
            "kind": "domain",
            "summary": "An earlier run's domain, and it had its parent.",
            "source": "src/",
        },
    ],
    "edges": [{"src": "src", "dst": "orders-web", "kind": "part_of"}],
}

#: The node in it this run rewrites into failing, and the file it stays in.
THE_REWRITTEN_NODE = "src"
THE_FILE_THE_BOOTSTRAP_REWRITES = "services.yml"


def _a_tree_this_run_rewrites(tmp_path: Path) -> Path:
    """A project that has been initialised before, carrying no rules file.

    No `rules.yml`, so this run writes `domain-needs-parent` itself and the rules
    half is `True` — which leaves the graph half as the only thing the cases
    below can move, the same way `_a_tree_carrying_an_undocumented_orphan` does.
    """
    project = typescript_project(tmp_path).root
    _write_graph_file(
        project, THE_FILE_THE_BOOTSTRAP_REWRITES, AN_INHERITED_FILE_THE_BOOTSTRAP_REWRITES
    )
    return project


class TestANodeThisRunRewroteIntoFailingIsThisRunS:
    """The error direction of the node grain — BDL-067 `.25`, covering `.24`.

    `.24` moved the graph half from the file's bytes to a per-node
    CREATED-OR-CHANGED sample, and its docstring states why the second half of
    that name is there: created ALONE fixes the annotated-sibling corner and
    mis-attributes in the opposite direction, so the instrument's error direction
    would become "hide our own defect". Nothing asserted it. Both of `.24`'s
    corner cases move a node this run CREATED or a node it left alone; neither
    reaches a node that was already there and that this run rewrote.

    This is that node, and the arrangement is BDL-UX #192's own shape on a
    RE-INIT rather than on a virgin tree: an `services.yml` an earlier run left,
    holding the two ref_ids the bootstrap computes for this project, and the
    sabotage `.17` uses — a `bootstrap_project` that writes the nodes and forgets
    the `part_of` edge. The run rewrites `src` into a domain with no parent and
    then fails its own `domain-needs-parent` over it.

    MEASURED, on this tree. Today: `(True, True)` — "This is a defect in
    Beadloom's bootstrap rather than in your project — please report it".
    With `_nodes_this_run_wrote` reduced to CREATED alone, the same run prints
    `(False, True)` — "the graph already in .beadloom/_graph/ ... predates them"
    — about a node it had just written itself, and the adopter is told to go and
    fix a file Beadloom broke. That is the direction this epic exists because of,
    and it is what these two cases hold shut.
    """

    def _corners_printed(self, output: str) -> list[Any]:
        return [key for key, sentence in _ATTRIBUTION.items() if sentence in output]

    def test_the_run_rewrites_a_node_that_was_already_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The premise, read off the tree rather than off the instrument.

        The ref_id is in the file before and after — so it is not created — and
        its content is not what it was, and the edge that made it pass is gone.
        Measured with `yaml` directly and not with `setup._graph_nodes_now`: a
        premise checked with the instrument under test agrees with it by
        construction.
        """
        project = _a_tree_this_run_rewrites(tmp_path)
        path = project / ".beadloom" / "_graph" / THE_FILE_THE_BOOTSTRAP_REWRITES
        before = yaml.safe_load(path.read_text(encoding="utf-8"))

        _a_bootstrap_that_forgets_the_edge(monkeypatch, PACKAGE_BINDING)
        _bootstrap(project)

        after = yaml.safe_load(path.read_text(encoding="utf-8"))
        was = {node["ref_id"]: node for node in before["nodes"]}
        now = {node["ref_id"]: node for node in after["nodes"]}
        assert THE_REWRITTEN_NODE in was, before
        assert THE_REWRITTEN_NODE in now, after
        assert now[THE_REWRITTEN_NODE] != was[THE_REWRITTEN_NODE]
        assert [e for e in after.get("edges") or [] if e["kind"] == "part_of"] == []

    def test_it_is_attributed_to_this_run_and_asks_for_the_bug_report(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The corner: our own defect, on a tree that was not virgin."""
        project = _a_tree_this_run_rewrites(tmp_path)

        _a_bootstrap_that_forgets_the_edge(monkeypatch, PACKAGE_BINDING)
        result = _bootstrap(project)

        assert result.exit_code == 1, result.output
        assert self._corners_printed(result.output) == [(True, True)], result.output
        assert _GRAPH_HALF[True] in result.output, result.output
        assert (
            f"domain-needs-parent: {THE_REWRITTEN_NODE} "
            f"(.beadloom/_graph/{THE_FILE_THE_BOOTSTRAP_REWRITES})" in result.output
        ), result.output


class TestTheNodeSampleTheGraphHalfIsReadFrom:
    """`setup._graph_nodes_now`, at its own grain — BDL-067 `.25`, covering `.24`.

    The sampler is what the graph half of `_ATTRIBUTION` is computed from, and
    `.24` shipped it with no case that reaches it directly: the two corner cases
    exercise it end to end, where a wrong answer is visible only as a sentence.
    Two of its decisions are load-bearing and one of its limitations is reachable
    in this product, so all three are stated here as cases.

    The rendering decisions are asserted rather than the digest's value: what a
    node hashes to is not a fact anybody depends on, and what two nodes hash the
    SAME to is the whole instrument.
    """

    def _sample(self, tmp_path: Path, files: dict[str, str]) -> dict[str, str]:
        graph_dir = tmp_path / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (graph_dir / name).write_text(text, encoding="utf-8")
        return _graph_nodes_now(tmp_path)

    def test_the_order_the_keys_are_written_in_is_not_a_change(self, tmp_path: Path) -> None:
        """Without this the node grain collapses back into the file grain.

        Every writer in the product rewrites a node's mapping rather than editing
        it in place, so if key order counted as content, every node in a file any
        writer touched would read as this run's — which is exactly the file-grain
        answer `.23` decided against.
        """
        one = self._sample(
            tmp_path / "one",
            {"a.yml": "nodes:\n  - ref_id: ledger\n    kind: domain\n    summary: One\n"},
        )
        reordered = self._sample(
            tmp_path / "two",
            {"a.yml": "nodes:\n  - summary: One\n    kind: domain\n    ref_id: ledger\n"},
        )

        assert one == reordered

    def test_a_value_yaml_types_and_json_does_not_is_sampled_rather_than_raised_on(
        self, tmp_path: Path
    ) -> None:
        """`added: 2026-09-02` loads as a `datetime.date`, which JSON cannot carry.

        The sample is taken in `init` before any writer runs, so a `TypeError`
        here would end the command before it had printed a line, on a graph file
        an adopter edited by hand. `default=str` is what prevents it, and nothing
        else asserted that.

        `init` still does not survive this file — `graph/loader.load_graph`
        renders the same value into JSON without a default and raises there, on
        every branch that reads the tree. That is measured and pinned in
        `tests/test_graph_files_are_read_under_one_policy.py`, and it belongs to
        `beadloom-l22o` rather than here. What this case holds is that the
        REPORT's instrument is not the thing that breaks.
        """
        sampled = self._sample(
            tmp_path,
            {"a.yml": ("nodes:\n  - ref_id: ledger\n    kind: domain\n    added: 2026-09-02\n")},
        )

        assert set(sampled) == {"ledger"}

    def test_two_files_declaring_one_ref_id_leave_one_entry(self, tmp_path: Path) -> None:
        """A limitation, recorded rather than endorsed, and reachable here.

        The sample is keyed by ref_id across the whole directory, so two files
        declaring the same ref_id collapse to whichever sorts last — and the
        report's attribution for that node then follows a file it may not be in.
        This is not hypothetical: the classic `src/<project>/` layout hands the
        root service and its single domain the same ref_id, which BDL-067's brief
        names and tracks as `beadloom-7c6k`. Stated as a case so that fixing the
        collision, or keying the sample by (file, ref_id), fails here rather than
        changing an unstated answer.
        """
        sampled = self._sample(
            tmp_path,
            {
                "a.yml": "nodes:\n  - ref_id: ledger\n    kind: domain\n",
                "b.yml": "nodes:\n  - ref_id: ledger\n    kind: service\n",
            },
        )
        only_b = self._sample(
            tmp_path / "only_b", {"b.yml": "nodes:\n  - ref_id: ledger\n    kind: service\n"}
        )

        assert set(sampled) == {"ledger"}
        assert sampled == only_b
