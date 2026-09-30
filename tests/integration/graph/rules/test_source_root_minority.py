"""`doc-area-coherence`: a minority source root, and a stand-down that was silent.

BDL-062 `.9` (`beadloom-viaj.9`), closing BDL-UX #195. Two defects, one trigger.

**The trigger.** The source root was the longest prefix EVERY documented node's
source shares. Unanimity gives every single source a veto: on this repository
one node whose source is `site/` collapsed the root from `src/beadloom` to
nothing for all 85 other pairs. `min_support` guarded the dominant-mapping half
and nothing guarded the prefix.

**The two faces**, measured on the real graph before the fix and reproduced in
miniature by the fixtures here:

    doc names the minority area   -> a bogus convention, SEVEN correct nodes reported wrong
    doc names no source area      -> nothing compares, the rule reports it checked nothing

**The second defect, and the dangerous one.** That stand-down went out through
`liveness_finding`, which forced `warn` whatever the rule's declared severity.
A rule this project had escalated to `error` could stop checking 100% of its
population while `lint --strict` exited 0.

**TESTS MUST BITE.** `test_the_gate_cannot_pass_while_the_rule_checked_nothing`
is the point of the file: it runs the real linter and fails if a blocking rule
stands down without the Gate noticing.

**FAKES PROVE FAKES.** Every graph here uses `platform/`, `atelier/`, `reference/`
and `endpoints/` — none of which this repository has — so a rule that passed by
recognising Beadloom's own tree would fail these.

BDL-076 K3 (`beadloom-5o48`) added the last section: a SUPPORTED second tree,
the case `.9` left open, with `storefront/web/` and `handbook/` as its fakes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules import (
    DOC_AREA_RULE_TYPE,
    LIVENESS_RULE_TYPE,
    DocAreaCoherenceRule,
    evaluate_doc_area_coherence_rules,
)
from beadloom.graph.rules.doc_area import _source_root, derive_convention
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.rules import Violation

Pair = tuple[str, str, str]

#: The outlier's source: one segment, sharing nothing with the main root. The
#: shape of a committed asset or tooling tree beside the code.
OUTLIER_SOURCE = "atelier/"


def _graph(tmp_path: Path, pairs: list[Pair]) -> sqlite3.Connection:
    conn = open_db(tmp_path / "graph.db")
    create_schema(conn)
    for ref_id, source, doc in pairs:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "feature", "", source),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            (doc, "feature", ref_id, ""),
        )
    conn.commit()
    return conn


def _coherent(area: str, count: int) -> list[Pair]:
    return [
        (
            f"{area}-{index}",
            f"platform/{area}/{area}_{index}.py",
            f"reference/{area}/{area}-{index}/SPEC.md",
        )
        for index in range(count)
    ]


def _main_tree() -> list[Pair]:
    """The majority tree, with its documents in TWO top-level buckets.

    The second bucket is what makes the fixture bite: under the correct root the
    compared segment is the AREA and both buckets are coherent; under a collapsed
    root it becomes the BUCKET, and the minority bucket's nodes are reported as
    contradicting a convention that does not exist.
    """
    return (
        _coherent("orders", 5)
        + _coherent("billing", 4)
        + [
            (
                f"gateway-{index}",
                f"platform/gateway/g{index}.py",
                f"endpoints/gateway/gateway-{index}.md",
            )
            for index in range(2)
        ]
    )


def _rule(**kwargs: object) -> DocAreaCoherenceRule:
    defaults: dict[str, object] = {
        "name": "doc-area-coherence",
        "description": "a node documents itself where its graph says it should",
    }
    defaults.update(kwargs)
    return DocAreaCoherenceRule(**defaults)  # type: ignore[arg-type]


def _reported(violations: list[Violation]) -> list[str | None]:
    return [v.from_ref_id for v in violations if v.rule_type == DOC_AREA_RULE_TYPE]


def _liveness(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.rule_type == LIVENESS_RULE_TYPE]


# --------------------------------------------------------------------------- #
# The root itself: one source must not veto the rest
# --------------------------------------------------------------------------- #


class TestTheSourceRootToleratesAMinority:
    """`_source_root` descends while exactly one way down is supported."""

    def test_a_single_outlier_does_not_collapse_the_root(self) -> None:
        sources = [("platform", "orders")] * 5 + [("platform", "billing")] * 4
        assert _source_root([*sources, ("atelier",)], min_support=2) == ("platform",)

    def test_the_root_still_stops_where_the_areas_genuinely_fork(self) -> None:
        """The old unanimity behaviour, preserved: a real fork ends the descent."""
        sources = [("platform", "orders")] * 5 + [("platform", "billing")] * 4
        assert _source_root(sources, min_support=2) == ("platform",)

    def test_an_outlier_one_level_down_does_not_shallow_the_root(self) -> None:
        """The same defect one segment deeper — `src/tools/x.py` beside `src/pkg/`."""
        sources = [("src", "pkg", "graph")] * 6 + [("src", "pkg", "docs")] * 6
        assert _source_root([*sources, ("src", "tools")], min_support=2) == ("src", "pkg")

    def test_two_genuine_roots_are_not_forced_into_one(self) -> None:
        """A real fork at the top is not an outlier, and neither side wins."""
        sources = [("platform", "orders")] * 5 + [("service", "billing")] * 5
        assert _source_root(sources, min_support=2) == ()

    def test_a_source_that_is_itself_the_root_does_not_end_the_descent(self) -> None:
        """A node whose source IS the root is rootless, not a veto."""
        sources = [("platform", "orders")] * 5 + [("platform", "billing")] * 4
        assert _source_root([*sources, ("platform",)], min_support=2) == ("platform",)

    def test_min_support_is_what_decides_a_minority(self) -> None:
        """Raising the declared dial moves the line — there is no second knob.

        At `min_support=2` the two-source `atelier` cluster is supported, so the
        top level is a genuine fork and the root stays empty. At 3 it is a
        minority, `platform` is the only supported way down, and the descent then
        stops at the real fork between the two areas below it.
        """
        sources = (
            [("platform", "orders")] * 3
            + [("platform", "billing")] * 3
            + [("atelier", "a")] * 2
        )
        assert _source_root(sources, min_support=2) == ()
        assert _source_root(sources, min_support=3) == ("platform",)


# --------------------------------------------------------------------------- #
# The two faces the collapse wore
# --------------------------------------------------------------------------- #


class TestBothFacesOfTheCollapse:
    """One cause, two observables. Kept as a pair because they diverge only in
    where the minority node's document happens to sit, which is not something a
    maintainer would think to vary."""

    def test_an_outlier_documented_under_its_own_name_invents_no_findings(
        self, tmp_path: Path
    ) -> None:
        """`site/vitepress-site/DOC.md` — the face that manufactured false errors."""
        pairs = [*_main_tree(), ("atelier", OUTLIER_SOURCE, "atelier/a/DOC.md")]
        conn = _graph(tmp_path, pairs)
        violations = evaluate_doc_area_coherence_rules(conn, [_rule()])

        assert _reported(violations) == []
        assert _liveness(violations) == []

    def test_an_outlier_documented_under_no_area_blanks_nothing(
        self, tmp_path: Path
    ) -> None:
        """`guides/vitepress-site.md` — the face that stood the whole rule down."""
        pairs = [*_main_tree(), ("atelier", OUTLIER_SOURCE, "manual/atelier.md")]
        conn = _graph(tmp_path, pairs)
        violations = evaluate_doc_area_coherence_rules(conn, [_rule()])

        assert _reported(violations) == []
        assert _liveness(violations) == []

    def test_the_outlier_is_counted_rather_than_dropped(self, tmp_path: Path) -> None:
        pairs = [*_main_tree(), ("atelier", OUTLIER_SOURCE, "manual/atelier.md")]
        conn = _graph(tmp_path, pairs)
        convention = derive_convention(conn, threshold=0.6, min_support=2)

        assert convention.outside_root == 1
        assert convention.examined == len(pairs)
        assert "1 sit outside" in convention.population()

    def test_a_real_contradiction_is_still_reported_beside_an_outlier(
        self, tmp_path: Path
    ) -> None:
        """The other half: tolerating an outlier must not blunt the rule.

        Without this, a fix that simply stopped reporting anything would pass
        every test above.
        """
        pairs = [
            *_main_tree(),
            ("atelier", OUTLIER_SOURCE, "manual/atelier.md"),
            ("orders-stray", "platform/orders/stray.py", "reference/billing/s/SPEC.md"),
        ]
        conn = _graph(tmp_path, pairs)
        violations = evaluate_doc_area_coherence_rules(conn, [_rule()])

        assert _reported(violations) == ["orders-stray"]


# --------------------------------------------------------------------------- #
# The stand-down is not silent
# --------------------------------------------------------------------------- #


class TestATotalStandDownCarriesTheDeclaredSeverity:
    """A rule that checked NONE of its population reports at the severity the
    project declared. A partial inertness stays advisory — see the module note
    in `doc_area.py` for why the two differ."""

    @staticmethod
    def _underivable() -> list[Pair]:
        return [
            (area, f"platform/{area}/service.py", f"reference/{area}/service/SPEC.md")
            for area in ("orders", "billing", "catalogue", "search", "payments", "audit")
        ]

    def test_an_escalated_rule_stands_down_at_error(self, tmp_path: Path) -> None:
        conn = _graph(tmp_path, self._underivable())
        violations = evaluate_doc_area_coherence_rules(conn, [_rule(severity="error")])

        liveness = _liveness(violations)
        assert len(liveness) == 1
        assert liveness[0].severity == "error"
        assert "checked nothing" in liveness[0].message

    def test_a_shipped_default_rule_stands_down_at_warn(self, tmp_path: Path) -> None:
        """The adopter's protection, and the reason this is not simply "follow
        severity everywhere": a rule that ships `warn` still reports `warn`, so
        nobody's first `beadloom ci` goes red on a graph that is merely small."""
        conn = _graph(tmp_path, self._underivable())
        violations = evaluate_doc_area_coherence_rules(conn, [_rule()])

        liveness = _liveness(violations)
        assert len(liveness) == 1
        assert liveness[0].severity == "warn"

    def test_the_gate_cannot_pass_while_the_rule_checked_nothing(
        self, tmp_path: Path
    ) -> None:
        """The point of this file, asserted end to end through the real linter.

        `lint --strict` exits non-zero on `result.has_errors`. Before this bead a
        blocking rule could stand down over its entire population and leave that
        flag False, so the Gate reported a pass for a check that never ran.
        """
        from beadloom.graph.linter import lint

        project = tmp_path / "project"
        (project / ".beadloom" / "_graph").mkdir(parents=True)
        (project / ".beadloom" / "_graph" / "rules.yml").write_text(
            "version: 3\nrules:\n"
            "  - name: doc-area-coherence\n"
            '    description: "a node documents itself where its graph says it should"\n'
            "    severity: error\n"
            "    doc_area_coherence: {}\n",
            encoding="utf-8",
        )
        conn = _graph(project / ".beadloom", self._underivable())
        conn.close()
        (project / ".beadloom" / "graph.db").rename(project / ".beadloom" / "beadloom.db")

        result = lint(project)

        assert result.rules_inert == 1, "the rule did not stand down; fixture is wrong"
        assert result.has_errors, (
            "the Gate would pass: a rule declared blocking checked NONE of its "
            "population and lint --strict would still exit 0"
        )

    def test_the_gate_stays_green_when_the_shipped_default_stands_down(
        self, tmp_path: Path
    ) -> None:
        """The same run with the rule left at `warn`: reported, not blocking."""
        from beadloom.graph.linter import lint

        project = tmp_path / "project"
        (project / ".beadloom" / "_graph").mkdir(parents=True)
        (project / ".beadloom" / "_graph" / "rules.yml").write_text(
            "version: 3\nrules:\n"
            "  - name: doc-area-coherence\n"
            '    description: "a node documents itself where its graph says it should"\n'
            "    doc_area_coherence: {}\n",
            encoding="utf-8",
        )
        conn = _graph(project / ".beadloom", self._underivable())
        conn.close()
        (project / ".beadloom" / "graph.db").rename(project / ".beadloom" / "beadloom.db")

        result = lint(project)

        assert result.rules_inert == 1
        assert not result.has_errors


