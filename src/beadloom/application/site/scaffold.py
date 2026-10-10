# beadloom:domain=application
# beadloom:feature=site-generation
"""The portal's hand-written files: the scaffold the package ships, and the project's own.

BDL-076 B1 (``beadloom-dfwt``). The theme, the viewer, ``package.json``, the
lockfile, the VitePress config and the browser tests are package data under
``beadloom/site_scaffold/``, laid out exactly as they sit in a portal. ``docs
site`` writes them into the output directory beside the content it generates,
and that directory is the project's, so this module tells its own files from
anybody else's by evidence rather than by path.

**The marker.** Every file written here carries one line naming the version that
wrote it and the SHA-256 of the rest of the file — a comment in JavaScript, Vue
CSS and SVG, a ``"//"`` key on the second line of a JSON file. Only the formats in
:data:`MARKABLE_SUFFIXES` can carry it, and a shipped file of any other kind is
a packaging defect, refused here and caught by a test before it ships.

**What each run does to a file the scaffold ships:**

- absent: written;
- present with an intact marker (its body still hashes to the marker's value):
  rewritten when the shipped body or version differs — an upgrade, or an
  editable install whose source changed — and left alone when nothing does;
- present with no marker, or a marker its body no longer matches: never
  overwritten, and reported with where the change belongs.

A file that carries an intact marker and that the installed version no longer
ships is removed, so a browser test retired upstream does not keep running
against a viewer that changed under it. Content ``docs site`` generates each run
carries no marker and is never touched here. A folder those removals leave empty
is removed with them (BDL-080 S2d): a slice the scaffold renamed would otherwise
outlive the version that wrote it as an empty tree. Only a folder a retired file
sat in, or one above it, is a candidate, so a folder the project made is never
touched, and one that still holds anything stays.

**This repository's annotations** (``beadloom-ujzb.18``). The scaffold's source
carries ``beadloom:component=<ref>`` lines so that the graph of the repository
it is developed in binds each theme file to one of that repository's nodes. An
adopter's portal is not that repository, and those lines would name nodes the
adopter does not have, so every line that is only such an annotation is left
out of the body a portal receives. The marker hashes the body as written, so
the rules above are the same rules over that body: a portal an earlier version
wrote with the lines is beadloom's, and it is rewritten without them.

**The override directory**, ``.beadloom/site/``, is copied last and verbatim. It
is where a project changes its portal — a page, a stylesheet, a component —
without editing a generated file, and a shipped path it provides is not written
by the scaffold at all.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from importlib.abc import Traversable

#: The package-data directory, under the ``beadloom`` package.
SCAFFOLD_PACKAGE_DIR = "site_scaffold"

#: A project's own portal files, relative to the project root, copied last.
OVERRIDE_DIR = Path(".beadloom") / "site"

#: How each kind of file carries the marker: text before and after it on its line.
_COMMENT_SYNTAX = {
    ".js": ("// ", ""),
    ".mjs": ("// ", ""),
    ".vue": ("<!-- ", " -->"),
    ".css": ("/* ", " */"),
    # The brand files under `public/brand/` (BDL-080 S4d): an XML comment above
    # the `<svg>` element, which none of them opens with a declaration.
    ".svg": ("<!-- ", " -->"),
}
_JSON = ".json"

#: Every suffix a shipped file may have: the ones that can carry the marker.
MARKABLE_SUFFIXES = frozenset({*_COMMENT_SYNTAX, _JSON})

#: Names never shipped and never walked: dependencies, build output, test output.
_NOT_SHIPPED = frozenset(
    {"node_modules", "__pycache__", ".DS_Store", "test-results", "playwright-report"}
)
#: Output directories VitePress owns, relative to the site root.
_BUILD_OUTPUT = (".vitepress/cache", ".vitepress/dist")

_MARKER_RE = re.compile(
    r"beadloom:generated version=(?P<version>[^\s;]+) sha256=(?P<sha>[0-9a-f]{64})"
)
#: The marker sits on the first line, or on the second of a JSON file.
_MARKER_LINES = 2

#: A line that is nothing but a graph annotation (the tool's name, a colon, then
#: ``<key>=<ref>``) in a comment of any syntax a shipped file is written in. The
#: generated marker puts a space, not ``=``, after its key, so it never matches;
#: neither does a line that only mentions beadloom. Worded without the literal
#: form on purpose: a comment holding it is read as an annotation of this module.
_ANNOTATION_LINE_RE = re.compile(r"^[ \t]*(?://|/\*|<!--)[ \t]*beadloom:\w+=.*(?:\n|$)", re.M)


class ScaffoldError(ValueError):
    """A shipped file cannot carry the generated marker."""


@dataclass(frozen=True)
class Marker:
    """The marker read from a written file, and the body it was found above."""

    version: str
    sha256: str
    body: str

    @property
    def intact(self) -> bool:
        """The body is still the one the marker was written for."""
        return _digest(self.body) == self.sha256


@dataclass(frozen=True)
class Placement:
    """What :func:`place_marked` did with one file, and why when it kept the file there."""

    outcome: Literal["written", "updated", "unchanged", "kept"]
    reason: str = ""


@dataclass(frozen=True)
class KeptFile:
    """A shipped path this run did not write, because the file there is not beadloom's."""

    path: str
    reason: str
    remediation: str


