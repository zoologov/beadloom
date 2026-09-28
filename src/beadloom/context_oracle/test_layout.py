# beadloom:domain=context-oracle
# beadloom:feature=test-mapping
"""Test layout: where a project keeps its tests, and which files are tests.

Read from the ``tests:`` block of ``.beadloom/config.yml`` (BDL-074 G2), with a
default for every key, because the binding was otherwise true of one layout only.
Review ``beadloom-b9ll`` M3 measured it: a Go module with a test beside each
package read ``none, 0 tests`` where the name-guessing mapper had read ``go_test,
1 tests``, and the same held for a Python project keeping its tests in ``test/``
or beside the code.

- ``roots`` — the folders tests are laid out in by kind, ``<root>/<kind>/...``.
  Default ``[tests]``. A declared list replaces the default.
- ``patterns`` — file-name patterns grouped by the framework they name. A file
  is a test when its name matches one, and its framework is that group's name.
  Default ``pytest`` (``test_*.py``, ``*_test.py``), ``go_test`` (``*_test.go``)
  and ``jest`` (``*.test.*``, ``*.spec.*``). A declared mapping replaces all
  three, because it states which frameworks the project has.
- ``kinds`` — the folder each kind is laid out in under a root. Default: each
  kind's own name. A declared entry replaces that one kind, so the population
  line can say which folder was declared and which is the default (review m4).
- ``beside_code`` — whether a test file inside the code, outside every root,
  binds to the node whose source covers it. Default ``true``. A project whose
  code has modules named like tests (this one has five ``test_*.py`` modules
  under ``src/``) switches it off, because a file name cannot tell a test module
  from a module about tests.

A declaration that cannot be used is reported and the default stands for it: a
layout that silently fell back would bind a project's tests by a rule it did not
write. Pure apart from :func:`load_test_layout`, which reads the file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, TypeGuard

import yaml

from beadloom.infrastructure.repository import KIND_ACCEPTANCE as KIND_ACCEPTANCE
from beadloom.infrastructure.repository import KIND_SELF_CHECK as KIND_SELF_CHECK
from beadloom.infrastructure.repository import RecordedTestLayout

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

#: Where the layout is declared, relative to the project root.
CONFIG_PATH = ".beadloom/config.yml"
#: The block of that file this module reads.
CONFIG_KEY = "tests"

#: A kind whose path under its folder mirrors the code it tests.
KIND_UNIT = "unit"
KIND_INTEGRATION = "integration"
MIRRORED_KINDS = frozenset({KIND_UNIT, KIND_INTEGRATION})
#: Every kind a folder can hold, in the order they are stated.
KINDS = (KIND_ACCEPTANCE, KIND_INTEGRATION, KIND_SELF_CHECK, KIND_UNIT)

DEFAULT_ROOTS = ("tests",)
#: The owner's ruling of 2026-09-28: Python, Go and JS/TS, each named for the
#: framework its patterns belong to.
DEFAULT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pytest", ("test_*.py", "*_test.py")),
    ("go_test", ("*_test.go",)),
    ("jest", ("*.test.*", "*.spec.*")),
)


@dataclass(frozen=True)
class TestLayout:
    """Where tests live and what makes a file one; see the module docstring."""

    __test__ = False  # a product type, not a pytest test class

    roots: tuple[str, ...] = DEFAULT_ROOTS
    patterns: tuple[tuple[str, tuple[str, ...]], ...] = DEFAULT_PATTERNS
    kind_folders: tuple[tuple[str, str], ...] = tuple((kind, kind) for kind in KINDS)
    declared_kinds: frozenset[str] = field(default_factory=frozenset)
    beside_code: bool = True

    def framework_of(self, name: str) -> str | None:
        """The framework whose pattern the file NAME matches first, or ``None``."""
        for framework, patterns in self.patterns:
            if any(fnmatchcase(name, pattern) for pattern in patterns):
                return framework
        return None

    def is_test_file(self, name: str) -> bool:
        """Whether a file NAME matches any pattern of any framework."""
        return self.framework_of(name) is not None

    def folder_of(self, kind: str) -> str:
        """The folder *kind* is laid out in under a root."""
        return dict(self.kind_folders)[kind]

    def kind_prefixes(self, kind: str) -> tuple[str, ...]:
        """*kind*'s folder under every root, as ``root/folder/``."""
        return tuple(f"{root}/{self.folder_of(kind)}/" for root in self.roots)

    def locate(self, path: str) -> tuple[str | None, str] | None:
        """Where *path* sits: ``None`` under no root, else its kind and the path below it.

        A file under a root but in no kind folder, or directly in one, has kind
        ``None`` and an empty rest: the layout has not reached it.
        """
        for root in self.roots:
            prefix = f"{root}/"
            if not path.startswith(prefix):
                continue
            parts = PurePosixPath(path[len(prefix) :]).parts
            kinds = {folder: kind for kind, folder in self.kind_folders}
            if len(parts) < 2 or parts[0] not in kinds:
                return None, ""
            return kinds[parts[0]], "/".join(parts[1:])
        return None

    def recorded(self) -> RecordedTestLayout:
        """The record the index keeps of this layout, for readers that may not import it."""
        return RecordedTestLayout(
            kind_prefixes={kind: self.kind_prefixes(kind) for kind in KINDS},
            declared_kinds=self.declared_kinds,
            beside_code=self.beside_code,
            roots=self.roots,
            frameworks=tuple(framework for framework, _ in self.patterns),
        )