# --------------------------------------------------------------------------- #
# A SUPPORTED second source tree (BDL-076 K3, `beadloom-5o48`)
# --------------------------------------------------------------------------- #
#
# `.9` fixed a MINORITY second tree. A second tree of two or more nodes is a
# supported second way down, so the descent forks at the very top and the root
# comes out empty; the areas became the tree names, no document named a tree, and
# the rule checked none of the pairs. On this repository 17 slice nodes under
# `site/` did that to all 126. Every two-tree test below was red before the fix:
# the old derivation reported nothing on these graphs, or reported only the tree
# whose documents happened to name the tree. The trees are `platform/` and
# `storefront/web/`, documented under `reference/` and `handbook/`.

#: The frontend tree's root: its areas begin two segments down.
FRONTEND = "storefront/web"


def _reported_sorted(violations: list[Violation]) -> list[str]:
    return sorted(str(v.from_ref_id) for v in violations if v.rule_type == DOC_AREA_RULE_TYPE)


def _backend(area: str, count: int, docs_area: str | None = None) -> list[Pair]:
    target = docs_area or area
    return [
        (
            f"{area}-{index}",
            f"platform/{area}/{area}_{index}.py",
            f"reference/{target}/{area}-{index}/SPEC.md",
        )
        for index in range(count)
    ]


