"""The intent a node carries, delivered to the reader of that node.

`beadloom ctx` answers what a node IS — its AS-IS documentation, its symbols,
its edges. This suite is about the other half: what it is FOR. The claim under
test is a **relation**, so the tests are written around the three answers that
relation can have and around the difference between two of them that reads the
same if nobody keeps them apart — *no epic declares this node* and *nobody
looked*.

The join itself is not re-tested here. `beadloom-mr2l.17` built and measured it
(`read_epic_intents`, the scoped `Related Files` read); this suite tests the
selection policy on top of it, the adapter that feeds it, and the two surfaces
that deliver it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from beadloom.application.intent_reader import read_intent, read_node_intent
from beadloom.context_oracle.intent import (
    INTENT_DECLARED,
    INTENT_NONE_DECLARED,
    INTENT_NOT_CHECKED,
    MAX_DECLARATIONS,
    REASON_CONFIG_ERROR,
    REASON_NO_EPIC_DECLARES_ANY_NODE,
    REASON_NO_INTENT_DOCUMENTS,
    REASON_NOT_READ,
    DeclaredIntent,
    IntentReading,
    describe_intent_reason,
    select_intent,
)
from beadloom.services.cli import main
from tests.adopter_project import beadloom_local_facts_in, typescript_project

if TYPE_CHECKING:
    from pathlib import Path

_EPICS = ".claude/development/docs/features"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _context(title: str, refs: str) -> str:
    return f"# {title}\n\n## Goal\n\nShip it.\n\n## Related Files\n\n{refs}\n"


def _declaration(epic: str, ref_id: str, *, line: int = 9) -> DeclaredIntent:
    return DeclaredIntent(
        epic=epic,
        title=f"{epic} title",
        document=f"{_EPICS}/{epic}/CONTEXT.md",
        line=line,
        ref_id=ref_id,
    )


class TestSelectIntent:
    """The policy: which recorded intent belongs to a node, and what absence says."""

    def test_a_declaring_epic_is_named_with_where_to_read_it(self) -> None:
        reading = IntentReading(
            declarations=(_declaration("ORD-4", "checkout", line=12),),
            epics_read=3,
            epics_declaring_nodes=1,
        )
        section = select_intent(reading, ["checkout"])
        assert section["status"] == INTENT_DECLARED
        assert section["declared_by"] == [
            {
                "epic": "ORD-4",
                "title": "ORD-4 title",
                "document": f"{_EPICS}/ORD-4/CONTEXT.md",
                "line": 12,
                "ref_id": "checkout",
            }
        ]

    def test_a_node_nobody_declared_is_checked_and_empty(self) -> None:
        """The common case, and it must carry the size of what was searched."""
        reading = IntentReading(
            declarations=(_declaration("ORD-4", "checkout"),),
            epics_read=61,
            epics_declaring_nodes=5,
        )
        section = select_intent(reading, ["shipping"])
        assert section["status"] == INTENT_NONE_DECLARED
        assert section["reason"] is None
        assert section["epics_read"] == 61
        assert section["epics_declaring_nodes"] == 5
        assert section["declared_by"] == []

    def test_a_space_nobody_read_is_not_the_same_as_a_node_nobody_declared(self) -> None:
        """Absence is not evidence — the distinction this epic paid two slices for."""
        section = select_intent(None, ["shipping"])
        assert section["status"] == INTENT_NOT_CHECKED
        assert section["reason"] == REASON_NOT_READ
        assert section["status"] != INTENT_NONE_DECLARED

    def test_an_empty_to_be_space_is_not_checked_rather_than_clean(self) -> None:
        section = select_intent(IntentReading(), ["shipping"])
        assert section["status"] == INTENT_NOT_CHECKED
        assert section["reason"] == REASON_NO_INTENT_DOCUMENTS
        assert section["epics_read"] == 0

    def test_a_population_that_declares_nothing_at_all_is_not_checked(self) -> None:
        """`relation_checked` is False when nothing was related; so is this."""
        reading = IntentReading(declarations=(), epics_read=12, epics_declaring_nodes=0)
        section = select_intent(reading, ["shipping"])
        assert section["status"] == INTENT_NOT_CHECKED
        assert section["reason"] == REASON_NO_EPIC_DECLARES_ANY_NODE
        assert section["epics_read"] == 12

    def test_a_configuration_that_could_not_be_read_says_so(self) -> None:
        reading = IntentReading(unreadable_reason=REASON_CONFIG_ERROR)
        section = select_intent(reading, ["shipping"])
        assert section["status"] == INTENT_NOT_CHECKED
        assert section["reason"] == REASON_CONFIG_ERROR

    def test_only_the_focus_refs_are_looked_up(self) -> None:
        """The subgraph reaches 20 nodes; the question was asked about one."""
        reading = IntentReading(
            declarations=(
                _declaration("ORD-4", "checkout"),
                _declaration("ORD-5", "routing"),
            ),
            epics_read=2,
            epics_declaring_nodes=2,
        )
        section = select_intent(reading, ["checkout"])
        assert [d["ref_id"] for d in section["declared_by"]] == ["checkout"]

    def test_every_focus_ref_is_looked_up(self) -> None:
        reading = IntentReading(
            declarations=(
                _declaration("ORD-4", "checkout"),
                _declaration("ORD-5", "routing"),
            ),
            epics_read=2,
            epics_declaring_nodes=2,
        )
        section = select_intent(reading, ["checkout", "routing"])
        assert {d["ref_id"] for d in section["declared_by"]} == {"checkout", "routing"}

    def test_the_highest_numbered_epic_comes_first(self) -> None:
        """Descending NATURAL key, because a tracker allocates numbers in time
        order. A heuristic, and it is why the truncated ones are still named.
        Plain string order would put ORD-4 above ORD-31, which is backwards."""
        reading = IntentReading(
            declarations=(
                _declaration("ORD-4", "checkout"),
                _declaration("ORD-31", "checkout"),
                _declaration("ORD-12", "checkout"),
            ),
            epics_read=3,
            epics_declaring_nodes=3,
        )
        section = select_intent(reading, ["checkout"])
        assert [d["epic"] for d in section["declared_by"]] == ["ORD-31", "ORD-12", "ORD-4"]

    def test_declarations_past_the_cap_are_named_rather_than_dropped(self) -> None:
        keys = [f"ORD-{n}" for n in range(1, MAX_DECLARATIONS + 3)]
        reading = IntentReading(
            declarations=tuple(_declaration(k, "checkout") for k in keys),
            epics_read=len(keys),
            epics_declaring_nodes=len(keys),
        )
        section = select_intent(reading, ["checkout"])
        assert len(section["declared_by"]) == MAX_DECLARATIONS
        named = [d["epic"] for d in section["declared_by"]] + section["also_declared_by"]
        assert sorted(named) == sorted(keys)

    def test_nothing_is_omitted_when_the_cap_is_not_reached(self) -> None:
        reading = IntentReading(
            declarations=(_declaration("ORD-4", "checkout"),),
            epics_read=1,
            epics_declaring_nodes=1,
        )
        assert select_intent(reading, ["checkout"])["also_declared_by"] == []

    def test_every_reason_has_prose(self) -> None:
        for reason in (
            REASON_NOT_READ,
            REASON_NO_INTENT_DOCUMENTS,
            REASON_NO_EPIC_DECLARES_ANY_NODE,
            REASON_CONFIG_ERROR,
        ):
            assert describe_intent_reason(reason) != reason
            assert describe_intent_reason(reason).strip()


class TestReadIntent:
    """The adapter: the TO-BE space read off disk, through `.17`'s join."""

    def test_a_declared_node_is_read_from_the_related_files_section(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, f"{_EPICS}/ORD-4/CONTEXT.md", _context("Checkout", "`checkout`"))
        reading = read_intent(tmp_path, known_refs=frozenset({"checkout"}))
        assert [d.ref_id for d in reading.declarations] == ["checkout"]
        assert reading.epics_read == 1
        assert reading.epics_declaring_nodes == 1

    def test_the_title_is_the_intent_documents_own_heading(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            f"{_EPICS}/ORD-4/CONTEXT.md",
            _context("ORD-4 — one-click checkout", "`checkout`"),
        )
        reading = read_intent(tmp_path, known_refs=frozenset({"checkout"}))
        assert reading.declarations[0].title == "ORD-4 — one-click checkout"

    def test_a_ref_outside_the_declaration_section_is_not_read(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            f"{_EPICS}/ORD-4/CONTEXT.md",
            "# ORD-4\n\n## Goal\n\nRewrite `checkout`.\n",
        )
        reading = read_intent(tmp_path, known_refs=frozenset({"checkout"}))
        assert reading.declarations == ()
        assert reading.epics_read == 1
        assert reading.epics_declaring_nodes == 0

    def test_a_project_with_no_planning_tree_reads_no_epic(self, tmp_path: Path) -> None:
        reading = read_intent(tmp_path, known_refs=frozenset({"checkout"}))
        assert reading.epics_read == 0
        assert reading.declarations == ()

    def test_the_tracker_is_never_opened(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`bd close` writes only the local database, so the committed export and
        the live tracker disagree on a branch. A bead status shown here would be
        confidently wrong, so this read makes no bead claim and pays no 2.7 MB."""
        from beadloom.application import doc_spaces

        def boom(_root: Path) -> None:
            raise AssertionError("the tracker export was read")

        monkeypatch.setattr(doc_spaces, "jsonl_records", boom)
        _write(tmp_path, f"{_EPICS}/ORD-4/CONTEXT.md", _context("Checkout", "`checkout`"))
        assert read_intent(tmp_path, known_refs=frozenset({"checkout"})).epics_read == 1


class TestReadIntentInAnAdopterProject:
    """TRUE HERE IS NOT TRUE — an adopter's planning tree is not laid out like ours."""

    @pytest.fixture()
    def adopter(self, tmp_path: Path) -> Path:
        project = typescript_project(tmp_path / "orders-web")
        _write(
            project.root,
            ".beadloom/config.yml",
            yaml.safe_dump({"doc_roots": {"to_be": {"roots": ["design/*/*.md"]}}}),
        )
        return project.root

    def test_the_configured_tree_is_the_one_read(self, adopter: Path) -> None:
        _write(adopter, "design/ORD-4/CONTEXT.md", _context("Checkout", "`checkout`"))
        reading = read_intent(adopter, known_refs=frozenset({"checkout"}))
        assert [d.epic for d in reading.declarations] == ["ORD-4"]
        assert reading.declarations[0].document == "design/ORD-4/CONTEXT.md"

    def test_a_document_at_our_default_path_is_not_read_there(self, adopter: Path) -> None:
        """The decoy: our shipped root is not this project's root."""
        _write(adopter, f"{_EPICS}/BDL-9/CONTEXT.md", _context("Ours", "`checkout`"))
        reading = read_intent(adopter, known_refs=frozenset({"checkout"}))
        assert reading.epics_read == 0
        assert reading.declarations == ()

    def test_no_beadloom_path_leaks_into_the_answer(self, adopter: Path) -> None:
        _write(adopter, "design/ORD-4/CONTEXT.md", _context("Checkout", "`checkout`"))
        reading = read_intent(adopter, known_refs=frozenset({"checkout"}))
        rendered = " ".join(f"{d.document} {d.title}" for d in reading.declarations)
        assert beadloom_local_facts_in(rendered) == []
        assert ".claude" not in rendered


def _project(tmp_path: Path, *, declare: str | None = "PROJ-1") -> Path:
    """A minimal indexed project, optionally with an epic declaring a node."""
    project = tmp_path / "proj"
    graph_dir = project / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "features.yml").write_text(
        yaml.safe_dump(
            {
                "nodes": [
                    {"ref_id": "PROJ-1", "kind": "feature", "summary": "Track filtering"},
                    {"ref_id": "routing", "kind": "domain", "summary": "Routing domain"},
                ],
                "edges": [{"src": "PROJ-1", "dst": "routing", "kind": "part_of"}],
            }
        ),
        encoding="utf-8",
    )
    _write(project, "docs/spec.md", "## Specification\n\nTrack filtering rules.\n")
    if declare is not None:
        _write(
            project,
            f"{_EPICS}/ORD-4/CONTEXT.md",
            _context("ORD-4 — filter tracks by mood", f"`{declare}`"),
        )
    from beadloom.application.reindex import reindex

    reindex(project)
    return project


