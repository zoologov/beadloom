# beadloom:domain=application
# beadloom:feature=flow-guards
"""The contract a guard check is written against (BDL-061 S1).

A check receives a :class:`GuardRequest` — the project root, the evaluation
context supplied by the caller (``path``, ``tool``, ``work_kind``), and the
read-only **probes** it may consult — and returns a :class:`GuardFinding`. The
finding says only what the check observed; turning that into a
:class:`~beadloom.application.guards.models.GuardVerdict` (applying strictness
and exclusions) is the evaluator's job, so a check never has to know how strict
the project is.

**Ports, not calls.** A check reads the world exclusively through the probe
protocols declared here. Two reasons, in order of weight: the concrete work
tracker is the ``bd`` seam, which lives in the *services* layer that the
application layer must not import (``architecture-layers``, severity ``error``);
and a port keeps every check trivially exercisable against a stub while the real
adapters get their own tests against the real binaries.

**Read-only.** No probe writes anything, and no check touches ``beadloom.db`` —
a check that writes to the artifact it inspects cannot be trusted about it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


@dataclass(frozen=True)
class ClaimedBead:
    """A work item the tracker reports as claimed / in progress."""

    id: str
    title: str = ""


@runtime_checkable
class WorkTracker(Protocol):
    """Read port over the issue tracker (``bd``)."""

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        """Beads currently in progress, or ``None`` when the tracker is unavailable.

        ``None`` is not an empty tuple: "no bead is claimed" is a violation,
        while "the tracker could not be reached" is a skip.
        """


@runtime_checkable
class Workspace(Protocol):
    """Read port over the working copy (git)."""

    def current_branch(self) -> str | None:
        """Checked-out branch name, or ``None`` outside a branch / repo."""


class _UnavailableTracker:
    """Tracker port that reports unavailability — the honest default."""

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        return None


class _UnavailableWorkspace:
    """Workspace port that reports unavailability — the honest default."""

    def current_branch(self) -> str | None:
        return None


@dataclass(frozen=True)
class GuardProbes:
    """The read-only ports a check may consult.

    Defaults report "unavailable", so a caller that wires nothing gets honest
    ``skip`` verdicts rather than a false ``pass``.
    """

    tracker: WorkTracker = field(default_factory=_UnavailableTracker)
    workspace: Workspace = field(default_factory=_UnavailableWorkspace)


@dataclass(frozen=True)
class GuardRequest:
    """Everything a check is allowed to look at.

    ``context`` is per-invocation (what the harness reported about this edit);
    ``options`` is the guard's own configuration from ``flow.yml`` (e.g. the
    trunk branch name). They are kept apart because only ``context`` is echoed
    into the verdict and the firing record.
    """

    project_root: Path
    context: Mapping[str, str] = field(default_factory=dict)
    probes: GuardProbes = field(default_factory=GuardProbes)
    options: Mapping[str, str] = field(default_factory=dict)

    @property
    def path(self) -> str | None:
        """The file the caller is about to touch, as supplied (may be absolute)."""
        return self.context.get("path") or None

    @property
    def relative_path(self) -> str | None:
        """:attr:`path` normalized to a project-relative POSIX path, when possible."""
        raw = self.path
        if raw is None:
            return None
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                candidate = candidate.relative_to(self.project_root)
            except ValueError:
                return candidate.as_posix()
        return candidate.as_posix()

    @property
    def work_kind(self) -> str | None:
        """The kind of work in flight (``epic``/``bug``/``chore``), when supplied."""
        return self.context.get("work_kind") or None


@dataclass(frozen=True)
class GuardFinding:
    """What a check observed — before strictness is applied.

    ``skipped_because`` set means the check could not apply at all; otherwise
    ``satisfied`` says whether the guarded condition holds.
    """

    satisfied: bool
    why: str
    not_covered: tuple[str, ...] = ()
    remediation: str = ""
    skipped_because: str | None = None

    @classmethod
    def ok(cls, why: str, *, not_covered: tuple[str, ...] = ()) -> GuardFinding:
        """The guarded condition holds."""
        return cls(satisfied=True, why=why, not_covered=not_covered)

    @classmethod
    def violated(
        cls, why: str, *, remediation: str, not_covered: tuple[str, ...] = ()
    ) -> GuardFinding:
        """The guarded condition does not hold."""
        return cls(
            satisfied=False, why=why, not_covered=not_covered, remediation=remediation
        )

    @classmethod
    def skipped(cls, reason: str, *, not_covered: tuple[str, ...] = ()) -> GuardFinding:
        """The check does not apply here — always with a stated reason."""
        return cls(
            satisfied=True,
            why=reason,
            not_covered=not_covered,
            skipped_because=reason,
        )


@dataclass(frozen=True)
class Guard:
    """A registered guard: its name, what it guards, and the check itself."""

    name: str
    summary: str
    check: Callable[[GuardRequest], GuardFinding]
    default_events: tuple[str, ...] = ("edit",)
