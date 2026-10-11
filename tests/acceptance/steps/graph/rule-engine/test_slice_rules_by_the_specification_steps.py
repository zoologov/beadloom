"""Steps for `graph/rule-engine/slice_rules_by_the_specification.feature` (BDL-082 S1b).

Each scenario writes one of the specification's examples to disk, a graph of its slices by
hand, and runs the real `beadloom lint --format json`, which reindexes first: the imports the
rules read are the ones the resolver resolved through the tsconfig `baseUrl` and `@/*` path.
Nothing is mocked.
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

scenarios("../../../graph/rule-engine/slice_rules_by_the_specification.feature")

_TSCONFIG = json.dumps({"compilerOptions": {"baseUrl": "./src", "paths": {"@/*": ["./*"]}}})

#: The specification's `@x` example (`/docs/reference/layers`), and a third entity.
_CROSS_IMPORTS = {
    "src/entities/song/index.ts": "export type { Song } from './model/song'\n",
    "src/entities/song/model/song.ts": "export interface Song { title: string }\n",
    "src/entities/song/@x/artist.ts": "export type { Song } from '../model/song'\n",
    "src/entities/artist/index.ts": "export { Artist } from './model/artist'\n",
    "src/entities/artist/model/artist.ts": (
        "import type { Song } from 'entities/song/@x/artist'\n"
        "export const Artist = { songs: [] as Song[] }\n"
    ),
    "src/entities/album/index.ts": "export { Album } from './model/album'\n",
    "src/entities/album/model/album.ts": (
        "import type { Song } from '@/entities/song/@x/artist'\n"
        "export const Album = { songs: [] as Song[] }\n"
    ),
}

#: The axes probe `p45-segments`, its `shared` half.
_SHARED = {
    "src/shared/ui/button/index.ts": "export { Button } from './Button'\n",
    "src/shared/ui/button/Button.ts": "export const Button = 1\n",
    "src/shared/ui/text-field/index.ts": "export { TextField } from './text-field'\n",
    "src/shared/ui/text-field/text-field.ts": "export const TextField = 1\n",
    "src/shared/routes/index.ts": "export { paths } from './paths'\n",
    "src/shared/routes/paths.ts": (
        "import { Button } from '../ui/button/Button'\nexport const paths = { b: Button }\n"
    ),
    "src/pages/home/index.ts": "export { HomePage } from './ui/home'\n",
    "src/pages/home/ui/home.ts": (
        "import { Button } from '@/shared/ui/button'\n"
        "import { TextField } from '@/shared/ui/text-field/text-field'\n"
        "import { paths } from '@/shared/routes'\n"
        "export const HomePage = [Button, TextField, paths]\n"
    ),
}


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "probe"}


def _project(
    world: dict[str, Any], files: dict[str, str], nodes: list[tuple[str, str, str, str | None]]
) -> None:
    """*files* on disk, and a graph of *nodes* — ``(ref, source, tag, container)`` — by hand."""
    root: Path = world["root"]
    for rel, text in {"tsconfig.json": _TSCONFIG, **files}.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        yaml.safe_dump({"scan_paths": ["src"], "languages": [".ts"]}), encoding="utf-8"
    )
    graph = [{"ref_id": "web", "kind": "service", "summary": "web", "source": ""}]
    graph += [
        {"ref_id": ref, "kind": "component", "summary": ref, "source": source, "tags": [tag]}
        for ref, source, tag, _ in nodes
    ]
    edges = [
        {"src": ref, "dst": container or "web", "kind": "part_of"}
        for ref, _, _, container in nodes
    ]
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump({"nodes": graph, "edges": edges}), encoding="utf-8"
    )


@given(
    "the specification's song and artist entities, and an album reaching the song's API "
    "for the artist"
)
def _cross_imports(world: dict[str, Any]) -> None:
    _project(
        world,
        _CROSS_IMPORTS,
        [
            (f"entities-{name}", f"src/entities/{name}/", "fsd-entities", None)
            for name in ("song", "artist", "album")
        ],
    )


@given("a page importing the segments of shared, and shared's segments importing each other")
def _shared(world: dict[str, Any]) -> None:
    _project(
        world,
        _SHARED,
        [
            ("shared", "src/shared/", "fsd-shared", None),
            ("shared-ui", "src/shared/ui/", "fsd-shared", "shared"),
            ("shared-routes", "src/shared/routes/", "fsd-shared", "shared"),
            ("pages-home", "src/pages/home/", "fsd-pages", None),
        ],
    )


@given(parsers.parse('a feature holding the segments "{first}" and "{second}"'))
def _segments(world: dict[str, Any], first: str, second: str) -> None:
    files = {
        "src/features/x/index.ts": "export const x = 1\n",
        f"src/features/x/{first}/a.ts": "export const a = 1\n",
        f"src/features/x/{second}/b.ts": "export const b = 1\n",
    }
    _project(world, files, [("features-x", "src/features/x/", "fsd-features", None)])


@given(
    parsers.parse(
        'the slice group "{group}" of the features layer, holding "{first}", "{second}" '
        "and a code file"
    )
)
def _group(world: dict[str, Any], group: str, first: str, second: str) -> None:
    files = {f"src/features/{group}/shared.ts": "export const shared = 1\n"}
    for name in (first, second):
        files[f"src/features/{group}/{name}/index.ts"] = f"export const {name} = 1\n"
    _project(
        world,
        files,
        [
            (f"features-{group}-{name}", f"src/features/{group}/{name}/", "fsd-features", None)
            for name in (first, second)
        ],
    )


def _rules(world: dict[str, Any], block: str) -> None:
    (world["root"] / ".beadloom" / "_graph" / "rules.yml").write_text(
        "version: 3\nrules:\n  - name: fsd-slices\n" + block, encoding="utf-8"
    )


@given("the rules declare slice_public_api over the entities layer")
def _public_api_entities(world: dict[str, Any]) -> None:
    _rules(world, "    slice_public_api:\n      tags: [fsd-entities]\n")


@given("the rules declare slice_public_api over the pages and the shared layer")
def _public_api_shared(world: dict[str, Any]) -> None:
    _rules(world, "    slice_public_api:\n      tags: [fsd-pages, fsd-shared]\n")


@given("the rules declare slice_shape over the features layer")
def _shape(world: dict[str, Any]) -> None:
    _rules(world, "    slice_shape:\n      tags: [fsd-features]\n")


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["lint", "--format", "json", "--project", str(world["root"])]
    )
    world["violations"] = json.loads(result.stdout)["violations"]


def _of_type(world: dict[str, Any], rule_type: str) -> list[dict[str, Any]]:
    return [v for v in world["violations"] if v["rule_type"] == rule_type]


@then(parsers.parse('"{rule_type}" reports "{importer}" reaching into "{slice_ref}"'))
def _reaching(world: dict[str, Any], rule_type: str, importer: str, slice_ref: str) -> None:
    found = [(v["file_path"], v["to_ref_id"]) for v in _of_type(world, rule_type)]
    assert (importer, slice_ref) in found, found


@then(parsers.parse('"{rule_type}" reports nothing from "{importer}"'))
def _nothing_from(world: dict[str, Any], rule_type: str, importer: str) -> None:
    assert [v for v in _of_type(world, rule_type) if v["file_path"] == importer] == []


@then(parsers.parse('"{rule_type}" reports line {line:d} of "{importer}" and no other line of it'))
def _only_line(world: dict[str, Any], rule_type: str, line: int, importer: str) -> None:
    lines = [v["line_number"] for v in _of_type(world, rule_type) if v["file_path"] == importer]
    assert lines == [line], world["violations"]


@then(parsers.parse('"{rule_type}" reports the folder "{folder}" of "{slice_ref}"'))
def _folder(world: dict[str, Any], rule_type: str, folder: str, slice_ref: str) -> None:
    found = [v["message"] for v in _of_type(world, rule_type) if v["from_ref_id"] == slice_ref]
    assert any(f"'{folder}'" in message for message in found), found


@then(parsers.parse('"{rule_type}" reports nothing naming "{folder}"'))
def _nothing_naming(world: dict[str, Any], rule_type: str, folder: str) -> None:
    assert [v for v in _of_type(world, rule_type) if f"'{folder}'" in v["message"]] == []


@then(parsers.parse('"{rule_type}" reports the code file "{path}" of a group'))
def _group_file(world: dict[str, Any], rule_type: str, path: str) -> None:
    found = [v for v in _of_type(world, rule_type) if v["file_path"] == path]
    assert len(found) == 1, world["violations"]
    assert "a group shares no code" in found[0]["message"]
