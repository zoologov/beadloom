"""Step implementations for `onboarding/agent-prime/init_on_an_fsd_app_with_expo_router.feature`.

BDL-080 S3e (`beadloom-af99.12`). The real `beadloom init --bootstrap` and `beadloom lint
--strict --format json` run through the CLI on a small synthetic Expo app; the graph is
read back from the YAML init wrote, which is what an adopter commits. Nothing is patched.

The tree plants one upward import on purpose: a page imports a route file, which the layer
rule reports only when the routes carry the app layer.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../onboarding/agent-prime/init_on_an_fsd_app_with_expo_router.feature")

_PACKAGE = (
    '{"name": "fern-trail", "main": "expo-router/entry",'
    ' "dependencies": {"expo": "52.0.11", "expo-router": "4.0.9", "react": "18.3.1"}}\n'
)

#: An Expo app: routes in `app/` at the root, the FSD layers under `src/`.
_EXPO_APP: dict[str, str] = {
    "package.json": _PACKAGE,
    "tsconfig.json": '{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}}\n',
    "app/_layout.tsx": (
        "import { AppProviders } from '@/app'\n"
        "export default function RootLayout() { return AppProviders }\n"
    ),
    "app/index.tsx": "export { HomeScreen as default } from '@/pages/home'\n",
    "app/trail/[id].tsx": (
        "import { TrailScreen } from '@/pages/trail'\n"
        "export default function TrailRoute() { return TrailScreen }\n"
    ),
    "src/app/index.ts": "export { AppProviders } from './providers/AppProviders'\n",
    "src/app/providers/AppProviders.tsx": "export const AppProviders = 1\n",
    "src/pages/home/index.ts": "export { HomeScreen } from './ui/HomeScreen'\n",
    "src/pages/home/ui/HomeScreen.tsx": (
        "import { trailName } from '@/entities/trail'\nexport const HomeScreen = trailName\n"
    ),
    "src/pages/trail/index.ts": "export { TrailScreen } from './ui/TrailScreen'\n",
    # The planted upward import: a page reaching into a route file.
    "src/pages/trail/ui/TrailScreen.tsx": (
        "import RootLayout from '../../../../app/_layout'\n"
        "import { trailName } from '@/entities/trail'\n"
        "export const TrailScreen = [RootLayout, trailName]\n"
    ),
    "src/entities/trail/index.ts": "export const trailName = 'ridge'\n",
    "src/shared/ui/index.ts": "export const Badge = 1\n",
}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given("an Expo app in the Feature-Sliced layout with Expo Router's routes in app/")
def _tree(tmp_path: Path, state: dict[str, Any]) -> None:
    root = tmp_path / "fern-trail"
    for rel, text in _EXPO_APP.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    state["root"] = root


@given("the project does not depend on expo-router")
def _without_the_router(state: dict[str, Any]) -> None:
    root: Path = state["root"]
    (root / "package.json").write_text(_PACKAGE.replace('"expo-router"', '"expo-font"'))
    # The first init wrote the scaffold; the second is asked on a clean project.
    for path in sorted((root / ".beadloom").rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    (root / ".beadloom").rmdir()


@when("beadloom init is run with --bootstrap")
def _init(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["init", "--bootstrap", "--project", str(state["root"])])
    # The tree breaks the rules init writes, on purpose; the exit code is not asked here.
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    graph = yaml.safe_load(
        (state["root"] / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
    )
    state["nodes"] = {node["ref_id"]: node for node in graph["nodes"]}
    state["parents"] = {
        edge["src"]: edge["dst"] for edge in graph["edges"] if edge["kind"] == "part_of"
    }


@when("beadloom lint --strict is run")
def _lint(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["lint", "--strict", "--format", "json", "--project", str(state["root"])]
    )
    state["lint"] = json.loads(result.stdout)


@then(parsers.parse('the node "{ref_id}" is a component with the source "{source}"'))
def _component(state: dict[str, Any], ref_id: str, source: str) -> None:
    node = state["nodes"][ref_id]
    assert (node["kind"], node["source"]) == ("component", source)


@then(parsers.parse('the node "{ref_id}" is tagged "{tag}" and part of "{parent}"'))
def _placed(state: dict[str, Any], ref_id: str, tag: str, parent: str) -> None:
    assert state["nodes"][ref_id]["tags"] == [tag]
    assert state["parents"][ref_id] == parent


@then(parsers.parse('no node has a source below "{folder}"'))
def _none_below(state: dict[str, Any], folder: str) -> None:
    below = [
        ref
        for ref, node in state["nodes"].items()
        if str(node.get("source") or "").startswith(folder) and node["source"] != folder
    ]
    assert below == []


@then(parsers.parse('no node has the source "{folder}"'))
def _none_at(state: dict[str, Any], folder: str) -> None:
    assert [r for r, n in state["nodes"].items() if n.get("source") == folder] == []


def _layer_findings(state: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (v.get("from_ref_id"), v.get("to_ref_id"))
        for v in state["lint"]["violations"]
        if v["rule_name"] == "fsd-layers" and v["rule_type"] != "layer_population"
    ]


@then(parsers.parse('lint reports "fsd-layers" for the edge "{src}" -> "{dst}"'))
def _reported(state: dict[str, Any], src: str, dst: str) -> None:
    assert (src, dst) in _layer_findings(state), state["lint"]["violations"]


@then(parsers.parse('lint does not report "fsd-layers" for the edge "{src}" -> "{dst}"'))
def _not_reported(state: dict[str, Any], src: str, dst: str) -> None:
    assert (src, dst) not in _layer_findings(state)
