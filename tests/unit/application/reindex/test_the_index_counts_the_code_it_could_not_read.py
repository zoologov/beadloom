"""The index counts the code files whose language has no parser installed (BDL-082 S2a).

S1T measured ``init`` on a project of TypeScript and Vue files without the ``languages``
extra: "Index: 0 symbols, 0 imports" and nothing else, and every FSD rule then had no input.
The reindex records every code file it saw in ``file_index``; the ones no grammar reads are
counted here, by language, so the commands can say so.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import UnreadCode, read_unread_code, unread_code
from beadloom.application.reindex.models import _CODE_EXTENSIONS
from beadloom.application.reindex.unread_code import LANGUAGE_OF
from beadloom.context_oracle import code_indexer

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The grammars the `languages` extra installs for the JavaScript family.
_TYPESCRIPT_GRAMMAR = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})


@pytest.fixture
def without_typescript(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    real = code_indexer.get_lang_config
    code_indexer.clear_cache()
    monkeypatch.setattr(
        code_indexer,
        "get_lang_config",
        lambda ext: None if ext in _TYPESCRIPT_GRAMMAR else real(ext),
    )
    yield
    code_indexer.clear_cache()


def _index(*paths: str, kind: str = "code") -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE file_index (path TEXT PRIMARY KEY, hash TEXT, kind TEXT)")
    conn.executemany(
        "INSERT INTO file_index (path, hash, kind) VALUES (?, 'h', ?)",
        [(path, kind) for path in paths],
    )
    return conn


@pytest.mark.usefixtures("without_typescript")
def test_files_with_no_grammar_are_counted_by_language() -> None:
    conn = _index(
        "src/a.ts",
        "src/b.tsx",
        "src/c.vue",
        "src/d.js",
        "src/e.py",
        "__parser_fingerprint__",
    )

    assert unread_code(conn) == (
        UnreadCode(language="TypeScript", files=2),
        UnreadCode(language="JavaScript", files=1),
        UnreadCode(language="Vue", files=1),
    )


def test_nothing_is_counted_when_every_grammar_is_installed() -> None:
    pytest.importorskip("tree_sitter_typescript")
    conn = _index("src/a.ts", "src/c.vue", "src/e.py")

    assert unread_code(conn) == ()


@pytest.mark.usefixtures("without_typescript")
def test_only_code_files_are_counted() -> None:
    conn = _index("docs/a.ts", kind="doc")

    assert unread_code(conn) == ()


def test_every_code_extension_the_reindex_reads_has_a_language_name() -> None:
    assert set(_CODE_EXTENSIONS) <= set(LANGUAGE_OF)


def test_a_project_with_no_index_has_nothing_to_count(tmp_path: Path) -> None:
    assert read_unread_code(tmp_path) == ()