def load_test_layout(project_root: Path) -> tuple[TestLayout, list[str]]:
    """The layout *project_root* declares, and a sentence for each unusable part of it."""
    config_path = project_root / CONFIG_PATH
    if not config_path.is_file():
        return TestLayout(), []
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return TestLayout(), [f"{CONFIG_PATH} could not be read; the default test layout is used"]
    return layout_from_config(config if isinstance(config, dict) else {})


def layout_from_config(config: Mapping[str, object]) -> tuple[TestLayout, list[str]]:
    """The layout a parsed config mapping declares, and what about it was unusable."""
    block = config.get(CONFIG_KEY)
    if block is None:
        return TestLayout(), []
    if not isinstance(block, dict):
        return TestLayout(), [
            f"`{CONFIG_KEY}` in {CONFIG_PATH} must be a mapping; the default test layout is used"
        ]
    problems: list[str] = []
    kind_folders, declared = _kinds(block.get("kinds"), problems)
    layout = TestLayout(
        roots=_roots(block.get("roots"), problems),
        patterns=_patterns(block.get("patterns"), problems),
        kind_folders=kind_folders,
        declared_kinds=declared,
        beside_code=_beside_code(block.get("beside_code"), problems),
    )
    return layout, problems


def _is_names(value: object) -> TypeGuard[list[str]]:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _roots(value: object, problems: list[str]) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_ROOTS
    if not _is_names(value):
        problems.append(
            f"`{CONFIG_KEY}.roots` in {CONFIG_PATH} must be a list of folders; "
            f"the default ({', '.join(DEFAULT_ROOTS)}) is used"
        )
        return DEFAULT_ROOTS
    return tuple(root.strip().strip("/") for root in value)


def _patterns(value: object, problems: list[str]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if value is None:
        return DEFAULT_PATTERNS
    if (
        not isinstance(value, dict)
        or not value
        or not all(
            isinstance(name, str) and _is_names(patterns) for name, patterns in value.items()
        )
    ):
        problems.append(
            f"`{CONFIG_KEY}.patterns` in {CONFIG_PATH} must map each framework name to a "
            "list of file-name patterns; the default (pytest, go_test, jest) is used"
        )
        return DEFAULT_PATTERNS
    return tuple(
        (str(name), tuple(str(pattern).strip() for pattern in patterns))
        for name, patterns in value.items()
    )


def _kinds(
    value: object, problems: list[str]
) -> tuple[tuple[tuple[str, str], ...], frozenset[str]]:
    folders = {kind: kind for kind in KINDS}
    if value is None:
        return tuple(folders.items()), frozenset()
    if not isinstance(value, dict):
        problems.append(
            f"`{CONFIG_KEY}.kinds` in {CONFIG_PATH} must map a kind to its folder; "
            "every kind keeps its default folder"
        )
        return tuple(folders.items()), frozenset()
    declared: set[str] = set()
    for kind, folder in value.items():
        if kind not in folders:
            problems.append(
                f"`{CONFIG_KEY}.kinds.{kind}` in {CONFIG_PATH} names no kind Beadloom knows "
                f"({', '.join(KINDS)}); it is ignored"
            )
        elif not isinstance(folder, str) or not folder.strip("/ "):
            problems.append(
                f"`{CONFIG_KEY}.kinds.{kind}` in {CONFIG_PATH} must be one folder name; "
                f"the default ({kind}) is used"
            )
        else:
            folders[kind] = folder.strip("/ ")
            declared.add(kind)
    return tuple(folders.items()), frozenset(declared)


def _beside_code(value: object, problems: list[str]) -> bool:
    if value is None:
        return True
    if not isinstance(value, bool):
        problems.append(
            f"`{CONFIG_KEY}.beside_code` in {CONFIG_PATH} must be true or false; "
            "the default (true) is used"
        )
        return True
    return value
