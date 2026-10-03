"""Swift packages of a project: the targets each ``Package.swift`` declares (BDL-076 B7).

A Swift ``import`` names a module, and in a Swift Package Manager project a module
is a target: ``import BeaconCore`` names the target ``BeaconCore``, wherever its
folder is. No folder path spells that, so the module has to be looked up in the
manifest that declares it. Until B7 nothing read the manifest: ``init`` knew no
``Package.swift`` and made no node of any target (B3, ``beadloom-hmqn``).

**What is read, without running Swift.** ``Package.swift`` is a Swift program, and
this module does not execute it. It reads the calls written in it:

- a target is a call ``.target(``, ``.executableTarget(``, ``.testTarget(``,
  ``.macro(``, ``.plugin(``, ``.binaryTarget(`` or ``.systemLibrary(`` that is
  not written inside another such call — so a dependency ``.target(name: "Core")``
  in a ``dependencies:`` list is no target of its own — and that has no
  ``targets:`` argument, which is what a ``.plugin`` *product* has;
- of its arguments, ``name:`` and ``path:`` when each is one plain string literal,
  and ``dependencies:`` when it is one array literal, whose plain strings and
  ``.target(name:)``/``.byName(name:)`` entries are the target's local
  dependencies; a ``.product(...)`` entry belongs to another package and is not one;
- comments are not read, and a comment marker inside a string is text.

**What is not read:** a name or path computed by code — a variable, an
interpolated string, a target built in a loop or a function; ``exclude:`` and
``sources:``; a target appended to ``package.targets`` after the fact under a name
that is not a string literal. A target whose name cannot be read is not reported:
it is skipped, and its code belongs to no node until it is declared by hand.

**The folder of a target** is its ``path:``, read from the package's folder; else
SwiftPM's predefined one: ``Tests/<name>`` for a test target, ``Plugins/<name>``
for a plugin, and for every other kind the first of ``Sources``, ``Source``,
``src``, ``srcs`` that holds a folder ``<name>`` (``Sources/<name>`` when none
does). A binary target is a prebuilt artifact and has no folder of code, nor does a
path that leaves the project.

**The module an import names** is the target of that name in the package whose
``Package.swift`` is nearest at or above the importing file; else the one target of
that name in the project's other packages, which a local package dependency
reaches; two of them, or none, name nothing. Only a target of source code is a
module an import resolves to: a library, an executable or a macro. A test target, a
plugin, a binary target and a system library hold no Swift source another target
imports, so an import of them stays unresolved — as does every Apple framework and
every product of a package the project does not hold.

**Which manifests are read:** every ``Package.swift`` in the project, found by one
walk that skips hidden folders (``.build``, ``.swiftpm``) and the folders that hold
other people's code or build output (``node_modules``, ``Pods``, ``Carthage``,
``DerivedData``, ``vendor``, ``build``).
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
    from pathlib import Path

#: The manifest of a Swift package.
MANIFEST = "Package.swift"

#: The target kinds, as the factory methods of ``PackageDescription.Target`` name them.
KIND_TARGET = "target"
KIND_EXECUTABLE = "executableTarget"
KIND_TEST = "testTarget"
KIND_MACRO = "macro"
KIND_PLUGIN = "plugin"
KIND_BINARY = "binaryTarget"
KIND_SYSTEM_LIBRARY = "systemLibrary"
#: The kinds whose Swift source another target imports as a module.
SOURCE_MODULE_KINDS = frozenset({KIND_TARGET, KIND_EXECUTABLE, KIND_MACRO})

#: SwiftPM's predefined folders, in the order it looks for a target's folder.
_SOURCE_FOLDERS = ("Sources", "Source", "src", "srcs")
_TEST_FOLDERS = ("Tests",)
_PLUGIN_FOLDERS = ("Plugins",)

#: Folders the walk for manifests never enters, beside every hidden one.
_SKIPPED_DIRECTORIES = frozenset(
    {"node_modules", "Pods", "Carthage", "DerivedData", "vendor", "build"}
)

_TARGET_CALL = re.compile(
    r"\.(target|executableTarget|testTarget|macro|plugin|binaryTarget|systemLibrary)\s*\("
)
_DEPENDENCY_CALL = re.compile(r"\.(?:target|byName|targetItem|byNameItem)\s*\(")
_LABELLED = re.compile(r"\s*([A-Za-z_]\w*)\s*:", re.DOTALL)
_OPENERS = "([{"
_CLOSERS = ")]}"
_QUOTE = '"'
_MULTILINE_QUOTE = '"""'
_INTERPOLATION = "\\("


@dataclass(frozen=True)
class DeclaredTarget:
    """One target call of a manifest: what was written, before any folder is looked up."""

    name: str
    kind: str
    path: str | None = None
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class SwiftTarget:
    """A target with the project-relative folder of its code, ``None`` when it has none."""

    name: str
    kind: str
    directory: str | None
    dependencies: tuple[str, ...] = ()

    @property
    def is_test(self) -> bool:
        return self.kind == KIND_TEST

    @property
    def is_source_module(self) -> bool:
        """Whether an import of this target names Swift source of the project."""
        return self.kind in SOURCE_MODULE_KINDS


