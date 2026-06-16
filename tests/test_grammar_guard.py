"""CI guard: tree-sitter language grammars must actually load.

The multi-language tests (TypeScript / Go / Rust / Kotlin / Java / Swift /
Obj-C / C / C++) are individually gated with ``skipif(not <grammar>_available())``
so the suite still runs when the optional ``languages`` extra is not installed
locally. The hazard: in CI (which installs ``--extra languages``) a missing or
broken grammar would make every one of those tests *silently skip and pass* —
green CI masking zero real coverage.

This guard closes that gap. When ``BEADLOOM_REQUIRE_LANGUAGE_GRAMMARS=1`` is set
(CI sets it for the job that installs the ``languages`` extra), the guard FAILS
if any declared grammar cannot be loaded through the production loader path
(``get_lang_config``). Without the env var it skips, so a local checkout without
the optional extra is unaffected.
"""

from __future__ import annotations

import os

import pytest

from beadloom.context_oracle.code_indexer import get_lang_config

# Optional-extra language extensions whose tests are skip-gated. Python's grammar
# is a core dependency (always present) and is excluded — these are exactly the
# grammars shipped by the ``languages`` extra in pyproject.toml.
_REQUIRED_EXTENSIONS: tuple[str, ...] = (
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".kt",
    ".java",
    ".swift",
    ".m",
    ".c",
    ".cpp",
)

# CI sets this for the job that installs the ``languages`` extra (see ci.yml).
_REQUIRE_ENV = "BEADLOOM_REQUIRE_LANGUAGE_GRAMMARS"


def _grammars_required() -> bool:
    """True when the environment demands all language grammars be loadable."""
    return os.environ.get(_REQUIRE_ENV) == "1"


@pytest.mark.skipif(
    not _grammars_required(),
    reason=f"{_REQUIRE_ENV} not set — language grammars optional in this environment",
)
@pytest.mark.parametrize("extension", _REQUIRED_EXTENSIONS)
def test_language_grammar_loads(extension: str) -> None:
    """Each declared grammar loads through the production path (no silent skip).

    A ``None`` config means the grammar import failed — which would silently
    skip the language tests. Under the require-env this is a hard failure so CI
    cannot go green with missing grammars.
    """
    config = get_lang_config(extension)
    assert config is not None, (
        f"tree-sitter grammar for '{extension}' is unavailable; the "
        f"'{extension}' language tests would silently skip-and-pass. "
        f"Install the 'languages' extra (uv sync --extra languages)."
    )


def test_grammar_guard_covers_every_optional_grammar() -> None:
    """Self-check: the guard's required set matches the production loader map.

    Protects against a new optional grammar being added to the loaders without
    being guarded here (which would let its language tests silently skip in CI).
    Python is core (always present), so it is intentionally excluded.
    """
    from beadloom.context_oracle.code_indexer import _EXTENSION_LOADERS

    loader_extensions = set(_EXTENSION_LOADERS) - {".py"}
    # ``.js``/``.jsx`` reuse the TypeScript grammar already guarded via ``.ts``/
    # ``.tsx``; ``.h``/``.hpp``/``.kts``/``.mm`` reuse C/C++/Kotlin/Obj-C grammars.
    reused = {".js", ".jsx", ".h", ".hpp", ".kts", ".mm"}
    distinct_grammar_extensions = loader_extensions - reused

    assert distinct_grammar_extensions == set(_REQUIRED_EXTENSIONS), (
        "grammar guard is out of sync with the production loader map: "
        f"loaders={sorted(distinct_grammar_extensions)}, "
        f"guarded={sorted(_REQUIRED_EXTENSIONS)}"
    )
