"""Step implementations for the S5 acceptance suite (BDL-061 S5).

Thin by design: each step arranges real files on disk and runs the real check.
Nothing is doubled, because a scenario that passes against a double proves the
double (FAKES PROVE FAKES). The tracker is the one exception — bead statuses
arrive as data, because ``check_spaces`` takes them as an argument precisely so
the relation can be exercised without a ``bd`` binary on the machine.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.doc_spaces import (
    FINDING_EPIC_NOT_IN_TRACKER,
    FINDING_NO_AS_IS,
    FINDING_WORKING_CONTRADICTED,
    FINDING_WORKING_INERT,
    TRACKER_EXPORT,
    UNRESOLVED_NO_INTENT_DOCUMENT,
    check_spaces,
)
from beadloom.application.reindex import reindex
from beadloom.context_oracle.search import search_fts5
from beadloom.doc_sync.engine import check_sync
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doc_roots import (
    SPACE_TO_BE,
    resolve_doc_spaces,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/doc_spaces.feature")

_EPIC_ROOT = ".claude/development/docs/features"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    (tmp_path / ".beadloom" / "_graph").mkdir(parents=True)
    return {"root": tmp_path, "beads": {}, "known": set(), "documented": set(), "declared": set()}


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _context(refs: str) -> str:
    return (
        "# CONTEXT: an epic\n\n## Goal\n\nShip the thing.\n\n"
        f"## Related Files\n\n{refs}\n"
    )


def _run(world: dict[str, Any]) -> None:
    world["report"] = check_spaces(
        world["root"],
        spaces=resolve_doc_spaces(world["root"]),
        known_refs=frozenset(world["known"]),
        documented_refs=frozenset(world["documented"]),
        declared_doc_paths=frozenset(world["declared"]),
        beads_by_epic=world["beads"],
    )


# ---------------------------------------------------------------------------
# The TO-BE space is indexed and searchable
# ---------------------------------------------------------------------------


@given("a project whose planning documents live under the TO-BE root")
def _to_be_project(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    (root / "docs").mkdir(exist_ok=True)
    (root / "src").mkdir(exist_ok=True)
    _write(
        root,
        f"{_EPIC_ROOT}/PROJ-1/PRD.md",
        "# PRD: PROJ-1\n\n## Goal\n\nThe distinguishing phrase is quokkasaurus.\n",
    )


@when("the project is reindexed")
def _do_reindex(world: dict[str, Any]) -> None:
    reindex(world["root"])


@then(parsers.parse('the planning document is in the index in the "{space}" space'))
def _indexed_in_space(world: dict[str, Any], space: str) -> None:
    conn = open_db(world["root"] / ".beadloom" / "beadloom.db")
    row = conn.execute(
        "SELECT space FROM docs WHERE path = ?",
        (f"{_EPIC_ROOT}/PROJ-1/PRD.md",),
    ).fetchone()
    assert row is not None, "the planning document reached no row in the docs table"
    assert row["space"] == space


@then("a search for a phrase only that document contains finds it")
def _searchable(world: dict[str, Any]) -> None:
    conn = open_db(world["root"] / ".beadloom" / "beadloom.db")
    hits = search_fts5(conn, "quokkasaurus")
    assert hits, "the phrase was indexed nowhere the search can reach"
    assert any(f"{_EPIC_ROOT}/PROJ-1/PRD.md" in h["ref_id"] for h in hits)


# ---------------------------------------------------------------------------
# The TO-BE -> AS-IS relation
# ---------------------------------------------------------------------------


@given(parsers.parse('an epic whose CONTEXT names the node "{ref}" and whose beads are closed'))
def _epic_naming(world: dict[str, Any], ref: str) -> None:
    _write(world["root"], f"{_EPIC_ROOT}/PROJ-2/CONTEXT.md", _context(f"`{ref}`"))
    world["known"].add(ref)
    world["beads"]["PROJ-2"] = ("closed", "closed")


@given(parsers.parse('the node "{ref}" has no AS-IS document'))
def _undocumented(world: dict[str, Any], ref: str) -> None:
    world["documented"].discard(ref)


@given("an epic whose CONTEXT names no node and whose beads are closed")
def _epic_naming_nothing(world: dict[str, Any]) -> None:
    _write(
        world["root"],
        f"{_EPIC_ROOT}/PROJ-3/CONTEXT.md",
        _context("Discover via `beadloom ctx <ref-id>` — never hardcode."),
    )
    world["beads"]["PROJ-3"] = ("closed",)


@given(
    parsers.parse(
        'an epic whose CONTEXT names the node "{ref}" and whose beads the tracker '
        "never mentions"
    )
)
def _epic_the_tracker_forgot(world: dict[str, Any], ref: str) -> None:
    """An epic present on disk and absent from the tracker.

    `bd close` writes only the local database, so this is what a repository
    looks like when somebody forgot to commit the export — ordinary use, not
    sabotage.
    """
    _write(world["root"], f"{_EPIC_ROOT}/PROJ-7/CONTEXT.md", _context(f"`{ref}`"))
    world["known"].add(ref)
    world["documented"].add(ref)
    world["beads"]["PROJ-OTHER"] = ("closed",)


@then("the epic is counted as one whose beads could not be resolved")
def _counted_unverifiable(world: dict[str, Any]) -> None:
    report = world["report"]
    assert "PROJ-7" in report.epics_unknown_to_tracker
    assert report.epics_without_bead_status >= 1


@then("the finding names the tracker that has no record of it")
def _finding_names_tracker(world: dict[str, Any]) -> None:
    findings = [
        f for f in world["report"].findings if f.rule == FINDING_EPIC_NOT_IN_TRACKER
    ]
    assert findings, [f.rule for f in world["report"].findings]
    assert TRACKER_EXPORT in findings[0].why


@given("a planning directory whose only document is a summary")
def _directory_without_intent(world: dict[str, Any]) -> None:
    """A directory that holds intent and declares no epic.

    Three of this repository's feature directories look like this, and so does
    `.claude/development`, which holds the ROADMAP and the issue log. All four
    were in no field of the report while their documents were in the TO-BE
    population.
    """
    _write(world["root"], f"{_EPIC_ROOT}/PROJ-8/SUMMARY.md", "# SUMMARY\n\nwhat happened.\n")


@then("the directory is counted as an epic that carries no intent document")
def _counted_without_intent(world: dict[str, Any]) -> None:
    report = world["report"]
    assert "PROJ-8" in report.unresolved_epics
    assert report.unresolved_reasons["PROJ-8"] == UNRESOLVED_NO_INTENT_DOCUMENT


@then("it is not reported as a finding")
def _not_a_finding(world: dict[str, Any]) -> None:
    assert not [f for f in world["report"].findings if "PROJ-8" in f.path]


@when("the documentation spaces are checked")
def _check(world: dict[str, Any]) -> None:
    _run(world)


@then("the epic is reported as intent that never reached AS-IS")
def _reported(world: dict[str, Any]) -> None:
    rules = [f.rule for f in world["report"].findings]
    assert FINDING_NO_AS_IS in rules, rules


@then(parsers.parse('the report names the node "{ref}"'))
def _names_ref(world: dict[str, Any], ref: str) -> None:
    assert any(
        f.rule == FINDING_NO_AS_IS and f"`{ref}`" in f.why
        for f in world["report"].findings
    )


@then("the epic is counted as stating no AS-IS relation")
def _counted_unresolved(world: dict[str, Any]) -> None:
    assert "PROJ-3" in world["report"].unresolved_epics
    assert world["report"].epics_declaring_nothing >= 1


@then("the epic is not reported as a finding")
def _not_reported(world: dict[str, Any]) -> None:
    assert not [f for f in world["report"].findings if f.rule == FINDING_NO_AS_IS]


# ---------------------------------------------------------------------------
# WORKING
# ---------------------------------------------------------------------------


def _node_with_active_doc(world: dict[str, Any]) -> tuple[str, str]:
    """A graph node whose only declared document is an ACTIVE.md.

    Returns the document in both spellings a reader may hold it in: the
    project-relative one the graph declares, and the docs-dir-relative one a
    ``sync_state`` row carries. They are one file and `beadloom-mr2l.75` is why
    the difference is spelled out here rather than assumed away.
    """
    indexed = "features/PROJ-4/ACTIVE.md"
    declared = f"docs/{indexed}"
    _write(world["root"], declared, "# ACTIVE: PROJ-4\n\n## Current\n\nstep two of five\n")
    world["known"].add("billing")
    world["documented"].add("billing")
    world["declared"].add(declared)
    return declared, indexed


@given("a graph node whose documentation is an ACTIVE document and whose code changed")
def _pair_with_active(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    _declared, indexed = _node_with_active_doc(world)
    code = "src/billing.py"
    _write(root, code, "def charge() -> None:\n    return None\n")
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("billing", "feature", "billing", code),
    )
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (indexed, code, "billing", "stale-hash", "stale-hash", "2026-01-01", "ok"),
    )
    conn.commit()
    world["conn"] = conn


@given("a graph node whose documentation is an ACTIVE document")
def _node_active_only(world: dict[str, Any]) -> None:
    _node_with_active_doc(world)


@when("freshness is checked")
def _freshness(world: dict[str, Any]) -> None:
    world["rows"] = check_sync(world["conn"], world["root"])


@then("the ACTIVE document is exempt rather than stale")
def _exempt(world: dict[str, Any]) -> None:
    rows = [r for r in world["rows"] if r["doc_path"].endswith("ACTIVE.md")]
    assert rows, "no row was produced for the ACTIVE document at all"
    assert all(r["status"] == "exempt" for r in rows), rows


@then("the exemption states the reason it was declared with")
def _exempt_reason(world: dict[str, Any]) -> None:
    rows = [r for r in world["rows"] if r["doc_path"].endswith("ACTIVE.md")]
    assert all(str(r.get("details", "")).strip() for r in rows), rows


@given("a project that declares a WORKING kind no document uses")
def _inert_working(world: dict[str, Any]) -> None:
    _write(
        world["root"],
        ".beadloom/config.yml",
        yaml.safe_dump(
            {
                "doc_roots": {
                    "working": {
                        "kinds": ["JOURNAL"],
                        "exempt_from_freshness": True,
                        "reason": "a journal records the day, not the code",
                    }
                }
            }
        ),
    )


@then("the WORKING exemption is reported as matching no document")
def _inert_reported(world: dict[str, Any]) -> None:
    assert FINDING_WORKING_INERT in [f.rule for f in world["report"].findings]


@given("a project that declares its whole documentation tree exempt from freshness")
def _docs_tree_declared_working(world: dict[str, Any]) -> None:
    """The gate defeat `beadloom-mr2l.75` closed, arranged on disk.

    The pair is spelled the way ``index_docs`` spells one — relative to the docs
    directory — because that spelling is what reached freshness while the report
    was reading another.
    """
    root: Path = world["root"]
    _write(
        root,
        ".beadloom/config.yml",
        yaml.safe_dump(
            {
                "doc_roots": {
                    "working": {
                        "roots": ["docs/**/*.md"],
                        "exempt_from_freshness": True,
                        "reason": "generated release notes, regenerated per tag",
                    }
                }
            }
        ),
    )
    _write(root, "docs/guides/ci.md", "# ci\n")
    _write(root, "src/billing.py", "def charge() -> None:\n    return None\n")
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        ("billing", "feature", "billing", "src/billing.py"),
    )
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "guides/ci.md",
            "src/billing.py",
            "billing",
            "stale-hash",
            "stale-hash",
            "2026-01-01",
            "ok",
        ),
    )
    conn.commit()
    world["conn"] = conn
    world["known"].add("billing")
    world["documented"].add("billing")
    world["declared"].add("docs/guides/ci.md")


@then("the paired document is exempt rather than stale")
def _pair_exempt(world: dict[str, Any]) -> None:
    rows = [r for r in world["rows"] if r["doc_path"] == "guides/ci.md"]
    assert rows, "no row was produced for the paired document at all"
    assert all(r["status"] == "exempt" for r in rows), rows


@then("the contradicted WORKING declaration is reported")
def _contradiction_reported(world: dict[str, Any]) -> None:
    assert FINDING_WORKING_CONTRADICTED in [f.rule for f in world["report"].findings]


# ---------------------------------------------------------------------------
# TRUE HERE IS NOT TRUE — a project that is not Beadloom
# ---------------------------------------------------------------------------


@given("a project whose doc roots are configured away from the shipped defaults")
def _elsewhere(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    _write(
        root,
        ".beadloom/config.yml",
        yaml.safe_dump(
            {
                "doc_roots": {
                    "to_be": {"roots": ["planning/*/*.md"]},
                    "as_is": {"roots": ["handbook/**/*.md"]},
                }
            }
        ),
    )
    _write(root, "planning/RIDE-9/CONTEXT.md", _context("`dispatch`"))
    _write(root, "handbook/dispatch.md", "# dispatch\n")
    # The shipped default location holds a decoy: a check that reads it anyway
    # passes here for the wrong reason.
    _write(root, f"{_EPIC_ROOT}/PROJ-9/CONTEXT.md", _context("`dispatch`"))
    world["known"].add("dispatch")
    world["beads"]["RIDE-9"] = ("closed",)
    world["beads"]["PROJ-9"] = ("closed",)


@then("the documents under the configured roots are the ones classified")
def _configured_used(world: dict[str, Any]) -> None:
    report = world["report"]
    spaces = resolve_doc_spaces(world["root"])
    found = [p.as_posix() for p in spaces.documents_in(world["root"], SPACE_TO_BE)]
    assert any("planning/RIDE-9" in p for p in found), found
    assert not any(_EPIC_ROOT in p for p in found), found
    assert [f.path for f in report.findings if f.rule == FINDING_NO_AS_IS] == [
        "planning/RIDE-9/CONTEXT.md"
    ]
