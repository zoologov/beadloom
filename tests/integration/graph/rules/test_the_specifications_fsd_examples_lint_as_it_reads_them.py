"""feature-sliced.design's own examples, after ``init --yes``, lint as the specification reads.

BDL-082 S1 (RFC D1, D4, D5; PRD goals 1, 4, 5), read on 2026-10-11 from
``/docs/reference/layers``, ``/docs/reference/public-api`` and
``/docs/reference/slices-segments``. Each tree copies one passage's example, ``init --yes``
writes the graph and the rules, and ``lint --strict --format json`` gives the verdict, so
the whole path an adopter takes is the one under test: the reindex records the ``@x`` fact,
the layer rule reads it, the slice rules read the folders.

The unit files of the two rules hold the cases one rule at a time. These hold the cases that
only the whole path shows: a layer rule that carries ``scope:``, as ``init`` writes it, an
importer on a higher layer, a segment of the ``app`` layer under a shape rule, and the
alias that hides ``@x`` — the one reading the reindex leaves conservative on purpose.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

#: What ``init`` reads as a frontend, and the aliases the specification's imports are written in.
_PACKAGE = json.dumps(
    {
        "name": "probe",
        "private": True,
        "dependencies": {"vue": "3.5.0"},
        "devDependencies": {"vite": "6.0.0", "typescript": "5.6.0"},
    }
)
_PATHS = {"@/*": ["./*"]}

#: An app and a page that reach the entities through their indexes, as every tree below does.
_FRAME: Mapping[str, str] = {
    "package.json": _PACKAGE,
    "src/app/entrypoint/main.ts": (
        "import { routes } from '@/app/routes'\nexport const main = routes\n"
    ),
    "src/app/routes/index.ts": "export { routes } from './routes'\n",
    "src/app/routes/routes.ts": (
        "import { ArtistPage } from '@/pages/artist'\nexport const routes = [ArtistPage]\n"
    ),
    "src/pages/artist/index.ts": "export { ArtistPage } from './ui/ArtistPage'\n",
    "src/pages/artist/ui/ArtistPage.ts": (
        "import type { Artist } from '@/entities/artist'\n"
        "export const ArtistPage = (a: Artist) => a.name\n"
    ),
}

#: ``/docs/reference/layers``, *Entities*: the artist's model imports ``entities/song/@x/artist``,
#: which re-exports ``"../model/song.ts"`` — the specification's text, extension included.
_SONG_AND_ARTIST: Mapping[str, str] = {
    "src/entities/song/index.ts": "export type { Song } from './model/song'\n",
    "src/entities/song/model/song.ts": "export interface Song { title: string }\n",
    "src/entities/song/@x/artist.ts": 'export type { Song } from "../model/song.ts";\n',
    "src/entities/artist/index.ts": "export type { Artist } from './model/artist'\n",
    "src/entities/artist/model/artist.ts": (
        'import type { Song } from "entities/song/@x/artist";\n\n'
        "export interface Artist {\n  name: string;\n  songs: Array<Song>;\n}\n"
    ),
}

#: ``/docs/reference/public-api``: "only use this notation on the Entities layer" — the same
#: notation between two features.
_FEATURES_X: Mapping[str, str] = {
    "src/pages/artist/ui/ArtistPage.ts": (
        "import { b } from '@/features/b'\nexport const ArtistPage = b\n"
    ),
    "src/features/a/index.ts": "export { a } from './model/a'\n",
    "src/features/a/model/a.ts": "export const a = 1\n",
    "src/features/a/@x/b.ts": "export { a } from '../model/a'\n",
    "src/features/b/index.ts": "export { b } from './model/b'\n",
    "src/features/b/model/b.ts": "import { a } from 'features/a/@x/b'\nexport const b = a + 1\n",
}


def _write(root: Path, files: Mapping[str, str], paths: Mapping[str, list[str]]) -> None:
    for rel, text in {**_FRAME, **files}.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    tsconfig = {"compilerOptions": {"baseUrl": "./src", "paths": dict(paths)}}
    (root / "tsconfig.json").write_text(json.dumps(tsconfig), encoding="utf-8")


def _init(root: Path) -> None:
    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(root)])
    assert (root / ".beadloom" / "beadloom.db").is_file(), result.output


def _reindex(root: Path) -> None:
    result = CliRunner().invoke(main, ["reindex", "--project", str(root)])
    assert result.exit_code == 0, result.output


def _findings(root: Path) -> tuple[int, list[dict[str, object]]]:
    """The exit code of ``lint --strict`` and its findings of the ``fsd-*`` rules."""
    result = CliRunner().invoke(
        main, ["lint", "--strict", "--format", "json", "--project", str(root)]
    )
    found = [
        v
        for v in json.loads(result.stdout)["violations"]
        if str(v["rule_name"]).startswith("fsd-")
        and v["rule_type"] not in {"rule_liveness", "layer_declaration", "layer_population"}
    ]
    return result.exit_code, found


def _project(
    tmp_path: Path, files: Mapping[str, str], paths: Mapping[str, list[str]] = _PATHS
) -> Path:
    root = tmp_path / "probe"
    _write(root, files, paths)
    _init(root)
    return root


def _scope_the_layer_rule_to(root: Path, layer: str) -> None:
    """Put the slices of *layer* in a container node and scope ``fsd-layers`` to it."""
    graph = root / ".beadloom" / "_graph" / "services.yml"
    data = yaml.safe_load(graph.read_text(encoding="utf-8"))
    data["nodes"].append(
        {"ref_id": "catalog", "kind": "component", "source": f"src/{layer}/", "summary": "catalog"}
    )
    for edge in data["edges"]:
        if edge["kind"] == "part_of" and str(edge["src"]).startswith(f"{layer}-"):
            edge["dst"] = "catalog"
    data["edges"].append({"src": "catalog", "dst": "probe", "kind": "part_of"})
    graph.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    rules = root / ".beadloom" / "_graph" / "rules.yml"
    text = rules.read_text(encoding="utf-8")
    assert "scope: probe" in text, "init no longer scopes the layer rule to the root"
    rules.write_text(text.replace("scope: probe", "scope: catalog", 1), encoding="utf-8")
    _reindex(root)


def test_the_specifications_cross_import_example_is_clean(tmp_path: Path) -> None:
    root = _project(tmp_path, _SONG_AND_ARTIST)

    code, found = _findings(root)

    assert (code, found) == (0, [])


@pytest.mark.parametrize(
    ("files", "layer", "expected"),
    [
        (_SONG_AND_ARTIST, "entities", []),
        (_FEATURES_X, "features", [("fsd-layers", "features-b", "features-a")]),
    ],
    ids=["entities-accepted", "features-reported"],
)
def test_a_scoped_layer_rule_reads_the_cross_import_fact_inside_its_scope(
    tmp_path: Path,
    files: Mapping[str, str],
    layer: str,
    expected: list[tuple[str, str, str]],
) -> None:
    root = _project(tmp_path, files)
    _scope_the_layer_rule_to(root, layer)

    _, found = _findings(root)

    assert [(v["rule_name"], v["from_ref_id"], v["to_ref_id"]) for v in found] == expected


def test_an_api_opened_to_a_sibling_entity_is_a_finding_from_a_higher_layer(
    tmp_path: Path,
) -> None:
    files = {
        **_SONG_AND_ARTIST,
        "src/features/like-song/index.ts": "export { like } from './model/like'\n",
        "src/features/like-song/model/like.ts": (
            'import type { Song } from "entities/song/@x/artist";\n'
            "export const like = (s: Song) => s.title\n"
        ),
        "src/pages/artist/ui/ArtistPage.ts": (
            "import type { Artist } from '@/entities/artist'\n"
            "import { like } from '@/features/like-song'\n"
            "export const ArtistPage = (a: Artist) => [a.name, like]\n"
        ),
    }
    root = _project(tmp_path, files)

    code, found = _findings(root)

    assert code == 1
    [finding] = found
    assert (finding["rule_name"], finding["file_path"], finding["line_number"]) == (
        "fsd-public-api",
        "src/features/like-song/model/like.ts",
        1,
    )
    assert "opens to its sibling slice 'artist' alone" in str(finding["message"])


def test_a_segment_of_the_app_layer_is_not_judged_for_shape_and_a_slice_is(
    tmp_path: Path,
) -> None:
    """``/docs/reference/layers``: App and Shared "are made up of segments" — a segment's top
    is its content, so a ``hooks/`` folder inside ``app/routes`` is no finding even under a
    shape rule that carries the app layer's tag, while a slice's ``store/`` folder is one.

    The layer itself is no slice either (S1 review, minor 2): ``app/store`` is a segment the
    same page lists for App, and ``app/main.ts`` is code at the layer's top, and neither is a
    shape finding. Steiger reports ``app/store`` (``segments-by-purpose``); Beadloom does not.
    """
    files = {
        **_SONG_AND_ARTIST,
        "src/app/routes/hooks/use-route.ts": "export const useRoute = 1\n",
        "src/app/store/index.ts": "export const store = {}\n",
        "src/app/main.ts": "export const main = 1\n",
        "src/entities/song/store/song-store.ts": "export const songStore = 1\n",
    }
    root = _project(tmp_path, files)
    rules = root / ".beadloom" / "_graph" / "rules.yml"
    text = rules.read_text(encoding="utf-8")
    sliced = "tags: [fsd-pages, fsd-widgets, fsd-features, fsd-entities]\n      segments:"
    assert sliced in text, "init no longer writes the shape rule this case widens"
    rules.write_text(
        text.replace(sliced, sliced.replace("fsd-entities]", "fsd-entities, fsd-app]")),
        encoding="utf-8",
    )
    _reindex(root)

    _, found = _findings(root)

    assert [(v["rule_name"], v["from_ref_id"]) for v in found] == [
        ("fsd-slice-shape", "entities-song")
    ]
    assert "holds the folder 'store/'" in str(found[0]["message"])


def test_an_alias_that_hides_the_cross_import_folder_reads_as_a_plain_crossing(
    tmp_path: Path,
) -> None:
    """The reading the reindex documents as conservative: a pinned limitation, not a goal.

    Only a specifier with an ``@x`` path segment is located, so ``@song-for-artist`` mapped
    onto ``entities/song/@x/artist`` makes an ordinary edge, and the layer rule reports it.
    A change to this reading is a decision, and this case is where it shows.
    """
    files = {
        **_SONG_AND_ARTIST,
        "src/entities/artist/model/artist.ts": (
            'import type { Song } from "@song-for-artist";\n'
            "export interface Artist { name: string; songs: Array<Song> }\n"
        ),
    }
    root = _project(tmp_path, files, {**_PATHS, "@song-for-artist": ["./entities/song/@x/artist"]})

    code, found = _findings(root)

    assert code == 1
    assert [(v["rule_name"], v["from_ref_id"], v["to_ref_id"]) for v in found] == [
        ("fsd-layers", "entities-artist", "entities-song")
    ]
