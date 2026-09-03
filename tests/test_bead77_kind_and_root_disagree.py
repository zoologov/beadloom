"""What the classifier does when a document's kind and its roots disagree.

BDL-061 S5, bead `beadloom-mr2l.77` (review `.19`, Majors 1-3). Three findings
that share one sentence: a fact nobody can place must still appear in a count.

* **M1 — the population's third hole.** ``documents_in`` globbed a space's own
  roots and then kept only what ``space_of`` returned to that same space. A
  document whose KIND sent it to a space whose ROOTS do not match it was found by
  one glob, rejected by one classifier and looked for by nobody else, so it was
  in no population, its directory was in no epic list, and nothing said so. The
  reviewer found it by PLANTING a ``README.md``-only planning directory, not by
  reading the code: ``.17``'s first denominator dropped 34 epics, ``.18`` found
  four directories falling out, ``.73`` widened the definition, and a planted
  file still found a way out.
* **M2 — a half-inert declaration.** ``working.kinds: [ACTIVE, SPEC]`` over 39
  ``SPEC.md`` files reported nothing: liveness was asked of the declaration as a
  whole, so one live half silenced every other, and ``space_of_kind`` walked
  ``SPACES`` — a reporting order — so the AS-IS default list shadowed a project's
  explicit declaration before liveness ever ran.
* **M3 — two adjacent lines contradicting.** ``sync-check --json`` reported
  ``exempt: 0`` while the doc-spaces line of the same tree read ``55 WORKING
  document(s) exempt``. One word, two populations: documents and sync pairs.

The invariant these pin, rather than the three symptoms:

* ``sum(populations) == |files any declared root matched|``, on any tree.
* Every declared half of the WORKING exemption reports what it reached.
* The pair count a surface prints is the number ``check_sync`` produced, never a
  second computation of the same idea.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.application.doc_spaces import (
    FINDING_OUTSIDE_DECLARED_ROOT,
    FINDING_WORKING_INERT,
    check_spaces,
)
from beadloom.application.gate import _step_doc_spaces, _step_sync_check
from beadloom.doc_sync.engine import STATUS_EXEMPT, check_sync
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doc_roots import (
    SPACE_AS_IS,
    SPACE_TO_BE,
    SPACE_WORKING,
    SPACES,
    default_doc_spaces,
    path_matches,
    resolve_doc_spaces,
)
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Mapping
    from pathlib import Path

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


def _write(root: Path, rel: str, text: str = "# doc\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(root: Path, block: Mapping[str, object]) -> None:
    _write(root, ".beadloom/config.yml", yaml.safe_dump({"doc_roots": dict(block)}))


def _found_by_any_root(root: Path, spaces: object) -> set[str]:
    """Every file a declared root matched, spelled project-relative.

    Recomputed here from the configuration rather than asked of the code under
    test: a classifier that agrees with itself proves nothing about whether it
    lost a file (`.18`'s recount suite could reproduce M1 faithfully and agreed
    with it, which is why the reviewer had to plant a file instead).
    """
    found: set[str] = set()
    for space in SPACES:
        for pattern in spaces.roots.get(space, ()):  # type: ignore[attr-defined]
            found.update(
                p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file()
            )
    return found


def _populations(root: Path, spaces: object) -> dict[str, int]:
    return {
        space: len(spaces.documents_in(root, space))  # type: ignore[attr-defined]
        for space in SPACES
    }


def _report(root: Path, **kwargs: object) -> object:
    defaults: dict[str, object] = {
        "spaces": resolve_doc_spaces(root),
        "known_refs": frozenset(),
        "documented_refs": frozenset(),
        "declared_doc_paths": frozenset(),
        "beads_by_epic": {},
    }
    defaults.update(kwargs)
    return check_spaces(root, **defaults)  # type: ignore[arg-type]


def _rules(report: object) -> list[str]:
    return [f.rule for f in report.findings]  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# M1 — the invariant, stated once, instead of a patch for the third case
# --------------------------------------------------------------------------- #


class TestEveryDocumentARootFoundIsInSomePopulation:
    """The counts are counts of documents, or they are not counts of anything.

    Not "the three cases `.17`, `.18` and `.73` found are handled" — an
    enumeration of known holes is what let a planted file find a fourth. The
    property is arithmetic and holds on any tree: what the roots found is what
    the populations add up to.
    """

    def test_the_populations_sum_to_the_files_the_declared_roots_found(
        self, tmp_path: Path
    ) -> None:
        """Three files matched by a declared root, and a population of three.

        Measured before the fix: 3 files found, populations summing to 1.
        """
        _write(tmp_path, ".claude/development/docs/features/ZALPHA/README.md")
        _write(tmp_path, "docs/PLAN.md")
        _write(tmp_path, "docs/notes.md")
        spaces = default_doc_spaces()

        populations = _populations(tmp_path, spaces)
        populations[SPACE_WORKING] = len(spaces.working_documents(tmp_path))

        assert sum(populations.values()) == len(_found_by_any_root(tmp_path, spaces))

    def test_a_document_its_own_space_excludes_is_counted_under_its_kind(
        self, tmp_path: Path
    ) -> None:
        """Kind wins, and winning means landing in a count rather than in none.

        ``README.md`` is an AS-IS kind sitting under a TO-BE root. The AS-IS
        roots do not reach into the planning tree, so before this bead no glob
        looked for it a second time.
        """
        _write(tmp_path, ".claude/development/docs/features/ZALPHA/README.md")
        spaces = default_doc_spaces()

        found = [p.name for p in spaces.documents_in(tmp_path, SPACE_AS_IS)]

        assert found == ["README.md"]

    def test_a_to_be_kind_under_the_as_is_root_is_counted_as_intent(
        self, tmp_path: Path
    ) -> None:
        """The other direction, because a hole with one direction fixed is half a hole."""
        _write(tmp_path, "docs/PLAN.md")
        spaces = default_doc_spaces()

        found = [p.name for p in spaces.documents_in(tmp_path, SPACE_TO_BE)]

        assert found == ["PLAN.md"]

    def test_the_control_still_holds_a_document_whose_root_agrees(
        self, tmp_path: Path
    ) -> None:
        """The passing control: an ordinary AS-IS document is unaffected."""
        _write(tmp_path, "docs/notes.md")
        spaces = default_doc_spaces()

        assert [p.name for p in spaces.documents_in(tmp_path, SPACE_AS_IS)] == ["notes.md"]

    def test_a_working_document_inside_the_to_be_tree_is_not_a_disagreement(
        self, tmp_path: Path
    ) -> None:
        """The shipped case, which must not become a finding.

        ``ACTIVE.md`` lives inside the TO-BE tree by design and WORKING declares
        no root at all. A space that declares no root has said nothing about
        where its documents live, so there is nothing for its kind to contradict
        — and Beadloom's own 55 ACTIVE.md files would otherwise print 55
        findings on every run.
        """
        _write(tmp_path, ".claude/development/docs/features/BDL-1/ACTIVE.md")

        report = _report(tmp_path)

        assert FINDING_OUTSIDE_DECLARED_ROOT not in _rules(report)


class TestTheDisagreementIsItselfAFinding:
    """Counted is not enough: the reader has to learn the classifier was overruled."""

    def test_a_planted_readme_only_planning_directory_is_reported(
        self, tmp_path: Path
    ) -> None:
        """The reviewer's probe, as an executable check."""
        _write(tmp_path, ".claude/development/docs/features/ZALPHA/README.md")

        report = _report(tmp_path)

        assert FINDING_OUTSIDE_DECLARED_ROOT in _rules(report)

    def test_the_finding_names_the_document_and_both_spaces(self, tmp_path: Path) -> None:
        """A finding a reader can act on names the file, its kind and the space."""
        _write(tmp_path, ".claude/development/docs/features/ZALPHA/README.md")

        report = _report(tmp_path)
        finding = next(
            f
            for f in report.findings  # type: ignore[attr-defined]
            if f.rule == FINDING_OUTSIDE_DECLARED_ROOT
        )

        assert "README" in finding.why
        assert SPACE_AS_IS in finding.why
        assert finding.path == ".claude/development/docs/features/ZALPHA/README.md"
        assert finding.path in finding.why

    def test_the_report_carries_the_count_not_only_the_findings(
        self, tmp_path: Path
    ) -> None:
        """A count somewhere, which is the whole equation of #174 and #175."""
        _write(tmp_path, ".claude/development/docs/features/ZALPHA/README.md")
        _write(tmp_path, "docs/PLAN.md")

        report = _report(tmp_path)

        assert sorted(report.documents_outside_declared_root) == [  # type: ignore[attr-defined]
            ".claude/development/docs/features/ZALPHA/README.md",
            "docs/PLAN.md",
        ]

    def test_one_finding_per_kind_rather_than_one_per_document(
        self, tmp_path: Path
    ) -> None:
        """An adopter whose whole convention disagrees reads a diagnosis, not a wall.

        Sixty planning directories named ``README.md`` are one decision made
        once, so they are one finding carrying sixty — the shape ``.74`` used for
        the epics the tracker does not name.
        """
        for n in range(6):
            _write(tmp_path, f".claude/development/docs/features/E{n}/README.md")

        report = _report(tmp_path)
        findings = [
            f
            for f in report.findings  # type: ignore[attr-defined]
            if f.rule == FINDING_OUTSIDE_DECLARED_ROOT
        ]

        assert len(findings) == 1
        assert "6" in findings[0].why


