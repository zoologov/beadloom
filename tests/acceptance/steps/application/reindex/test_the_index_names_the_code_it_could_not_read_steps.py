"""Steps of `application/reindex/the_index_names_the_code_it_could_not_read.feature`.

BDL-082 S2a (`beadloom-6e2o`). The real `beadloom init --yes` and `beadloom reindex` run
through the CLI. The one thing patched is the grammar loader, made to report no grammar
for the JavaScript family, which is what a project without the `languages` extra has.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.context_oracle import code_indexer
from beadloom.services.cli import main
from tests.support.fsd_spec_examples import GROUP, write_example

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

scenarios("../../../application/reindex/the_index_names_the_code_it_could_not_read.feature")

#: The extensions the `languages` extra's TypeScript grammar reads, `.vue` through its script.
_TYPESCRIPT_GRAMMAR = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@pytest.fixture
def without_typescript(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    real: Callable[[str], object] = code_indexer.get_lang_config

    def loader(extension: str) -> object:
        return None if extension in _TYPESCRIPT_GRAMMAR else real(extension)

    code_indexer.clear_cache()
    monkeypatch.setattr(code_indexer, "get_lang_config", loader)
    yield
    code_indexer.clear_cache()


@given(
    parsers.parse('the specification\'s slice group "{group}" holding "{first}" and "{second}"')
)
def _group(tmp_path: Path, state: dict[str, Any], group: str, first: str, second: str) -> None:
    assert {f"src/{group}/{first}/index.ts", f"src/{group}/{second}/index.ts"} <= set(GROUP)
    state["root"] = write_example(tmp_path / "probe", GROUP)


@given("no grammar is installed for TypeScript")
def _no_grammar(without_typescript: None) -> None:
    del without_typescript


@when(parsers.parse("beadloom init is run with {flag}"))
def _init(state: dict[str, Any], flag: str) -> None:
    result = CliRunner().invoke(main, ["init", flag, "--project", str(state["root"])])
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    state["init_exit"] = result.exit_code
    state["output"] = result.output


@when("beadloom reindex is run")
def _reindex(state: dict[str, Any]) -> None:
    _run_reindex(state)


@when("beadloom reindex --full is run")
def _full_reindex(state: dict[str, Any]) -> None:
    _run_reindex(state, "--full")


def _run_reindex(state: dict[str, Any], *flags: str) -> None:
    result = CliRunner().invoke(main, ["reindex", *flags, "--project", str(state["root"])])
    state["reindex_exit"] = result.exit_code
    state["output"] = result.output


@then(parsers.parse('the output says "{text}"'))
def _says(state: dict[str, Any], text: str) -> None:
    assert text in state["output"], state["output"]


@then("exactly one line of the output speaks of a parser")
def _one_parser_line(state: dict[str, Any]) -> None:
    lines = [line for line in state["output"].splitlines() if "parser" in line.lower()]
    assert len(lines) == 1, lines


@then(parsers.parse("init exits {code:d}"))
def _init_exit(state: dict[str, Any], code: int) -> None:
    assert state["init_exit"] == code, state["output"]


@then(parsers.parse("the reindex exits {code:d}"))
def _reindex_exit(state: dict[str, Any], code: int) -> None:
    assert state["reindex_exit"] == code, state["output"]
