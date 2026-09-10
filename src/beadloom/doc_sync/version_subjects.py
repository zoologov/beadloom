"""Which named subjects a version token in this project's prose can belong to.

A document that records what a DEPENDENCY was measured to do has to name the
release it measured -- "measured on bd 1.0.4", "on git 2.49.0", "every verdict
taken on CPython 3.13.7".  The version scanner matched every
``\\bv?\\d+\\.\\d+\\.\\d+\\b`` outside a pin and compared each one against this
project's own version, so those sentences were stale-fact findings and the only
way to write them was a ``docs_audit.ignore`` triple per document.  Ten of them
stood in this repository's config for one sentence shape, three inside
user-facing guides (BDL-UX #253, and the foreign-subject face of #190).

This module holds the VOCABULARY half of the answer: the set of names a version
in this project's documents can belong to that are not this project.  The other
half -- which name a particular token is attributed to -- lives in
:mod:`beadloom.doc_sync.scanner`, beside the token-boundary policy it reuses.

THE VOCABULARY IS DERIVED WHERE IT CAN BE.  A project already declares most of
the products its documentation cites: every distribution in its manifest, the
interpreter family implied by ``requires-python`` / ``engines.node`` /
``rust-version``, and ``git`` when the project is a git repository.  What no
manifest declares -- a CLI such as ``bd``, a database, a service -- is named
once in ``docs_audit.subjects``, per NAME rather than per document.

A SOURCE THAT CANNOT BE CONSULTED ANSWERS NEITHER YES NOR NO.  ``git`` is
confirmed by the environment rather than by a file the project ships, and the
absent case was read as the assertion that this project has nothing to do with
git.  A directory built by ``git archive HEAD`` -- every clean room this
repository measures in -- carries no ``.git`` by construction, so
``git 2.49.0`` lost its subject and was compared against this project's own
version, and every clean-room Gate run on this repository was rc 1 for that one
line (BDL-UX #266).  Such a name is UNRESOLVED: it stays in the vocabulary, a
version beside it is still attributed to it, and the audit reports the token it
declined to judge with the reason it declined.  Unresolved is not silence --
:mod:`beadloom.doc_sync.audit` counts it in its own population and the Gate line
names it.

IT IS A VOCABULARY AND NOT A SILENCER, and the difference is the failure mode.
A name nobody declared still produces a finding, so an unknown subject fails
LOUD.  The alternative shape -- read every word beside a version as a subject
unless it is a function word -- was measured against this repository's prose and
rejected: ``Phase 3.0.0``, ``Implemented 3.0.0``, ``Release 2.1.0``,
``dated 3.0.0`` and ``published 2.2.0`` all put an ordinary English word beside
this project's OWN version, so that rule turns a stale claim into silence, which
is the one outcome this scanner's design notes call worse than a false positive.
"""

# beadloom:feature=docs-audit

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The interpreter families a manifest key implies.  A project that declares
#: which interpreters it runs under has named that interpreter as a product,
#: which is what makes "CPython 3.13.7" attributable without configuration.
_INTERPRETER_FAMILIES: dict[str, tuple[str, ...]] = {
    "requires-python": ("python", "cpython", "pypy"),
    "engines.node": ("node", "nodejs"),
    "rust-version": ("rust", "rustc"),
}

#: Subjects whose NAME is known without any declaration and whose presence is
#: confirmed by the environment rather than by a file the project ships:
#: ``(name, the marker that confirms it, the origin to record)``.  The marker's
#: absence is not a denial -- ``git archive`` produces a tree of a git project
#: with no ``.git`` in it -- so an unconfirmed name here becomes unresolved
#: rather than leaving the vocabulary (BDL-UX #266).
_ENVIRONMENT_SUBJECTS: tuple[tuple[str, str, str], ...] = (
    ("git", ".git", "the project is a git repository"),
)

#: A PEP 508 / npm requirement's distribution name is its leading run of name
#: characters, before any extras marker, comparator or environment marker.
_REQUIREMENT_NAME_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9._-]*)")

#: A quoted string inside a TOML array.
_TOML_STRING_RE = re.compile(r'"([^"]*)"|\'([^\']*)\'')

#: TOML comment introducer, outside a string.
_COMMENT_CHAR = "#"

#: A TOML table header, e.g. ``[project.optional-dependencies]``.
_TOML_TABLE_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")

#: ``key = ...`` at the start of a TOML line.
_TOML_KEY_RE = re.compile(r"^\s*(?:\"([^\"]+)\"|([A-Za-z0-9_.-]+))\s*=")

#: Cargo tables whose KEYS are distribution names.
_CARGO_DEPENDENCY_TABLES = frozenset(
    {"dependencies", "dev-dependencies", "build-dependencies"}
)


