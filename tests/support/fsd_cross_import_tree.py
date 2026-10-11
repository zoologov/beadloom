"""The specification's ``@x`` example as a tree on disk, for the scenarios of BDL-082 S1a.

feature-sliced.design, ``/docs/reference/layers`` (*Entity relationships*):
``entities/artist/model/artist.ts`` imports ``entities/song/@x/artist``, and
``entities/song/@x/artist.ts`` re-exports from the song's model. The artist imports it the
three ways a project spells it — the specification's bare specifier through the tsconfig
``baseUrl``, the ``@/`` alias, and a relative path — so a reading that missed one form is
seen. The probe of the work item's axes (``p1-x``) is this tree.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

TSCONFIG = json.dumps({"compilerOptions": {"baseUrl": "./src", "paths": {"@/*": ["./*"]}}})

#: The song and the artist entities; every import of the artist goes through ``@x/artist``.
SPEC_CROSS_IMPORTS: Mapping[str, str] = {
    "src/entities/song/index.ts": "export type { Song } from './model/song'\n",
    "src/entities/song/model/song.ts": "export interface Song { title: string }\n",
    "src/entities/song/@x/artist.ts": "export type { Song } from '../model/song'\n",
    "src/entities/artist/index.ts": (
        "export { Artist } from './model/artist'\n"
        "export { rel } from './model/rel'\n"
        "export { card } from './ui/card'\n"
    ),
    "src/entities/artist/model/artist.ts": (
        "import type { Song } from 'entities/song/@x/artist'\n"
        "export const Artist = { songs: [] as Song[] }\n"
    ),
    "src/entities/artist/model/rel.ts": (
        "import type { Song } from '../../song/@x/artist'\nexport const rel = (s: Song) => s\n"
    ),
    "src/entities/artist/ui/card.ts": (
        "import type { Song } from '@/entities/song/@x/artist'\n"
        "export const card = (s: Song) => s\n"
    ),
}

#: Two features, ``b`` importing the API ``a`` opens to it: ``@x`` off the entities layer.
FEATURES_CROSS_IMPORT: Mapping[str, str] = {
    "src/features/a/index.ts": "export { a } from './model/a'\n",
    "src/features/a/model/a.ts": "export const a = 1\n",
    "src/features/a/@x/b.ts": "export { a } from '../model/a'\n",
    "src/features/b/index.ts": "export { b } from './model/b'\n",
    "src/features/b/model/b.ts": "import { a } from '@/features/a/@x/b'\nexport const b = a + 1\n",
}

SPEC_SLICES = (
    ("entities-song", "src/entities/song/", "fsd-entities"),
    ("entities-artist", "src/entities/artist/", "fsd-entities"),
)
FEATURE_SLICES = (
    ("features-a", "src/features/a/", "fsd-features"),
    ("features-b", "src/features/b/", "fsd-features"),
)

#: The Feature-Sliced layers as ``init`` declares them, as a ``layers`` rule.
FSD_LAYERS_RULE = """version: 3
rules:
  - name: fsd-layers
    description: "The Feature-Sliced layers import downward"
    severity: error
    layers:
      - { name: app, tag: fsd-app }
      - { name: pages, tag: fsd-pages }
      - { name: widgets, tag: fsd-widgets }
      - { name: features, tag: fsd-features }
      - { name: entities, tag: fsd-entities }
      - { name: shared, tag: fsd-shared }
    enforce: top-down
    allow_skip: true
    edge_kind: depends_on
"""


def write_fsd_project(
    root: Path,
    files: Mapping[str, str],
    slices: Sequence[tuple[str, str, str]],
    *,
    declared: Sequence[tuple[str, str]] = (),
) -> None:
    """*files* on disk, a graph of *slices* — ``(ref, source, tag)`` — and *declared* edges."""
    for rel, text in {"tsconfig.json": TSCONFIG, **files}.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        yaml.safe_dump({"scan_paths": ["src"], "languages": [".ts"]}), encoding="utf-8"
    )
    nodes = [{"ref_id": "web", "kind": "service", "summary": "web", "source": ""}]
    nodes += [
        {"ref_id": ref, "kind": "component", "summary": ref, "source": source, "tags": [tag]}
        for ref, source, tag in slices
    ]
    edges = [{"src": ref, "dst": "web", "kind": "part_of"} for ref, _, _ in slices]
    edges += [{"src": src, "dst": dst, "kind": "depends_on"} for src, dst in declared]
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump({"nodes": nodes, "edges": edges}), encoding="utf-8"
    )