class TestTheHoleIsInvisibleOnThisRepositoryAndOnAnAdopter:
    """TRUE HERE IS NOT TRUE, in both directions.

    Beadloom's own stems happen to agree with its own roots, which is exactly why
    three rounds of review counted the population correctly and none of them saw
    this. The repository leg proves the fix is silent here; the adopter leg
    proves it is not silent on a project that is not us.
    """

    def test_this_repository_places_every_document_a_root_found(self) -> None:
        spaces = resolve_doc_spaces(REPO_ROOT)
        populations = _populations(REPO_ROOT, spaces)
        populations[SPACE_WORKING] = len(spaces.working_documents(REPO_ROOT))

        assert sum(populations.values()) == len(_found_by_any_root(REPO_ROOT, spaces))

    def test_this_repository_reports_no_disagreement(self) -> None:
        """Zero here, and zero is the honest number rather than a silence."""
        spaces = resolve_doc_spaces(REPO_ROOT)

        assert spaces.classify(REPO_ROOT).outside_declared_root == ()

    def test_an_adopter_whose_planning_documents_are_readmes_is_told(
        self, tmp_path: Path
    ) -> None:
        """A TypeScript project with no ``.claude/`` convention of its own."""
        project = typescript_project(tmp_path / "orders-web")
        _config(
            project.root,
            {"to_be": {"roots": ["design/*/*.md"]}, "as_is": {"roots": ["docs/**/*.md"]}},
        )
        _write(project.root, "design/ORD-4/README.md")

        report = _report(project.root)

        assert FINDING_OUTSIDE_DECLARED_ROOT in _rules(report)
        assert report.documents_outside_declared_root == (  # type: ignore[attr-defined]
            "design/ORD-4/README.md",
        )

    def test_the_same_adopter_goes_quiet_once_the_kind_is_declared(
        self, tmp_path: Path
    ) -> None:
        """The remedy the finding recommends actually removes the finding."""
        project = typescript_project(tmp_path / "orders-web")
        _config(
            project.root,
            {
                "to_be": {"roots": ["design/*/*.md"], "kinds": ["README", "PRD"]},
                "as_is": {"roots": ["docs/**/*.md"]},
            },
        )
        _write(project.root, "design/ORD-4/README.md")

        report = _report(project.root)

        assert FINDING_OUTSIDE_DECLARED_ROOT not in _rules(report)
        assert report.populations[SPACE_TO_BE] == 1  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# M2 — a declaration is live per item, and it is not shadowed by a default