def _frontend(area: str, count: int, docs_area: str | None = None) -> list[Pair]:
    target = docs_area or area
    return [
        (
            f"web-{area}-{index}",
            f"{FRONTEND}/{area}/{area}-{index}/",
            f"handbook/{target}/{area}-{index}/README.md",
        )
        for index in range(count)
    ]


def _two_trees() -> list[Pair]:
    return (
        _backend("orders", 5)
        + _backend("billing", 4)
        + _frontend("widgets", 3)
        + _frontend("entities", 3)
    )


class TestEachTreeIsJudged:
    def test_a_coherent_two_tree_graph_is_checked_and_clean_at_error(
        self, tmp_path: Path
    ) -> None:
        """The failure this bead fixes: no finding, and no "checked nothing" either."""
        conn = _graph(tmp_path, _two_trees())
        assert evaluate_doc_area_coherence_rules(conn, [_rule(severity="error")]) == []

        convention = derive_convention(conn, threshold=0.6, min_support=2)
        assert convention.sampled == 15
        assert len(convention.checked) == 15

    def test_a_misplaced_document_in_each_tree_is_reported_sorted(self, tmp_path: Path) -> None:
        pairs = [
            *_two_trees(),
            ("orders-stray", "platform/orders/stray.py", "reference/billing/stray/SPEC.md"),
            ("web-stray", f"{FRONTEND}/widgets/stray/", "handbook/entities/stray/README.md"),
        ]
        conn = _graph(tmp_path, pairs)
        violations = evaluate_doc_area_coherence_rules(conn, [_rule()])

        assert _reported_sorted(violations) == ["orders-stray", "web-stray"]
        assert _liveness(violations) == []

    def test_the_finding_names_the_area_with_its_tree(self, tmp_path: Path) -> None:
        pairs = [
            *_two_trees(),
            ("web-stray", f"{FRONTEND}/widgets/stray/", "handbook/entities/stray/README.md"),
        ]
        conn = _graph(tmp_path, pairs)
        (finding,) = [
            v
            for v in evaluate_doc_area_coherence_rules(conn, [_rule()])
            if v.rule_type == DOC_AREA_RULE_TYPE
        ]
        assert f"under `{FRONTEND}/widgets`" in finding.message
        assert "3 of 4" in finding.message

    def test_an_area_name_two_trees_share_is_two_areas(self, tmp_path: Path) -> None:
        """`shared` in the backend and `shared` in the frontend keep separate conventions.

        Keyed by the bare name, the two pool into one area documented half under
        `shared` and half under `kit`, which no majority covers, and the stray
        below would go unchecked.
        """
        pairs = [
            *_backend("orders", 4),
            *_backend("shared", 3),
            *_frontend("widgets", 3),
            *_frontend("shared", 3, docs_area="kit"),
            ("web-shared-stray", f"{FRONTEND}/shared/stray/", "handbook/widgets/stray/README.md"),
        ]
        conn = _graph(tmp_path, pairs)

        assert _reported_sorted(evaluate_doc_area_coherence_rules(conn, [_rule()])) == [
            "web-shared-stray"
        ]

    def test_a_tree_whose_documents_name_no_area_is_read_at_the_projects_depth(
        self, tmp_path: Path
    ) -> None:
        """This repository's site: every slice documented in one shared directory."""
        frontend = [
            (
                f"web-{area}-{i}",
                f"{FRONTEND}/{area}/{area}-{i}/",
                f"reference/storefront/{area}-{i}.md",
            )
            for area in ("widgets", "entities")
            for i in range(3)
        ]
        strays = [
            ("web-stray", f"{FRONTEND}/widgets/stray/", "reference/orders/stray/SPEC.md"),
            ("orders-stray", "platform/orders/stray.py", "reference/billing/stray/SPEC.md"),
        ]
        conn = _graph(
            tmp_path, [*_backend("orders", 5), *_backend("billing", 4), *frontend, *strays]
        )

        # Read as two areas `platform` and `storefront`, only the frontend stray
        # is caught: the backend's documents name no tree, so `platform` has no
        # majority and its stray goes unchecked.
        assert _reported_sorted(evaluate_doc_area_coherence_rules(conn, [_rule()])) == [
            "orders-stray",
            "web-stray",
        ]