@dataclass(frozen=True)
class SwiftPackage:
    """One ``Package.swift``: its project-relative folder (``""`` for the root) and targets."""

    directory: str
    targets: tuple[SwiftTarget, ...]

    def target(self, name: str) -> SwiftTarget | None:
        return next((target for target in self.targets if target.name == name), None)


# --- Reading one manifest ----------------------------------------------------


def _string_end(text: str, start: int) -> int:
    """The index just past the string literal opening at *start*."""
    if text.startswith(_MULTILINE_QUOTE, start):
        end = text.find(_MULTILINE_QUOTE, start + len(_MULTILINE_QUOTE))
        return len(text) if end < 0 else end + len(_MULTILINE_QUOTE)
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char in (_QUOTE, "\n"):
            return index + 1
        index += 1
    return index


def _comment_end(text: str, start: int) -> int:
    """The index just past the comment opening at *start* (block comments nest in Swift)."""
    if text.startswith("//", start):
        end = text.find("\n", start)
        return len(text) if end < 0 else end
    depth, index = 0, start
    while index < len(text):
        if text.startswith("/*", index):
            depth, index = depth + 1, index + 2
        elif text.startswith("*/", index):
            depth, index = depth - 1, index + 2
            if depth == 0:
                return index
        else:
            index += 1
    return index


def _blank(fragment: str) -> str:
    """*fragment* with every character but a line break turned into a space."""
    return re.sub(r"[^\n]", " ", fragment)


def _readings(text: str) -> tuple[str, str]:
    """The manifest without comments, and the same with string contents blanked too.

    Both keep every character's position, so a call found in the second — where no
    string can hold a parenthesis or a comma — is read from the first.
    """
    code: list[str] = []
    shape: list[str] = []
    index = 0
    while index < len(text):
        if text[index] == _QUOTE:
            end = _string_end(text, index)
            literal = text[index:end]
            code.append(literal)
            shape.append(_QUOTE + _blank(literal[1:-1]) + _QUOTE if len(literal) > 1 else literal)
        elif text.startswith(("//", "/*"), index):
            end = _comment_end(text, index)
            code.append(_blank(text[index:end]))
            shape.append(_blank(text[index:end]))
        else:
            end = index + 1
            code.append(text[index])
            shape.append(text[index])
        index = end
    return "".join(code), "".join(shape)


def _closing(shape: str, opening: int) -> int:
    """The index of the bracket closing the one at *opening* (or the end of the text)."""
    depth = 0
    for index in range(opening, len(shape)):
        if shape[index] in _OPENERS:
            depth += 1
        elif shape[index] in _CLOSERS:
            depth -= 1
            if depth == 0:
                return index
    return len(shape)


def _items(shape: str, start: int, end: int) -> list[tuple[int, int]]:
    """The ``(start, end)`` of each comma-separated item between *start* and *end*."""
    items: list[tuple[int, int]] = []
    depth, begin = 0, start
    for index in range(start, end):
        char = shape[index]
        if char in _OPENERS:
            depth += 1
        elif char in _CLOSERS:
            depth -= 1
        elif char == "," and depth == 0:
            items.append((begin, index))
            begin = index + 1
    if shape[begin:end].strip():
        items.append((begin, end))
    return items


def _first_visible(shape: str, start: int, end: int) -> int:
    """The index of the first character between *start* and *end* that is not blank."""
    return start + len(shape[start:end]) - len(shape[start:end].lstrip())


def _arguments(shape: str, start: int, end: int) -> dict[str, tuple[int, int]]:
    """Each labelled argument between *start* and *end*: its label and its value's span."""
    labelled: dict[str, tuple[int, int]] = {}
    for begin, finish in _items(shape, start, end):
        match = _LABELLED.match(shape, begin, finish)
        if match is not None:
            labelled[match.group(1)] = (match.end(), finish)
    return labelled


def _string(code: str, shape: str, span: tuple[int, int] | None) -> str | None:
    """The value of one plain string literal at *span*, else ``None``."""
    if span is None:
        return None
    written, outline = code[span[0] : span[1]].strip(), shape[span[0] : span[1]].strip()
    if len(outline) < 2 or outline[0] != _QUOTE or outline[-1] != _QUOTE:
        return None
    if _QUOTE in outline[1:-1] or outline.startswith(_MULTILINE_QUOTE):
        return None
    value = written[1:-1]
    return None if _INTERPOLATION in value or not value else value