# --------------------------------------------------------------------------- #


class TestADeclaredKindIsNotShadowedByADefaultList:
    """Kind precedence is a decision with a reason, not a reporting order reused.

    ``space_of_kind`` walked ``SPACES``, whose own docstring says it is "every
    space, in the order a report reads best". One constant asked to mean two
    things, which is `.74`'s ``not_verified`` one module over: the AS-IS DEFAULT
    kind list silently beat a project's explicit WORKING declaration.
    """

    def test_a_project_that_declares_a_kind_for_working_gets_it(
        self, tmp_path: Path
    ) -> None:
        """39 SPEC files were the reviewer's measurement; one is the same fact."""
        _write(tmp_path, "docs/domains/billing/SPEC.md")
        _config(
            tmp_path,
            {
                "working": {
                    "exempt_from_freshness": True,
                    "reason": "specs are drafted ahead of the code in this project",
                    "kinds": ["ACTIVE", "SPEC"],
                }
            },
        )
        spaces = resolve_doc_spaces(tmp_path)

        assert spaces.space_of("docs/domains/billing/SPEC.md") == SPACE_WORKING

    def test_the_shipped_kind_lists_do_not_overlap_so_nothing_here_moves(self) -> None:
        """Precedence decides only a case a project CREATED by declaring twice.

        The three default kind lists are disjoint, so no shipped classification
        depends on which order they are consulted in — the reason this change is
        safe, stated as a check rather than as a claim.
        """
        spaces = default_doc_spaces()
        seen: set[str] = set()
        for space in SPACES:
            kinds = {k.upper() for k in spaces.kinds.get(space, ())}
            assert not (kinds & seen)
            seen |= kinds

    def test_this_repository_keeps_its_three_populations(self) -> None:
        """The measured denominators `.19` recounted a third time, unchanged."""
        spaces = resolve_doc_spaces(REPO_ROOT)
        populations = _populations(REPO_ROOT, spaces)

        # 190 -> 194 in BDL-062, -> 198 in BDL-066, -> 199 in BDL-067, -> 203 in BDL-068:
        # each feature's own PRD, RFC, CONTEXT and PLAN. This literal has been
        # hand-edited once per feature since it was written, which is the class
        # `mr2l.72` exists to remove: a count a human maintains where the tool could
        # compute it. The BDL-068 increment is the measurement rather than the claim —
        # the epic's own planning commit `409e977` moved it and left this case red,
        # and nobody saw it, because `beadloom ci` does not run pytest.
        assert populations[SPACE_TO_BE] == 203
        # 93 -> 94 -> 95 -> 96 in S6: `docs/domains/application/features/wave-plan/SPEC.md`,
        # then `docs/domains/application/features/review-brief/SPEC.md`, then
        # `docs/guides/parallel-waves.md` in the documentation pass `.24`. 96 -> 98 in
        # `.87`, which added the two components that carry intent into a context
        # bundle. 98 -> 100 in BDL-062 `.4`, which documented the two undocumented
        # nodes that could be documented (`status`, `cli-commands`). The number moves
        # when this repository gains a document, which is what makes it a denominator
        # rather than a constant. 100 -> 101 in BDL-067 `.24`, which documented the
        # `graph-files` component: the four readers of `.beadloom/_graph/` became one
        # body, and a body with a single responsibility is a node with a DOC. 101 -> 102
        # in BDL-068 `.1`, which lifted the three AST derivations into
        # `application/source_derivation/` and documented them as a component.
        # 102 -> 103 in BDL-068 `.2`, which documented `impact` — the feature an
        # adopter runs over that component. 103 -> 105 in BDL-068 `.4`: the
        # `axes-section` grammar and the `planning-report` composition, each a
        # node with its own responsibility and therefore its own document.
        # 105 -> 107 in BDL-068 `.5`: `work-item-routing` (the routes derived from
        # the composed /task-init) and `work-item-type` (the two checks over a
        # work-item folder), which are a derivation and a check and not one thing.
        # 107 -> 109 in BDL-068 `.6`: `scope-check` (the paths a commit stages
        # judged against a declared scope) and `declared-scope` (the branch, the
        # index and the planning corpus joined for it), which are again a check
        # and the composition that feeds it and not one thing.
        assert populations[SPACE_AS_IS] == 109
        # 55 -> 56 in BDL-062, -> 57 in BDL-067, -> 58 in BDL-068: this feature's ACTIVE.md.
        assert len(spaces.working_documents(REPO_ROOT)) == 58


