"""The skeleton `init` writes names the modules its freshness rule requires (BDL-069 S1).

`missing_modules` requires a document paired with a source directory to name each
module in that directory, and `generate_skeletons` wrote a document that named the
directory and nothing in it. The acceptance scenarios in
`tests/acceptance/features/init_skeleton_names_modules.feature` run the whole
chain on a repository built for the purpose. These cases pin the parts of the
writer's contract a gate run cannot isolate: which files are named, which are
not, that the new section is never demanded of a document that predates it, and
that writing a skeleton records no verdict about it.

**Where the list comes from.** The source directory on disk, and not the index.
`init --yes` writes the skeletons BEFORE its reindex, so on a virgin project there
is no index to read at that moment; the list read out of it would be empty on
exactly the run BDL-UX #282 was measured on.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.onboarding.doc_generator import generate_skeletons
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG, required_sections

if TYPE_CHECKING:
    from pathlib import Path

#: The code files the fixture's source directory holds, in the order a reader
#: should meet them. `__init__.py` is named too: it is a file the node's pairs
#: cover, and naming it is what keeps the list independent of which boilerplate
#: the freshness rule chooses to exempt.
CODE_FILES = ("__init__.py", "core.py", "journal.py")

#: Where a skeleton's module list starts. Delivered through a placeholder, so a
#: node with nothing to list gets no empty section.
MODULES_HEADING = "## Modules"

_DOC_PATH_FOR_KIND = {
    "domain": "docs/domains/ledger/README.md",
    "service": "docs/services/ledger.md",
    "feature": "docs/domains/accounts/features/ledger/SPEC.md",
}


def _graph(root: Path, node: dict[str, Any]) -> None:
    """A root, a parent domain for features, and *node* — the graph `init` would write."""
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    nodes = [
        {"ref_id": "myapp", "kind": "service", "source": "", "summary": "Root"},
        {"ref_id": "accounts", "kind": "domain", "source": "", "summary": "Accounts"},
        node,
    ]
    edges = [
        {"src": "accounts", "dst": "myapp", "kind": "part_of"},
        {"src": node["ref_id"], "dst": "accounts", "kind": "part_of"},
    ]
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump({"nodes": nodes, "edges": edges}, sort_keys=False), encoding="utf-8"
    )


def _package(root: Path, files: tuple[str, ...] = CODE_FILES) -> str:
    package = root / "src" / "ledger"
    package.mkdir(parents=True, exist_ok=True)
    for name in files:
        (package / name).write_text("X = 1\n", encoding="utf-8")
    return "src/ledger/"


def _node(kind: str, source: str) -> dict[str, Any]:
    return {"ref_id": "ledger", "kind": kind, "source": source, "summary": "The ledger"}


def _skeleton(root: Path, kind: str) -> str:
    generate_skeletons(root)
    return (root / _DOC_PATH_FOR_KIND[kind]).read_text(encoding="utf-8")


@pytest.mark.parametrize("kind", sorted(_DOC_PATH_FOR_KIND))
def test_every_code_file_in_the_source_directory_is_named(tmp_path: Path, kind: str) -> None:
    """All three node kinds: the rule reads any node with a directory source."""
    _graph(tmp_path, _node(kind, _package(tmp_path)))

    text = _skeleton(tmp_path, kind)

    assert MODULES_HEADING in text, text
    listed = [line for line in text.splitlines() if line.startswith("- `")]
    assert listed == [f"- `{name}`" for name in CODE_FILES], text


def test_the_list_is_sorted_rather_than_in_directory_order(tmp_path: Path) -> None:
    source = _package(tmp_path, ("zeta.py", "alpha.py", "mid.py"))
    _graph(tmp_path, _node("domain", source))

    text = _skeleton(tmp_path, "domain")

    listed = [line for line in text.splitlines() if line.startswith("- `")]
    assert listed == ["- `alpha.py`", "- `mid.py`", "- `zeta.py`"], text


def test_a_file_that_is_not_a_python_module_is_not_named(tmp_path: Path) -> None:
    """The list is the population `missing_modules` reads, which is Python files.

    A TypeScript file is not left out by oversight: no rule requires a document to
    name it, and the scanner's wider code vocabulary is owned by a node that
    depends on this one (see `_modules_for_node`).
    """
    source = _package(tmp_path, ("core.py",))
    for name, text in (("index.ts", "export {};\n"), ("schema.json", "{}\n")):
        (tmp_path / "src" / "ledger" / name).write_text(text, encoding="utf-8")
    _graph(tmp_path, _node("domain", source))

    text = _skeleton(tmp_path, "domain")

    assert "`core.py`" in text, text
    assert "index.ts" not in text, text
    assert "schema.json" not in text, text


def test_the_skeleton_satisfies_the_rule_it_is_judged_by(tmp_path: Path) -> None:
    """The agreement between the list and the rule, stated by running the rule.

    The two populations live in two domains that may not import each other, so
    nothing but this test holds them together. It is stated over a directory
    holding the files the rule exempts as well as the ones it requires, so a rule
    that stopped exempting one, or started reading another, is met here.
    """
    from beadloom.application.reindex import reindex
    from beadloom.doc_sync.engine import check_doc_coverage
    from beadloom.infrastructure.db import readonly_connection

    source = _package(
        tmp_path, ("__init__.py", "__main__.py", "conftest.py", "core.py", "journal.py")
    )
    _graph(tmp_path, _node("domain", source))
    generate_skeletons(tmp_path)
    reindex(tmp_path)

    with readonly_connection(tmp_path / ".beadloom" / "beadloom.db") as conn:
        judged = conn.execute(
            "SELECT COUNT(*) FROM nodes n JOIN docs d ON d.ref_id = n.ref_id WHERE n.source = ?",
            (source,),
        ).fetchone()[0]
        gaps = check_doc_coverage(conn, tmp_path)

    # Anti-vacuity: a rule that never met the document reports no gap either.
    assert judged == 1, "the index holds no document for the package"
    assert gaps == []


def test_a_code_file_in_a_subdirectory_is_left_to_the_subdirectory(tmp_path: Path) -> None:
    """The rule reads the directory itself and not below it; a subpackage is its own node."""
    source = _package(tmp_path, ("core.py",))
    nested = tmp_path / "src" / "ledger" / "postings"
    nested.mkdir()
    (nested / "rules.py").write_text("X = 1\n", encoding="utf-8")
    _graph(tmp_path, _node("domain", source))

    text = _skeleton(tmp_path, "domain")

    assert "`core.py`" in text, text
    assert "rules.py" not in text, text


def test_a_node_whose_source_is_one_file_gets_no_module_list(tmp_path: Path) -> None:
    """Its `## Source` line already names the only file it has."""
    _package(tmp_path, ("core.py",))
    _graph(tmp_path, _node("domain", "src/ledger/core.py"))

    text = _skeleton(tmp_path, "domain")

    assert MODULES_HEADING not in text, text
    assert "`src/ledger/core.py`" in text, text


@pytest.mark.parametrize(
    "arrange",
    [
        pytest.param(lambda root: None, id="the-directory-is-not-on-disk"),
        pytest.param(
            lambda root: (root / "src" / "ledger").mkdir(parents=True), id="it-holds-no-code"
        ),
    ],
)
def test_a_directory_with_nothing_to_name_gets_no_empty_section(
    tmp_path: Path, arrange: Any
) -> None:
    arrange(tmp_path)
    _graph(tmp_path, _node("domain", "src/ledger/"))

    text = _skeleton(tmp_path, "domain")

    assert MODULES_HEADING not in text, text
    assert "## Dependencies" in text, text


@pytest.mark.parametrize("kind", sorted(_DOC_PATH_FOR_KIND))
def test_the_module_list_is_never_required_of_a_document(kind: str) -> None:
    """A required section is a literal heading in the template (`doc_templates`).

    Had the list been one, every document an adopter already has would be found
    to lack it on upgrade, and their Gate would change verdict — which this epic
    rules out. It arrives through a placeholder, the way `## Public API` does.
    """
    assert "Modules" not in required_sections(kind, config=DEFAULT_DOC_CONFIG)


def test_writing_a_skeleton_records_no_pair(tmp_path: Path) -> None:
    """The green has to come from the document, so the writer attests nothing.

    Decided in CONTEXT: attesting at write time asserts a freshness nobody
    checked, the false-green shape BDL-061 removed. The index `init` builds
    afterwards takes its baseline from the tree like any other reindex.
    """
    _graph(tmp_path, _node("domain", _package(tmp_path)))
    db_path = tmp_path / ".beadloom" / "beadloom.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE sync_state (doc_path TEXT, code_path TEXT, ref_id TEXT, status TEXT)"
        )
    before = db_path.read_bytes()

    generate_skeletons(tmp_path)

    assert (tmp_path / _DOC_PATH_FOR_KIND["domain"]).is_file()
    assert db_path.read_bytes() == before


def test_writing_a_skeleton_on_a_virgin_project_creates_no_index(tmp_path: Path) -> None:
    """The run BDL-UX #282 was measured on: `init --yes` has no index at this point."""
    _graph(tmp_path, _node("domain", _package(tmp_path)))

    generate_skeletons(tmp_path)

    assert "`core.py`" in (tmp_path / _DOC_PATH_FOR_KIND["domain"]).read_text(encoding="utf-8")
    assert not (tmp_path / ".beadloom" / "beadloom.db").exists()
