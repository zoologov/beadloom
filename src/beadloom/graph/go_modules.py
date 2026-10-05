"""Go modules of a project: which directory a Go import path names (BDL-076 B5).

A Go import is written as ``<module path>/<package directory>``, where the module
path is what a ``go.mod`` declares on its ``module`` line. To find the package an
import names, the module path is stripped and the rest is read as a directory
under that module's ``go.mod``. Until B5 nothing stripped it: the resolver read
``example.org/tidewater/internal/catalog`` as a directory path and matched none,
and ``init``'s quick scan took the first segment naming a cluster, which on the
standard layout is ``cmd/<module-name>/``.

**Which module governs a file.** The nearest ``go.mod`` at or above the file's
directory, within the project — the rule the ``go`` command uses. A directory
the ``go`` tool ignores (a name beginning with ``.`` or ``_``, ``testdata``) and
the dependency folders ``vendor`` and ``node_modules`` are not searched.

**Which modules an import may name, longest module path first.** Every module the
project holds; then the local ``replace`` directives of the importer's ``go.mod``;
then those of the ``go.work`` that uses the importer's module; the importer's own
module last, so nothing redirects it. A module the project holds is mapped to its
directory however the importer reaches it — by the workspace, by a ``replace``, or
from the module proxy at some version — because the dependency on that package is
the same one. A ``replace`` to another module path or to a directory outside the
project maps nothing, since no node can own it. The directory an import maps to
must be governed by the module it was matched under: a nested module takes its
subtree out of the enclosing one, as it does for the ``go`` command.

**What stays unmapped:** the standard library and every module the project does
not hold, including one whose path shares a segment with a directory of ours.
"""

# beadloom:domain=graph
# beadloom:feature=import-resolver

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The file that declares a module, and the file that declares a workspace.
_GO_MOD = "go.mod"
_GO_WORK = "go.work"

#: Directories never searched for a module: the ``go`` tool's own ignored names,
#: and the folders that hold other people's code.
_SKIPPED_DIRECTORIES = frozenset({"testdata", "vendor", "node_modules"})
_IGNORED_PREFIXES = (".", "_")

#: One token of a ``go.mod``/``go.work`` line: a quoted string, the replace arrow,
#: a block parenthesis, or a bare word that does not run into an arrow.
_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|`[^`]*`|=>|[()]|(?:(?!=>)[^\s"`()])+')
_COMMENT = "//"
_ARROW = "=>"
_BLOCK_OPEN = "("
_BLOCK_CLOSE = ")"
#: A replacement written as a path, not a module: Go requires ``./``, ``../`` or
#: an absolute path.
_LOCAL_PREFIXES = ("./", "../", "/")


@dataclass(frozen=True)
class GoModule:
    """One ``go.mod``: the module path it declares and the directory it sits in.

    ``directory`` is project-relative POSIX, ``""`` for the project root.
    ``replacements`` are its ``replace`` directives whose target is a directory in
    the project, as ``(module path, directory)``.
    """

    path: str
    directory: str
    replacements: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class _Workspace:
    """One ``go.work``: the module directories it uses and its local replacements."""

    directory: str
    uses: frozenset[str]
    replacements: tuple[tuple[str, str], ...]


def _tokens(line: str) -> list[str]:
    """The tokens of one line, with its ``//`` comment dropped and quotes removed."""
    code = line.split(_COMMENT, 1)[0]
    return [token.strip('"`') for token in _TOKEN.findall(code)]


def _directives(text: str) -> Iterator[tuple[str, list[str]]]:
    """Each ``(verb, arguments)`` of a ``go.mod``/``go.work``, block entries unfolded."""
    block_verb: str | None = None
    for line in text.splitlines():
        tokens = _tokens(line)
        if not tokens:
            continue
        if block_verb is not None:
            if tokens == [_BLOCK_CLOSE]:
                block_verb = None
            else:
                yield block_verb, tokens
        elif tokens[1:] == [_BLOCK_OPEN]:
            block_verb = tokens[0]
        else:
            yield tokens[0], tokens[1:]


def _within(directory: str, target: str) -> str | None:
    """*target* written relative to *directory*, as a project-relative directory.

    ``None`` when it leaves the project. An absolute *target* cannot be read
    against the project and is ``None`` as well.
    """
    if target.startswith("/"):
        return None
    joined = posixpath.normpath(posixpath.join(directory or ".", target))
    if joined == ".." or joined.startswith("../"):
        return None
    return "" if joined == "." else joined


def _local_replacements(directory: str, text: str) -> tuple[tuple[str, str], ...]:
    """The ``replace`` directives of a file in *directory* that name a project directory."""
    found: list[tuple[str, str]] = []
    for verb, arguments in _directives(text):
        if verb != "replace" or _ARROW not in arguments:
            continue
        arrow = arguments.index(_ARROW)
        old, new = arguments[:arrow], arguments[arrow + 1 :]
        if not old or len(new) != 1 or not new[0].startswith(_LOCAL_PREFIXES):
            continue
        target = _within(directory, new[0])
        if target is not None:
            found.append((old[0], target))
    return tuple(found)


def _module_path(text: str) -> str:
    """The path a ``go.mod``'s ``module`` line declares, or ``""`` when it has none."""
    for verb, arguments in _directives(text):
        if verb == "module" and arguments:
            return arguments[0]
    return ""


def _read(path: Path) -> str | None:
    """The text of *path*, or ``None`` when it is not a readable file."""
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _relative(root: Path, directory: Path) -> str:
    """*directory* as a project-relative POSIX path, ``""`` for the root itself."""
    relative = directory.relative_to(root).as_posix()
    return "" if relative == "." else relative