class TestEachDeclaredHalfReportsWhatItReached:
    """`.48`'s rule liveness and `.49`'s suppressed count, in the doc-spaces layer.

    The vocabulary already exists twice in this codebase — ``rules_inert``
    qualifies lint's rule count so it cannot over-claim, and a suppressed count
    prints on every run — so this reuses it rather than inventing a third.
    """

    def _declared(self, tmp_path: Path, **working: object) -> object:
        _config(
            tmp_path,
            {
                "working": {
                    "exempt_from_freshness": True,
                    "reason": "progress notes, not descriptions of the code",
                    **working,
                }
            },
        )
        return _report(tmp_path)

    def test_a_live_half_no_longer_silences_an_inert_half(self, tmp_path: Path) -> None:
        """One document in WORKING used to make every other declared item inert."""
        _write(tmp_path, ".claude/development/docs/features/BDL-1/ACTIVE.md")

        report = self._declared(tmp_path, kinds=["ACTIVE", "SPEC"])
        inert = [
            f
            for f in report.findings  # type: ignore[attr-defined]
            if f.rule == FINDING_WORKING_INERT
        ]

        assert len(inert) == 1
        assert "SPEC" in inert[0].why
        assert "ACTIVE" not in inert[0].why

    def test_an_inert_root_and_an_inert_kind_are_two_findings(
        self, tmp_path: Path
    ) -> None:
        """Per item means per item; two dead halves are two diagnoses."""
        _write(tmp_path, "docs/notes.md")

        report = self._declared(tmp_path, kinds=["ACTIVE"], roots=["journal/*.md"])
        inert = sorted(
            f.why
            for f in report.findings  # type: ignore[attr-defined]
            if f.rule == FINDING_WORKING_INERT
        )

        assert len(inert) == 2

    def test_the_exemption_prints_how_many_documents_each_half_excused(
        self, tmp_path: Path
    ) -> None:
        """A one-line declaration covering 39 files has to say it covers 39."""
        _write(tmp_path, ".claude/development/docs/features/BDL-1/ACTIVE.md")
        for n in range(3):
            _write(tmp_path, f"docs/domains/d{n}/SPEC.md")

        report = self._declared(tmp_path, kinds=["ACTIVE", "SPEC"])

        assert dict(report.working_reach) == {  # type: ignore[attr-defined]
            "kind ACTIVE": 1,
            "kind SPEC": 3,
        }

    def test_a_shipped_default_reports_no_reach_because_it_declared_nothing(
        self, tmp_path: Path
    ) -> None:
        """A project that inherited the default has switched nothing off.

        The liveness finding is scoped to a DECLARATION for the reason `.75`
        gave, and so is the reach line: printing it for every clean adopter
        would make it a greeting rather than a report.
        """
        _write(tmp_path, ".claude/development/docs/features/BDL-1/ACTIVE.md")

        report = _report(tmp_path)

        assert dict(report.working_reach) == {}  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# M3 — one word, two populations, and now two names
