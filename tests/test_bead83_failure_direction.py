"""BDL-061.83 — which way each of the S6 decisions fails when it is wrong.

Two mechanisms shipped in S6, and `beadloom-mr2l.23` measured that each was wrong
in the direction that costs the most:

* the DECLARATION PARSER, which the wave decision rests on, failed toward MORE
  parallelism. A second ref written after `;` was dropped, a `refs:` written
  inside a sentence adopted the next word, and the MCP caller composed the
  declaration with spaces where both CLI callers used newlines. Every one of
  those makes two beads MORE likely to share a wave, and the wave shape is
  trusted, so a parser wrong in that direction is worse than no parser.
* the RELEASE GATE, which decides when a reviewer may read the author's account,
  failed toward LESS independence. The verdict marker matched without its colon,
  so `REVIEW ISSUES are still open` opened the gate — the exact string the
  function's own docstring named as the case it prevents — and the author of the
  verdict comment was read from the tracker and never compared with the author of
  the bead.

What this module pins is the DIRECTION, not the individual parses. Every case
below is written as "when the parser cannot tell, the beads are serialised" and
"when the gate cannot tell, the release says so", because a fix that closed the
three measured parses and left the direction alone would be re-broken by the next
declaration nobody thought of.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import pytest

from beadloom.application.review_brief import (
    FINDING_NO_SCOPE,
    FINDING_OUTSIDE_SCOPE,
    FINDING_UNKNOWN_REF,
    AuthorNote,
    assemble_brief,
    release_notes,
)
from beadloom.application.waves import (
    UNRESOLVED_DROPPED_NODE,
    UNRESOLVED_UNANCHORED,
    BeadRecord,
    WaveOverride,
    compose_declaration,
    declared_refs,
    plan_waves,
    resolve_scope,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

#: The sentence measured in `.23`'s M4: a bead DISCUSSING the declaration grammar
#: acquired a genuine scope it never declared, reported as fully resolved.
_PROSE_ABOUT_A_DECLARATION = (
    "It is serialised until it declares `refs: <ref_id>`, billing being the example."
)


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """A graph with two sibling nodes — enough to make a shared node visible."""
    connection = open_db(tmp_path / "beadloom.db")
    create_schema(connection)
    for ref in ("billing", "shipping"):
        connection.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "feature", ref, f"src/{ref}/"),
        )
        connection.execute(
            "INSERT INTO docs (ref_id, path, kind, hash) VALUES (?, ?, ?, ?)",
            (ref, f"docs/{ref}/SPEC.md", "feature", f"h-{ref}"),
        )
    connection.commit()
    return connection


class TestTheParserFailsTowardSerialisation:
    """Every way the declaration cannot be read must serialise, never widen a wave."""

    def test_a_second_ref_after_a_semicolon_is_read_rather_than_dropped(self) -> None:
        """`.23` M3 / OBSERVATION BDL-061.22-A, ruled a defect by `.23` R1.

        `;` is a separator this project's own prose uses for a list. Ending the
        declaration at it dropped a ref the author really did declare.
        """
        assert declared_refs("refs: shipping; billing") == ("billing", "shipping")

    def test_the_two_beads_that_shared_a_wave_at_exit_zero_no_longer_do(
        self, conn: sqlite3.Connection
    ) -> None:
        """`.23` M3, measured on the planner: one wave, no conflict, exit 0.

        Both beads declared `billing`; one wrote its two refs with a semicolon.
        The narrowed scope compared independent and nothing said so.
        """
        plan = plan_waves(
            [
                BeadRecord("a", "work.\nrefs: shipping; billing"),
                BeadRecord("b", "work.\nrefs: billing"),
            ],
            conn=conn,
        )
        assert plan.conflicts != ()
        assert plan.wave_of("a") != plan.wave_of("b")

    def test_a_dotted_ref_id_reaches_the_graph_whole(self) -> None:
        """`_REF_TOKEN` admits a dot that the declaration pattern could not deliver.

        `refs: svc.billing` truncated to `svc`, so a dotted ref id was unusable —
        and if `svc` happened to be a node, the bead was handed a scope it never
        named.
        """
        assert declared_refs("refs: svc.billing") == ("svc.billing",)

    def test_a_word_dropped_from_the_declaration_that_is_a_node_serialises_the_bead(
        self, conn: sqlite3.Connection
    ) -> None:
        """The repair OBSERVATION BDL-061.22-A itself identified.

        Only the first word of a list item is read as a ref, because a declaration
        is written inside prose. That rule cannot change, so the bead says when it
        threw away a word the graph DOES have.
        """
        scope = resolve_scope(conn, BeadRecord("a", "work.\nrefs: billing shipping"))
        assert scope.unresolved == UNRESOLVED_DROPPED_NODE
        assert scope.dropped_refs == ("shipping",)
        assert not scope.resolved

    def test_a_dropped_word_the_graph_does_not_have_leaves_the_scope_resolved(
        self, conn: sqlite3.Connection
    ) -> None:
        """The other direction: prose after a ref must not serialise everything.

        A parser that refused every declaration written inside a sentence would
        serialise every bead in this repository, which is a decision nobody could
        use. Only a dropped word the graph can confirm is a node counts.
        """
        scope = resolve_scope(
            conn, BeadRecord("a", "work.\nrefs: billing and nothing else at all")
        )
        assert scope.resolved
        assert scope.refs == {"billing"}

    def test_a_refs_token_inside_a_sentence_is_prose_and_not_a_declaration(self) -> None:
        """`.23` M4. Bead `.80` did exactly this and the brief printed a finding."""
        assert declared_refs(_PROSE_ABOUT_A_DECLARATION) == ()

    def test_a_bead_that_only_mentions_refs_in_prose_is_unresolved_not_resolved(
        self, conn: sqlite3.Connection
    ) -> None:
        """`.23` M4, measured: refs=('billing',) with unresolved=None.

        A bead acquired a genuine scope it never declared, reported as fully
        RESOLVED, and every pairwise verdict then rested on it.
        """
        scope = resolve_scope(conn, BeadRecord("a", _PROSE_ABOUT_A_DECLARATION))
        assert scope.unresolved == UNRESOLVED_UNANCHORED
        assert scope.refs == frozenset()

    def test_a_bead_whose_declaration_is_prose_does_not_share_a_wave(
        self, conn: sqlite3.Connection
    ) -> None:
        plan = plan_waves(
            [
                BeadRecord("a", _PROSE_ABOUT_A_DECLARATION),
                BeadRecord("b", "work.\nrefs: billing"),
            ],
            conn=conn,
        )
        assert plan.wave_of("a") != plan.wave_of("b")
        assert plan.exit_code == 1

    def test_a_declaration_that_starts_a_bullet_is_still_a_declaration(self) -> None:
        """A list item is how a bead's notes are actually written."""
        assert declared_refs("- refs: billing\n") == ("billing",)
        assert declared_refs("  refs: billing\n") == ("billing",)


