# beadloom:domain=application
# beadloom:component=typed-surface
"""The surface a project declares typed, derived from its own mypy declaration.

A type check is a claim about the files it was handed. Hand it more than the
project declares typed and every commit is red for reasons nobody signed up to;
the one commit that carries a genuine violation prints the same sentence as the
rest and is scrolled past with them. This repository measured that: the
pre-commit hook ran ``mypy`` over every staged ``.py`` under ``src/`` or
``tests/`` while ``pyproject`` declares ``packages = ["beadloom"]``, and
``uv run mypy tests/`` reports 970 errors in 90 files -- not one of them a
violation of anything the project claims. Over the 24 commits of
``features/BDL-068`` the hook warned on 4 of the 7 that staged Python, and all
4 warnings were false.

**The surface is DERIVED, never listed.** ``beadloom-mr2l.82`` was the first
attempt at this and shipped a hand-written surface in the hook template. The
mypy configuration then moved and the hook did not. A second list is a second
thing to forget, which is the class this epic exists to remove.

**What could not be resolved is part of the answer.** A derivation that drops
what it could not read hands back a clean list, and a clean list is trusted and
stopped at. A package that resolves to no directory, an ``exclude`` pattern this
derivation does not apply, a ``mypy.ini`` beside a ``pyproject.toml`` that
declares nothing -- each is reported with its reason rather than omitted.

**A surface that could not be derived is NOT CHECKED, never "everything".**
Falling back to checking whatever was staged is the behaviour being removed, and
falling back to checking nothing while saying nothing is the phantom gate this
epic is named for. The caller gets a reason and prints it.

**The declaration is read without a TOML parser**, for the reason
``application/rooms.py`` states about the packaging metadata: ``tomllib`` is
3.11+ and ``tomli`` is not a runtime dependency, so a parse answers differently
on 3.10 than on 3.13. A module whose subject is *what a check actually covers*
must not have a room-dependent answer. The keys read here are a handful of
string arrays and two scalars out of one known section; anything in that section
this reader cannot turn into a surface is reported, not assumed away.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

#: ``[tool.mypy]`` up to the next table header. ``[[tool.mypy.overrides]]`` is a
#: different table and is deliberately outside the match: an override changes
#: which findings are reported, never which files are in the surface.
_SECTION_RE = re.compile(
    r"^\[tool\.mypy\]\s*$(?P<body>.*?)(?=^\[)", re.MULTILINE | re.DOTALL
)

#: The same header when it is the last table in the file, so there is no next
#: ``[`` to stop at.
_TRAILING_SECTION_RE = re.compile(r"^\[tool\.mypy\]\s*$(?P<body>.*)", re.MULTILINE | re.DOTALL)

#: A double- or single-quoted TOML basic string. Enough for the keys read here,
#: which are package names and paths; a multi-line literal in one of them is
#: reported unresolved rather than half-read.
_STRING_RE = re.compile(r"""(["'])(?P<value>(?:(?!\1).)*)\1""")

#: The keys of ``[tool.mypy]`` that name a surface, in the order mypy documents
#: them. All three may appear; each contributes its own roots.
_SURFACE_KEYS = ("packages", "modules", "files")

#: Separators mypy accepts inside ``mypy_path``.
_MYPY_PATH_SPLIT = re.compile(r"[:,]")

#: Characters that make a ``files`` entry a glob rather than a path.
_GLOB_CHARS = frozenset("*?[")

#: Declaration files this derivation does NOT read. Their presence is reported
#: so an adopter is told why the answer is empty rather than left to guess.
_UNREAD_DECLARATIONS = ("mypy.ini", ".mypy.ini", "setup.cfg", "tox.ini")


@dataclass(frozen=True)
class SurfaceRoot:
    """One directory or module the declaration puts inside the typed surface.

    ``source`` names the declaration rather than this module, so a reader who
    disagrees with the surface goes and edits the thing that decides it.
    """

    path: str
    source: str


@dataclass(frozen=True)
class Unresolved:
    """Something in the declaration this derivation could not turn into a root."""

    source: str
    why: str


@dataclass(frozen=True)
class TypedSurface:
    """What a project declares typed, and what the derivation could not resolve."""

    roots: tuple[SurfaceRoot, ...] = ()
    unresolved: tuple[Unresolved, ...] = ()
    why_undeclared: str | None = None

    @property
    def declared(self) -> bool:
        """True when at least one root was resolved from the declaration."""
        return bool(self.roots)

    @property
    def label(self) -> str:
        """The roots, in a stable order, for a one-line verdict."""
        return ", ".join(sorted(root.path for root in self.roots))

    def contains(self, path: str) -> bool:
        """Is ``path`` (project-relative, POSIX) inside a declared root?

        A root that is a module file matches only itself; a root that is a
        directory matches itself and everything under it. The comparison is over
        path SEGMENTS, so ``src/beadloom_extra`` is not inside ``src/beadloom``.
        """
        candidate = PurePosixPath(path.replace("\\", "/"))
        for root in self.roots:
            expected = PurePosixPath(root.path)
            if candidate == expected or expected in candidate.parents:
                return True
        return False

    def partition(self, paths: tuple[str, ...]) -> SurfacePartition:
        """Split staged paths into the ones this surface covers and the rest."""
        inside = tuple(p for p in paths if self.contains(p))
        return SurfacePartition(
            inside=inside,
            outside=tuple(p for p in paths if p not in set(inside)),
            surface=self,
        )


@dataclass(frozen=True)
class SurfacePartition:
    """Staged paths held against a declared surface, and the sentence for it."""

    inside: tuple[str, ...]
    outside: tuple[str, ...]
    surface: TypedSurface

    def describe(self) -> str:
        """One line stating the population, in the three states it has.

        The three are deliberately different sentences. A surface that could not
        be derived, a surface with nothing staged inside it and a surface with
        files to check are three different facts, and a check whose population
        is empty reading as a check that passed is the defect this replaces.
        """
        if not self.surface.declared:
            why = self.surface.why_undeclared or "the declaration could not be read"
            return f"Typed surface: NOT CHECKED -- {why}"
        total = len(self.inside) + len(self.outside)
        where = f"Typed surface ({self.surface.label})"
        if not self.inside:
            return (
                f"{where}: NOTHING TO CHECK -- 0 of {total} staged Python "
                f"file(s) are inside it, {len(self.outside)} outside."
            )
        return (
            f"{where}: {len(self.inside)} of {total} staged Python file(s) "
            f"inside it, {len(self.outside)} outside."
        )


def declared_typed_surface(project_root: Path) -> TypedSurface:
    """Derive the typed surface from ``pyproject.toml``'s ``[tool.mypy]``.

    Never raises: an unreadable, absent or silent declaration comes back as a
    surface that is not declared, carrying the reason it is not.
    """
    pyproject = project_root / "pyproject.toml"
    if not pyproject.is_file():
        return TypedSurface(
            why_undeclared=(
                f"no pyproject.toml in {project_root.name or project_root}, so "
                "no [tool.mypy] surface could be read"
            ),
            unresolved=_unread_declarations(project_root),
        )
    try:
        text = pyproject.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return TypedSurface(
            why_undeclared=f"pyproject.toml could not be read: {exc}",
            unresolved=_unread_declarations(project_root),
        )
    section = _mypy_section(text)
    if section is None:
        return TypedSurface(
            why_undeclared="pyproject.toml declares no [tool.mypy] section",
            unresolved=_unread_declarations(project_root),
        )
    return _resolve(project_root, section)


def _mypy_section(text: str) -> str | None:
    """The body of ``[tool.mypy]``, or ``None`` when the table is absent."""
    match = _SECTION_RE.search(text) or _TRAILING_SECTION_RE.search(text)
    return match.group("body") if match else None


def _resolve(project_root: Path, section: str) -> TypedSurface:
    """Turn one ``[tool.mypy]`` body into roots plus what it could not resolve."""
    search_dirs = _search_dirs(section)
    roots: list[SurfaceRoot] = []
    unresolved: list[Unresolved] = list(_unread_declarations(project_root))
    declared_any = False
    for key in _SURFACE_KEYS:
        values = _string_list(section, key)
        if not values:
            continue
        declared_any = True
        for value in values:
            resolve = _resolve_path if key == "files" else _resolve_module
            root, problem = resolve(project_root, value, search_dirs, key)
            if root is not None:
                roots.append(root)
            if problem is not None:
                unresolved.append(problem)
    unresolved.extend(_narrowing_keys(section))
    why = None if roots else _why_no_root(declared_any)
    return TypedSurface(
        roots=tuple(roots), unresolved=tuple(unresolved), why_undeclared=why
    )


def _why_no_root(declared_any: bool) -> str:
    if declared_any:
        return (
            "[tool.mypy] names a surface, and none of its entries resolves to a "
            "path in this project"
        )
    return "[tool.mypy] names no packages, modules or files, so it declares no surface"


def _search_dirs(section: str) -> tuple[str, ...]:
    """``mypy_path`` entries, plus the project root mypy always searches."""
    raw = _string_list(section, "mypy_path") or []
    parts = [p.strip() for entry in raw for p in _MYPY_PATH_SPLIT.split(entry)]
    return (*[p for p in parts if p], ".")


def _resolve_module(
    project_root: Path, name: str, search_dirs: tuple[str, ...], key: str
) -> tuple[SurfaceRoot | None, Unresolved | None]:
    """Resolve a dotted package/module name against the search path."""
    relative = PurePosixPath(*name.split("."))
    for search in search_dirs:
        base = PurePosixPath(search) / relative if search != "." else relative
        if (project_root / base).is_dir():
            return SurfaceRoot(str(base), f"[tool.mypy] {key} = {name!r}"), None
        module = base.with_suffix(".py")
        if (project_root / module).is_file():
            return SurfaceRoot(str(module), f"[tool.mypy] {key} = {name!r}"), None
    return None, Unresolved(
        source=f"[tool.mypy] {key} = {name!r}",
        why=(
            f"no directory or .py module for `{name}` under "
            f"{', '.join(search_dirs)}"
        ),
    )


def _resolve_path(
    project_root: Path, entry: str, search_dirs: tuple[str, ...], key: str
) -> tuple[SurfaceRoot | None, Unresolved | None]:
    """Resolve a ``files`` entry, which is a path or a glob under the root."""
    source = f"[tool.mypy] {key} = {entry!r}"
    if _GLOB_CHARS & set(entry):
        matches = sorted(project_root.glob(entry))
        if not matches:
            return None, Unresolved(source, f"the glob `{entry}` matches nothing here")
        if len(matches) > 1:
            return None, Unresolved(
                source,
                f"the glob `{entry}` matches {len(matches)} paths; this "
                "derivation resolves a glob only when it names one root",
            )
        entry = matches[0].relative_to(project_root).as_posix()
    normalised = PurePosixPath(entry.strip("/"))
    if (project_root / normalised).exists():
        return SurfaceRoot(str(normalised), source), None
    return None, Unresolved(source, f"`{entry}` does not exist in this project")


def _narrowing_keys(section: str) -> tuple[Unresolved, ...]:
    """Declared keys that narrow the surface and are not applied here.

    ``exclude`` is not applied because mypy itself does not apply it to files
    named on the command line, which is how the hook invokes it. Stating that is
    the difference between a surface that is slightly wide and one that is wide
    for a reason nobody wrote down.
    """
    if _string_list(section, "exclude") is None and _scalar(section, "exclude") is None:
        return ()
    return (
        Unresolved(
            source="[tool.mypy] exclude",
            why=(
                "an exclude pattern is declared and is not applied here, because "
                "mypy does not apply it to files named on the command line; a "
                "path it excludes is still reported inside the surface"
            ),
        ),
    )


def _unread_declarations(project_root: Path) -> tuple[Unresolved, ...]:
    """Configuration files that can declare a mypy surface and are not read."""
    return tuple(
        Unresolved(
            source=name,
            why=(
                f"{name} can declare a mypy surface and this derivation reads "
                "only pyproject.toml's [tool.mypy]"
            ),
        )
        for name in _UNREAD_DECLARATIONS
        if (project_root / name).is_file()
    )


def _string_list(section: str, key: str) -> list[str] | None:
    """The strings of ``key = [...]``, or ``[key]`` written as a bare string.

    ``None`` means the key is absent; an empty list means it is present and
    declares nothing, which is a different fact and is reported as one.
    """
    array = re.search(
        rf"^\s*{re.escape(key)}\s*=\s*\[(?P<body>.*?)\]",
        section,
        re.MULTILINE | re.DOTALL,
    )
    if array is not None:
        return [m.group("value") for m in _STRING_RE.finditer(array.group("body"))]
    scalar = _scalar(section, key)
    return None if scalar is None else [scalar]


def _scalar(section: str, key: str) -> str | None:
    """The value of ``key = "…"``, or ``None`` when it is not a plain string."""
    match = re.search(
        rf"""^\s*{re.escape(key)}\s*=\s*(["'])(?P<value>(?:(?!\1).)*)\1\s*$""",
        section,
        re.MULTILINE,
    )
    return match.group("value") if match else None
