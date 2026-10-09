"""Steps for `init_keeps_a_frontends_package_json_as_it_was_written.feature`.

BDL-080 S3f (`beadloom-af99.14`). The real `beadloom init --bootstrap` runs through the CLI
on the synthetic FSD tree of `tests/support/fsd_tree.py`, its package.json rewritten in the
indentation a scenario names. What init must write is the original file with one script
added, serialised in that same indentation. Nothing is patched.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.fsd_tree import write_fsd_tree

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios(
    "../../../onboarding/agent-prime/init_keeps_a_frontends_package_json_as_it_was_written.feature"
)

_INDENTS = {"tabs": "\t", "4 spaces": "    "}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given(parsers.parse("a Feature-Sliced frontend whose package.json is indented with {indent}"))
def _tree(tmp_path: Path, state: dict[str, Any], indent: str) -> None:
    root = write_fsd_tree(tmp_path / "orchard-web")
    path = root / "package.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    state["indent"] = _INDENTS[indent]
    state["package"] = package
    path.write_text(json.dumps(package, indent=state["indent"]) + "\n", encoding="utf-8")
    state["root"] = root


@when("beadloom init is run with --bootstrap")
def _init(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["init", "--bootstrap", "--project", str(state["root"])])
    # The tree breaks the rules init writes, on purpose; only package.json is judged here.
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output


@then(parsers.parse('package.json differs from what it was only by the "{script}" script'))
def _only_the_script(state: dict[str, Any], script: str) -> None:
    written = (state["root"] / "package.json").read_text(encoding="utf-8")
    package = state["package"]
    expected = {**package, "scripts": {**package["scripts"], script: "steiger ./src"}}
    assert written == json.dumps(expected, indent=state["indent"]) + "\n"
