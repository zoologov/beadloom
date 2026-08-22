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

**Accept a narrow shape; refuse the rest.** The first fix closed ``..`` and
opened a NUL: ``Path.resolve`` calls ``lstat``, which rejects an embedded NUL
with ``ValueError``, so a model-supplied string produced no verdict at all. Both
defects have one root — an arbitrary string was *normalised*, and every
normalisation is a guess about what the harness will write. So the input is
narrowed instead. A well-formed edit target is a non-empty string that carries
no C0 control character or ``DEL``, no backslash, no leading ``~``, and can be
encoded for this filesystem (:func:`os.fsencode`). Each rule removes a spelling
that means one file to this guard and a different one to whoever writes it: a
NUL ends the name in the C layer, a backslash separates directories on the
harness's platform and does not here, ``~`` is expanded by a shell and not by
us, and a string the filesystem cannot encode names nothing at all. Anything
outside the shape is :attr:`PathScope.MALFORMED` — refused with a stated reason,
never repaired, never resolved, and never matched against an exclusion. What is
NOT part of the shape, deliberately: a length limit (a long path resolves to
exactly what it says; the OS enforces its own maximum) and percent-encoding
(nothing here decodes it, so ``%2e%2e`` names a directory called ``%2e%2e``).

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

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

#: Stated in ``not_covered`` when the target resolved outside the project root.
OUTSIDE_ROOT_NOT_COVERED = (
    "the edit target {target} resolves outside the project root, so no "
    "exclusion in flow.yml was applied to it"
)

#: Stated in ``not_covered`` when the target was refused before anything ran.
MALFORMED_NOT_COVERED = (
    "everything this guard checks: the edit target {label} was refused as "
    "malformed before any exclusion or check was applied to it"
)

#: The ``why`` of the verdict a refused target produces.
MALFORMED_WHY = "the supplied edit target is not a well-formed path: {rejection}"

#: How to get past a refusal — stated, because a verdict nobody can act on is noise.
MALFORMED_REMEDIATION = (
    "supply the target as a POSIX path ('/' separators, no control characters, "
    "no leading '~'), or set this guard's strictness to 'off' in flow.yml if "
    "such a name is legitimate in this project"
)

#: Used in messages when the harness supplied no path at all.
UNNAMED_TARGET = "an unnamed file"

#: Why one rule of the accepted shape refused this path. One sentence each,
#: naming the offence rather than the rule, because the reader has to fix a path
#: and not look up a specification.
CONTROL_CHARACTER_REJECTION = (
    "it contains a control character ({code}) at position {index}, and the "
    "layer that writes the file may read the name as ending there"
)
BACKSLASH_REJECTION = (
    "it contains a backslash, which separates directories on the harness's "
    "platform and is an ordinary file-name character on this one, so the guard "
    "and the writer would not be looking at the same file"
)
HOME_PREFIX_REJECTION = (
    "it starts with '~', a shell abbreviation this guard does not expand"
)
UNENCODABLE_REJECTION = "it cannot be encoded for this filesystem ({detail})"
UNRESOLVABLE_REJECTION = "the operating system refused to resolve it ({detail})"

#: Highest code point treated as a C0 control character, and the DEL code point.
_LAST_CONTROL = 0x1F
_DELETE = 0x7F

#: How much of a refused target is echoed back. A refusal is read by a human in
#: a hook's stderr and stored in the firing record; neither is a place for an
#: unbounded model-supplied string.
_LABEL_LIMIT = 120


class PathScope(str, Enum):
    """Where the caller-supplied path landed relative to the project root."""

    ABSENT = "absent"
    INSIDE = "inside"
    OUTSIDE = "outside"
    MALFORMED = "malformed"


@dataclass(frozen=True)
class ResolvedEditPath:
    """A caller-supplied path after resolution, with its scope made explicit.

    ``relative`` is populated **only** for :attr:`PathScope.INSIDE`, because it
    is the value exclusion patterns are matched against and a pattern must never
    be applied to something outside the tree it was written about — nor to
    something the guard has refused to interpret.

    ``rejection`` is populated **only** for :attr:`PathScope.MALFORMED`, and it
    says which rule of the accepted shape the path broke.
    """

    scope: PathScope
    relative: str | None = None
    label: str = UNNAMED_TARGET
    rejection: str = ""

    @property
    def not_covered_note(self) -> str:
        """What this resolution left unverified, or ``""`` when nothing did."""
        if self.scope is PathScope.OUTSIDE:
            return OUTSIDE_ROOT_NOT_COVERED.format(target=self.label)
        if self.scope is PathScope.MALFORMED:
            return MALFORMED_NOT_COVERED.format(label=self.label)
        return ""


def rejection_reason(raw: str) -> str:
    """Why *raw* is outside the accepted shape, or ``""`` when it is inside it.

    Purely lexical, and deliberately so: it runs *before* anything touches the
    filesystem, which is where the NUL crash came from. Order is by cost of
    being wrong, not by likelihood.
    """
    for index, char in enumerate(raw):
        code = ord(char)
        if code <= _LAST_CONTROL or code == _DELETE:
            return CONTROL_CHARACTER_REJECTION.format(
                code=f"U+{code:04X}", index=index
            )
    if "\\" in raw:
        return BACKSLASH_REJECTION
    if raw.startswith("~"):
        return HOME_PREFIX_REJECTION
    try:
        os.fsencode(raw)
    except ValueError as exc:  # UnicodeEncodeError: a lone surrogate names no file
        return UNENCODABLE_REJECTION.format(detail=exc)
    return ""


def _echo(supplied: str) -> str:
    """The supplied target, escaped and bounded, safe to print and to store."""
    text = repr(supplied)
    if len(text) <= _LABEL_LIMIT:
        return text
    return text[:_LABEL_LIMIT] + "…"


def _malformed(label: str, rejection: str) -> ResolvedEditPath:
    """The refusal, with the offending target echoed back for the reader."""
    return ResolvedEditPath(
        scope=PathScope.MALFORMED, label=label, rejection=rejection
    )


def resolve_edit_path(raw: str | None, project_root: Path) -> ResolvedEditPath:
    """Resolve *raw* against *project_root* and classify where it landed.

    Whitespace at either end is stripped as a transport artifact before the
    shape is judged. The cost is named rather than hidden: a file whose name
    genuinely ends in a space is guarded as though it did not.
    """
    if raw is None or not raw.strip():
        return ResolvedEditPath(scope=PathScope.ABSENT)
    supplied = raw.strip()
    label = _echo(supplied)
    rejection = rejection_reason(supplied)
    if rejection:
        return _malformed(label, rejection)
    candidate = Path(supplied)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    try:
        target = candidate.resolve()
        root = project_root.resolve()
    except (OSError, ValueError) as exc:
        # Unreachable for every input the shape gate admits today — which is
        # exactly why it is here. The property this module exists to hold is
        # "no supplied path ends in a traceback", and that property cannot be
        # made to depend on having enumerated every future refusal of the OS.
        return _malformed(label, UNRESOLVABLE_REJECTION.format(detail=exc))
    try:
        relative = target.relative_to(root)
    except ValueError:
        return ResolvedEditPath(scope=PathScope.OUTSIDE, label=target.as_posix())
    text = relative.as_posix()
    return ResolvedEditPath(scope=PathScope.INSIDE, relative=text, label=text)