class TestThePopulationPerTree:
    def test_the_population_states_each_tree(self, tmp_path: Path) -> None:
        conn = _graph(tmp_path, _two_trees())
        population = derive_convention(conn, threshold=0.6, min_support=2).population()

        assert "derived from 15 node/doc pairs: 15 compare" in population
        assert "per source tree" in population
        assert "`platform`: 9 of 9 pairs compare, 9 under a dominant mapping, 9 agree" in (
            population
        )
        assert f"`{FRONTEND}`: 6 of 6 pairs compare, 6 under a dominant mapping, 6 agree" in (
            population
        )

    def test_a_minority_third_tree_is_still_counted_outside(self, tmp_path: Path) -> None:
        pairs = [*_two_trees(), ("atelier", "atelier/", "manual/atelier.md")]
        conn = _graph(tmp_path, pairs)
        convention = derive_convention(conn, threshold=0.6, min_support=2)

        assert convention.outside_root == 1
        assert convention.examined == len(pairs)
        assert "1 sit outside" in convention.population()
        assert _reported_sorted(evaluate_doc_area_coherence_rules(conn, [_rule()])) == []

    def test_a_node_above_its_trees_root_is_counted_outside_that_tree(
        self, tmp_path: Path
    ) -> None:
        """`site/` beside `site/.vitepress/theme/...`: the tree's own umbrella node."""
        pairs = [*_two_trees(), ("storefront", "storefront/", "handbook/storefront.md")]
        conn = _graph(tmp_path, pairs)
        convention = derive_convention(conn, threshold=0.6, min_support=2)

        assert convention.outside_root == 1
        assert f"`{FRONTEND}`: 6 of 7 pairs compare" in convention.population()

    def test_two_trees_too_small_for_a_convention_say_so_per_tree(
        self, tmp_path: Path
    ) -> None:
        pairs = [
            (f"b-{area}", f"platform/{area}/x.py", f"reference/{area}/x/SPEC.md")
            for area in ("orders", "billing", "audit")
        ] + [
            (f"f-{area}", f"{FRONTEND}/{area}/x/", f"handbook/{area}/x/README.md")
            for area in ("widgets", "entities", "pages")
        ]
        conn = _graph(tmp_path, pairs)
        (liveness,) = _liveness(
            evaluate_doc_area_coherence_rules(conn, [_rule(severity="error")])
        )

        assert liveness.severity == "error"
        assert "6 pairs across 6 source areas" in liveness.message
        assert "`platform`: 3 of 3 pairs compare" in liveness.message