def _module(directory: str, text: str) -> GoModule:
    """The module a ``go.mod`` in *directory* with *text* declares."""
    return GoModule(_module_path(text), directory, _local_replacements(directory, text))


def _contains(ancestor: str, path: str) -> bool:
    """Whether project-relative *path* is *ancestor* or lies beneath it."""
    return ancestor == "" or path == ancestor or path.startswith(f"{ancestor}/")


class GoModules:
    """The Go modules and workspaces of one project, read once on first use."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    @cached_property
    def _declarations(self) -> dict[str, list[tuple[str, str]]]:
        """``(directory, text)`` of each ``go.mod`` and ``go.work`` the ``go`` tool would read.

        One walk of the project, taken on first use, so a project with no Go file
        never pays for it. A symbolic link is not followed, as ``./...`` does not.
        """
        found: dict[str, list[tuple[str, str]]] = {_GO_MOD: [], _GO_WORK: []}
        pending = [self._root]
        while pending:
            current = pending.pop()
            for name, declared in found.items():
                text = _read(current / name)
                if text is not None:
                    declared.append((_relative(self._root, current), text))
            try:
                children = sorted(current.iterdir())
            except OSError:
                continue
            pending.extend(
                child
                for child in children
                if child.is_dir()
                and not child.is_symlink()
                and not child.name.startswith(_IGNORED_PREFIXES)
                and child.name not in _SKIPPED_DIRECTORIES
            )
        return found

    @cached_property
    def _module_texts(self) -> dict[str, str]:
        """The text of every ``go.mod`` of the project, keyed by its directory.

        A module a ``go.work`` uses counts even where the search does not look,
        since the ``go`` command reads it from there.
        """
        found = dict(self._declarations[_GO_MOD])
        for workspace in self._workspaces:
            for used in sorted(workspace.uses - found.keys()):
                text = _read(self._root / used / _GO_MOD)
                if text is not None:
                    found[used] = text
        return found

    @cached_property
    def modules(self) -> tuple[GoModule, ...]:
        """Every module of the project, in directory order."""
        texts = self._module_texts
        return tuple(_module(directory, texts[directory]) for directory in sorted(texts))

    @cached_property
    def manifests(self) -> tuple[tuple[str, str], ...]:
        """``(path, text)`` of every ``go.mod`` and ``go.work`` an answer here rests on.

        In path order, so two readings of one tree compare equal. An import
        resolved through this reading changes its answer only when one of these
        changes, which is what makes them inputs of the files they govern
        (``beadloom-jcng``).
        """
        files = [
            (posixpath.join(directory, _GO_MOD), text)
            for directory, text in self._module_texts.items()
        ]
        files += [
            (posixpath.join(directory, _GO_WORK), text)
            for directory, text in self._declarations[_GO_WORK]
        ]
        return tuple(sorted(files))

    @cached_property
    def _workspaces(self) -> tuple[_Workspace, ...]:
        workspaces: list[_Workspace] = []
        for directory, text in self._declarations[_GO_WORK]:
            uses = {
                used
                for verb, arguments in _directives(text)
                if verb == "use" and arguments
                for used in [_within(directory, arguments[0])]
                if used is not None
            }
            workspaces.append(
                _Workspace(directory, frozenset(uses), _local_replacements(directory, text))
            )
        return tuple(workspaces)

    def governing(self, rel_path: str) -> GoModule | None:
        """The module whose ``go.mod`` is nearest at or above *rel_path*, if any."""
        holders = [m for m in self.modules if _contains(m.directory, rel_path)]
        return max(holders, key=lambda m: len(m.directory)) if holders else None

    def _workspace_of(self, module: GoModule) -> _Workspace | None:
        """The ``go.work`` nearest above *module* that uses it, if any."""
        holders = [
            w
            for w in self._workspaces
            if _contains(w.directory, module.directory) and module.directory in w.uses
        ]
        return max(holders, key=lambda w: len(w.directory)) if holders else None

    def _reachable(self, importer: GoModule) -> dict[str, str]:
        """Module path to directory, as *importer*'s module reads an import."""
        reachable: dict[str, str] = {}
        for module in self.modules:
            if module.path:
                reachable.setdefault(module.path, module.directory)
        reachable.update(importer.replacements)
        workspace = self._workspace_of(importer)
        if workspace is not None:
            reachable.update(workspace.replacements)
        reachable[importer.path] = importer.directory
        return reachable

    def package_directory(self, import_path: str, importer: str) -> str | None:
        """The project directory of the package *import_path* names, read from file *importer*.

        *importer* is the importing file's project-relative POSIX path. ``None``
        when the importer is under no module or the project holds no such package.
        """
        module = self.governing(importer)
        if module is None:
            return None
        reachable = self._reachable(module)
        matches = [path for path in reachable if path and _contains(path, import_path)]
        if not matches:
            return None
        matched = max(matches, key=len)
        root = reachable[matched]
        rest = import_path[len(matched) :].lstrip("/")
        directory = posixpath.join(root, rest) if rest else root
        return None if self._inside_a_nested_module(root, directory) else directory

    def _inside_a_nested_module(self, root: str, directory: str) -> bool:
        """Whether *directory* lies in a module nested below the module rooted at *root*."""
        return any(
            m.directory != root
            and _contains(root, m.directory)
            and _contains(m.directory, directory)
            for m in self.modules
        )