# --------------------------------------------------------------------------- #


def _pair_project(root: Path, *, doc_rel: str) -> sqlite3.Connection:
    """A project with one indexed doc/code pair, spelled as ``index_docs`` spells it."""
    _write(root, "src/billing.py", "def charge() -> None:\n    return None\n")
    _write(root, f"docs/{doc_rel}", "# billing\n")
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("billing", "component", "billing", "src/billing.py"),
    )
    conn.execute(
        "INSERT INTO declared_docs (declared_path, doc_path, ref_id) VALUES (?, ?, ?)",
        (f"docs/{doc_rel}", doc_rel, "billing"),
    )
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_rel, "src/billing.py", "billing", "baseline", "baseline", "2026-01-01", "ok"),
    )
    conn.commit()
    return conn


class TestTheTwoReadingsOfExemptAreNamedApart:
    """Two adjacent lines of one run said 0 and 55 about "exempt"."""

    def test_the_gate_line_says_which_population_the_number_counts(
        self, tmp_path: Path
    ) -> None:
        """`55 WORKING document(s) exempt` invited the pair reading and got it.

        Built on a tmp project rather than REPO_ROOT. The first version read the
        live repository, so on a leg where `.beadloom/beadloom.db` did not exist
        yet the step came back `skipped` and the assertion compared its text
        against "skipped — no index" — a text mismatch reported where a missing
        PRECONDITION was the fact. That is this epic's own subject: asserting on
        a result without first establishing that the result was produced. The
        step is now asserted to have RUN before its summary is read.
        """
        conn = _pair_project(tmp_path, doc_rel="guides/ci.md")
        conn.close()
        _write(tmp_path, ".claude/development/docs/features/BDL-1/CONTEXT.md")
        step = _step_doc_spaces(tmp_path, pairs_excused=0)

        assert not step.skipped, step.summary
        assert "WORKING document(s) in the exempt space" in step.summary
        assert "0 sync pair(s) excused" in step.summary

    def test_the_command_makes_no_pair_claim_it_did_not_measure(self) -> None:
        """``docs spaces`` runs no freshness check, so it states no pair count.

        Saying nothing about a number you did not compute is the difference
        between a report and a guess; the gate, which HAS the number, prints it.
        """
        report = check_spaces(
            REPO_ROOT,
            spaces=resolve_doc_spaces(REPO_ROOT),
            known_refs=frozenset(),
            documented_refs=frozenset(),
            declared_doc_paths=frozenset(),
            beads_by_epic={},
        )

        assert report.pairs_excused is None

    def test_the_gate_prints_the_number_check_sync_produced(self, tmp_path: Path) -> None:
        """One reader of one fact: the doc-spaces line quotes the sync-check run.

        Not a second computation that happens to agree today — the count travels
        from the step that measured it, which is the seam `.75` closed one layer
        down where a WORKING root meant two things to two readers.
        """
        conn = _pair_project(tmp_path, doc_rel="guides/ci.md")
        conn.close()
        _write(tmp_path, ".claude/development/docs/features/BDL-1/CONTEXT.md")
        _config(
            tmp_path,
            {
                "working": {
                    "exempt_from_freshness": True,
                    "reason": "these guides are drafted ahead of the code",
                    "roots": ["docs/guides/*.md"],
                }
            },
        )

        sync = _step_sync_check(tmp_path)
        spaces_step = _step_doc_spaces(tmp_path, pairs_excused=sync.pairs_excused)

        assert sync.pairs_excused == 1
        assert "1 sync pair(s) excused" in spaces_step.summary

    def test_the_threaded_number_equals_the_exempt_rows(self, tmp_path: Path) -> None:
        """The step's count IS ``check_sync``'s, asserted against the rows."""
        conn = _pair_project(tmp_path, doc_rel="guides/ci.md")
        _config(
            tmp_path,
            {
                "working": {
                    "exempt_from_freshness": True,
                    "reason": "these guides are drafted ahead of the code",
                    "roots": ["docs/guides/*.md"],
                }
            },
        )
        rows = check_sync(conn, project_root=tmp_path)
        conn.close()
        excused = [r for r in rows if r["status"] == STATUS_EXEMPT]

        assert _step_sync_check(tmp_path).pairs_excused == len(excused)

    def test_a_project_that_excuses_nothing_still_says_zero(self, tmp_path: Path) -> None:
        """Zero printed is the repair; zero omitted is how 55 read as 55 pairs."""
        conn = _pair_project(tmp_path, doc_rel="guides/ci.md")
        conn.close()

        step = _step_sync_check(tmp_path)

        assert step.pairs_excused == 0


