# beadloom:domain=graph
"""The seams between BDL-062's four dev beads, which no one of them could test.

Each dev bead verified its own work against fixtures it built. Three contracts
run *between* them, and each was held by a hand-written stub on one side of the
seam rather than by the code that actually sits there:

**`.1`'s rule consumes `.3`'s registry.** ``graph-summary-facts`` reports a
claim it cannot check by quoting the reason ``FactRegistry`` gave for declining
the fact. `.1`'s own tests supply that reason from a literal ``FactSet``, so
they pass whatever the registry really says — including nothing. The tests here
build the ``FactSet`` with the real registry over a real project and assert the
finding carries **that** string, so a reworded decline reaches the rule or the
seam fails.

**`.4` renamed ``framework_count`` to ``nodes_with_framework``.** The name is a
key in four places — the scanner's keyword table, the audit's tolerance table,
the count-fact exceptions and the registry's own output — and a claim travels
through all of them before `.1`'s rule prints it. The acceptance scenario
checks the scanner and the registry at their own level; what is checked here is
whether any *path* still resolves the retired name end to end.

**A ``docs_audit.ignore`` triple that matches nothing is not reported by
anything.** `.4` retired one by measuring it by hand and recording the
measurement in a config comment. NO CALLER NO CAPABILITY: nothing computes
whether a suppression still earns its place, and nothing prints it — the
equivalent check exists one layer up for ``overlays.suppress``
(:func:`beadloom.onboarding.config_sync._suppression_drifts`) and has no
counterpart here. Until it does, :class:`TestEverySuppressionStillSuppresses`
is the only thing that would notice, so it runs against this repository's real
config and its real documents.

FAKES PROVE FAKES throughout: every project below is ``invoice-svc``, built by
:func:`tests.adopter_project.indexed_python_project`, and every state is
asserted beside its control — a stand-down beside the same fixture checking
cleanly, a retired name beside the current one.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import reindex
from beadloom.doc_sync.audit import (
    DEFAULT_TOLERANCES,
    FactRegistry,
    IgnoreRule,
    _load_ignore_from_config,
)
from beadloom.doc_sync.scanner import _COUNT_FACTS_WITHOUT_SUFFIX, DocScanner
from beadloom.graph.rules import LIVENESS_RULE_TYPE, evaluate_all, load_rules
from beadloom.graph.rules.summary_facts import SUMMARY_FACTS_RULE_TYPE
from beadloom.infrastructure.db import create_schema, open_db
from tests.adopter_project import IndexedProjectSpec, indexed_python_project

if TYPE_CHECKING:
    import sqlite3

    from beadloom.graph.rules import Violation

#: This repository's root — the only project whose real config is read here.
REPO_ROOT = Path(__file__).resolve().parents[1]

#: The fact name BDL-UX #193 retired. Two unrelated meanings of "framework"
#: collided under it: the web frameworks a parser supports, and the nodes that
#: declare a test framework.
RETIRED_FACT = "framework_count"

#: What it was renamed to.
CURRENT_FACT = "nodes_with_framework"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


#: A ``rules.yml`` declaring ``graph-summary-facts`` and nothing else.
#:
#: These tests are about `.1`'s seam with `.3`, so they load `.1`'s rule alone.
#: Leaving ``doc-area-coherence`` in would make every assertion below depend on
#: a rule none of them is about, and a sibling bead editing that rule would red
#: this file for a reason it has nothing to do with — which is exactly what
#: happened while it was being written.
SUMMARY_FACTS_ONLY = (
    "version: 3\n"
    "rules:\n"
    "  - name: graph-summary-facts\n"
    "    description: a number in a node summary matches what the project computes\n"
    "    summary_facts: {}\n"
)


def _indexed(
    root: Path, spec: IndexedProjectSpec | None = None
) -> tuple[Path, sqlite3.Connection]:
    """An indexed adopter project and an open connection to its graph.

    *spec* is the fixture's own keyword shape (``tests.adopter_project``), taken
    as one argument rather than as ``**kwargs`` so the keys stay type-checked at
    every call site. It defaults to :data:`SUMMARY_FACTS_ONLY`; a caller wanting
    another rule set passes ``rules`` through.
    """
    merged: IndexedProjectSpec = {"rules": SUMMARY_FACTS_ONLY}
    merged.update(spec or {})
    project = indexed_python_project(root, **merged)
    reindex(project.root)
    return project.root, open_db(project.root / ".beadloom" / "beadloom.db")


def _findings(root: Path, conn: sqlite3.Connection) -> list[Violation]:
    """Every finding the project's own ``rules.yml`` produces over its own index."""
    rules = load_rules(root / ".beadloom" / "_graph" / "rules.yml")
    return evaluate_all(conn, rules, project_root=root)


