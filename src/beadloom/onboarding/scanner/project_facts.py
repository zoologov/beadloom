"""What the TARGET project declares about itself — read from its own manifests.

Separate from :mod:`beadloom.onboarding.scanner.claude_md` on purpose. That
module's one responsibility is *rendering a marked region*; this one's is
*reading a fact out of somebody else's project*, and the two failed together
once already: the version bullet in the composed ``CLAUDE.md`` was filled from
:func:`beadloom.application.doctor.get_actual_version`, which returns
**Beadloom's** ``__version__`` — correctly, since it exists to diagnose
Beadloom's own drift (BDL-UX #92) — and rendered it inside the section
describing the *adopter's* project (BDL-UX #183).

Two rules hold everywhere in here:

* **Read the project, never ourselves.** Nothing in this module may consult
  ``beadloom.__version__``, our package layout, or anything else true of this
  repository. Every returned value comes from a file under ``project_root``.
* **Unknown is not zero.** A fact that cannot be determined is ``None`` and the
  caller renders nothing. A plausible-looking substitute is worse than a gap,
  because a gap is visibly a gap and a substitute is read as measured.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

#: ``version = "1.2.3"`` in a TOML table, captured. Deliberately a regex rather
#: than a TOML parse: ``tomllib`` is 3.11+, this package supports 3.10, and the
#: only thing needed is one scalar out of one known table.
_TOML_VERSION_RE = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

#: Tables whose ``version`` key declares the project's own version, in the order
#: a Python project declares them. ``[tool.poetry]`` is included because Poetry
#: projects have no ``[project]`` table at all.
_PYPROJECT_TABLES: tuple[str, ...] = ("[project]", "[tool.poetry]")


def _table_body(text: str, table: str) -> str | None:
    """The body of ``table`` in a TOML document, or ``None`` when it is absent."""
    start = text.find(f"\n{table}")
    if start == -1 and not text.startswith(table):
        return None
    if start == -1:
        start = 0
    else:
        start += 1
    body_start = start + len(table)
    next_table = re.search(r"^\[", text[body_start:], re.MULTILINE)
    end = body_start + next_table.start() if next_table else len(text)
    return text[body_start:end]


def _read(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Unreadable is unknown, not absent — but the caller's only honest
        # action is the same one either way: render nothing.
        return None


def _pyproject_version(project_root: Path) -> str | None:
    text = _read(project_root / "pyproject.toml")
    if text is None:
        return None
    for table in _PYPROJECT_TABLES:
        body = _table_body(text, table)
        if body is None:
            continue
        match = _TOML_VERSION_RE.search(body)
        if match is not None:
            return match.group(1)
    return None


def _package_json_version(project_root: Path) -> str | None:
    text = _read(project_root / "package.json")
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    version = data.get("version")
    return version if isinstance(version, str) and version else None


def _cargo_version(project_root: Path) -> str | None:
    text = _read(project_root / "Cargo.toml")
    if text is None:
        return None
    body = _table_body(text, "[package]")
    if body is None:
        return None
    match = _TOML_VERSION_RE.search(body)
    return match.group(1) if match is not None else None


#: ``__version__ = "1.2.3"`` in a Python module, captured.
_DUNDER_VERSION_RE = re.compile(
    r'^\s*__version__\s*[:=][^=]*?["\']([^"\']+)["\']', re.MULTILINE
)


def _dynamic_python_version(project_root: Path) -> str | None:
    """A ``dynamic = ["version"]`` project's version, read from where it points.

    ``[tool.hatch.version] path`` and ``[tool.setuptools.dynamic] version =
    {attr = ...}`` both keep the version in the package rather than in the
    manifest. That is a declaration, not an absence — Beadloom's own
    ``pyproject.toml`` is this shape — so treating it as unknown would make the
    common modern Python layout unreadable for no gain in honesty.

    The path is resolved **under** ``project_root`` and a traversal out of the
    tree is refused: the manifest is the target project's own text, and reading
    an arbitrary absolute path it names is not something this module does.
    """
    text = _read(project_root / "pyproject.toml")
    if text is None:
        return None
    candidates: list[str] = []
    hatch = _table_body(text, "[tool.hatch.version]")
    if hatch is not None:
        match = re.search(r'^\s*path\s*=\s*["\']([^"\']+)["\']', hatch, re.MULTILINE)
        if match is not None:
            candidates.append(match.group(1))
    setuptools = _table_body(text, "[tool.setuptools.dynamic]")
    if setuptools is not None:
        match = re.search(r'attr\s*=\s*["\']([\w.]+)["\']', setuptools)
        if match is not None:
            module = match.group(1).rsplit(".", 1)[0].replace(".", "/")
            candidates.extend([f"src/{module}/__init__.py", f"{module}/__init__.py"])
    for relative in candidates:
        target = (project_root / relative).resolve()
        if not target.is_relative_to(project_root.resolve()):
            continue
        module_text = _read(target)
        if module_text is None:
            continue
        match = _DUNDER_VERSION_RE.search(module_text)
        if match is not None:
            return match.group(1)
    return None


#: Manifest readers, tried in order. The order is the ecosystems' own
#: precedence in a polyglot repo (a Python package that also ships a JS client
#: declares the shipped artifact's version in ``pyproject.toml``).
_VERSION_READERS = (
    _pyproject_version,
    _dynamic_python_version,
    _package_json_version,
    _cargo_version,
)


def detect_project_version(project_root: Path) -> str | None:
    """The version ``project_root`` declares about itself, or ``None``.

    Reads ``pyproject.toml`` (``[project]``, ``[tool.poetry]``, then a
    ``dynamic`` version through ``[tool.hatch.version]`` /
    ``[tool.setuptools.dynamic]``), ``package.json`` and ``Cargo.toml``, in that
    order.

    Returns ``None`` — never a guess, and never Beadloom's own version — when
    the project declares no version Beadloom can read. A VCS tag is
    deliberately *not* consulted: a tag is a release marker on a commit rather
    than a statement the project makes about itself, and reading one would need
    the infrastructure layer that ``onboarding`` is forbidden to import.
    """
    for reader in _VERSION_READERS:
        version = reader(project_root)
        if version is not None:
            return version
    return None


def detect_source_packages(project_root: Path) -> set[str]:
    """Top-level package directories under ``<project_root>/src/<pkg>/``.

    A package is a directory with an ``__init__.py``; its children with one are
    the project's own top-level modules. Purely a scan of the *target* tree —
    the previous implementation fell back to a helper that looked for
    ``src/beadloom/`` inside the adopter's repository, which could only ever
    find something in this one (BDL-UX #183's sweep).
    """
    packages: set[str] = set()
    src_dir = project_root / "src"
    if not src_dir.is_dir():
        return packages
    for pkg_root in src_dir.iterdir():
        if not (pkg_root.is_dir() and (pkg_root / "__init__.py").is_file()):
            continue
        for child in pkg_root.iterdir():
            if child.is_dir() and (child / "__init__.py").is_file():
                packages.add(child.name)
    return packages


#: Manifests a project declares itself through. Concatenated (never parsed as a
#: whole) to answer "does this project mention <tool> anywhere it declares its
#: dependencies?" — the only honest basis for auditing a toolchain claim in an
#: adopter's file.
_MANIFEST_FILES: tuple[str, ...] = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "build.gradle",
    "pom.xml",
)


def manifest_text(project_root: Path) -> str | None:
    """Every readable dependency manifest under ``project_root``, concatenated.

    ``None`` — not ``""`` — when the project has no manifest Beadloom can read:
    "nothing declares this" and "we could not look" are different answers and a
    caller must be able to tell them apart.
    """
    parts = [
        text
        for name in _MANIFEST_FILES
        if (text := _read(project_root / name)) is not None
    ]
    if not parts:
        return None
    return "\n".join(parts)


def detect_requires_python(project_root: Path) -> str | None:
    """The ``requires-python`` constraint the project declares, or ``None``.

    Rendered verbatim rather than normalised: a project on ``>=3.12`` was
    previously described as "Python 3.10+" because that string was Beadloom's
    own floor written into the renderer.
    """
    text = _read(project_root / "pyproject.toml")
    if text is None:
        return None
    match = re.search(
        r'^\s*requires-python\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE
    )
    return match.group(1) if match is not None else None


#: A requirement string's distribution name: everything before the first
#: version specifier, extra marker or environment marker.
_REQUIREMENT_NAME_RE = re.compile(r"^([A-Za-z0-9][\w.-]*)")

#: How many dependencies to name. A bullet is a summary, not an inventory; the
#: manifest is one file away and is the authority.
_MAX_DEPENDENCIES = 6


def detect_declared_dependencies(project_root: Path) -> tuple[str, ...]:
    """The RUNTIME dependencies this project declares, in declared order.

    Read from ``[project].dependencies`` or ``package.json``'s
    ``dependencies``. The renderer used to look for a fixed vocabulary instead —
    ``sqlite``, ``click``, ``rich``, ``tree-sitter`` — which is Beadloom's own
    dependency list applied as a lens to somebody else's project: right here,
    empty for a project using anything else (BDL-UX #183's sweep).
    """
    names = _pyproject_dependencies(project_root) or _package_json_dependencies(
        project_root
    )
    return tuple(names[:_MAX_DEPENDENCIES])


def _pyproject_dependencies(project_root: Path) -> list[str]:
    text = _read(project_root / "pyproject.toml")
    if text is None:
        return []
    body = _table_body(text, "[project]")
    if body is None:
        return []
    match = re.search(r"^\s*dependencies\s*=\s*\[(.*?)\]", body, re.MULTILINE | re.DOTALL)
    if match is None:
        return []
    names: list[str] = []
    for raw in re.findall(r"[\"\']([^\"\']+)[\"\']", match.group(1)):
        name = _REQUIREMENT_NAME_RE.match(raw.strip())
        if name is not None and name.group(1) not in names:
            names.append(name.group(1))
    return names


def _package_json_dependencies(project_root: Path) -> list[str]:
    text = _read(project_root / "package.json")
    if text is None:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    deps = data.get("dependencies") if isinstance(data, dict) else None
    if not isinstance(deps, dict):
        return []
    return [name for name in deps if isinstance(name, str)]
