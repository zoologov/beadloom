# beadloom:domain=onboarding
# beadloom:component=ignore-block
"""The generated working set under ``.beadloom/`` and the ignore block naming it.

Beadloom writes derived state into a project's ``.beadloom/`` — the SQLite index
and, since the flow guards, an appended firing record. Before BDL-061.35 it wrote
an ignore entry for none of it, anywhere: an adopter got untracked churn from the
first ``reindex`` and again from the first guarded edit, and only *this*
repository was clean, because its ``.gitignore`` had been hand-edited.

**Why this lives at init and not in the guard scaffolder.** The entry is a
property of the directory Beadloom creates, not of any one feature. Adding it to
``scaffold_guard_hooks`` alone would make the flow guards a special case while
leaving the larger churn — the index — unignored, and would require *editing* a
block written earlier every time a feature is enabled. Written once, for the whole
working set, at the moment the working set is created, nothing later has to
manage the file.

**Why written once and never rewritten.** ``.gitignore`` is the project's file and
is edited constantly; the composed flow artifacts have a manifest and a
drift-guard precisely because Beadloom owns them, and this one it does not own.
So the block is a *default*, and the override is to edit it: delete a line and it
does not come back, because a run that finds the marker does nothing at all. A
config key would be the opposite trade — it would force the block to become
managed, so that flipping the key rewrote somebody's ignore file, which is the
behaviour being avoided.

**Why the firing record is ignored by default**, given that it is evidence about
what the flow did and a team could reasonably want it committed: it is
machine-local and append-only, so committing it makes every guarded edit a
working-tree change and every branch a conflict on the same last line. The reason
is written into the block itself rather than only into these docs, because the
adopter meets the line in their own file. The block also says what ignoring does
not settle on its own: keeping a file out of git says nothing about its size.
Since BDL-061.56 the size is settled elsewhere — the record rolls over at
:data:`~beadloom.application.guards.firing.ACTIVE_FIRINGS_CAP` firings — and the
pattern covers the rotated generation as well, so ignoring the record does not
leave its archive to show up as untracked churn.

The patterns are the measured set: on this repository the only paths under
``.beadloom/`` that are not source are the ``.db`` family and the
``guard-firings*.jsonl`` pair; the graph and ``flow.yml`` are tracked and must
stay committable.
"""

from __future__ import annotations

import fnmatch
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

#: The project's ignore file, relative to the project root.
IGNORE_RELPATH = Path(".gitignore")

#: The directory whose contents the block names; nothing generated, nothing to ignore.
_WORKING_SET_DIR = Path(".beadloom")

#: Opens the block; its presence means "already written — hands off".
BLOCK_MARKER = "# Beadloom: generated working set under .beadloom/"

#: Width the reason comments wrap at, so the block stays readable in a diff.
_WRAP = 92

_HEADER = (
    "Written once by Beadloom and never rewritten, so an edit here is permanent: "
    "delete a line you disagree with and it will not come back. Only derived state "
    "is listed - the graph (.beadloom/_graph/) and flow.yml are source and belong in git."
)


@dataclass(frozen=True)
class IgnoreEntry:
    """One ignored pattern and the reason it is ignored, which is never optional."""

    pattern: str
    why: str


#: What Beadloom generates under ``.beadloom/``, each with the reason it is ignored.
GENERATED_WORKING_SET: tuple[IgnoreEntry, ...] = (
    IgnoreEntry(
        pattern=".beadloom/**/*.db",
        why=(
            "The index. Rebuilt from the graph and the code by `beadloom reindex`, so it "
            "is derived state: committing it means a binary merge conflict that carries "
            "no information."
        ),
    ),
    IgnoreEntry(
        pattern=".beadloom/**/*.db-wal",
        why="SQLite's write-ahead log for that index, live only while it is open.",
    ),
    IgnoreEntry(
        pattern=".beadloom/**/*.db-shm",
        why="SQLite's shared-memory sidecar for the same, and equally short-lived.",
    ),
    IgnoreEntry(
        pattern=".beadloom/guard-firings*.jsonl",
        why=(
            "The guard firing record and its rotated generation. "
            "Evidence that a gate ran, appended on every guarded edit; ignored by "
            "default because it is machine-local and append-only - committing it makes "
            "every edit a working-tree change and every branch a conflict on the same "
            "last line. A team that wants the audit trail deletes this line, once - "
            "and what it then commits is one line per guarded edit carrying the "
            "verdict, the file an edit named, and for a shell edit the program that "
            "ran and the files it was seen to write. Not the command line: that would "
            "put your agents' shell history, and whatever their arguments carried, "
            "into git. The size is bounded since BDL-061.56: the active record rolls "
            "over at 2000 firings into `guard-firings.1.jsonl`, so both files together "
            "are bounded and `beadloom guard --liveness` parses only the active one."
        ),
    ),
)