@dataclass(frozen=True)
class VersionSubjects:
    """The named products a version token in this project's prose may belong to.

    Attributes
    ----------
    names:
        Case-folded names that are NOT this project.  A version attributed to
        one of these is that product's release and is never compared against
        this project's version.
    project:
        Case-folded names of this project itself.  They stop the attribution
        walk without making the version foreign, so a clause naming both --
        ``beadloom 3.1.0 was measured on bd 1.0.4`` -- gives each number to the
        name beside it rather than to whichever appears first.
    origins:
        ``(name, where it came from)`` for every entry of ``names``, sorted.
        The audit reports this so the vocabulary is visible rather than an
        invisible rule about which sentences are checked.
    unresolved:
        Case-folded names the environment could not confirm HERE.  A version
        attributed to one of these is judged neither against this project nor
        as another product's release: the audit reports it as a token it
        declined to judge, with the reason (BDL-UX #266).
    unresolved_origins:
        ``(name, why it could not be confirmed)`` for every entry of
        ``unresolved``, sorted.  A population the audit declines is only honest
        while a reader can see why it was declined.
    """

    names: frozenset[str] = frozenset()
    project: frozenset[str] = frozenset()
    origins: tuple[tuple[str, str], ...] = ()
    unresolved: frozenset[str] = frozenset()
    unresolved_origins: tuple[tuple[str, str], ...] = ()

    def __bool__(self) -> bool:
        """Whether any subject is known: an empty vocabulary changes nothing.

        An unresolved name counts.  It decides the attribution walk as firmly
        as a confirmed one -- a vocabulary holding only unresolved names that
        read as empty would send every token straight back to the comparison
        this design exists to keep it out of.
        """
        return bool(self.names or self.unresolved)


def derive_version_subjects(
    project_root: Path, *, config_path: Path | None = None
) -> VersionSubjects:
    """The subject vocabulary for *project_root*, derived then declared.

    Sources, in the order they are recorded:

    1. every distribution the project's manifest declares as a dependency
       (``pyproject.toml``, ``package.json``, ``Cargo.toml``);
    2. the interpreter families implied by ``requires-python``,
       ``engines.node`` or ``rust-version``;
    3. the environment-confirmed names of :data:`_ENVIRONMENT_SUBJECTS` --
       ``git``, when *project_root* holds a ``.git``;
    4. ``docs_audit.subjects`` in ``.beadloom/config.yml``.

    An environment-confirmed name whose marker is absent is UNRESOLVED rather
    than dropped: the filesystem cannot tell a project that never used git from
    an export of one, and answering "no" to that question is what reddened
    every clean-room Gate run on this repository (BDL-UX #266).  A later source
    still resolves it -- a project that names ``git`` under
    ``docs_audit.subjects`` has answered the question the marker could not.
    """
    found: dict[str, str] = {}
    unresolved: dict[str, str] = {}
    project_names: set[str] = set()

    for name, origin in _from_pyproject(project_root):
        found.setdefault(name, origin)
    for name, origin in _from_package_json(project_root):
        found.setdefault(name, origin)
    for name, origin in _from_cargo(project_root):
        found.setdefault(name, origin)

    project_names.update(_project_names(project_root))

    for name, marker, origin in _ENVIRONMENT_SUBJECTS:
        if (project_root / marker).exists():
            found.setdefault(name, origin)
        else:
            unresolved.setdefault(
                name,
                f"no {marker} here, and its absence cannot tell a project that"
                f" never used {name} from an export of one",
            )

    for name in _configured_subjects(project_root, config_path):
        found[name] = "docs_audit.subjects"

    # A project never cites itself as somebody else's product, and a name it
    # declared for itself is not a question the environment still owes.
    for own in project_names:
        found.pop(own, None)
    for name in (*project_names, *found):
        unresolved.pop(name, None)

    return VersionSubjects(
        names=frozenset(found),
        project=frozenset(project_names),
        origins=tuple(sorted(found.items())),
        unresolved=frozenset(unresolved),
        unresolved_origins=tuple(sorted(unresolved.items())),
    )


def _normalise(name: str) -> str:
    """A distribution name as a document would spell it: folded, `_` as `-`."""
    return name.strip().casefold().replace("_", "-")


def _project_names(project_root: Path) -> set[str]:
    """This project's own names, as its manifests spell them."""
    names: set[str] = set()

    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        text = _read(pyproject)
        match = re.search(
            r'^\s*name\s*=\s*"([^"]+)"', text, re.MULTILINE
        )
        if match:
            names.add(_normalise(match.group(1)))

    package_json = project_root / "package.json"
    if package_json.is_file():
        data = _read_json(package_json)
        name = data.get("name") if isinstance(data, dict) else None
        if isinstance(name, str):
            names.add(_normalise(name))

    return names


def _from_pyproject(project_root: Path) -> list[tuple[str, str]]:
    """Distributions and interpreter families a ``pyproject.toml`` declares."""
    path = project_root / "pyproject.toml"
    if not path.is_file():
        return []
    text = _read(path)

    found: list[tuple[str, str]] = []
    for requirement in _toml_dependency_strings(text):
        name = _requirement_name(requirement)
        if name:
            found.append((name, "pyproject.toml dependency"))

    if re.search(r'^\s*requires-python\s*=', text, re.MULTILINE):
        found.extend(
            (family, "pyproject.toml requires-python")
            for family in _INTERPRETER_FAMILIES["requires-python"]
        )
    return found


