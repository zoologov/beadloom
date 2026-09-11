"""A skeleton's Public API table is read from the code, not from the index (BDL-069 S1).

`beadloom-8lmj`. The table was read out of `.beadloom/beadloom.db`, and three of
the four ways a skeleton gets written have no index at that moment: `init --yes`
and `init --bootstrap` write their skeletons before their reindex, and a clone has
none because `init` lists the index in `.gitignore`. Only the wizard, which
re-indexes before its skeleton prompt, wrote the table. The acceptance scenarios
in `tests/acceptance/features/init_skeleton_carries_public_api.feature` run the
entry points end to end; these cases pin the reader's contract.

**The population is the index's, restated over the disk.** The index holds every
symbol `extract_symbols` returns for a file, and the skeleton took the files whose
path starts with the node's source. One case below builds the index with the real
reindex and compares the two readers, so the restatement is held to the original
rather than to a description of it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.onboarding.doc_generator import generate_skeletons

if TYPE_CHECKING:
    from pathlib import Path

PUBLIC_API_HEADING = "## Public API"

_DOC_PATH_FOR_KIND = {
    "domain": "docs/domains/ledger/README.md",
    "service": "docs/services/ledger.md",
    "feature": "docs/domains/accounts/features/ledger/SPEC.md",
}

#: The ledger package: two public names at the top level, one in a subpackage,
#: one private name, and two files the parser has no grammar for.
LEDGER_FILES: dict[str, str] = {
    "__init__.py": '"""The ledger."""\n',
    "core.py": (
        "class Journal:\n    pass\n\n\n"
        "def record(amount: int) -> int:\n    return amount\n\n\n"
        "def _balance() -> int:\n    return 0\n"
    ),
    "postings/rules.py": "def post(entry: str) -> str:\n    return entry\n",
    "schema.json": '{"record": 1}\n',
    "logo.png": "not an image, and not a module either\n",
}
LEDGER_PUBLIC = ["Journal", "post", "record"]


def _graph(root: Path, *nodes: dict[str, Any]) -> None:
    """A root, a parent domain for features, and *nodes* — the graph `init` would write."""
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    all_nodes = [
        {"ref_id": "myapp", "kind": "service", "source": "", "summary": "Root"},
        {"ref_id": "accounts", "kind": "domain", "source": "", "summary": "Accounts"},
        *nodes,
    ]
    edges = [{"src": "accounts", "dst": "myapp", "kind": "part_of"}] + [
        {"src": node["ref_id"], "dst": "accounts", "kind": "part_of"} for node in nodes
    ]
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump({"nodes": all_nodes, "edges": edges}, sort_keys=False), encoding="utf-8"
    )


def _files(root: Path, package: str, files: dict[str, str]) -> str:
    for name, text in files.items():
        path = root / "src" / package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return f"src/{package}/"


def _node(kind: str, source: str, ref_id: str = "ledger") -> dict[str, Any]:
    return {"ref_id": ref_id, "kind": kind, "source": source, "summary": "The ledger"}


def _table(text: str) -> list[str] | None:
    """The names in the document's Public API table, in order; None without one."""
    lines = text.splitlines()
    if PUBLIC_API_HEADING not in lines:
        return None
    names: list[str] = []
    for line in lines[lines.index(PUBLIC_API_HEADING) + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("| `"):
            names.append(line.split("`")[1])
    return names


def _skeleton(root: Path, doc_path: str) -> str:
    generate_skeletons(root)
    return (root / doc_path).read_text(encoding="utf-8")


@pytest.mark.parametrize("kind", sorted(_DOC_PATH_FOR_KIND))
def test_a_virgin_project_skeleton_carries_the_table(tmp_path: Path, kind: str) -> None:
    """The run `beadloom-8lmj` was measured on: no index exists when the skeleton is written."""
    _graph(tmp_path, _node(kind, _files(tmp_path, "ledger", LEDGER_FILES)))

    text = _skeleton(tmp_path, _DOC_PATH_FOR_KIND[kind])

    assert _table(text) == LEDGER_PUBLIC, text
    assert "_balance" not in text, text
    assert not (tmp_path / ".beadloom" / "beadloom.db").exists()


def test_the_table_describes_the_code_rather_than_an_index_that_predates_it(
    tmp_path: Path,
) -> None:
    """A stale index is the other half of the same dependency, and it is not consulted.

    The index below names a symbol the code no longer has. Read from there, the
    table would describe a package that is not on disk.
    """
    source = _files(tmp_path, "ledger", {"core.py": "def record() -> None:\n    pass\n"})
    _graph(tmp_path, _node("domain", source))
    with sqlite3.connect(tmp_path / ".beadloom" / "beadloom.db") as conn:
        conn.execute(
            "CREATE TABLE code_symbols (file_path TEXT, symbol_name TEXT, kind TEXT, "
            "line_start INTEGER, line_end INTEGER)"
        )
        conn.execute(
            "INSERT INTO code_symbols VALUES ('src/ledger/core.py', 'removed_long_ago', "
            "'function', 1, 2)"
        )

    text = _skeleton(tmp_path, _DOC_PATH_FOR_KIND["domain"])

    assert _table(text) == ["record"], text


def test_the_disk_reader_agrees_with_the_index_the_reindex_builds(tmp_path: Path) -> None:
    """The two readers over one tree, the index built by the real reindex.

    Stated over a subpackage and files with no grammar as well as plain modules,
    so a disk reader that stopped at the top level, or read a file the indexer
    skips, is met here rather than in an adopter's document.
    """
    from beadloom.application.reindex import reindex
    from beadloom.onboarding.doc_generator import (
        _load_symbols_by_source,
        _symbols_for_node,
        _symbols_on_disk,
    )

    node = _node("domain", _files(tmp_path, "ledger", LEDGER_FILES))
    _graph(tmp_path, node)
    reindex(tmp_path)

    from_index = _symbols_for_node(node, _load_symbols_by_source(tmp_path))
    from_disk = _symbols_on_disk(node, tmp_path, {})

    def rows(symbols: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return sorted((s["symbol_name"], s["kind"]) for s in symbols)

    # Anti-vacuity: an empty index agrees with an empty disk read.
    assert rows(from_index), "the reindex indexed no symbol, so nothing was compared"
    assert rows(from_disk) == rows(from_index)


def test_a_node_whose_source_is_one_file_takes_that_files_symbols(tmp_path: Path) -> None:
    _files(tmp_path, "ledger", LEDGER_FILES)
    _graph(tmp_path, _node("domain", "src/ledger/core.py"))

    text = _skeleton(tmp_path, _DOC_PATH_FOR_KIND["domain"])

    assert _table(text) == ["Journal", "record"], text


def test_a_sibling_directory_that_shares_the_prefix_is_not_part_of_the_node(
    tmp_path: Path,
) -> None:
    """`src/ledger/` is a directory, and `src/ledger_archive/` is not inside it.

    The index reader matches by string prefix and takes both. The disk reader
    walks the directory, so the table names what the node's source holds.
    """
    source = _files(tmp_path, "ledger", {"core.py": "def record() -> None:\n    pass\n"})
    _files(tmp_path, "ledger_archive", {"old.py": "def replay() -> None:\n    pass\n"})
    _graph(tmp_path, _node("domain", source))

    text = _skeleton(tmp_path, _DOC_PATH_FOR_KIND["domain"])

    assert _table(text) == ["record"], text


def test_a_file_that_cannot_be_decoded_leaves_the_rest_of_the_table(tmp_path: Path) -> None:
    """The table is best effort, as it was when it came from the index."""
    source = _files(tmp_path, "ledger", {"core.py": "def record() -> None:\n    pass\n"})
    (tmp_path / "src" / "ledger" / "legacy.py").write_bytes(b"def caf\xe9() -> None: pass\n")
    _graph(tmp_path, _node("domain", source))

    text = _skeleton(tmp_path, _DOC_PATH_FOR_KIND["domain"])

    assert _table(text) == ["record"], text


def test_a_document_that_already_exists_costs_no_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing is parsed for a document that will not be written.

    Measured on this repository: parsing every node source enumerated 17 294 files
    in about 13 seconds, 16 433 of them under one site node's `node_modules`, for
    a command that wrote nothing because every document already existed.
    """
    from beadloom.context_oracle import code_indexer

    source = _files(tmp_path, "ledger", LEDGER_FILES)
    _graph(tmp_path, _node("domain", source))
    existing = tmp_path / _DOC_PATH_FOR_KIND["domain"]
    existing.parent.mkdir(parents=True)
    existing.write_text("# ledger\n\nWritten by hand.\n", encoding="utf-8")

    def refuse(path: Path) -> list[dict[str, Any]]:
        raise AssertionError(f"parsed {path} for a document that already exists")

    monkeypatch.setattr(code_indexer, "extract_symbols", refuse)

    result = generate_skeletons(tmp_path)

    assert result["files_skipped"] >= 1
    assert existing.read_text(encoding="utf-8") == "# ledger\n\nWritten by hand.\n"


def test_each_file_is_parsed_once_when_nodes_nest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A domain and a feature inside it share files; the run parses each file once."""
    from beadloom.context_oracle import code_indexer

    source = _files(tmp_path, "ledger", LEDGER_FILES)
    _graph(
        tmp_path,
        _node("domain", source),
        _node("feature", "src/ledger/postings/", ref_id="postings"),
    )
    parsed: list[str] = []
    real = code_indexer.extract_symbols

    def counting(path: Path) -> list[dict[str, Any]]:
        parsed.append(path.name)
        return real(path)

    monkeypatch.setattr(code_indexer, "extract_symbols", counting)

    generate_skeletons(tmp_path)

    feature_doc = tmp_path / "docs" / "domains" / "accounts" / "features" / "postings" / "SPEC.md"
    assert _table(feature_doc.read_text(encoding="utf-8")) == ["post"]
    assert parsed.count("rules.py") == 1, parsed