def _dependencies(code: str, shape: str, span: tuple[int, int] | None) -> tuple[str, ...]:
    """The local target names an array literal of dependencies at *span* holds."""
    if span is None:
        return ()
    begin = _first_visible(shape, *span)
    if begin >= span[1] or shape[begin] != "[":
        return ()
    names: list[str] = []
    for start, end in _items(shape, begin + 1, _closing(shape, begin)):
        name = _string(code, shape, (start, end))
        call = _DEPENDENCY_CALL.match(shape, _first_visible(shape, start, end), end)
        if name is None and call is not None:
            opening = call.end() - 1
            arguments = _arguments(shape, opening + 1, _closing(shape, opening))
            name = _string(code, shape, arguments.get("name"))
        if name is not None:
            names.append(name)
    return tuple(names)


def declared_targets(text: str) -> tuple[DeclaredTarget, ...]:
    """The targets the manifest *text* declares, in the order written (see the docstring)."""
    code, shape = _readings(text)
    targets: list[DeclaredTarget] = []
    seen: set[str] = set()
    consumed = 0
    for call in _TARGET_CALL.finditer(shape):
        if call.start() < consumed:
            continue
        opening = call.end() - 1
        closing = _closing(shape, opening)
        consumed = closing
        arguments = _arguments(shape, opening + 1, closing)
        name = _string(code, shape, arguments.get("name"))
        if name is None or "targets" in arguments or name in seen:
            continue
        seen.add(name)
        targets.append(
            DeclaredTarget(
                name=name,
                kind=call.group(1),
                path=_string(code, shape, arguments.get("path")),
                dependencies=_dependencies(code, shape, arguments.get("dependencies")),
            )
        )
    return tuple(targets)


# --- The project's packages --------------------------------------------------


def _within(directory: str, target: str) -> str | None:
    """*target* read from *directory*, as a project-relative folder; ``None`` outside it."""
    if target.startswith("/"):
        return None
    joined = posixpath.normpath(posixpath.join(directory or ".", target))
    if joined == ".." or joined.startswith("../"):
        return None
    return "" if joined == "." else joined


def _contains(ancestor: str, path: str) -> bool:
    return ancestor == "" or path == ancestor or path.startswith(f"{ancestor}/")


def _predefined_folders(kind: str) -> tuple[str, ...]:
    if kind == KIND_TEST:
        return _TEST_FOLDERS
    if kind == KIND_PLUGIN:
        return _PLUGIN_FOLDERS
    return _SOURCE_FOLDERS


class SwiftPackages:
    """The Swift packages of one project, read once on first use."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    @cached_property
    def packages(self) -> tuple[SwiftPackage, ...]:
        """Every package of the project, in folder order."""
        found: list[SwiftPackage] = []
        for directory in self._manifest_directories():
            try:
                text = (self._root / directory / MANIFEST).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            targets = tuple(
                SwiftTarget(
                    declared.name,
                    declared.kind,
                    self._directory(directory, declared),
                    declared.dependencies,
                )
                for declared in declared_targets(text)
            )
            found.append(SwiftPackage(directory, targets))
        return tuple(found)

    def _manifest_directories(self) -> list[str]:
        """The project-relative folder of every ``Package.swift``, sorted."""
        found: list[str] = []
        pending = [self._root]
        while pending:
            current = pending.pop()
            if (current / MANIFEST).is_file():
                relative = current.relative_to(self._root).as_posix()
                found.append("" if relative == "." else relative)
            try:
                children = list(current.iterdir())
            except OSError:
                continue
            pending.extend(
                child
                for child in children
                if child.is_dir()
                and not child.is_symlink()
                and not child.name.startswith(".")
                and child.name not in _SKIPPED_DIRECTORIES
            )
        return sorted(found)

    def _directory(self, package: str, declared: DeclaredTarget) -> str | None:
        """The folder of *declared*'s code (see the module docstring)."""
        if declared.kind == KIND_BINARY:
            return None
        if declared.path is not None:
            return _within(package, declared.path)
        folders = _predefined_folders(declared.kind)
        for folder in folders:
            candidate = posixpath.join(package, folder, declared.name)
            if (self._root / candidate).is_dir():
                return candidate
        return posixpath.join(package, folders[0], declared.name)

    def governing(self, rel_path: str) -> SwiftPackage | None:
        """The package whose ``Package.swift`` is nearest at or above *rel_path*, if any."""
        holders = [p for p in self.packages if _contains(p.directory, rel_path)]
        return max(holders, key=lambda p: len(p.directory)) if holders else None

    def declares(self, module: str) -> bool:
        """Whether any manifest of the project declares a target named *module*."""
        return any(package.target(module) is not None for package in self.packages)

    def module_directory(self, import_path: str, importer: str) -> str | None:
        """The folder of the module *import_path* names, read from the file *importer*.

        ``import Core.Route`` names the module ``Core``. ``None`` for a module the
        project holds no source of (see the module docstring).
        """
        module = import_path.split(".", 1)[0]
        own = self.governing(importer)
        target = own.target(module) if own is not None else None
        if target is None:
            elsewhere = [
                found
                for package in self.packages
                if package is not own
                for found in [package.target(module)]
                if found is not None
            ]
            target = elsewhere[0] if len(elsewhere) == 1 else None
        return target.directory if target is not None and target.is_source_module else None