class TestCtxDeliversIntent:
    """The surface an agent actually travels: `beadloom ctx <ref-id>`."""

    def test_json_names_the_epic_that_declared_the_node(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        result = CliRunner().invoke(
            main, ["ctx", "PROJ-1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        intent = json.loads(result.output)["intent"]
        assert intent["status"] == INTENT_DECLARED
        assert intent["declared_by"][0]["epic"] == "ORD-4"
        assert intent["declared_by"][0]["document"].endswith("ORD-4/CONTEXT.md")

    def test_markdown_points_at_the_intent_document(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        result = CliRunner().invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "ORD-4" in result.output
        assert "CONTEXT.md" in result.output

    def test_the_epic_key_is_not_printed_twice(self, tmp_path: Path) -> None:
        """A planning heading usually opens with the key it belongs to, so
        prefixing it again reads as `ORD-4 — ORD-4 — one-click checkout`."""
        project = _project(tmp_path)
        result = CliRunner().invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "ORD-4 — ORD-4" not in result.output
        assert "ORD-4 — filter tracks by mood" in result.output

    def test_a_title_without_the_key_keeps_the_key(self, tmp_path: Path) -> None:
        project = _project(tmp_path, declare=None)
        _write(
            project,
            f"{_EPICS}/ORD-4/CONTEXT.md",
            _context("Filter tracks by mood", "`PROJ-1`"),
        )
        result = CliRunner().invoke(main, ["ctx", "PROJ-1", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "ORD-4 — Filter tracks by mood" in result.output

    def test_a_node_nobody_declared_says_how_much_was_read(self, tmp_path: Path) -> None:
        project = _project(tmp_path, declare="routing")
        result = CliRunner().invoke(
            main, ["ctx", "PROJ-1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        intent = json.loads(result.output)["intent"]
        assert intent["status"] == INTENT_NONE_DECLARED
        assert intent["epics_read"] == 1
        assert intent["epics_declaring_nodes"] == 1

    def test_no_intent_reports_not_checked_rather_than_none(self, tmp_path: Path) -> None:
        """Opting out must not read as evidence that no epic declared the node."""
        project = _project(tmp_path)
        result = CliRunner().invoke(
            main, ["ctx", "PROJ-1", "--json", "--no-intent", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        intent = json.loads(result.output)["intent"]
        assert intent["status"] == INTENT_NOT_CHECKED
        assert intent["reason"] == REASON_NOT_READ

    def test_a_project_with_no_planning_tree_is_not_checked(self, tmp_path: Path) -> None:
        project = _project(tmp_path, declare=None)
        result = CliRunner().invoke(
            main, ["ctx", "PROJ-1", "--json", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        intent = json.loads(result.output)["intent"]
        assert intent["status"] == INTENT_NOT_CHECKED
        assert intent["reason"] == REASON_NO_INTENT_DOCUMENTS


class TestIntentAndTheBundleCache:
    """A cached bundle must not outlive the intent it carries."""

    def test_opting_out_does_not_share_a_cache_entry(self) -> None:
        from beadloom.context_oracle.cache import bundle_cache_key

        assert bundle_cache_key(["A"], 2, 20, 10, with_intent=True) != bundle_cache_key(
            ["A"], 2, 20, 10, with_intent=False
        )

    def test_an_edited_intent_document_advances_the_docs_mtime(self, tmp_path: Path) -> None:
        """The TO-BE tree is an input to the bundle, so it is an input to freshness."""
        from beadloom.context_oracle.cache import compute_bundle_mtimes

        _write(tmp_path, "docs/x.md", "# x\n")
        before = compute_bundle_mtimes(tmp_path)[1]
        _write(tmp_path, f"{_EPICS}/ORD-4/CONTEXT.md", _context("Checkout", "`checkout`"))
        assert compute_bundle_mtimes(tmp_path)[1] > before


class TestReadNodeIntentFromTheIndex:
    """The one call a surface makes: known refs from the index, intent from disk."""

    def test_it_resolves_known_refs_from_the_graph(self, tmp_path: Path) -> None:
        from beadloom.infrastructure.db import open_db

        project = _project(tmp_path)
        conn = open_db(project / ".beadloom" / "beadloom.db")
        try:
            reading = read_node_intent(conn, project)
        finally:
            conn.close()
        assert [d.ref_id for d in reading.declarations] == ["PROJ-1"]