# --------------------------------------------------------------------------- #
# The classifier, established once
# --------------------------------------------------------------------------- #


class TestOneScanClassifiesEveryDocumentOnce:
    """``working_documents`` was the only population computed by a full scan.

    That is why WORKING never had M1's hole and the other two spaces did: one
    special case doing the right thing beside two doing the wrong one. The scan
    is the rule now, and ``documents_in`` reads off it.
    """

    def test_classify_returns_a_bucket_for_every_space(self, tmp_path: Path) -> None:
        _write(tmp_path, "docs/notes.md")
        _write(tmp_path, ".claude/development/docs/features/BDL-1/CONTEXT.md")
        _write(tmp_path, ".claude/development/docs/features/BDL-1/ACTIVE.md")

        classified = default_doc_spaces().classify(tmp_path)

        assert sorted(classified.by_space) == sorted(SPACES)
        assert [p.name for p in classified.by_space[SPACE_WORKING]] == ["ACTIVE.md"]

    def test_documents_in_agrees_with_the_scan(self, tmp_path: Path) -> None:
        """Two entry points, one classification — they cannot report differently."""
        _write(tmp_path, "docs/notes.md")
        _write(tmp_path, "docs/PLAN.md")
        spaces = default_doc_spaces()
        classified = spaces.classify(tmp_path)

        for space in SPACES:
            assert list(classified.by_space[space]) == spaces.documents_in(tmp_path, space)

    def test_a_file_two_globs_name_is_counted_once(self, tmp_path: Path) -> None:
        """The de-duplication `documents_in` already promised, kept by the scan."""
        _write(tmp_path, "notes.md")
        _config(tmp_path, {"as_is": {"roots": ["*.md", "**/*.md"]}})
        spaces = resolve_doc_spaces(tmp_path)

        assert len(spaces.documents_in(tmp_path, SPACE_AS_IS)) == 1

    @pytest.mark.parametrize(
        ("rel", "pattern", "expected"),
        [
            ("docs/a/b.md", "docs/**/*.md", True),
            ("vendor/lib/notes.md", "*.md", False),
        ],
    )
    def test_the_glob_vocabulary_is_unchanged(
        self, rel: str, pattern: str, expected: bool
    ) -> None:
        """The scan reuses ``path_matches``; a rewrite that widened it would show here."""
        assert path_matches(rel, pattern) is expected
