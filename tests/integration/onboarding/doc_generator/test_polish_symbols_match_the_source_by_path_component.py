"""`docs polish` takes the index rows under a node's source by path component (BDL-069).

`beadloom-6rgr`. `_symbols_for_node` took every `code_symbols` row whose file path
started with the node's source as a STRING, after stripping its trailing slash. A
node whose source is `src/ledger/` therefore also took `src/ledger_archive/` and
`src/ledger_tools.py`, and `generate_polish_data` handed those symbols to an AI
agent as the node's public API. The acceptance scenarios in
`tests/acceptance/features/polish_symbols_under_source.feature` run the commands end
to end; these cases pin the matcher.

**Two shapes, because a fix for one breaks the other.** A prefix-sharing sibling is
the defect. A source that is ONE file is where the obvious repair goes wrong: a
match on `source + "/"` alone takes nothing for `src/ledger/core.py`, since no path
starts with `src/ledger/core.py/`.

**The index reader is held to the disk reader.** `beadloom-8lmj` gave the skeleton a
reader that walks the source directory, and the polish reader stays on the index
because every other field of the polish payload is read from there. What keeps the
two from being two answers is the last case: both readers over one tree, the index
built by the real reindex, for every shape of source.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.onboarding.doc_generator import (
    _load_symbols_by_source,
    _symbols_for_node,
    _symbols_on_disk,
    generate_polish_data,
)

if TYPE_CHECKING:
    from pathlib import Path

#: One symbol per file, named after where it lives, so a wrong attribution names
#: the file it came from. `.ts`/`.tsx` exist only at the matcher level, where no
#: grammar is needed: they are the prefix-sharing sibling of a single-file source.
INDEX_FILES = (
    "src/ledger/__init__.py",
    "src/ledger/core.py",
    "src/ledger/postings/rules.py",
    "src/ledger_archive/core.py",
    "src/ledgerx/core.py",
    "src/ledger.py",
    "src/app.ts",
    "src/app.tsx",
)


def _index(*paths: str) -> dict[str, list[dict[str, Any]]]:
    """A `symbols_by_source` mapping as `_load_symbols_by_source` returns it."""
    return {path: [{"symbol_name": path, "kind": "function", "file_path": path}] for path in paths}


def _files(symbols: list[dict[str, Any]]) -> list[str]:
    return sorted({str(symbol["symbol_name"]) for symbol in symbols})


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            "src/ledger/",
            ["src/ledger/__init__.py", "src/ledger/core.py", "src/ledger/postings/rules.py"],
            id="directory",
        ),
        pytest.param(
            "src/ledger",
            ["src/ledger/__init__.py", "src/ledger/core.py", "src/ledger/postings/rules.py"],
            id="directory-without-trailing-slash",
        ),
        pytest.param("src/ledger/core.py", ["src/ledger/core.py"], id="single-file"),
        pytest.param("src/ledger.py", ["src/ledger.py"], id="single-file-beside-its-package"),
        pytest.param("src/app.ts", ["src/app.ts"], id="single-file-with-a-prefix-sharing-sibling"),
        pytest.param("src/ledger/__init__.py", ["src/ledger/__init__.py"], id="package-facade"),
        pytest.param(
            " src/ledger/ ",
            ["src/ledger/__init__.py", "src/ledger/core.py", "src/ledger/postings/rules.py"],
            id="surrounding-whitespace",
        ),
    ],
)
def test_a_node_takes_the_files_under_its_source_and_no_sibling(
    source: str, expected: list[str]
) -> None:
    node = {"ref_id": "ledger", "kind": "domain", "source": source}

    assert _files(_symbols_for_node(node, _index(*INDEX_FILES))) == expected


@pytest.mark.parametrize("source", ["", None, "/"])
def test_a_node_without_a_source_takes_nothing(source: str | None) -> None:
    """`/` strips to nothing, and nothing is not a prefix of every path."""
    node = {"ref_id": "root", "kind": "service", "source": source}

    assert _symbols_for_node(node, _index(*INDEX_FILES)) == []


# ------------------------------------------------------------------
# Over a real index
# ------------------------------------------------------------------

#: The tree the reindex indexes: the package, a sibling package and a sibling
#: module whose names both start with `ledger`, and a nested subpackage.
TREE: dict[str, str] = {
    "src/ledger/__init__.py": '"""The ledger."""\n\n\ndef open_ledger() -> None:\n    pass\n',
    "src/ledger/core.py": "class Journal:\n    pass\n\n\ndef record() -> None:\n    pass\n",
    "src/ledger/postings/rules.py": "def post() -> None:\n    pass\n",
    "src/ledger_archive/__init__.py": '"""The archive."""\n',
    "src/ledger_archive/core.py": "def replay() -> None:\n    pass\n",
    "src/ledger_tools.py": "def export() -> None:\n    pass\n",
}


def _project(root: Path, *nodes: dict[str, Any]) -> None:
    for relative, text in TREE.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    all_nodes = [{"ref_id": "myapp", "kind": "service", "source": "", "summary": "Root"}, *nodes]
    edges = [{"src": node["ref_id"], "dst": "myapp", "kind": "part_of"} for node in nodes]
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump({"nodes": all_nodes, "edges": edges}, sort_keys=False), encoding="utf-8"
    )


def _domain(ref_id: str, source: str) -> dict[str, Any]:
    return {"ref_id": ref_id, "kind": "domain", "source": source, "summary": ref_id}


def _names(symbols: list[dict[str, Any]]) -> list[str]:
    return sorted(str(symbol["symbol_name"]) for symbol in symbols)


def test_polish_data_names_the_package_and_not_its_prefix_sharing_siblings(
    tmp_path: Path,
) -> None:
    """The measurement `beadloom-8lmj` recorded, through the public entry point."""
    from beadloom.application.reindex import reindex

    _project(
        tmp_path,
        _domain("ledger", "src/ledger/"),
        _domain("ledger_archive", "src/ledger_archive/"),
    )
    reindex(tmp_path)
    indexed = {
        str(row["symbol_name"])
        for rows in _load_symbols_by_source(tmp_path).values()
        for row in rows
    }
    # Anti-vacuity: the siblings' symbols are in the index to be wrongly taken.
    assert {"replay", "export"} <= indexed, indexed

    (ledger,) = generate_polish_data(tmp_path, ref_id="ledger")["nodes"]
    (archive,) = generate_polish_data(tmp_path, ref_id="ledger_archive")["nodes"]

    assert _names(ledger["symbols"]) == ["Journal", "open_ledger", "post", "record"]
    assert _names(archive["symbols"]) == ["replay"]


@pytest.mark.parametrize(
    "source",
    [
        "src/ledger/",
        "src/ledger",
        "src/ledger/core.py",
        "src/ledger/__init__.py",
        "src/ledger_tools.py",
    ],
)
def test_the_index_reader_agrees_with_the_disk_reader_for_every_shape_of_source(
    tmp_path: Path, source: str
) -> None:
    """The polish reader and the skeleton reader take one population from one tree.

    The tree holds prefix-sharing siblings, so the directory walk and a string
    prefix would disagree here, and did until `beadloom-6rgr`.
    """
    from beadloom.application.reindex import reindex

    node = _domain("ledger", source)
    _project(tmp_path, node)
    reindex(tmp_path)

    from_index = _symbols_for_node(node, _load_symbols_by_source(tmp_path))
    from_disk = _symbols_on_disk(node, tmp_path, {})

    def rows(symbols: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return sorted((str(s["symbol_name"]), str(s["kind"])) for s in symbols)

    # Anti-vacuity: an empty index agrees with an empty disk read.
    assert rows(from_disk), f"{source} holds no symbol on disk, so nothing was compared"
    assert rows(from_index) == rows(from_disk)
