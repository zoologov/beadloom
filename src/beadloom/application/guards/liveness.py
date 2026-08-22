# beadloom:domain=application
# beadloom:feature=flow-guards
"""Liveness — which guards are actually doing anything (BDL-061 S1).

Three ways a gate stops protecting anything without anyone noticing, all
reported per guard alongside the firing evidence by ``beadloom guard
--liveness``:

* it is configured off, or excluded everywhere (a catch-all pattern);
* it simply never fires;
* one of its exclusions matches nothing that exists — the author believes a
  directory is exempt and it is not, and only a reread of ``flow.yml`` would
  say otherwise.

The third needs the project's tree, which is why it is answered here rather than
on :class:`~beadloom.application.guards.config.GuardSpec`: "is this pattern a
catch-all" is a question about the pattern, "does this pattern match anything"
is a question about the project. Two questions, two homes, neither pretending to
answer the other.

This module reads; it decides nothing. Whether an idle guard should fail a build
is the Gate's question (S2+), and folding that policy in here would make the
report unusable on a fresh clone, where every guard is legitimately idle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.application.guards.checks import GUARD_NAMES
from beadloom.application.guards.config import load_guards_config
from beadloom.application.guards.firing import read_firings

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.guards.config import GuardsConfig, GuardSpec
    from beadloom.application.guards.firing import FiringRecord

#: Directories never descended when listing the project's own files. Vendor and
#: build trees are not what an exclusion is written about, and walking them turns
#: a report into a minute.
_UNWALKED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".tox",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        "site",
        "target",
    }
)

#: Upper bound on files listed. A report must stay cheap; past this many paths a
#: pattern that has matched nothing yet is overwhelmingly likely to be dead
#: anyway, and the cap only ever makes the report quieter, never louder.
_MAX_FILES = 20_000


@dataclass(frozen=True)
class GuardLiveness:
    """One guard's liveness row."""

    guard: str
    declared: bool
    strictness: str
    fired_count: int
    never_fired: bool
    excluded_everywhere: bool
    last_fired_at: str = ""
    last_outcome: str = ""
    dead_exclusions: tuple[str, ...] = ()

    @property
    def idle(self) -> bool:
        """True when this guard protects nothing right now."""
        return self.never_fired or self.excluded_everywhere

    def to_dict(self) -> dict[str, object]:
        """JSON-ready mapping for ``--liveness --json``."""
        return {
            "guard": self.guard,
            "declared": self.declared,
            "strictness": self.strictness,
            "fired_count": self.fired_count,
            "never_fired": self.never_fired,
            "excluded_everywhere": self.excluded_everywhere,
            "last_fired_at": self.last_fired_at,
            "last_outcome": self.last_outcome,
            "idle": self.idle,
            "dead_exclusions": list(self.dead_exclusions),
        }


def dead_exclusions(spec: GuardSpec, project_files: tuple[str, ...]) -> tuple[str, ...]:
    """Declared patterns that match no file currently in *project_files*.

    An empty file list yields nothing rather than everything: a tree that could
    not be read makes every pattern look dead, and a report that cries wolf on a
    fresh or unreadable checkout is one nobody reads twice.

    Stated precisely, because the wording is the value: a named pattern matches
    nothing that exists **right now**. It is not a claim that the pattern can
    never match — a directory added tomorrow revives it.
    """
    if not project_files:
        return ()
    return tuple(
        exclusion.path
        for exclusion in spec.exclusions
        if not any(exclusion.matches(path) for path in project_files)
    )


def project_files(project_root: Path) -> tuple[str, ...]:
    """Project-relative POSIX paths of the files an exclusion could match.

    Symlinks are not followed — a link is not an extra file to protect, and
    following them invites a cycle.
    """
    found: list[str] = []
    stack = [project_root]
    while stack and len(found) < _MAX_FILES:
        try:
            entries = sorted(stack.pop().iterdir())
        except OSError:  # unreadable directory — report what is readable
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in _UNWALKED_DIRS:
                    stack.append(entry)
            elif entry.is_file():
                found.append(entry.relative_to(project_root).as_posix())
                if len(found) >= _MAX_FILES:
                    break
    return tuple(sorted(found))


def _row(
    name: str,
    config: GuardsConfig,
    firings: tuple[FiringRecord, ...],
    files: tuple[str, ...],
) -> GuardLiveness:
    """Build one liveness row from the config, the recorded firings and the tree."""
    spec = config.spec_for(name)
    own = [record for record in firings if record.guard == name]
    last = own[-1] if own else None
    return GuardLiveness(
        guard=name,
        declared=spec.declared,
        strictness=spec.strictness_for(None),
        fired_count=len(own),
        never_fired=not own,
        excluded_everywhere=spec.excluded_everywhere(),
        last_fired_at=last.at if last else "",
        last_outcome=last.outcome if last else "",
        dead_exclusions=dead_exclusions(spec, files),
    )


def build_liveness(project_root: Path) -> tuple[GuardLiveness, ...]:
    """Liveness rows for every registered guard, in deterministic name order."""
    config = load_guards_config(project_root)
    firings = read_firings(project_root)
    files = project_files(project_root) if any(
        config.spec_for(name).exclusions for name in GUARD_NAMES
    ) else ()
    return tuple(_row(name, config, firings, files) for name in GUARD_NAMES)