def _toml_dependency_strings(text: str) -> list[str]:
    """Every requirement string inside a dependency array of a TOML manifest.

    Scoped to the dependency keys rather than to every quoted string in the
    file: ``keywords``, ``classifiers`` and ``license`` are quoted strings too,
    and reading them as product names would silence a version standing beside
    an ordinary word such as ``documentation``.
    """
    strings: list[str] = []
    table = ""
    collecting = False
    for raw_line in text.splitlines():
        line = _without_comment(raw_line)
        header = _TOML_TABLE_RE.match(line)
        if header:
            table = header.group(1).strip()
            collecting = False
            continue

        if not collecting:
            key_match = _TOML_KEY_RE.match(line)
            key = (
                (key_match.group(1) or key_match.group(2)) if key_match else None
            )
            if key is None or not _is_dependency_key(table, key):
                continue
            collecting = True

        strings.extend(
            m.group(1) or m.group(2) for m in _TOML_STRING_RE.finditer(line)
        )
        if "]" in line:
            collecting = False

    return strings


def _without_comment(line: str) -> str:
    """*line* with its TOML comment removed.

    A comment is prose, and prose carries apostrophes and quotation marks.
    Reading one as a TOML string put the word ``an`` into this repository's own
    vocabulary, which would have silenced any version standing beside it -- a
    stray name in the vocabulary is a silent false negative, the failure this
    design exists to avoid.
    """
    in_double = False
    in_single = False
    for index, char in enumerate(line):
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
        elif char == _COMMENT_CHAR and not in_double and not in_single:
            return line[:index]
    return line


def _is_dependency_key(table: str, key: str) -> bool:
    """Whether ``table.key`` is a place a TOML manifest lists dependencies."""
    if table == "project" and key == "dependencies":
        return True
    if table.startswith("project.optional-dependencies"):
        return True
    return table == "dependency-groups"


def _from_package_json(project_root: Path) -> list[tuple[str, str]]:
    """Distributions and the runtime a ``package.json`` declares."""
    path = project_root / "package.json"
    if not path.is_file():
        return []
    data = _read_json(path)
    if not isinstance(data, dict):
        return []

    found: list[tuple[str, str]] = []
    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        block = data.get(section)
        if not isinstance(block, dict):
            continue
        for raw in block:
            name = _requirement_name(str(raw))
            if name:
                found.append((name, f"package.json {section}"))

    engines = data.get("engines")
    if isinstance(engines, dict) and "node" in engines:
        found.extend(
            (family, "package.json engines.node")
            for family in _INTERPRETER_FAMILIES["engines.node"]
        )
    return found


def _from_cargo(project_root: Path) -> list[tuple[str, str]]:
    """Crates and the toolchain a ``Cargo.toml`` declares.

    Cargo lists a dependency as a TABLE KEY rather than as an array item, so
    this reads keys where :func:`_toml_dependency_strings` reads strings.
    """
    path = project_root / "Cargo.toml"
    if not path.is_file():
        return []
    text = _read(path)

    found: list[tuple[str, str]] = []
    table = ""
    for raw_line in text.splitlines():
        line = _without_comment(raw_line)
        header = _TOML_TABLE_RE.match(line)
        if header:
            table = header.group(1).strip()
            continue
        if table.split(".")[-1] not in _CARGO_DEPENDENCY_TABLES:
            continue
        key_match = _TOML_KEY_RE.match(line)
        if key_match is None:
            continue
        name = _requirement_name(key_match.group(1) or key_match.group(2))
        if name:
            found.append((name, f"Cargo.toml [{table}]"))

    if re.search(r'^\s*rust-version\s*=', text, re.MULTILINE):
        found.extend(
            (family, "Cargo.toml rust-version")
            for family in _INTERPRETER_FAMILIES["rust-version"]
        )
    return found


def _configured_subjects(
    project_root: Path, config_path: Path | None
) -> list[str]:
    """Names declared under ``docs_audit.subjects`` in the project's config."""
    path = config_path or project_root / ".beadloom" / "config.yml"
    if not path.is_file():
        return []

    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        logger.warning("Cannot read %s for docs_audit.subjects: %s", path, exc)
        return []

    if not isinstance(data, dict):
        return []
    section = data.get("docs_audit")
    if not isinstance(section, dict):
        return []
    raw = section.get("subjects")
    if raw is None:
        return []
    if not isinstance(raw, list):
        logger.warning("docs_audit.subjects is not a list: %r", raw)
        return []

    names: list[str] = []
    for entry in raw:
        name = _normalise(str(entry))
        if name:
            names.append(name)
    return names


def _requirement_name(requirement: str) -> str | None:
    """The distribution name a requirement string starts with."""
    match = _REQUIREMENT_NAME_RE.match(requirement)
    return _normalise(match.group(1)) if match else None


def _read(path: Path) -> str:
    """A manifest's text, or an empty string when it cannot be read."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return ""


def _read_json(path: Path) -> object:
    """A manifest's parsed JSON, or ``None`` when it cannot be read."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return None
