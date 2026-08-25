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
  say otherwise;
* one of its exclusions has outlived the date it gave itself — the exit
  condition arrived and nothing announced it (BDL-061.49). Reported, never
  enforced: an exclusion does not stop applying on a calendar day, because a
  guard that starts blocking with no commit behind it is a worse failure than
  the one being reported.

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
from beadloom.application.guards.firing import read_carried, read_firings
from beadloom.application.guards.models import GuardOutcome

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from beadloom.application.guards.config import GuardsConfig, GuardSpec
    from beadloom.application.guards.firing import Carried, FiringRecord

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
    never_fired: bool  # no firing that reached a verdict; `error` records do not count
    excluded_everywhere: bool
    last_fired_at: str = ""
    last_outcome: str = ""
    dead_exclusions: tuple[str, ...] = ()
    expired_exclusions: tuple[str, ...] = ()
    #: How many of ``fired_count`` come from the carried summary rather than
    #: from a record still on the active file (BDL-061.56). Reported so a reader
    #: can tell a count backed by readable firings from one backed by a rotated
    #: total — the number is the same, the evidence behind it is not.
    carried_count: int = 0

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
            "expired_exclusions": list(self.expired_exclusions),
            "carried_count": self.carried_count,
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


def expired_exclusions(spec: GuardSpec, *, today: date | None = None) -> tuple[str, ...]:
    """Declared patterns whose stated exit condition is a date that has passed.

    Answered from the configuration alone — unlike :func:`dead_exclusions` this
    needs no tree, because a deadline is a property of the entry. An exclusion
    whose ``until`` names an event rather than a date is never listed: it is not
    unexpired, it is uncheckable, and saying so is the SPEC's job, not a row's.
    """
    return tuple(
        exclusion.path for exclusion in spec.exclusions if exclusion.expired(today)
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
    carried: Carried,
) -> GuardLiveness:
    """Build one liveness row from the config, the recorded firings and the tree.

    *carried* holds the firings that have rotated out of the active record
    (BDL-061.56). It is added to every answer this row gives, because a rotation
    that reduced ``fired_count`` would let a bounded file report a live guard as
    ``never-fired`` — the exact silence the report exists to break.
    """
    spec = config.spec_for(name)
    own = [record for record in firings if record.guard == name]
    summary = carried.for_guard(name)
    last = own[-1] if own else None
    # An `error` record is evidence the guard RAN and did NOT answer, so it is
    # counted in fired_count and does not clear `never-fired`. Counting it as a
    # firing would let a guard that has never once reached a verdict read as a
    # live gate — the same silence the report exists to break.
    answered = [record for record in own if record.outcome != GuardOutcome.ERROR.value]
    carried_answered = summary.answered if summary else 0
    last_at = last.at if last else (summary.last_at if summary else "")
    last_outcome = last.outcome if last else (summary.last_outcome if summary else "")
    return GuardLiveness(
        guard=name,
        declared=spec.declared,
        strictness=spec.strictness_for(None),
        fired_count=len(own) + (summary.count if summary else 0),
        never_fired=not answered and not carried_answered,
        excluded_everywhere=spec.excluded_everywhere(),
        last_fired_at=last_at,
        last_outcome=last_outcome,
        dead_exclusions=dead_exclusions(spec, files),
        expired_exclusions=expired_exclusions(spec),
        carried_count=summary.count if summary else 0,
    )


def build_liveness(project_root: Path) -> tuple[GuardLiveness, ...]:
    """Liveness rows for every registered guard, in deterministic name order."""
    config = load_guards_config(project_root)
    firings = read_firings(project_root)
    carried = read_carried(project_root)
    files = project_files(project_root) if any(
        config.spec_for(name).exclusions for name in GUARD_NAMES
    ) else ()
    return tuple(_row(name, config, firings, files, carried) for name in GUARD_NAMES)
