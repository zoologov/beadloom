"""BDL-068 S1.4 — ``## Axes`` as a required section, and the grammar behind it.

The bead's premise was that ``doc_templates.required_sections`` already derives a
document's required sections from the composed template, so adding the heading
would make the section required by the same act. Measured before anything was
designed, that premise did NOT hold: ``required_sections`` derives over the
``docs`` artifact kind, whose kinds are graph NODE documents, and BRIEF and RFC
have no template in that family at all — their skeletons are fenced blocks
inside the composed ``/templates`` command. So the derivation was EXTENDED to
that second family rather than duplicated beside it, and these cases hold the
extension to the same shape as the original.

The corpus numbers behind the policy choice, measured on this repository's 259
planning documents at the time this was written: requiring every template
heading of every document gives **767** findings, because the archive predates
``language: en`` and carries none of today's headings. Under the peer-majority
policy ``doc_shape`` already declares for generated documentation, the same
requirement gives **6** statements about a kind and **102** about a document.
The second is the policy this project already chose for this exact class.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.application.impact.answer import Boundary, ImpactAnswer, Population, Site
from beadloom.application.impact.section import UNDECIDED, render_axes_section
from beadloom.application.impact.seeds import Seed
from beadloom.application.impact.unresolved import Unresolved
from beadloom.doc_sync.axes_section import (
    AXES_HEADING,
    AXES_WITHOUT_A_SEED,
    AXIS_WITHOUT_A_SCOPE_DECISION,
    NO_SEED,
    check_axes_section,
    read_axes_section,
    refs_line,
)
from beadloom.doc_sync.doc_shape import (
    EMPTY_SECTION,
    MISSING_SECTION,
    check_planning_sections,
    peer_section_shape,
    read_sections,
)
from beadloom.onboarding.composer import PROJECT_FLOW_DIRNAME
from beadloom.onboarding.doc_templates import (
    DEFAULT_DOC_CONFIG,
    planning_skeletons,
    required_sections_by_document_kind,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def _requirements(project_root: Path | None = None) -> dict[str, tuple[str, ...]]:
    return required_sections_by_document_kind(
        config=DEFAULT_DOC_CONFIG, project_root=project_root
    )


def _brief(*, carrying: Sequence[str], empty: Sequence[str] = ()) -> str:
    lines = ["# BRIEF: KEY-1 — a brief", ""]
    for section in carrying:
        lines.append(f"## {section}")
        lines.append("")
        if section not in empty:
            lines.append("a sentence.")
            lines.append("")
    return "\n".join(lines)


class TestTheRequirementIsDerivedFromTheTemplate:
    """The section is required because the template carries it, not because a
    list in code names it."""

    def test_the_brief_and_the_rfc_both_require_axes(self) -> None:
        requirements = _requirements()
        assert AXES_HEADING in requirements["BRIEF"]
        assert AXES_HEADING in requirements["RFC"]

    def test_a_kind_the_templates_do_not_describe_has_no_requirement(self) -> None:
        assert "NOTES" not in _requirements()

    def test_only_the_fenced_skeleton_is_read_not_the_commentary(self) -> None:
        # `## BRIEF.md — Simplified Task Document` is the command's own heading
        # for the kind. Reading the prose would make the commentary's headings
        # required OF the document.
        assert "BRIEF.md — Simplified Task Document" not in _requirements()["BRIEF"]

    def test_a_project_layer_makes_its_own_section_required(self, tmp_path: Path) -> None:
        fragment = tmp_path / PROJECT_FLOW_DIRNAME / "commands"
        fragment.mkdir(parents=True)
        (fragment / "templates.md").write_text(
            "\n## RUNBOOK.md — how this service is operated\n\n"
            "```markdown\n# RUNBOOK\n\n## Paging\n\n[who to wake]\n```\n",
            encoding="utf-8",
        )
        assert _requirements(tmp_path)["RUNBOOK"] == ("Paging",)

    def test_the_two_shipped_axes_blocks_are_one_text(self) -> None:
        # The BRIEF and the RFC carry the same section. Two copies that drift are
        # two sections with one name, so the drift is checked rather than trusted.
        skeletons = planning_skeletons(config=DEFAULT_DOC_CONFIG)
        blocks = {
            kind: skeletons[kind].split(f"## {AXES_HEADING}", 1)[1].split("\n## ", 1)[0]
            for kind in ("BRIEF", "RFC")
        }
        assert blocks["BRIEF"] == blocks["RFC"]


class TestReadingADocumentsSections:
    """What counts as a section, and what counts as an empty one."""

    def test_a_heading_inside_a_fence_is_not_a_section(self) -> None:
        text = "# doc\n\n## Real\n\ntext\n\n```markdown\n## Quoted\n```\n"
        assert [s.title for s in read_sections(text)] == ["doc", "Real"]

    def test_a_section_whose_content_is_in_its_subsections_is_not_empty(self) -> None:
        text = "## Code Standards\n\n### Language\n\nPython 3.10+\n"
        assert not read_sections(text)[0].is_empty

    def test_a_heading_over_only_a_horizontal_rule_is_empty(self) -> None:
        text = "## Axes\n\n---\n\n## Beads\n\nrows\n"
        assert read_sections(text)[0].is_empty

    def test_a_section_that_states_something_is_not_empty(self) -> None:
        assert not read_sections("## Axes\n\na row\n")[0].is_empty


class TestTheStructuralChecksOverPlanningDocuments:
    """``missing-section`` is peer-relative; ``empty-section`` is not."""

    def test_a_brief_missing_a_section_its_peers_carry_is_reported(self) -> None:
        required = _requirements()["BRIEF"]
        without = tuple(s for s in required if s != AXES_HEADING)
        report = check_planning_sections(
            [
                ("a/BRIEF.md", _brief(carrying=required)),
                ("b/BRIEF.md", _brief(carrying=required)),
                ("c/BRIEF.md", _brief(carrying=without)),
            ],
            _requirements(),
        )
        assert [(f.path, f.check) for f in report.findings] == [
            ("c/BRIEF.md", MISSING_SECTION)
        ]
        assert report.findings[0].excerpt == AXES_HEADING

    def test_a_section_below_the_majority_is_reported_once_against_the_kind(
        self,
    ) -> None:
        required = _requirements()["BRIEF"]
        without = tuple(s for s in required if s != AXES_HEADING)
        report = check_planning_sections(
            [
                ("a/BRIEF.md", _brief(carrying=required)),
                ("b/BRIEF.md", _brief(carrying=without)),
                ("c/BRIEF.md", _brief(carrying=without)),
            ],
            _requirements(),
        )
        assert not report.findings
        assert [(c.section, c.ratio) for c in report.conventions] == [
            (AXES_HEADING, "1/3")
        ]

    def test_a_tie_is_not_yet_a_convention(self) -> None:
        required = _requirements()["BRIEF"]
        without = tuple(s for s in required if s != AXES_HEADING)
        report = check_planning_sections(
            [
                ("a/BRIEF.md", _brief(carrying=required)),
                ("b/BRIEF.md", _brief(carrying=without)),
            ],
            _requirements(),
        )
        assert not report.findings
        assert [c.ratio for c in report.conventions] == ["1/2"]

    def test_an_empty_section_is_reported_whatever_the_peers_do(self) -> None:
        required = _requirements()["BRIEF"]
        report = check_planning_sections(
            [("a/BRIEF.md", _brief(carrying=required, empty=(AXES_HEADING,)))],
            _requirements(),
        )
        # One document, so nothing is a majority convention; the empty section is
        # reported anyway, because a heading with nothing under it satisfies a
        # presence check and answers no question.
        assert [f.check for f in report.findings] == [EMPTY_SECTION]
        assert report.findings[0].line == 11

    def test_a_kind_no_template_describes_is_not_judged(self) -> None:
        report = check_planning_sections(
            [("a/NOTES.md", "# notes\n\nprose.\n")], _requirements()
        )
        assert not report.findings
        assert report.kinds_judged == ()
        assert report.documents == 0

    def test_the_peer_policy_is_one_function_over_any_corpus(self) -> None:
        conventions, lost = peer_section_shape(
            {"BRIEF": [("a", ["Axes"]), ("b", ["Axes"]), ("c", [])]},
            {"BRIEF": ("Axes",)},
        )
        assert not conventions
        assert [(entry.document, entry.sections) for entry in lost] == [
            ("c", ("Axes",))
        ]


_SECTION = """## Axes

