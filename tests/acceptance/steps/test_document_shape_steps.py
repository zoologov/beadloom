"""Step implementations for the document-shape half of S4 (BDL-061 S4b).

Thin by design: each step arranges real files on disk and runs the real check.
Nothing is doubled, because a scenario that passes against a double proves the
double (FAKES PROVE FAKES).

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.mutation_scope import (
    MUTATION_OUTSIDE_SOURCE,
    MUTATION_TARGET_MISSING,
    MUTATION_ZERO_MUTANTS,
    check_mutation_scope,
)
from beadloom.doc_sync.doc_quality import check_document
from beadloom.doc_sync.doc_shape import (
    REASON_MISSING_SECTIONS,
    REASON_SECTION_NOT_IN_USE,
    check_section_shape,
)
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.onboarding.composer import PROJECT_FLOW_DIRNAME
from beadloom.onboarding.doc_generator import _render_domain_readme
from beadloom.onboarding.doc_templates import (
    DEFAULT_DOC_CONFIG,
    required_sections_by_node_kind,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/document_shape.feature")
scenarios("../features/document_quality.feature")
scenarios("../features/mutation_scope.feature")
scenarios("../features/doc_templates.feature")

_REQUIREMENTS = {"domain": ("Features",)}

_DOC = "# {ref}\n\n> summary\n\n{body}"
_FEATURES = "## Features\n\n- one\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path}


def _domain_docs(root: Path, bodies: list[str]) -> None:
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    conn = open_db(root / ".beadloom" / "beadloom.db")
    create_schema(conn)
    for index, body in enumerate(bodies):
        ref = f"d{index}"
        relative = f"domains/{ref}/README.md"
        path = root / "docs" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_DOC.format(ref=ref, body=body), encoding="utf-8")
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref, "domain", "", f"src/{ref}/"),
        )
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, 'domain', ?, 'h')",
            (relative, ref),
        )
    conn.commit()
    conn.close()


# --- document shape --------------------------------------------------------


@given(
    parsers.parse(
        'three domain documents of which two carry a "{section}" section'
    )
)
def _two_of_three(world: dict[str, Any], section: str) -> None:
    body = f"## {section}\n\n- one\n"
    _domain_docs(world["root"], [body, body, "## Notes\n\nnone\n"])


@given(
    parsers.parse(
        'three domain documents of which one carries a "{section}" section'
    )
)
def _one_of_three(world: dict[str, Any], section: str) -> None:
    body = f"## {section}\n\n- one\n"
    _domain_docs(world["root"], [body, "## Notes\n\nnone\n", "## Notes\n\nnone\n"])


@given(parsers.parse('three domain documents of which one states "{heading}"'))
def _one_states(world: dict[str, Any], heading: str) -> None:
    _domain_docs(
        world["root"], [_FEATURES, _FEATURES, f"## {heading}\n\n- one\n"]
    )


@when("the document shape is checked")
def _check_shape(world: dict[str, Any]) -> None:
    conn = open_db(world["root"] / ".beadloom" / "beadloom.db")
    world["rows"] = check_section_shape(conn, world["root"], _REQUIREMENTS)
    conn.close()


@then(parsers.parse('the third document is reported as missing "{section}"'))
def _third_reported(world: dict[str, Any], section: str) -> None:
    missing = [r for r in world["rows"] if r["reason"] == REASON_MISSING_SECTIONS]
    assert [r["ref_id"] for r in missing] == ["d2"]
    assert missing[0]["details"] == section


@then("no document is reported")
def _no_document(world: dict[str, Any]) -> None:
    assert [r for r in world["rows"] if r["reason"] == REASON_MISSING_SECTIONS] == []


@then(parsers.parse('the kind is reported once with the ratio "{ratio}"'))
def _kind_reported(world: dict[str, Any], ratio: str) -> None:
    unused = [r for r in world["rows"] if r["reason"] == REASON_SECTION_NOT_IN_USE]
    assert len(unused) == 1
    assert ratio in unused[0]["details"]


# --- document quality ------------------------------------------------------


@given(parsers.parse('a document whose only goal is "{goal}"'))
def _goal_document(world: dict[str, Any], goal: str) -> None:
    world["text"] = f"## Goals\n\n- {goal}\n"


@given(parsers.parse('a document with a risk mitigated by "{mitigation}"'))
def _risk_document(world: dict[str, Any], mitigation: str) -> None:
    world["text"] = (
        "## Risks\n\n"
        "| Risk | Mitigation |\n|------|------------|\n"
        f"| the index goes stale | {mitigation} |\n"
    )


@given(
    parsers.parse(
        '{status} document with an open question answered "{decision}"'
    )
)
def _question_document(world: dict[str, Any], status: str, decision: str) -> None:
    word = status.split()[-1]
    world["text"] = (
        f"> **Status:** {word}\n\n## Open Questions\n\n"
        "| # | Question | Decision |\n|---|----------|----------|\n"
        f"| Q1 | where does it live? | {decision} |\n"
    )


@when("the writing standard is checked")
def _check_quality(world: dict[str, Any]) -> None:
    world["report"] = check_document(world["text"], path="D.md")


@then(parsers.parse('"{check}" is reported'))
def _check_reported(world: dict[str, Any], check: str) -> None:
    assert [f.check for f in world["report"].findings] == [check]


@then("nothing is reported")
def _nothing_reported(world: dict[str, Any]) -> None:
    if "report" in world:
        assert world["report"].findings == ()
    else:
        assert world["findings"] == []


# --- mutation scope --------------------------------------------------------


def _flow(root: Path, target: str, *, scan: str = "src") -> None:
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "flow.yml").write_text(
        "tools:\n- claude\narchitecture:\n- ddd\nstack:\n- python\n"
        f"mutation:\n  targets:\n  - {target}\n",
        encoding="utf-8",
    )
    (root / ".beadloom" / "config.yml").write_text(
        f"languages:\n- .py\nscan_paths:\n- {scan}\n", encoding="utf-8"
    )


@given(parsers.parse('a project declaring the mutation target "{target}"'))
def _project_target(world: dict[str, Any], target: str) -> None:
    _flow(world["root"], target)


@given(
    parsers.parse(
        'a project whose source path is "{scan}" declaring the mutation '
        'target "{target}"'
    )
)
def _project_outside(world: dict[str, Any], scan: str, target: str) -> None:
    _flow(world["root"], target, scan=scan)
    path = world["root"] / target / "test_x.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("def test_x() -> None:\n    assert True\n", encoding="utf-8")


@given(
    parsers.parse(
        'a project declaring the mutation target "{target}" holding a Python module'
    )
)
def _project_valid(world: dict[str, Any], target: str) -> None:
    _flow(world["root"], target)
    path = world["root"] / target / "rules.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("def f() -> int:\n    return 1\n", encoding="utf-8")


@when("the mutation scope is checked")
def _check_scope(world: dict[str, Any]) -> None:
    world["findings"] = check_mutation_scope(world["root"])


@then("the target is reported as running zero mutants")
def _zero_mutants(world: dict[str, Any]) -> None:
    assert [f.check for f in world["findings"]] in (
        [MUTATION_TARGET_MISSING],
        [MUTATION_ZERO_MUTANTS],
    )
    assert "zero mutants" in world["findings"][0].why


@then("the target is reported as outside the source paths")
def _outside(world: dict[str, Any]) -> None:
    assert [f.check for f in world["findings"]] == [MUTATION_OUTSIDE_SOURCE]


# --- doc templates ---------------------------------------------------------


@given(
    parsers.parse(
        'a project whose layer appends a "{section}" section to the domain template'
    )
)
def _project_layer(world: dict[str, Any], section: str) -> None:
    fragment = world["root"] / PROJECT_FLOW_DIRNAME / "docs" / "domain.md"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    fragment.write_text(f"## {section}\n\nWho to page.\n", encoding="utf-8")


@when(parsers.parse('a domain document is generated for the node "{ref}"'))
def _generate_domain_doc(world: dict[str, Any], ref: str) -> None:
    world["document"] = _render_domain_readme(
        {"ref_id": ref, "summary": "", "source": f"src/{ref}/"},
        [],
        project_root=world["root"],
    )


@when("the required sections of a domain document are resolved")
def _resolve_sections(world: dict[str, Any]) -> None:
    world["sections"] = required_sections_by_node_kind(
        config=DEFAULT_DOC_CONFIG, project_root=world["root"]
    )["domain"]


@then(parsers.parse('the document carries a "{section}" section'))
def _document_carries(world: dict[str, Any], section: str) -> None:
    assert f"## {section}" in world["document"]


@then(parsers.parse('"{section}" is required'))
def _section_required(world: dict[str, Any], section: str) -> None:
    assert section in world["sections"]