class TestOneDeclarationHasOneComposition:
    """`.23` M5 — the parser is shared; the string handed to it was not.

    Both CLI callers joined the four tracker fields with a newline; the MCP tool
    joined them with a space. `.80`'s repair (the separator between the colon and
    the list is `[ \t]`, so a dangling header ends the match instead of moving to
    the next line) rests on that newline, so the space-join gave one caller of
    three the old bug back — the one an agent reaches through MCP.
    """

    #: A record whose declaration DANGLES at a field boundary. Joined with
    #: newlines the header ends the match and the bead declares nothing; joined
    #: with spaces the next field's first word is adopted as a ref.
    _DANGLING: ClassVar[dict[str, str]] = {
        "title": "[a] the bead",
        "description": "Scope\nrefs:",
        "design": "billing is the one we mean",
        "notes": "",
    }

    def test_the_shared_composition_reads_a_dangling_header_as_no_declaration(
        self,
    ) -> None:
        assert declared_refs(compose_declaration(self._DANGLING)) == ()

    def test_a_missing_field_composes_the_same_as_an_empty_one(self) -> None:
        """A tracker that omits `design` must not shift the field boundaries."""
        assert compose_declaration({"title": "t"}) == compose_declaration(
            {"title": "t", "description": "", "design": "", "notes": ""}
        )

    def test_the_mcp_tool_refuses_a_ref_the_declaration_never_named(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The caller an agent reaches through MCP, run rather than read.

        Space-joining the fields put `billing` in front of the dangling header, so
        the tool resolved a bundle for a node the bead never declared while
        `beadloom waves` read the same bead as declaring nothing.
        """
        from beadloom.services import mcp_server

        monkeypatch.setattr(
            mcp_server,
            "_bd_show",
            lambda bead, root: dict(self._DANGLING),
            raising=True,
        )
        payload = mcp_server.handle_bead_context(tmp_path, bead="a")
        assert payload["status"] == "ERROR"
        assert "could not resolve a graph ref" in payload["error"]


class TestAFindingSaysWhatWasMeasured:
    """A finding that claims more than its measurement is the S6 failure in miniature."""

    def test_the_unresolved_finding_does_not_claim_a_placement_the_plan_contradicts(
        self, conn: sqlite3.Connection
    ) -> None:
        """`.23` M10 — the finding said "serialised against every bead"; it was not.

        A `parallel` override is legitimate, its effect is correctly counted, and
        the plan prints the wave list beside the sentence that denies it.
        """
        override = WaveOverride(("a", "b"), "parallel", "measured", "2099-01-01")
        plan = plan_waves(
            [BeadRecord("a", "work."), BeadRecord("b", "work.")],
            conn=conn,
            overrides=[override],
        )
        assert plan.wave_of("a") == plan.wave_of("b")
        unresolved = [f for f in plan.findings if f.startswith("unresolved_scope:")]
        assert unresolved, "the fixture produced no unresolved finding — nothing was tested"
        for finding in unresolved:
            assert "serialised against every bead" not in finding
            assert "refs:" in finding

    def test_the_outside_scope_finding_names_the_window_it_measured(
        self, conn: sqlite3.Connection
    ) -> None:
        """`.23` M8 — measured over the BRANCH, reported as if measured over the BEAD.

        All five S6 briefs reported the identical 65 files and four of them raised
        this finding over a sibling bead's work. No per-bead data exists in the
        commits, so the finding names its window instead of claiming an
        attribution it cannot make.
        """
        brief = assemble_brief(
            conn,
            BeadRecord("a", "work.\nrefs: billing"),
            assignment="do the work",
            changed_paths=frozenset({"src/shipping/core.py"}),
            measured_since="main",
        )
        outside = [f for f in brief.findings if f.startswith(FINDING_OUTSIDE_SCOPE)]
        assert len(outside) == 1
        assert "since main" in outside[0]
        assert "sibling" in outside[0]
        assert "src/shipping/core.py" in outside[0]

    def test_a_bead_that_declares_no_scope_is_a_finding_on_the_brief(
        self, conn: sqlite3.Connection
    ) -> None:
        """`.23` M9 — an exit-1-bearing output with no test anywhere in the suite."""
        brief = assemble_brief(
            conn,
            BeadRecord("a", "work."),
            assignment="do the work",
            changed_paths=frozenset(),
        )
        assert FINDING_NO_SCOPE in brief.findings

    def test_a_ref_the_graph_does_not_have_is_named_on_the_brief(
        self, conn: sqlite3.Connection
    ) -> None:
        """`.23` M9 — and the one that actually misfired in production, on `.80`."""
        brief = assemble_brief(
            conn,
            BeadRecord("a", "work.\nrefs: nowhere"),
            assignment="do the work",
            changed_paths=frozenset(),
        )
        named = [f for f in brief.findings if f.startswith(FINDING_UNKNOWN_REF)]
        assert len(named) == 1
        assert "nowhere" in named[0]


class TestTheReleaseGateFailsTowardWithholding:
    """`.23` M1 and M2 — the gate's two ways of opening for something it should not."""

    def test_the_string_the_docstring_named_as_prevented_does_not_release(self) -> None:
        """`.23` M1, verbatim from `_marker_in`'s own docstring.

        The docstring said a checkpoint that MENTIONS a review does not read as
        one being recorded, and named this string. Measured before the fix:
        released=1, refused=False. The line anchor was there; the colon was not.
        """
        outcome = release_notes(
            [AuthorNote("REVIEW ISSUES are still open, will fix", author="dev")],
            bead_author="dev",
        )
        assert outcome.released == ()
        assert outcome.refused_reason is not None

    def test_a_verdict_line_buried_in_a_checkpoint_does_not_release(self) -> None:
        """A verdict comment OPENS with its marker — the role file says so.

        `.23` M2 measured this exact note releasing the account: the author writes
        a checkpoint, a verdict line sits in the middle of it, and the gate opens.
        """
        outcome = release_notes(
            [
                AuthorNote(
                    "COMPLETED: shipped it\nREVIEW PASSED: I checked my own work",
                    author="dev",
                )
            ],
            bead_author="dev",
        )
        assert outcome.released == ()
        assert outcome.refused_reason is not None

    def test_a_verdict_recorded_by_the_beads_own_author_releases_and_says_so(
        self,
    ) -> None:
        """`.23` M2 — `AuthorNote.author` was read from the tracker and never compared.

        The comparison now happens and its answer is printed. It does not REFUSE,
        for the reason stated in `release.py`: this repository's dev agent and its
        review agent write under one tracker identity, so a refusal would make the
        gate unusable and unusable gates get bypassed rather than obeyed.
        """
        notes = [
            AuthorNote("COMPLETED: shipped it", author="dev"),
            AuthorNote("REVIEW PASSED: reads correct", author="dev"),
        ]
        outcome = release_notes(notes, bead_author="dev")
        assert len(outcome.released) == 2
        assert outcome.independence_note is not None
        assert "dev" in outcome.independence_note

    def test_a_verdict_recorded_by_another_party_releases_with_nothing_to_report(
        self,
    ) -> None:
        notes = [
            AuthorNote("COMPLETED: shipped it", author="dev"),
            AuthorNote("REVIEW PASSED: reads correct", author="reviewer"),
        ]
        outcome = release_notes(notes, bead_author="dev")
        assert len(outcome.released) == 2
        assert outcome.independence_note is None
        assert outcome.verdict_author == "reviewer"

    def test_a_verdict_whose_author_the_tracker_did_not_name_is_reported(self) -> None:
        """An unknown identity is not an independent one — the `unmeasured` rule."""
        outcome = release_notes(
            [AuthorNote("REVIEW PASSED: reads correct", author="")], bead_author="dev"
        )
        assert outcome.released != ()
        assert outcome.independence_note is not None

    def test_a_verdict_and_the_beads_author_differing_only_in_case_is_not_independent(
        self,
    ) -> None:
        outcome = release_notes(
            [AuthorNote("REVIEW PASSED: reads correct", author=" V.Zoologov ")],
            bead_author="v.zoologov",
        )
        assert outcome.independence_note is not None


class TestTheHonestyNoteAndTheCodeAgree:
    """`.79`'s note listed the line-start protection under ENFORCED. It was not.

    The reviewer's own words: had it read that first, it would have accepted the
    claim as the specification instead of probing it. So the sentence is fixed
    with the code, in every place that carries it.
    """

    def test_the_spec_states_the_colon_and_the_opening_line(self) -> None:
        from pathlib import Path as _Path

        spec = (
            _Path(__file__).resolve().parents[1]
            / "docs"
            / "domains"
            / "application"
            / "features"
            / "review-brief"
            / "SPEC.md"
        ).read_text(encoding="utf-8")
        recognised = spec.split("### How a verdict is recognised", 1)[1]
        recognised = recognised.split("###", 1)[0]
        assert "colon" in recognised
        assert "first" in recognised

    def test_every_string_the_docstring_names_as_prevented_is_actually_prevented(
        self,
    ) -> None:
        """The note held to the code, mechanically rather than by reading.

        `_opening_marker`'s docstring quotes the comment texts it says do not open
        the gate. Each quoted string is run through the function. That is what the
        old docstring could not survive: it named `REVIEW ISSUES are still open`
        as prevented, and the function released on it.
        """
        import re

        from beadloom.application.review_brief import release

        doc = release._opening_marker.__doc__ or ""
        quoted = re.findall(r'"([^"]+)"', doc)
        assert quoted, "the docstring names no case — it can claim nothing"
        for text in quoted:
            assert release._opening_marker(text) is None, text
