"""Unit tests for the three documentation spaces (BDL-061 S5).

Two halves, matching the two modules: the vocabulary and roots
(``infrastructure/doc_roots.py``), and the TO-BE -> AS-IS relation
(``application/doc_spaces.py``).

The adopter half is not decoration. Every check in this epic has measured
Beadloom measuring Beadloom, and a classification that reads correct here
because our own layout happens to match the default is exactly the class
``tests/adopter_project.py`` was built to catch — so the relation is exercised
against a TypeScript project with its own tree and no ``.claude/`` at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.application.doc_spaces import (
    FINDING_CONFIG,
    FINDING_NO_AS_IS,
    FINDING_WORKING_CONTRADICTED,
    FINDING_WORKING_INERT,
    SpacesReport,
    beads_by_epic,
    check_spaces,
    jsonl_records,
    read_epic_intents,
)
from beadloom.infrastructure.doc_roots import (
    SPACE_AS_IS,
    SPACE_TO_BE,
    SPACE_WORKING,
    default_doc_spaces,
    document_kind,
    resolve_doc_spaces,
)
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    from pathlib import Path

_EPICS = ".claude/development/docs/features"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(root: Path, block: dict[str, object]) -> None:
    _write(root, ".beadloom/config.yml", yaml.safe_dump({"doc_roots": block}))


def _context(refs: str) -> str:
    return f"# CONTEXT\n\n## Goal\n\nShip it.\n\n## Related Files\n\n{refs}\n"


def _report(root: Path, **kwargs: object) -> SpacesReport:
    return check_spaces(
        root,
        spaces=resolve_doc_spaces(root),
        known_refs=frozenset(kwargs.get("known", ())),  # type: ignore[arg-type]
        documented_refs=frozenset(kwargs.get("documented", ())),  # type: ignore[arg-type]
        declared_doc_paths=frozenset(kwargs.get("declared", ())),  # type: ignore[arg-type]
        beads_by_epic=kwargs.get("beads"),  # type: ignore[arg-type]
    )


class TestDocumentKind:
    def test_stem_is_the_kind(self) -> None:
        assert document_kind("docs/features/X/PRD.md") == "PRD"

    def test_windows_separator_is_a_separator(self) -> None:
        assert document_kind(r".claude\x\ACTIVE.md") == "ACTIVE"

    def test_a_dotfile_with_no_suffix_is_its_own_name(self) -> None:
        assert document_kind("ROADMAP") == "ROADMAP"


class TestSpaceOf:
    def test_kind_beats_root(self) -> None:
        """ACTIVE.md lives INSIDE the TO-BE tree; kind is what decides."""
        spaces = default_doc_spaces()
        assert spaces.space_of(f"{_EPICS}/BDL-1/ACTIVE.md") == SPACE_WORKING
        assert spaces.space_of(f"{_EPICS}/BDL-1/PRD.md") == SPACE_TO_BE

    def test_case_does_not_make_a_second_vocabulary(self) -> None:
        assert default_doc_spaces().space_of("planning/prd.md") == SPACE_TO_BE

    def test_a_recursive_root_matches_its_own_top_level(self) -> None:
        """``docs/**/*.md`` must classify ``docs/x.md``; ``Path.glob`` finds it.

        A document a root glob FINDS and the classifier then puts in no space is
        the check disagreeing with itself, and it would silently drop the file
        from every population.
        """
        assert default_doc_spaces().space_of("docs/architecture.md") == SPACE_AS_IS

    def test_a_document_in_no_root_and_no_kind_is_unclassified(self) -> None:
        assert default_doc_spaces().space_of("vendor/lib/notes.md") is None


class TestConfiguredRoots:
    def test_roots_move(self, tmp_path: Path) -> None:
        _config(tmp_path, {"to_be": {"roots": ["planning/*/*.md"]}})
        _write(tmp_path, "planning/RIDE-9/CONTEXT.md", _context("`x`"))
        _write(tmp_path, f"{_EPICS}/DECOY/CONTEXT.md", _context("`x`"))
        found = [
            p.as_posix()
            for p in resolve_doc_spaces(tmp_path).documents_in(tmp_path, SPACE_TO_BE)
        ]
        assert any("planning/RIDE-9" in p for p in found)
        assert not any("DECOY" in p for p in found)

    def test_an_empty_list_is_a_declaration_not_a_default(self, tmp_path: Path) -> None:
        _config(tmp_path, {"to_be": {"roots": []}})
        assert resolve_doc_spaces(tmp_path).roots[SPACE_TO_BE] == ()

    def test_an_unknown_space_is_a_config_error(self, tmp_path: Path) -> None:
        _config(tmp_path, {"todo": {"roots": ["x/*.md"]}})
        errors = resolve_doc_spaces(tmp_path).config_errors
        assert any("not a documentation space" in e for e in errors)

    def test_a_malformed_block_does_not_raise(self, tmp_path: Path) -> None:
        _write(tmp_path, ".beadloom/config.yml", yaml.safe_dump({"doc_roots": ["a"]}))
        spaces = resolve_doc_spaces(tmp_path)
        assert spaces.config_errors
        assert spaces.roots[SPACE_AS_IS] == default_doc_spaces().roots[SPACE_AS_IS]

    def test_no_config_file_is_the_shipped_default(self, tmp_path: Path) -> None:
        assert resolve_doc_spaces(tmp_path).roots == default_doc_spaces().roots


class TestWorkingExemption:
    def test_an_exemption_without_a_reason_is_a_config_error(self, tmp_path: Path) -> None:
        _config(tmp_path, {"working": {"exempt_from_freshness": True}})
        errors = resolve_doc_spaces(tmp_path).config_errors
        assert any("without a stated reason" in e for e in errors)

    def test_the_exemption_still_applies_while_the_error_stands(self, tmp_path: Path) -> None:
        """The remedy for a missing sentence must not be a wave of stale docs."""
        _config(tmp_path, {"working": {"exempt_from_freshness": True}})
        assert resolve_doc_spaces(tmp_path).working.exempt_from_freshness is True

    def test_a_declared_reason_is_carried(self, tmp_path: Path) -> None:
        _config(
            tmp_path,
            {"working": {"exempt_from_freshness": True, "reason": "a diary, not a spec"}},
        )
        assert resolve_doc_spaces(tmp_path).working.reason == "a diary, not a spec"

    def test_turning_it_off_is_allowed_and_needs_no_reason(self, tmp_path: Path) -> None:
        _config(tmp_path, {"working": {"exempt_from_freshness": False}})
        spaces = resolve_doc_spaces(tmp_path)
        assert spaces.working.exempt_from_freshness is False
        assert spaces.config_errors == ()

    def test_an_exemption_matching_nothing_reports_itself(self, tmp_path: Path) -> None:
        _config(
            tmp_path,
            {
                "working": {
                    "kinds": ["JOURNAL"],
                    "exempt_from_freshness": True,
                    "reason": "a journal records the day",
                }
            },
        )
        rules = [f.rule for f in _report(tmp_path).findings]
        assert FINDING_WORKING_INERT in rules

    def test_it_goes_quiet_once_it_excuses_something(self, tmp_path: Path) -> None:
        """TESTS MUST BITE: the liveness finding must be able to STOP firing."""
        _config(
            tmp_path,
            {
                "working": {
                    "kinds": ["JOURNAL"],
                    "exempt_from_freshness": True,
                    "reason": "a journal records the day",
                }
            },
        )
        _write(tmp_path, f"{_EPICS}/BDL-1/JOURNAL.md", "# journal\n")
        rules = [f.rule for f in _report(tmp_path).findings]
        assert FINDING_WORKING_INERT not in rules

    def test_a_declaration_the_graph_contradicts_is_reported(self, tmp_path: Path) -> None:
        doc = f"{_EPICS}/BDL-1/ACTIVE.md"
        _write(tmp_path, doc, "# ACTIVE\n")
        report = _report(tmp_path, declared={doc})
        assert FINDING_WORKING_CONTRADICTED in [f.rule for f in report.findings]

    def test_an_undeclared_working_document_is_not_a_contradiction(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/ACTIVE.md", "# ACTIVE\n")
        report = _report(tmp_path)
        assert FINDING_WORKING_CONTRADICTED not in [f.rule for f in report.findings]

    def test_config_errors_reach_the_report(self, tmp_path: Path) -> None:
        _config(tmp_path, {"working": {"exempt_from_freshness": True}})
        assert FINDING_CONFIG in [f.rule for f in _report(tmp_path).findings]


class TestRelatedFilesIsADeclaration:
    def test_a_ref_outside_the_section_is_not_read(self, tmp_path: Path) -> None:
        """The measured false-positive class: prose that uses a ref as a word."""
        _write(
            tmp_path,
            f"{_EPICS}/BDL-1/CONTEXT.md",
            "# CONTEXT\n\n## Goal\n\nThe `status` line was wrong.\n\n"
            "## Related Files\n\nDiscover via `beadloom ctx <ref-id>`.\n",
        )
        intents = read_epic_intents(
            tmp_path,
            spaces=resolve_doc_spaces(tmp_path),
            known_refs=frozenset({"status"}),
            beads_by_epic={},
        )
        assert intents[0].declared_refs == ()

    def test_a_ref_inside_the_section_is_read_with_its_line(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`, `ledger`"))
        intents = read_epic_intents(
            tmp_path,
            spaces=resolve_doc_spaces(tmp_path),
            known_refs=frozenset({"billing", "ledger"}),
            beads_by_epic={},
        )
        assert [r for r, _ in intents[0].declared_refs] == ["billing", "ledger"]
        assert all(line > 0 for _, line in intents[0].declared_refs)

    def test_a_backticked_token_that_is_no_node_is_not_a_declaration(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`not-a-node`"))
        intents = read_epic_intents(
            tmp_path,
            spaces=resolve_doc_spaces(tmp_path),
            known_refs=frozenset({"billing"}),
            beads_by_epic={},
        )
        assert intents[0].declared_refs == ()

    def test_a_brief_declares_the_same_way(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BUG-2/BRIEF.md", _context("`billing`"))
        intents = read_epic_intents(
            tmp_path,
            spaces=resolve_doc_spaces(tmp_path),
            known_refs=frozenset({"billing"}),
            beads_by_epic={},
        )
        assert intents[0].key == "BUG-2"


class TestRelation:
    def test_closed_beads_and_no_as_is_document_is_reported(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        report = _report(
            tmp_path, known={"billing"}, beads={"BDL-1": ("closed", "closed")}
        )
        assert [f.rule for f in report.findings] == [FINDING_NO_AS_IS]
        assert report.refs_checked == 1

    def test_a_documented_node_is_not_reported(self, tmp_path: Path) -> None:
        """TESTS MUST BITE: the finding must stop when the document exists."""
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        report = _report(
            tmp_path,
            known={"billing"},
            documented={"billing"},
            beads={"BDL-1": ("closed",)},
        )
        assert report.findings == ()
        assert report.refs_checked == 1

    def test_an_epic_with_no_closed_bead_is_not_reported(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        report = _report(tmp_path, known={"billing"}, beads={"BDL-1": ("open",)})
        assert report.findings == ()
        assert report.refs_checked == 0

    def test_an_epic_declaring_nothing_is_unresolved_not_clean(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("nothing here"))
        report = _report(tmp_path, beads={"BDL-1": ("closed",)})
        assert report.unresolved_epics == ("BDL-1",)
        assert report.epics_declaring_nothing == 1
        assert report.findings == ()

    def test_an_empty_population_says_it_related_nothing(self, tmp_path: Path) -> None:
        """A relation check with nothing to relate must not read as clean."""
        report = _report(tmp_path, beads={})
        assert report.relation_checked is False

    def test_a_population_that_related_something_says_so(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        report = _report(
            tmp_path, known={"billing"}, documented={"billing"}, beads={"BDL-1": ("closed",)}
        )
        assert report.relation_checked is True

    def test_no_tracker_is_not_an_epic_without_closed_beads(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        report = _report(tmp_path, known={"billing"}, beads=None)
        assert report.epics_without_bead_status == 1
        assert report.findings == ()

    def test_a_working_document_is_not_in_the_to_be_population(self, tmp_path: Path) -> None:
        _write(tmp_path, f"{_EPICS}/BDL-1/CONTEXT.md", _context("`billing`"))
        _write(tmp_path, f"{_EPICS}/BDL-1/ACTIVE.md", "# ACTIVE\n")
        report = _report(tmp_path, known={"billing"}, beads={})
        assert report.populations[SPACE_TO_BE] == 1
        assert report.populations[SPACE_WORKING] == 1


class TestBeadsByEpic:
    def test_the_key_is_read_from_the_title(self) -> None:
        grouped = beads_by_epic(
            [
                {"title": "[BDL-061.17][dev] S5", "status": "closed"},
                {"title": "[BDL-061.18][test] S5", "status": "open"},
            ]
        )
        assert grouped == {"BDL-061": ("closed", "open")}

    def test_a_bracketless_epic_key_is_read(self) -> None:
        grouped = beads_by_epic([{"title": "[BDL-060] epic", "status": "closed"}])
        assert grouped == {"BDL-060": ("closed",)}

    def test_a_suffixed_key_keeps_its_suffix(self) -> None:
        grouped = beads_by_epic([{"title": "[BDL-025-UX.3] x", "status": "closed"}])
        assert grouped == {"BDL-025-UX": ("closed",)}

    def test_a_title_naming_no_key_is_dropped_not_guessed(self) -> None:
        assert beads_by_epic([{"title": "Merge Slot", "status": "open"}]) == {}


class TestJsonlRecords:
    def test_a_missing_export_is_none_not_empty(self, tmp_path: Path) -> None:
        """None and () mean different things: unknown versus known-to-be-none."""
        assert jsonl_records(tmp_path) is None

    def test_a_blank_line_is_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path, ".beads/issues.jsonl", '{"title":"[A-1] x","status":"closed"}\n\n')
        records = jsonl_records(tmp_path)
        assert records is not None
        assert len(records) == 1

    def test_an_unparseable_line_does_not_abandon_the_file(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            ".beads/issues.jsonl",
            'not json\n{"title":"[A-1] x","status":"closed"}\n',
        )
        records = jsonl_records(tmp_path)
        assert records is not None
        assert len(records) == 1


class TestNotBeadloom:
    """TRUE HERE IS NOT TRUE — the relation on a project with no ``.claude/``."""

    @pytest.fixture()
    def adopter(self, tmp_path: Path) -> Path:
        project = typescript_project(tmp_path / "orders-web")
        _config(
            project.root,
            {
                "to_be": {"roots": ["design/*/*.md"]},
                "as_is": {"roots": ["handbook/**/*.md"]},
            },
        )
        return project.root

    def test_the_shipped_default_finds_nothing_here(self, adopter: Path) -> None:
        """The premise: this project has no planning tree at our default path."""
        assert default_doc_spaces().documents_in(adopter, SPACE_TO_BE) == []

    def test_the_configured_tree_is_the_one_read(self, adopter: Path) -> None:
        _write(adopter, "design/ORD-4/CONTEXT.md", _context("`checkout`"))
        report = _report(adopter, known={"checkout"}, beads={"ORD-4": ("closed",)})
        assert [f.path for f in report.findings] == ["design/ORD-4/CONTEXT.md"]

    def test_a_documented_node_is_clean_there_too(self, adopter: Path) -> None:
        _write(adopter, "design/ORD-4/CONTEXT.md", _context("`checkout`"))
        _write(adopter, "handbook/checkout.md", "# checkout\n")
        report = _report(
            adopter,
            known={"checkout"},
            documented={"checkout"},
            beads={"ORD-4": ("closed",)},
        )
        assert report.findings == ()
        assert report.populations[SPACE_AS_IS] == 1

    def test_no_beadloom_path_leaks_into_the_answer(self, adopter: Path) -> None:
        _write(adopter, "design/ORD-4/CONTEXT.md", _context("`checkout`"))
        report = _report(adopter, known={"checkout"}, beads={"ORD-4": ("closed",)})
        rendered = " ".join(f"{f.path} {f.why}" for f in report.findings)
        assert ".claude" not in rendered
        assert "beadloom" not in rendered.lower()