class TestOneTreeIsReadAsBefore:
    def test_a_single_tree_population_is_the_same_sentence(self, tmp_path: Path) -> None:
        pairs = [
            *_backend("orders", 5),
            *_backend("billing", 4),
            ("atelier", "atelier/", "m/a.md"),
        ]
        conn = _graph(tmp_path, pairs)

        assert derive_convention(conn, threshold=0.6, min_support=2).population() == (
            "derived from 10 node/doc pairs: 9 compare, 9 fall under a dominant mapping "
            "(majority 0.60 over at least 2 observations) and 9 of those agree; "
            "1 sit outside the source root"
        )

    def test_top_level_packages_the_documents_name_stay_the_areas(
        self, tmp_path: Path
    ) -> None:
        """A fork at the top that is where the areas begin, not where trees begin.

        Read as trees, every node here sits at its tree's root and nothing
        compares; read as areas, all eight compare. The documents name the
        packages, so the second reading is the one kept.
        """
        pairs = [
            (f"{area}-{i}", f"{area}/{area}_{i}.py", f"manual/{area}/{area}-{i}.md")
            for area, count in (("ledger", 4), ("catalogue", 3))
            for i in range(count)
        ] + [("ledger-stray", "ledger/stray.py", "manual/catalogue/stray.md")]
        conn = _graph(tmp_path, pairs)
        convention = derive_convention(conn, threshold=0.6, min_support=2)

        assert set(convention.dominant) == {"ledger", "catalogue"}
        assert _reported_sorted(evaluate_doc_area_coherence_rules(conn, [_rule()])) == [
            "ledger-stray"
        ]
