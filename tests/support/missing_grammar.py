"""A tree-sitter grammar that is not installed, simulated at the loader's boundary.

``beadloom[languages]`` ships the grammars beyond Python's. A test that needs the reindex to
meet a code file whose language has no parser installed patches the one function the
indexer asks for a language's configuration, and clears the cache it keeps, so the next
read sees the absence and the test after it sees the grammar again.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from beadloom.context_oracle import code_indexer

if TYPE_CHECKING:
    from collections.abc import Iterator

    import pytest

#: The extensions the TypeScript and JavaScript grammars read.
TYPESCRIPT_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})


@contextmanager
def grammars_missing(
    monkeypatch: pytest.MonkeyPatch, extensions: frozenset[str] = TYPESCRIPT_EXTENSIONS
) -> Iterator[None]:
    """Make the indexer find no grammar for *extensions* until the block exits."""
    real = code_indexer.get_lang_config
    code_indexer.clear_cache()
    monkeypatch.setattr(
        code_indexer, "get_lang_config", lambda ext: None if ext in extensions else real(ext)
    )
    try:
        yield
    finally:
        monkeypatch.setattr(code_indexer, "get_lang_config", real)
        code_indexer.clear_cache()