@dataclass(frozen=True)
class ScaffoldReport:
    """What one run did with each file, as paths relative to the site root."""

    version: str
    written: tuple[str, ...] = ()
    updated: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    retired: tuple[str, ...] = ()
    #: Folders the retired files left empty, removed with them (BDL-080 S2d).
    retired_folders: tuple[str, ...] = ()
    kept: tuple[KeptFile, ...] = ()
    overridden: tuple[str, ...] = ()


@dataclass
class _Tally:
    written: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    kept: list[KeptFile] = field(default_factory=list)


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def marker_line(body: str, version: str, note: str) -> str:
    """The marker's text for *body*, written by *version*, followed by *note* for a reader.

    The comment syntax around it is the caller's: this is the part every
    generated file shares, and the part :func:`read_marker` reads back.
    """
    return f"beadloom:generated version={version} sha256={_digest(body)}; {note}"


def _marker_text(rel: str, body: str, version: str) -> str:
    note = f"written by `beadloom docs site`, a change belongs in {OVERRIDE_DIR.as_posix()}/{rel}"
    return marker_line(body, version, note)


def mark(rel: str, body: str, version: str) -> str:
    """*body* as ``docs site`` writes it at *rel*: with the marker line."""
    suffix = Path(rel).suffix
    text = _marker_text(rel, body, version)
    if suffix == _JSON:
        head, newline, rest = body.partition("\n")
        if head.strip() != "{" or not newline:
            raise ScaffoldError(
                f"{rel}: a shipped JSON file must open with `{{` on a line of its own"
            )
        return f'{head}\n  "//": "{text}",\n{rest}'
    syntax = _COMMENT_SYNTAX.get(suffix)
    if syntax is None:
        raise ScaffoldError(
            f"{rel}: a `{suffix or 'suffixless'}` file cannot carry the generated marker; "
            f"shipped files are {', '.join(sorted(MARKABLE_SUFFIXES))}"
        )
    before, after = syntax
    return f"{before}{text}{after}\n{body}"


def read_marker(text: str) -> Marker | None:
    """The marker in *text* and the body under it, or ``None`` when it carries none."""
    lines = text.split("\n")
    for index, line in enumerate(lines[:_MARKER_LINES]):
        found = _MARKER_RE.search(line)
        if found is not None:
            body = "\n".join(lines[:index] + lines[index + 1 :])
            return Marker(version=found["version"], sha256=found["sha"], body=body)
    return None


def without_annotations(body: str) -> str:
    """*body* without the lines that bind it to a node of the repository it ships from."""
    return _ANNOTATION_LINE_RE.sub("", body)


def _walk(root: Traversable, prefix: str = "") -> dict[str, str]:
    shipped: dict[str, str] = {}
    for entry in root.iterdir():
        if entry.name in _NOT_SHIPPED:
            continue
        rel = f"{prefix}{entry.name}"
        if rel in _BUILD_OUTPUT:
            continue
        if entry.is_dir():
            shipped.update(_walk(entry, f"{rel}/"))
        elif entry.is_file():
            shipped[rel] = without_annotations(entry.read_text(encoding="utf-8"))
    return shipped


def shipped_files(source: Traversable | Path | None = None) -> dict[str, str]:
    """Every file the scaffold ships, by its path in a portal, with the body a portal gets.

    That body is the source's without its graph annotations
    (:func:`without_annotations`): they name the nodes of the repository the
    scaffold is developed in, and the portal is somebody else's.

    *source* replaces the installed package's scaffold, for a test.
    """
    root = source if source is not None else files("beadloom").joinpath(SCAFFOLD_PACKAGE_DIR)
    return dict(sorted(_walk(root).items()))


def _override_files(project_root: Path) -> dict[str, Path]:
    root = project_root / OVERRIDE_DIR
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"))
        if path.is_file() and not _NOT_SHIPPED.intersection(path.relative_to(root).parts)
    }


def _read_head(path: Path) -> str:
    """The first lines of *path*, where a marker would be; ``""`` when unreadable."""
    try:
        with path.open(encoding="utf-8") as handle:
            return "".join(handle.readline() for _ in range(_MARKER_LINES))
    except (OSError, UnicodeDecodeError):
        return ""