def _of_type(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


# --------------------------------------------------------------------------- #
# `.1` consumes `.3`: the reason belongs to whoever declined
# --------------------------------------------------------------------------- #


class TestTheDeclineReasonCrossesTheSeamVerbatim:
    """The rule quotes the registry's reason; it does not compose one of its own."""

    @pytest.mark.parametrize(
        ("summary", "fact_name"),
        [
            ("The billing module of release v3.7.0", "version"),
            ("An MCP stdio server exposing 18 tools to agents", "mcp_tool_count"),
        ],
        ids=["no-manifest-declares-a-version", "a-surface-that-describes-our-package"],
    )
    def test_the_finding_carries_the_registrys_own_string(
        self, tmp_path: Path, summary: str, fact_name: str
    ) -> None:
        """Two facts, declined for unrelated reasons, each quoted correctly.

        One parameter alone would pass on a rule that pasted *any* fixed
        sentence. Two whose reasons share no wording will not.
        """
        root, conn = _indexed(
            tmp_path / "invoice-svc",
            {"version": None, "summaries": {"billing-m0": summary}},
        )
        declared = FactRegistry().collect_set(root, conn)
        expected = declared.not_applicable[fact_name]

        found = _of_type(_findings(root, conn), LIVENESS_RULE_TYPE)

        assert len(found) == 1, [v.message for v in found]
        assert expected in found[0].message, (expected, found[0].message)

    def test_the_two_reasons_do_not_share_the_wording_being_checked(self, tmp_path: Path) -> None:
        """The parametrisation above is only evidence if its two cases differ.

        A registry that returned one sentence for every decline would make the
        pair look like two passes and be one.
        """
        root, conn = _indexed(tmp_path / "invoice-svc", {"version": None})

        declared = FactRegistry().collect_set(root, conn)

        assert declared.not_applicable["version"] != declared.not_applicable["mcp_tool_count"]

    def test_a_declined_fact_is_reported_rather_than_read_as_agreement(
        self, tmp_path: Path
    ) -> None:
        """UNCHECKED IS NOT CLEAN: the claim produces a finding, not silence."""
        root, conn = _indexed(
            tmp_path / "invoice-svc",
            {
                "version": None,
                "summaries": {"billing-m0": "The billing module of release v3.7.0"},
            },
        )

        violations = _findings(root, conn)

        assert _of_type(violations, SUMMARY_FACTS_RULE_TYPE) == []
        assert len(_of_type(violations, LIVENESS_RULE_TYPE)) == 1

    def test_the_same_claim_is_checked_when_the_project_declares_the_fact(
        self, tmp_path: Path
    ) -> None:
        """The control. Without it the test above passes on a rule that reports
        every claim, and "could not be verified" would mean nothing."""
        root, conn = _indexed(
            tmp_path / "invoice-svc",
            {
                "version": "3.7.0",
                "summaries": {"billing-m0": "The billing module of release v3.7.0"},
            },
        )

        violations = _findings(root, conn)

        assert violations == [], [v.message for v in violations]


# --------------------------------------------------------------------------- #
# `.4`'s rename: does any path still resolve the old name?
# --------------------------------------------------------------------------- #


class TestNoPathStillResolvesTheRetiredFactName:
    """``framework_count`` is a key in nothing and is produced by nothing."""

    def test_the_scanner_registers_no_keywords_under_the_retired_name(self) -> None:
        keywords = DocScanner.FACT_KEYWORDS

        assert RETIRED_FACT not in keywords
        assert CURRENT_FACT in keywords

    def test_the_tolerance_table_is_keyed_by_the_current_name(self) -> None:
        """A tolerance under the old key would silently apply to nothing."""
        assert RETIRED_FACT not in DEFAULT_TOLERANCES
        assert CURRENT_FACT in DEFAULT_TOLERANCES

    def test_the_count_fact_exception_is_keyed_by_the_current_name(self) -> None:
        """``nodes_with_framework`` has no ``_count`` suffix, so it is listed here.

        Listing the retired name instead would make the current one fail the
        suffix test and stop being read as a count at all.
        """
        assert RETIRED_FACT not in _COUNT_FACTS_WITHOUT_SUFFIX
        assert CURRENT_FACT in _COUNT_FACTS_WITHOUT_SUFFIX

    def test_the_registry_declines_under_the_current_name_too(self, tmp_path: Path) -> None:
        """The decline path, which the acceptance scenario does not reach.

        A rename that moved only the success branch would leave the old name
        reappearing on any project whose nodes table cannot be read — the exact
        projects nobody looks at.
        """
        conn = open_db(tmp_path / "graph.db")
        create_schema(conn)
        conn.execute("DROP TABLE nodes")
        conn.commit()

        fact_set = FactRegistry().collect_set(tmp_path, conn)

        assert RETIRED_FACT not in fact_set.facts
        assert RETIRED_FACT not in fact_set.not_applicable
        assert CURRENT_FACT in fact_set.not_applicable

    def test_a_summary_about_nodes_is_read_as_a_claim_about_nodes(self, tmp_path: Path) -> None:
        """End to end through `.1`'s rule, not only through the scanner."""
        root, conn = _indexed(
            tmp_path / "invoice-svc",
            {"summaries": {"billing-m0": "84 nodes declare a test framework"}},
        )

        found = _of_type(_findings(root, conn), SUMMARY_FACTS_RULE_TYPE)

        assert len(found) == 1, [v.message for v in found]
        assert CURRENT_FACT in found[0].message
        assert RETIRED_FACT not in found[0].message

    def test_a_summary_about_a_parsers_frameworks_states_no_claim(self, tmp_path: Path) -> None:
        """The live finding `.4` had to clear, held at the rule's own level.

        ``route-extraction``'s summary is factually correct and was reported as
        disagreeing with 84. If the retired keywords ever come back this is the
        finding that returns.

        Thirty-seven, not the twelve the live summary states, and not a
        single digit either. Twelve is what this fixture computes for
        ``nodes_with_framework``, so a claim of twelve would AGREE and the test
        would pass on the very regression it guards; anything under
        ``MIN_READABLE_COUNT`` (10) is not read as a count at all, so it would
        pass for the second wrong reason. Measured — with the retired keywords
        restored, this assertion is green at 12, green at 7 and red at 37.
        """
        root, conn = _indexed(
            tmp_path / "invoice-svc",
            {"summaries": {"billing-m0": "regex fallback across 37 web frameworks"}},
        )

        violations = _findings(root, conn)

        assert _of_type(violations, SUMMARY_FACTS_RULE_TYPE) == []
        assert _of_type(violations, LIVENESS_RULE_TYPE), (
            "the rule must report that it checked nothing, not return an empty list"
        )

    def test_a_suppression_naming_the_retired_fact_would_silence_nothing(
        self, tmp_path: Path
    ) -> None:
        """Why the triple in this repository's config had to go, not merely could.

        A suppression keyed to a fact no extractor produces matches nothing, and
        a suppression that suppresses nothing reads as coverage it does not have.
        """
        page = tmp_path / "README.md"
        page.write_text(
            "The extractor covers 12 web frameworks and 12 supported languages.\n",
            encoding="utf-8",
        )
        mentions = DocScanner().scan([page])
        retired = IgnoreRule(path="README.md", fact=RETIRED_FACT, value="12")

        assert [m for m in mentions if retired.matches(m)] == []
        assert mentions, "the fixture must produce SOME mention, or it proves nothing"


# --------------------------------------------------------------------------- #
# a suppression that suppresses nothing (NO CALLER NO CAPABILITY)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def repo_mentions() -> list[object]:
    """Every fact mention in this repository's own documentation surface.

    Module-scoped because the scan reads 59 documents and the three tests below
    ask the same question of the same corpus. Measured at 0.42 s for the scan.
    """
    scanner = DocScanner()
    surface = scanner.resolve_surface(REPO_ROOT, None)
    return list(scanner.scan(list(surface.scanned)))


class TestEverySuppressionStillSuppresses:
    """Each ``docs_audit.ignore`` triple this repository declares still matches.

    There is no production check for this. ``compare_facts`` drops a matching
    mention and counts nothing, ``docs audit`` prints nothing about the rules it
    was given, and no gate step reads them — so an ignore triple outlives the
    prose it was written for in complete silence, and the config comment saying
    it was "measured: 0 matching mentions" is the only record that anybody
    looked. Measured at the time of writing: 10 declared triples, 59 documents,
    41 mentions, every triple matching at least one.
    """

    def test_the_corpus_under_test_is_not_empty(self, repo_mentions: list[object]) -> None:
        """A sweep over zero documents would call every suppression inert."""
        assert len(repo_mentions) > 0

    def test_every_declared_triple_matches_at_least_one_mention(
        self, repo_mentions: list[object]
    ) -> None:
        rules = _load_ignore_from_config(REPO_ROOT)
        assert rules, "this repository declares suppressions; the loader read none"

        inert = [
            f"{rule.path} {rule.fact}={rule.value}"
            for rule in rules
            if not any(rule.matches(m) for m in repo_mentions)  # type: ignore[arg-type]
        ]

        assert inert == [], (
            "these suppressions match no mention in this repository — they "
            "silence nothing and read as coverage they do not have: " + str(inert)
        )

    def test_the_sweep_would_notice_a_triple_that_matches_nothing(self) -> None:
        """The guard's own bite, without editing the config it guards."""
        page = REPO_ROOT / "README.md"
        mentions = DocScanner().scan([page])
        retired = IgnoreRule(path="README.md", fact=RETIRED_FACT, value="12")

        assert [m for m in mentions if retired.matches(m)] == []


class TestAConfigThatCannotBeReadSuppressesNothing:
    """Every way ``docs_audit.ignore`` can be malformed ends in an empty list.

    An empty list is the safe direction — nothing is silenced, so a stale fact
    stays reported. It is also silent: a project whose ``config.yml`` stopped
    parsing loses every suppression it wrote, and the only sign is a log line
    nobody reads. That is the same shape as the missing inert-suppression check
    above and is recorded here for the same reason: the behaviour is pinned so a
    change to it is deliberate, not so it is endorsed.
    """

    def _config(self, tmp_path: Path, body: str) -> Path:
        (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".beadloom" / "config.yml").write_text(body, encoding="utf-8")
        return tmp_path

    def test_a_project_with_no_config_declares_no_suppressions(self, tmp_path: Path) -> None:
        assert _load_ignore_from_config(tmp_path) == []

    @pytest.mark.parametrize(
        ("body", "why"),
        [
            ("docs_audit:\n  ignore:\n  - [unclosed\n", "unparsable YAML"),
            ("- a\n- b\n", "a list where a mapping was expected"),
            ("docs_audit: a string\n", "docs_audit is not a mapping"),
            ("docs_audit:\n  ignore: 12\n", "ignore is not a list"),
            ("docs_audit:\n  ignore:\n  - just-a-string\n", "an entry is not a mapping"),
            (
                "docs_audit:\n  ignore:\n  - path: README.md\n    fact: node_count\n",
                "an entry omits `value`",
            ),
        ],
        ids=[
            "unparsable",
            "not-a-mapping",
            "section-not-a-mapping",
            "ignore-not-a-list",
            "entry-not-a-mapping",
            "entry-incomplete",
        ],
    )
    def test_a_malformed_declaration_yields_no_rule(
        self, tmp_path: Path, body: str, why: str
    ) -> None:
        assert _load_ignore_from_config(self._config(tmp_path, body)) == [], why

    def test_a_well_formed_declaration_beside_a_malformed_one_still_loads(
        self, tmp_path: Path
    ) -> None:
        """One bad entry must not cost a project the suppressions it got right."""
        root = self._config(
            tmp_path,
            "docs_audit:\n"
            "  ignore:\n"
            "  - just-a-string\n"
            "  - path: README.md\n"
            "    fact: node_count\n"
            "    value: 20\n",
        )

        rules = _load_ignore_from_config(root)

        assert [(r.path, r.fact, r.value) for r in rules] == [("README.md", "node_count", "20")]
