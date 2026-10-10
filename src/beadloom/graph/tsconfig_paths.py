"""What a project's ``tsconfig.json`` maps a non-relative specifier to (BDL-080 ``beadloom-cwzc``).

A TypeScript or JavaScript project names its own modules without a relative path through
``compilerOptions.paths`` (``"@/*": ["./src/*"]``) and ``compilerOptions.baseUrl``. Until
this module the resolver knew two prefixes, ``@/`` and ``~/``, and read both as ``src/``
whatever the project declared, so an Expo app whose ``@/*`` names the project root got no
edge for any of those imports.

**Which configs are read.** Every ``tsconfig.json``, ``tsconfig.<name>.json`` and
``jsconfig.json`` in the project, found by the project's one walk
(:class:`~beadloom.graph.project_walk.ProjectFiles`), which skips hidden folders and the
folders that hold other people's code or build output. An importing file is governed by
the configs of the nearest folder at or above it that holds any: all of them, because
``create-vue`` puts ``paths`` in ``tsconfig.app.json`` beside a ``tsconfig.json`` that
only lists references. In that folder ``tsconfig.json`` is read first, then the others by
name, ``jsconfig.json`` last.

**How a config is read.** As JSON with comments and trailing commas, which is what
``tsc`` accepts. ``extends`` is followed when it names a file by a relative path, as a
string or a list; a package (``expo/tsconfig.base``) is not read, and the config that
names it still is. A child's ``paths`` and ``baseUrl`` replace its parent's. ``paths``
targets are read from ``baseUrl`` when one is in force, else from the folder of the config
that declared ``paths``; a target that leaves the project is dropped.

**How a specifier is matched**, as ``tsc`` does: a key without ``*`` matches only itself
and beats every pattern; of the patterns, the one with the longest prefix before ``*``
wins, and each of its targets is a candidate, in order.

Not read: ``references`` to a config in another folder, ``include``/``exclude`` (an
importer is governed by folder, not by the config's file list), ``rootDirs``, and a config
``extends`` names inside ``node_modules``.
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

if TYPE_CHECKING:
    from pathlib import Path

#: The configs read: ``tsconfig.json``, ``tsconfig.<name>.json`` and ``jsconfig.json``.
_TSCONFIG = "tsconfig.json"
_TSCONFIG_PREFIX = "tsconfig."
_JSCONFIG = "jsconfig.json"
_JSON = ".json"

#: The deepest ``extends`` chain followed; a longer one is a cycle in all but name.
_MAX_EXTENDS = 16

_WILDCARD = "*"


def read_jsonc(text: str) -> object | None:
    """*text* read as JSON with comments and trailing commas, or ``None`` when it is not."""
    try:
        data: object = json.loads(_strip_trailing_commas(_strip_comments(text)))
    except ValueError:
        return None
    return data


def _strip_comments(text: str) -> str:
    """*text* without ``//`` and ``/* */`` comments; a marker inside a string is text."""
    out: list[str] = []
    index, length, in_string = 0, len(text), False
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if char == "\\" and index + 1 < length:
                out.append(text[index + 1])
                index += 1
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            out.append(char)
        elif text.startswith("//", index):
            end = text.find("\n", index)
            index = length if end < 0 else end
            continue
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        else:
            out.append(char)
        index += 1
    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    """*text* without a comma whose next visible character closes an array or object."""
    out: list[str] = []
    in_string, escaped = False, False
    for index, char in enumerate(text):
        if in_string:
            in_string = escaped or char != '"'
            escaped = not escaped and char == "\\"
        elif char == '"':
            in_string = True
        elif char == "," and text[index + 1 :].lstrip()[:1] in ("]", "}"):
            continue
        out.append(char)
    return "".join(out)


@dataclass(frozen=True)
class _Options:
    """The two options this module reads, each with the folder it is read from."""

    paths: tuple[tuple[str, tuple[str, ...]], ...] | None = None
    paths_folder: str = ""
    base_url: str | None = None


def _within_project(path: str) -> str | None:
    """*path* normalised, or ``None`` when it leaves the project root."""
    normal = posixpath.normpath(path)
    if normal == ".." or normal.startswith("../") or normal.startswith("/"):
        return None
    return "" if normal == "." else normal


def _is_config(name: str) -> bool:
    if name in (_TSCONFIG, _JSCONFIG):
        return True
    return name.startswith(_TSCONFIG_PREFIX) and name.endswith(_JSON)


def _config_order(name: str) -> tuple[int, str]:
    """``tsconfig.json`` first, then ``tsconfig.<name>.json`` by name, ``jsconfig.json`` last."""
    if name == _TSCONFIG:
        return (0, name)
    return (2, name) if name == _JSCONFIG else (1, name)


def _paths_of(value: object) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """The usable entries of a ``paths`` object: a string key, a list of string targets."""
    if not isinstance(value, dict):
        return ()
    return tuple(
        (key, tuple(t for t in targets if isinstance(t, str)))
        for key, targets in value.items()
        if isinstance(key, str) and isinstance(targets, list)
    )