@dataclass(frozen=True)
class IgnoreFinding:
    """One generated pattern a project's ignore file does not declare.

    Carries the :class:`IgnoreEntry` rather than a copy of it, so the finding's
    text is the generator's text and a pattern added later needs no second list.
    """

    entry: IgnoreEntry
    supersedes: tuple[str, ...] = ()

    @property
    def pattern(self) -> str:
        """The pattern this version emits and the file does not declare."""
        return self.entry.pattern

    @property
    def why(self) -> str:
        """What drifted, in the words a reader of the ignore file needs."""
        subject = (
            f"the ignore block this version generates declares {self.pattern!r} "
            f"and {IGNORE_RELPATH} does not"
        )
        if not self.supersedes:
            return (
                f"{subject}. The block is written once, at init, and never rewritten, "
                "so a pattern a later release adds never reaches a project that "
                "already ran it"
            )
        declared = ", ".join(repr(p) for p in self.supersedes)
        return (
            f"{subject} — it declares {declared} instead, which the current pattern "
            "covers and supersedes. The narrower line goes on matching until the "
            "wider one has something extra to match, and then stops silently"
        )

    @property
    def remediation(self) -> str:
        """The human's edit, in the human's file — never a command."""
        if not self.supersedes:
            return (
                f"add {self.pattern} to {IGNORE_RELPATH} by hand; Beadloom will not "
                "add it, because the file is the project's from the moment the block "
                "is first written"
            )
        declared = " and ".join(self.supersedes)
        return (
            f"replace {declared} in {IGNORE_RELPATH} with {self.pattern} by hand; "
            "Beadloom does not edit a block it has already written"
        )


def supersedes(pattern: str, declared: str) -> bool:
    """Whether *pattern* covers *declared* and is a widening of it.

    The measured case is a filename a later release widened into a glob:
    ``.beadloom/guard-firings.jsonl`` against ``.beadloom/guard-firings*.jsonl``.
    Glob-matching the declared line against the expected one answers that
    without a table of known renames — a table is the second list this check
    exists to avoid. ``fnmatchcase`` rather than ``fnmatch`` so the answer does
    not depend on the case-folding of the filesystem the check runs on.
    """
    return declared != pattern and fnmatch.fnmatchcase(declared, pattern)


def undeclared_patterns(text: str) -> list[IgnoreFinding]:
    """Every generated pattern *text* does not declare, in generator order.

    The single predicate behind both directions: :func:`ensure_ignore_block`
    writes what it returns, and the drift check reports it. Comparing the
    PATTERNS and not the block's bytes is deliberate — the reason comments are
    prose in a file people edit, and a project that ignores the same paths under
    a heading it wrote itself is correct. This repository is that project.
    """
    declared = _declared_patterns(text)
    return [
        IgnoreFinding(
            entry=entry,
            supersedes=tuple(sorted(d for d in declared if supersedes(entry.pattern, d))),
        )
        for entry in GENERATED_WORKING_SET
        if entry.pattern not in declared
    ]


def ignore_block_findings(project_root: Path) -> list[IgnoreFinding]:
    """The undeclared patterns for a project, or none where there is nothing to check.

    Silent in the two states :func:`ensure_ignore_block` also declines to act on:
    outside a git working tree, where the writer never wrote and which VCS the
    project uses is not ours to guess, and where Beadloom has generated nothing
    under ``.beadloom/`` for an ignore file to name.
    """
    if _git_root(project_root) is None or not (project_root / _WORKING_SET_DIR).is_dir():
        return []
    path = project_root / IGNORE_RELPATH
    return undeclared_patterns(path.read_text(encoding="utf-8") if path.is_file() else "")


@dataclass
class IgnoreBlockResult:
    """What :func:`ensure_ignore_block` did, so the caller can report it.

    Editing someone's ``.gitignore`` silently would be its own surprise.
    """

    path: Path | None = None
    added: list[str] = field(default_factory=list)
    skipped_reason: str = ""


def _git_root(project_root: Path) -> Path | None:
    """The enclosing git working tree, or ``None``.

    Walks upward because a project root is often a package inside a repository,
    where a ``.gitignore`` beside it is still honoured. ``.git`` may be a file
    (worktrees, submodules), so existence is the test rather than directory-ness.
    """
    for candidate in (project_root, *project_root.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _declared_patterns(text: str) -> set[str]:
    """Every pattern the file already declares, comments and blanks excluded."""
    return {
        stripped
        for line in text.splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    }


def _comment(text: str) -> list[str]:
    """Wrap *text* as ignore-file comment lines."""
    return [f"# {line}" for line in textwrap.wrap(text, width=_WRAP)]


def _render(entries: list[IgnoreEntry]) -> str:
    """The block: a marker, why it is here, then each pattern under its reason."""
    lines = [BLOCK_MARKER, *_comment(_HEADER)]
    for entry in entries:
        lines.extend(["", *_comment(entry.why), entry.pattern])
    return "\n".join(lines) + "\n"


def ensure_ignore_block(project_root: Path) -> IgnoreBlockResult:
    """Append the working-set ignore block to *project_root*'s ``.gitignore``, once.

    Does nothing when the block marker is already present (the file is the
    project's from then on), when every pattern is declared some other way, or
    when the project is not under git — an ignore file for a VCS the project does
    not use is noise, and which VCS it does use is not ours to guess.
    """
    result = IgnoreBlockResult()
    if _git_root(project_root) is None:
        result.skipped_reason = "not inside a git working tree — no .gitignore written"
        return result

    path = project_root / IGNORE_RELPATH
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if BLOCK_MARKER in existing:
        result.path = path
        result.skipped_reason = (
            "the Beadloom block is already in .gitignore — left exactly as it is"
        )
        return result

    missing = [finding.entry for finding in undeclared_patterns(existing)]
    if not missing:
        result.path = path
        result.skipped_reason = (
            "every generated path is already ignored — .gitignore left untouched"
        )
        return result

    prefix = existing if not existing or existing.endswith("\n") else existing + "\n"
    separator = "\n" if prefix else ""
    path.write_text(prefix + separator + _render(missing), encoding="utf-8")
    result.path = path
    result.added = [entry.pattern for entry in missing]
    return result
