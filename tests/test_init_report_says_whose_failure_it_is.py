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
