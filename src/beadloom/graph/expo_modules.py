"""The bridge an Expo module declares between its TypeScript and its native code.

BDL-080 S3b (``beadloom-wbqd``), RFC D5 (e). An Expo module's TypeScript reaches its Swift
and Kotlin through no import: ``requireNativeModule('Pulse')`` names the native module by a
string, and the native class registers under that string. The one file that says which
native code answers is the module's ``expo-module.config.json``, and Expo's autolinking
reads exactly that file. So the bridge is read from it, as a ``uses`` edge from the node
that owns the config (the module's TypeScript) to the node that owns each linked
platform's folder.

**What is read**, per config:

- ``apple.modules``, else the earlier ``ios.modules`` (autolinking reads ``apple`` first):
  the Swift classes linked on iOS, whose code is in the module's ``ios/`` folder;
- ``android.modules``: the Kotlin or Java classes linked on Android, in ``android/``;
- ``platforms``, when it is a list: a platform it does not name is not linked, whatever
  its block says (``apple`` or ``ios`` names the iOS one).

A platform is bridged when its block names at least one module and its folder exists.

**Not read:** ``apple.podspecPath`` and ``android.path``, which can move the native code
out of ``ios/`` and ``android/``; the app delegate subscribers and other hooks that are no
module; a config inside ``node_modules`` (an installed package is not the project's code).

**Derived, not declared.** The edges are rebuilt on every reindex beside the import
edges, marked ``derived: expo-module`` in their ``extra``, so a platform the config stops
naming stops being bridged; an edge the graph YAML declares on the same pair keeps the
YAML's row. The configs join the fingerprint an incremental reindex compares
(:mod:`beadloom.graph.import_manifests`), so editing one alone is seen.
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from beadloom.graph.project_walk import ProjectFiles
from beadloom.infrastructure.repository import get_owning_ref_id

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

#: The file an Expo module declares its native modules in.
EXPO_MODULE_CONFIG = "expo-module.config.json"


@dataclass(frozen=True)
class _Platform:
    """One platform a config can link: its name, the keys naming it, and its folder.

    *keys* are the config's blocks, read in order, the first holding ``modules`` wins;
    *names* are the values of ``platforms`` that link it.
    """

    name: str
    keys: tuple[str, ...]
    names: frozenset[str]
    folder: str


_PLATFORMS = (
    _Platform("ios", ("apple", "ios"), frozenset({"apple", "ios"}), "ios"),
    _Platform("android", ("android",), frozenset({"android"}), "android"),
)

#: The provenance marker of a bridge edge, in its ``extra``.
DERIVED_BY_EXPO_MODULE = "expo-module"


@dataclass(frozen=True)
class NativeBridge:
    """One linked platform of one Expo module.

    *config* is the project-relative path of the module's ``expo-module.config.json``;
    *folder* the project-relative folder of the platform's native code; *modules* the
    native classes the config links there, in its order.
    """

    config: str
    platform: str
    folder: str
    modules: tuple[str, ...]


def _module_names(config: dict[str, object], platform: _Platform) -> tuple[str, ...]:
    """The classes *config* links on *platform*: its first block that holds ``modules``."""
    for key in platform.keys:
        block = config.get(key)
        if isinstance(block, dict) and "modules" in block:
            listed = block["modules"]
            if not isinstance(listed, list):
                return ()
            return tuple(name for name in listed if isinstance(name, str) and name)
    return ()


def _is_listed(config: dict[str, object], platform: _Platform) -> bool:
    """Whether ``platforms`` leaves *platform* linked: it names it, or it is no list."""
    listed = config.get("platforms")
    if not isinstance(listed, list):
        return True
    return any(name in platform.names for name in listed)


def bridges_of(project_root: Path, config_path: str, text: str) -> tuple[NativeBridge, ...]:
    """The bridges the config at *config_path* (project-relative) declares in *text*."""
    try:
        config = json.loads(text)
    except ValueError:
        return ()
    if not isinstance(config, dict):
        return ()
    module = posixpath.dirname(config_path)
    bridges = []
    for platform in _PLATFORMS:
        names = _module_names(config, platform)
        folder = posixpath.join(module, platform.folder)
        if names and _is_listed(config, platform) and (project_root / folder).is_dir():
            bridges.append(NativeBridge(config_path, platform.name, folder, names))
    return tuple(bridges)


class ExpoModules:
    """The ``expo-module.config.json`` files of one project, found by one walk on first use.

    *files* is the project's walk, shared with the other readers of one run; without it
    the configs are found by a walk of their own.
    """

    def __init__(self, project_root: Path, files: ProjectFiles | None = None) -> None:
        self._root = project_root
        self._files = files if files is not None else ProjectFiles(project_root)

    @cached_property
    def manifests(self) -> tuple[tuple[str, str], ...]:
        """``(path, text)`` of every config, by project-relative path."""
        found: list[tuple[str, str]] = []
        for path in self._files.named(lambda name: name == EXPO_MODULE_CONFIG):
            try:
                text = (self._root / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            found.append((path, text))
        return tuple(found)

    @cached_property
    def bridges(self) -> tuple[NativeBridge, ...]:
        """Every linked platform of every module, by config path, iOS before Android."""
        return tuple(
            bridge
            for path, text in self.manifests
            for bridge in bridges_of(self._root, path, text)
        )


def delete_bridge_edges(conn: sqlite3.Connection) -> int:
    """Delete the ``uses`` edges derived from Expo module configs; return how many."""
    cursor = conn.execute(
        "DELETE FROM edges WHERE kind = 'uses' AND json_extract(extra, '$.derived') = ?",
        (DERIVED_BY_EXPO_MODULE,),
    )
    return int(cursor.rowcount or 0)


def refresh_bridge_edges(conn: sqlite3.Connection, modules: ExpoModules) -> int:
    """Rebuild the bridge edges from *modules*; return the number written.

    The edge goes from the node owning the config to the node owning the platform's
    folder. A bridge none of whose ends has a node, or whose two ends are one node (the
    module was written as one node), yields no edge: there is nothing to draw between.
    """
    delete_bridge_edges(conn)
    written = 0
    for bridge in modules.bridges:
        source = get_owning_ref_id(conn, bridge.config)
        target = get_owning_ref_id(conn, f"{bridge.folder}/")
        if source is None or target is None or source == target:
            continue
        extra = {
            "derived": DERIVED_BY_EXPO_MODULE,
            "config": bridge.config,
            "platform": bridge.platform,
            "modules": list(bridge.modules),
        }
        cursor = conn.execute(
            "INSERT OR IGNORE INTO edges (src_ref_id, dst_ref_id, kind, extra) "
            "VALUES (?, ?, 'uses', ?)",
            (source, target, json.dumps(extra, ensure_ascii=False)),
        )
        written += int(cursor.rowcount or 0)
    conn.commit()
    return written