def _matched(specifier: str, paths: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    """The targets of the key *specifier* matches, ``*`` replaced, as ``tsc`` picks it."""
    best: tuple[int, tuple[str, ...], str] | None = None
    for key, targets in paths:
        if _WILDCARD not in key:
            if key == specifier:
                return list(targets)
            continue
        prefix, _, suffix = key.partition(_WILDCARD)
        fits = (
            specifier.startswith(prefix)
            and specifier.endswith(suffix)
            and len(specifier) >= len(prefix) + len(suffix)
        )
        if fits and (best is None or len(prefix) > best[0]):
            best = (len(prefix), targets, specifier[len(prefix) : len(specifier) - len(suffix)])
    if best is None:
        return []
    _, targets, captured = best
    return [target.replace(_WILDCARD, captured, 1) for target in targets]


class TsConfigs:
    """The tsconfig/jsconfig files of one project, read once on first use.

    *files* is the project's walk, shared with the other readers of one run; without it
    the configs are found by a walk of their own.
    """

    def __init__(self, project_root: Path, files: ProjectFiles | None = None) -> None:
        self._root = project_root
        self._files = files if files is not None else ProjectFiles(project_root)

    @cached_property
    def _found(self) -> dict[str, list[str]]:
        """Every config's project-relative path, keyed by its folder, in reading order."""
        return {
            folder: [posixpath.join(folder, n) for n in sorted(configs, key=_config_order)]
            for folder, names in self._files.folders
            if (configs := [name for name in names if _is_config(name)])
        }

    @cached_property
    def _texts(self) -> dict[str, str]:
        """The text of every config read, the ones ``extends`` reaches included, by path."""
        texts: dict[str, str] = {}
        for paths in self._found.values():
            for path in paths:
                self._read_chain(path, texts)
        return texts

    @cached_property
    def manifests(self) -> tuple[tuple[str, str], ...]:
        """``(path, text)`` of every config an answer here rests on, by path.

        An import resolved through this reading changes its answer only when one of these
        changes, or when a file a target names appears or vanishes, which a source file does
        too (``beadloom-jcng``).
        """
        return tuple(sorted(self._texts.items()))

    def _read(self, path: str) -> dict[str, object] | None:
        try:
            text = (self._root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        data = read_jsonc(text)
        return data if isinstance(data, dict) else None

    def _read_chain(self, path: str, texts: dict[str, str]) -> None:
        """Record the text of *path* and of every config its ``extends`` chain reaches."""
        for step in self._chain(path):
            if step not in texts:
                texts[step] = (self._root / step).read_text(encoding="utf-8")

    def _chain(self, path: str) -> list[str]:
        """*path* and every readable config it extends, the farthest ancestor last."""
        chain: list[str] = []
        pending = [path]
        while pending and len(chain) < _MAX_EXTENDS:
            current = pending.pop(0)
            if current in chain:
                continue
            data = self._read(current)
            if data is None:
                continue
            chain.append(current)
            pending.extend(self._extended(current, data.get("extends")))
        return chain

    def _extended(self, path: str, value: object) -> list[str]:
        """The project-relative configs an ``extends`` *value* names by a relative path."""
        names = value if isinstance(value, list) else [value]
        found: list[str] = []
        for name in names:
            if not isinstance(name, str) or not name.startswith("."):
                continue  # a package config is not read
            target = _within_project(posixpath.join(posixpath.dirname(path), name))
            if target is None:
                continue
            if not target.endswith(_JSON) and not (self._root / target).is_file():
                target += _JSON
            found.append(target)
        return found

    @cached_property
    def _options(self) -> dict[str, _Options]:
        """Each config's ``paths`` and ``baseUrl`` in force, its ``extends`` chain applied."""
        return {path: self._options_of(path) for paths in self._found.values() for path in paths}

    def _options_of(self, path: str) -> _Options:
        options = _Options()
        # Parents first, so a child's value replaces its parent's.
        for step in reversed(self._chain(path)):
            data = self._read(step)
            compiler = data.get("compilerOptions") if data is not None else None
            if not isinstance(compiler, dict):
                continue
            folder = posixpath.dirname(step)
            base_url = compiler.get("baseUrl")
            if isinstance(base_url, str):
                read_from = _within_project(posixpath.join(folder, base_url))
                options = _Options(options.paths, options.paths_folder, read_from)
            if "paths" in compiler:
                options = _Options(_paths_of(compiler["paths"]), folder, options.base_url)
        return options

    def _governing(self, importer: str) -> list[_Options]:
        """The options of the configs in the nearest folder at or above *importer*."""
        folder = posixpath.dirname(importer)
        while True:
            if folder in self._found:
                return [self._options[path] for path in self._found[folder]]
            if not folder:
                return []
            folder = posixpath.dirname(folder)

    def mapped(self, specifier: str, importer: str) -> tuple[str, ...]:
        """The project-relative paths ``paths`` maps *specifier* to, for the file *importer*."""
        found: list[str] = []
        for options in self._governing(importer):
            if not options.paths:
                continue
            read_from = options.base_url if options.base_url is not None else options.paths_folder
            for target in _matched(specifier, options.paths):
                path = _within_project(posixpath.join(read_from, target))
                if path is not None and path not in found:
                    found.append(path)
        return tuple(found)

    def under_base_url(self, specifier: str, importer: str) -> tuple[str, ...]:
        """The project-relative path *specifier* names under ``baseUrl``, if one is in force."""
        found: list[str] = []
        for options in self._governing(importer):
            if options.base_url is None:
                continue
            path = _within_project(posixpath.join(options.base_url, specifier))
            if path is not None and path not in found:
                found.append(path)
        return tuple(found)
