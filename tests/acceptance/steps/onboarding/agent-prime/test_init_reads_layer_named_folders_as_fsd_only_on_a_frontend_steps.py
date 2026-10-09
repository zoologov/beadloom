"""Steps for `init_reads_layer_named_folders_as_fsd_only_on_a_frontend.feature`.

BDL-080 S3f (`beadloom-af99.14`). The real `beadloom init --bootstrap` runs through the CLI
on two small trees with the same three layer-named folders: one Python, one TypeScript.
The graph and the rules are read back from the files init wrote. Nothing is patched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios(
    "../../../onboarding/agent-prime/init_reads_layer_named_folders_as_fsd_only_on_a_frontend.feature"
)

#: The reviewer's probe (beadloom-jtki, major 1): clean architecture in Python.
_PYTHON_TREE: dict[str, str] = {
    "pyproject.toml": '[project]\nname = "ledger"\nversion = "0.1.0"\n',
    "src/app/main.py": "from src.entities.order import Order\n\n\ndef run() -> Order:\n"
    "    return Order()\n",
    "src/entities/order.py": "class Order:\n    pass\n",
    "src/shared/clock.py": "def now() -> int:\n    return 0\n",
    "src/infrastructure/repo.py": "def save() -> None:\n    return None\n",
}

_TYPESCRIPT_TREE: dict[str, str] = {
    "src/app/index.ts": "export { order } from '../entities/order'\n",
    "src/entities/order/index.ts": "export const order = 1\n",
    "src/shared/clock/index.ts": "export const now = () => 0\n",
}


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given(
    "a Python project with the folders src/app, src/entities and src/shared and no package.json"
)
def _python_tree(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = _write(tmp_path / "ledger", _PYTHON_TREE)


@given("a project with the folders src/app, src/entities and src/shared holding TypeScript")
def _typescript_tree(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = _write(tmp_path / "ledger-web", _TYPESCRIPT_TREE)


@when("beadloom init is run with --bootstrap")
def _init(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["init", "--bootstrap", "--project", str(state["root"])])
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    state["init_output"] = result.output


@then(parsers.parse('init chose the "{preset}" preset'))
def _preset(state: dict[str, Any], preset: str) -> None:
    assert f"(preset: {preset})" in state["init_output"], state["init_output"]


@then(parsers.parse('the rules init wrote do not mention "{text}"'))
def _rules_silent(state: dict[str, Any], text: str) -> None:
    rules = (state["root"] / ".beadloom" / "_graph" / "rules.yml").read_text(encoding="utf-8")
    assert text not in rules


@then(parsers.parse('a node owns "{path}"'))
def _owned(state: dict[str, Any], path: str) -> None:
    graph = yaml.safe_load(
        (state["root"] / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
    )
    sources = [str(node.get("source") or "") for node in graph["nodes"]]
    assert any(source and path.startswith(source) for source in sources), sources