def _kept(rel: str, out_dir: Path, reason: str) -> KeptFile:
    override = f"{OVERRIDE_DIR.as_posix()}/{rel}"
    return KeptFile(
        path=rel,
        reason=reason,
        remediation=(
            f"put your version in {override}, which is copied last on every run, and delete "
            f"{(out_dir / rel).as_posix()}; or delete it to take the shipped one"
        ),
    )


def place_marked(target: Path, expected: str) -> Placement:
    """Write *expected* at *target* unless the file already there is not beadloom's.

    *expected* carries its marker. A file with an intact marker is beadloom's and
    is rewritten when it differs; any other file is left exactly as it is, and
    the returned :class:`Placement` says why.
    """
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8")
        return Placement("written")
    try:
        current = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Placement("kept", "could not be read as text, so it was not replaced")
    marker = read_marker(current)
    if marker is None:
        return Placement(
            "kept", "carries no beadloom:generated marker, so it is not beadloom's to replace"
        )
    if not marker.intact:
        return Placement(
            "kept", "was edited by hand after beadloom wrote it, so it was not replaced"
        )
    if current == expected:
        return Placement("unchanged")
    target.write_text(expected, encoding="utf-8")
    return Placement("updated")


def _place(rel: str, expected: str, out_dir: Path, tally: _Tally) -> None:
    """Write one shipped file, or record why the file already there was kept."""
    placed = place_marked(out_dir / rel, expected)
    if placed.outcome == "kept":
        tally.kept.append(_kept(rel, out_dir, placed.reason))
        return
    written = {"written": tally.written, "updated": tally.updated, "unchanged": tally.unchanged}
    written[placed.outcome].append(rel)


def _written_files(root: Path, prefix: str = "") -> list[tuple[str, Path]]:
    """Every file under *root* that could carry the marker, pruning what is never shipped.

    Pruned rather than filtered: a portal's ``node_modules`` holds tens of
    thousands of files, and none of them is the scaffold's.
    """
    found: list[tuple[str, Path]] = []
    for path in sorted(root.iterdir()):
        rel = f"{prefix}{path.name}"
        if path.name in _NOT_SHIPPED or rel in _BUILD_OUTPUT or path.is_symlink():
            continue
        if path.is_dir():
            found.extend(_written_files(path, f"{rel}/"))
        elif path.suffix in MARKABLE_SUFFIXES and path.is_file():
            found.append((rel, path))
    return found


def _retire(out_dir: Path, keep: set[str]) -> list[str]:
    """Remove every file beadloom wrote that the installed version no longer ships."""
    retired: list[str] = []
    for rel, path in _written_files(out_dir):
        if rel in keep or _MARKER_RE.search(_read_head(path)) is None:
            continue
        marker = read_marker(path.read_text(encoding="utf-8"))
        if marker is not None and marker.intact:
            path.unlink()
            retired.append(rel)
    return retired


def retire_emptied_folders(out_dir: Path, retired: list[str]) -> list[str]:
    """Remove every folder the retired files leave empty, deepest first, sorted for the report.

    The candidates are the folders the retired files sat in and the folders above them,
    never the portal's root: a folder no retired file sat in is the project's, and a
    folder that still holds anything, a file beadloom did not write included, stays.
    The node pages a run retires from a section they left go the same way (BDL-081 R2).
    """
    candidates = {
        parent
        for rel in retired
        for parent in PurePosixPath(rel).parents
        if parent != PurePosixPath()
    }
    removed: list[str] = []
    for rel in sorted(candidates, key=lambda folder: len(folder.parts), reverse=True):
        folder = out_dir / rel
        if folder.is_dir() and not folder.is_symlink() and not any(folder.iterdir()):
            folder.rmdir()
            removed.append(rel.as_posix())
    return sorted(removed)


def write_scaffold(
    out_dir: Path,
    *,
    project_root: Path,
    version: str,
    source: Traversable | Path | None = None,
) -> ScaffoldReport:
    """Write the shipped scaffold into *out_dir*, then copy the project's overrides last.

    Args:
        out_dir: The portal's root, where ``docs site`` writes its content.
        project_root: The project, whose ``.beadloom/site/`` is copied last.
        version: The installed beadloom version, recorded in every marker.
        source: Replaces the installed package's scaffold, for a test.
    """
    shipped = shipped_files(source)
    overrides = _override_files(project_root)
    tally = _Tally()
    for rel, body in shipped.items():
        if rel not in overrides:
            _place(rel, mark(rel, body, version), out_dir, tally)
    retired = _retire(out_dir, set(shipped) | set(overrides)) if out_dir.is_dir() else []
    retired_folders = retire_emptied_folders(out_dir, retired)
    for rel, path in overrides.items():
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    return ScaffoldReport(
        version=version,
        written=tuple(tally.written),
        updated=tuple(tally.updated),
        unchanged=tuple(tally.unchanged),
        retired=tuple(retired),
        retired_folders=tuple(retired_folders),
        kept=tuple(tally.kept),
        overridden=tuple(overrides),
    )
