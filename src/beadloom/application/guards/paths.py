# beadloom:domain=application
# beadloom:feature=flow-guards
"""Resolving the edit path a guard is asked about (BDL-061 S1 fix).

Why this is a module and not one line on the request object: the path arrives
from the harness as ``tool_input.file_path`` — i.e. from the model — and it is
the input to exclusion matching, which decides whether a guard runs at all.
Matching an unresolved string made every declared exclusion a skeleton key:
with ``scripts/**`` declared, ``scripts/../src/app.py`` matched the pattern and
skipped, while the write landed on ``src/app.py`` and the printed reason
("excluded by 'scripts/**'") was true about the string and false about the file.

Two decisions, both about what a path means rather than how it is spelled:

**Resolve, don't merely normalise.** :meth:`Path.resolve` collapses ``..`` *and*
follows symlinks. A purely lexical ``normpath`` closes the traversal spelling
and leaves the symlink one open — a link inside an excluded directory would
still carry the exemption out to its target. A write lands on the target, so the
target is what the guard must be told about.

**A path that resolves OUTSIDE the project root is matched against no
exclusion, and the verdict says so.** The alternatives were rejected for being
silent: inheriting a pattern gives an out-of-project write the same reassuring
skip as an in-project one, and refusing the path outright turns a legitimate
edit elsewhere on the machine into a guard error. So the guard still runs on its
other evidence, no exclusion applies (an exclusion is written about *this*
project's tree and cannot speak for anything else), and ``not_covered`` carries
:data:`OUTSIDE_ROOT_NOT_COVERED` naming the resolved target. What is deliberately
NOT claimed: the guard does not decide whether editing outside the project is
acceptable — no shipped guard has that condition, and inventing one here would
be a policy nobody declared.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

#: Stated in ``not_covered`` when the target resolved outside the project root.
OUTSIDE_ROOT_NOT_COVERED = (
    "the edit target {target} resolves outside the project root, so no "
    "exclusion in flow.yml was applied to it"
)

#: Used in messages when the harness supplied no path at all.
UNNAMED_TARGET = "an unnamed file"


class PathScope(str, Enum):
    """Where the caller-supplied path landed relative to the project root."""

    ABSENT = "absent"
    INSIDE = "inside"
    OUTSIDE = "outside"


@dataclass(frozen=True)
class ResolvedEditPath:
    """A caller-supplied path after resolution, with its scope made explicit.

    ``relative`` is populated **only** for :attr:`PathScope.INSIDE`, because it
    is the value exclusion patterns are matched against and a pattern must never
    be applied to something outside the tree it was written about.
    """

    scope: PathScope
    relative: str | None = None
    label: str = UNNAMED_TARGET

    @property
    def not_covered_note(self) -> str:
        """What this resolution left unverified, or ``""`` when nothing did."""
        if self.scope is PathScope.OUTSIDE:
            return OUTSIDE_ROOT_NOT_COVERED.format(target=self.label)
        return ""


def _resolved(path: Path) -> Path:
    """``Path.resolve`` that tolerates a path which does not exist yet.

    An edit guard is asked about files *before* they are written, so a strict
    resolve would fail on exactly the case the guard exists for.
    """
    try:
        return path.resolve()
    except OSError:  # e.g. a symlink loop — treat as unresolvable, keep it lexical
        return Path(str(path))


def resolve_edit_path(raw: str | None, project_root: Path) -> ResolvedEditPath:
    """Resolve *raw* against *project_root* and classify where it landed."""
    if raw is None or not raw.strip():
        return ResolvedEditPath(scope=PathScope.ABSENT)
    candidate = Path(raw.strip())
    if not candidate.is_absolute():
        candidate = project_root / candidate
    target = _resolved(candidate)
    root = _resolved(project_root)
    try:
        relative = target.relative_to(root)
    except ValueError:
        return ResolvedEditPath(scope=PathScope.OUTSIDE, label=target.as_posix())
    text = relative.as_posix()
    return ResolvedEditPath(scope=PathScope.INSIDE, relative=text, label=text)