> **Derived by:** `beadloom impact src/pkg/writer.py`
> **Seed:** `write_yaml` (effect `serialises-yaml`), under rule
> `reaches-an-effect-sink`
> **Unresolved:** 2 unnameable-callee

| Axis | Node | Sites | In scope | Why |
|------|------|-------|----------|-----|
| co-writers | writer | 1 — `src/pkg/save.py:3` | yes | the invariant moves |
| callers | reader | 2 — `src/pkg/read.py:8` | no | reads the result only |
| callers | writer | 1 — `src/pkg/again.py:2` | yes | the same node again |
"""


class TestTheAxesGrammar:
    """One grammar, read in both directions."""

    def test_the_seed_field_is_read_across_the_lines_it_wraps_over(self) -> None:
        section = read_axes_section(_SECTION)
        assert section is not None
        assert "reaches-an-effect-sink" in section.seed

    def test_the_scope_decision_is_read_per_row(self) -> None:
        section = read_axes_section(_SECTION)
        assert section is not None
        assert [axis.in_scope for axis in section.axes] == [True, False, True]

    def test_the_refs_line_names_the_kept_nodes_once_in_order(self) -> None:
        section = read_axes_section(_SECTION)
        assert section is not None
        assert refs_line(section) == "refs: writer"

    def test_the_skeletons_offered_cell_decides_nothing(self) -> None:
        # `yes / no` OFFERS both. Reading it as a yes because the word occurs in
        # it would turn the template's own prompt into a decision.
        section = read_axes_section(_SECTION.replace("| yes |", "| yes / no |", 1))
        assert section is not None
        assert section.axes[0].in_scope is None

    def test_a_document_with_no_axes_section_reads_as_none(self) -> None:
        assert read_axes_section("# BRIEF\n\n## Problem\n\ntext\n") is None

    def test_axes_without_a_seed_are_reported(self) -> None:
        text = "\n".join(
            line for line in _SECTION.splitlines() if not line.startswith("> **Seed:")
        )
        assert [f.check for f in check_axes_section("a/BRIEF.md", text)] == [
            AXES_WITHOUT_A_SEED
        ]

    def test_a_stated_absence_of_a_seed_is_naming_one(self) -> None:
        text = _SECTION.replace(
            "> **Seed:** `write_yaml` (effect `serialises-yaml`), under rule",
            f"> **Seed:** {NO_SEED} — no name the target reaches performs a declared",
        )
        assert not [
            f for f in check_axes_section("a/BRIEF.md", text) if f.check == AXES_WITHOUT_A_SEED
        ]

    def test_an_undecided_row_is_reported_with_its_line(self) -> None:
        text = _SECTION.replace("| yes | the invariant moves |", f"| {UNDECIDED} |  |")
        findings = [
            f
            for f in check_axes_section("a/BRIEF.md", text)
            if f.check == AXIS_WITHOUT_A_SCOPE_DECISION
        ]
        assert len(findings) == 1
        assert findings[0].line == 10

    def test_a_section_with_no_rows_is_not_reported_by_these_checks(self) -> None:
        # An empty section is `empty-section`'s finding, and reporting it here
        # too would be one fault under two names.
        assert check_axes_section("a/BRIEF.md", "## Axes\n\n") == ()


def _answer(
    *,
    seeds: tuple[Seed, ...] = (),
    co_writers: Population,
    unresolved: tuple[Unresolved, ...] = (),
) -> ImpactAnswer:
    return ImpactAnswer(
        target="src/pkg/writer.py",
        root="src/pkg",
        seed_rule="reaches-an-effect-sink",
        seed_rule_statement="a name the target reaches whose own body performs an effect",
        effect_rules=(("serialises-yaml", "the body calls a YAML serialiser itself"),),
        seeds=seeds,
        co_writers=co_writers,
        callers=Population(resolved=True),
        commands=(),
        boundary=Boundary(
            resolved=True,
            target_node="writer",
            target_domain="pkg",
            nodes_touched=("writer",),
            domains_touched=("pkg",),
            leaves_the_target_node=False,
            leaves_the_target_domain=False,
        ),
        unresolved=unresolved,
    )


class TestRenderingASectionFromAnAnswer:
    """The renderer writes the derivation's half and leaves the person's."""

    def test_the_rendered_section_reads_back_as_what_it_was_rendered_from(self) -> None:
        rendered = render_axes_section(
            _answer(
                seeds=(
                    Seed(
                        name="write_yaml",
                        path=Path("src/pkg/writer.py"),
                        lineno=10,
                        effect="serialises-yaml",
                    ),
                ),
                co_writers=Population(
                    resolved=True,
                    sites=(
                        Site(
                            name="save",
                            path="src/pkg/save.py",
                            lineno=3,
                            node="writer",
                            domain="pkg",
                        ),
                    ),
                ),
            )
        )
        section = read_axes_section(rendered)
        assert section is not None
        assert "write_yaml" in section.seed
        # The callers axis is RESOLVED and empty, so it is stated rather than
        # omitted: "nothing else calls this" and "nobody asked" are different
        # answers, and a row that vanishes reads as the second.
        assert [(a.axis, a.node) for a in section.axes] == [
            ("co-writers", "writer"),
            ("callers", ""),
        ]

    def test_every_rendered_row_is_undecided_until_a_person_rules_on_it(self) -> None:
        rendered = render_axes_section(
            _answer(
                seeds=(
                    Seed(
                        name="write_yaml",
                        path=Path("src/pkg/writer.py"),
                        lineno=10,
                        effect="serialises-yaml",
                    ),
                ),
                co_writers=Population(resolved=True),
            )
        )
        findings = check_axes_section("a/BRIEF.md", rendered)
        assert {f.check for f in findings} == {AXIS_WITHOUT_A_SCOPE_DECISION}

    def test_an_absent_seed_renders_as_unresolved_and_never_as_zero(self) -> None:
        rendered = render_axes_section(
            _answer(
                co_writers=Population(
                    resolved=False, reason="no seed was derived, so no writer population"
                ),
                unresolved=(
                    Unresolved(kind="no-seed", detail="no declared effect is reached"),
                ),
            )
        )
        assert f"**Seed:** {NO_SEED}" in rendered
        row = next(line for line in rendered.splitlines() if "| co-writers |" in line)
        assert "unresolved" in row
        assert "0" not in row

    def test_the_unresolved_population_is_counted_by_kind(self) -> None:
        rendered = render_axes_section(
            _answer(
                seeds=(
                    Seed(
                        name="write_yaml",
                        path=Path("src/pkg/writer.py"),
                        lineno=1,
                        effect="serialises-yaml",
                    ),
                ),
                co_writers=Population(resolved=True),
                unresolved=(
                    Unresolved(kind="unnameable-callee", detail="one"),
                    Unresolved(kind="unnameable-callee", detail="two"),
                    Unresolved(kind="getattr-dispatch", detail="three"),
                ),
            )
        )
        assert "2 unnameable-callee" in rendered
        assert "1 getattr-dispatch" in rendered


class TestOneCompositionBehindBothSurfaces:
    """The Gate and the CLI report one run, so they cannot disagree."""

    def test_the_gate_step_and_the_command_read_the_same_findings(
        self, tmp_path: Path
    ) -> None:
        from click.testing import CliRunner

        from beadloom.application.gate import _step_docs_quality
        from beadloom.services.cli import main

        features = tmp_path / ".claude" / "development" / "docs" / "features" / "K-1"
        features.mkdir(parents=True)
        required = _requirements()["BRIEF"]
        (features / "BRIEF.md").write_text(
            _brief(carrying=required, empty=(AXES_HEADING,)), encoding="utf-8"
        )

        step = _step_docs_quality(tmp_path)
        result = CliRunner().invoke(
            main, ["docs", "quality", "--json", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0
        import json

        payload = json.loads(result.stdout)
        assert payload["checks"][EMPTY_SECTION]["findings"] == 1
        assert sum(
            1 for finding in step.findings if finding["rule"] == EMPTY_SECTION
        ) == 1
