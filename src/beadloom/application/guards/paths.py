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

**A harness that supplies a COMMAND rather than a path resolves to nothing, and
the verdict says so.** The binding fires on the shell tool too (BDL-UX #170), and
what a shell command writes is not decidable: the targets a declared write shape
names are a *lower bound*, never the set. So such an edit is
:attr:`PathScope.UNDETERMINED` — ``relative`` stays ``None``, which is what makes
:meth:`~beadloom.application.guards.config.GuardSpec.exclusion_for` return
nothing, and the derived targets travel in ``not_covered`` instead. Feeding a
derived target to exclusion matching would exempt the writes the derivation could
not see: ``sed -i docs/a.md && python3 write_src.py`` names one and performs two.

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
from typing import TYPE_CHECKING

from beadloom.application.guards.models import exception_detail

if TYPE_CHECKING:
    from collections.abc import Sequence

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

#: Stated in ``not_covered`` when the harness supplied a shell command. The
#: sentence is one clause about the command plus one about the derivation,
#: because a reader who sees only "not derived" cannot tell whether the guard
#: looked at a command at all.
UNDETERMINED_NOT_COVERED = (
    "every file this shell command writes — {seen}. A command line's write set "
    "is not decidable, so no exclusion in flow.yml was applied to it"
)

#: The three ways the derivation can come up short, in the words of what it saw.
NOTHING_DERIVED = "no write target could be derived from it"
SOME_DERIVED = "it names {targets}, and any other write it performs was not derived"
UNREADABLE_COMMAND = "it could not be read ({detail}), so no target was derived from it"

#: How a shell command is named in a verdict a human reads.
COMMAND_TARGET = "a shell command"
COMMAND_TARGET_WITH_WRITES = "a shell command writing {targets}"

#: How many derived targets are echoed back. The list comes from a model-supplied
#: command line and lands in a firing record; the rest are counted, not printed.
_DERIVED_LIMIT = 5

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
UNRESOLVABLE_REJECTION = "it could not be resolved ({detail})"

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
    UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class ResolvedEditPath:
    """A caller-supplied path after resolution, with its scope made explicit.

    ``relative`` is populated **only** for :attr:`PathScope.INSIDE`, because it
    is the value exclusion patterns are matched against and a pattern must never
    be applied to something outside the tree it was written about — nor to
    something the guard has refused to interpret.

    ``rejection`` is populated **only** for :attr:`PathScope.MALFORMED`, and it
    says which rule of the accepted shape the path broke.

    ``derived`` and ``unreadable`` are populated **only** for
    :attr:`PathScope.UNDETERMINED`: the write targets a shell command line was
    seen to name, and why the command line could not be read at all. They are
    reported and never resolved — see the module docstring for why a derived
    target may not stand in for the path.
    """

    scope: PathScope
    relative: str | None = None
    label: str = UNNAMED_TARGET
    rejection: str = ""
    derived: tuple[str, ...] = ()
    unreadable: str = ""

    @property
    def not_covered_note(self) -> str:
        """What this resolution left unverified, or ``""`` when nothing did."""
        if self.scope is PathScope.OUTSIDE:
            return OUTSIDE_ROOT_NOT_COVERED.format(target=self.label)
        if self.scope is PathScope.MALFORMED:
            return MALFORMED_NOT_COVERED.format(label=self.label)
        if self.scope is PathScope.UNDETERMINED:
            return UNDETERMINED_NOT_COVERED.format(seen=self._derivation_note)
        return ""

    @property
    def _derivation_note(self) -> str:
        """What the derivation over the command line came back with."""
        if self.unreadable:
            return UNREADABLE_COMMAND.format(detail=self.unreadable)
        if self.derived:
            return SOME_DERIVED.format(targets=_echo_targets(self.derived))
        return NOTHING_DERIVED


def _echo_targets(targets: tuple[str, ...]) -> str:
    """The derived targets as a bounded, quoted list a human can read."""
    shown = ", ".join(repr(target) for target in targets[:_DERIVED_LIMIT])
    remaining = len(targets) - _DERIVED_LIMIT
    return f"{shown} and {remaining} more" if remaining > 0 else shown


def undetermined_target(
    targets: Sequence[str], *, unreadable: str = ""
) -> ResolvedEditPath:
    """The resolution of an edit the harness described as a shell command.

    Takes the derivation's output rather than the command, so that path
    resolution stays free of shell knowledge: what a command line means is
    :mod:`beadloom.application.guards.shell_targets`' question, and where a path
    lands is this module's.
    """
    ordered = tuple(targets)
    label = (
        COMMAND_TARGET_WITH_WRITES.format(targets=_echo_targets(ordered))
        if ordered
        else COMMAND_TARGET
    )
    return ResolvedEditPath(
        scope=PathScope.UNDETERMINED,
        label=label,
        derived=ordered,
        unreadable=unreadable,
    )


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

    **Nothing is removed before the shape is judged.** An earlier version
    stripped surrounding whitespace as "a transport artifact", and
    :meth:`str.strip` removes every character Python calls whitespace — which
    includes nine code points (``\t \n \v \f \r`` and ``U+001C``-``U+001F``)
    inside the C0 range this same module refuses, so the strip decided them in
    the ACCEPTING direction. Measured with ``src/*.py`` excluded and strictness
    ``block``: ``'src/app.py\n'`` skipped, quoting an exclusion that does not
    cover the file the writer would create (BDL-061.28, F10). Every stripped
    character is a legal file-name character on this platform, so removing any
    of them is the same guess the shape gate exists to stop making: the guard
    must be told the name the writer will use.

    The cost, named rather than implied: a target that arrives with a stray
    trailing newline is refused instead of evaluated — the over-guarding
    direction, with a stated reason and a way out, and no caller in this repo
    sends one (a JSON string carries no trailing newline, and shell command
    substitution removes it).
    """
    if not raw:
        return ResolvedEditPath(scope=PathScope.ABSENT)
    supplied = raw
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
    except Exception as exc:  # as wide as the sentence it holds; see below
        # AS WIDE AS THE SENTENCE IT HOLDS. The property is "no supplied path
        # ends in a traceback", and the previous handler was three words
        # narrower than that: `(OSError, ValueError)` with a comment declaring
        # the case unreachable. MEASURED on real interpreters, `a -> b -> a`:
        # 3.10.1 / 3.11.13 / 3.12.12 raise RuntimeError("Symlink loop from
        # ...") — neither an OSError nor a ValueError — while 3.13.7 raises
        # nothing at all. So the comment was false on three of the four
        # versions this project supports, and true only on the one the suite ran
        # on (BDL-061.36). Enumerating RuntimeError as a fourth class would fix
        # this loop and leave the next one open; what the sentence quantifies
        # over is every way a resolution can refuse.
        #
        # `Exception`, deliberately NOT `BaseException`: a KeyboardInterrupt or
        # a SystemExit arriving mid-resolution is the process being stopped, not
        # this path being refused, and reporting it as "the target is malformed"
        # would be a false statement about the caller's path. Those belong to
        # the invocation boundary, which catches BaseException and has a
        # distinct answer for them ("the evaluation was interrupted").
        return _malformed(label, UNRESOLVABLE_REJECTION.format(detail=exception_detail(exc)))
    try:
        relative = target.relative_to(root)
    except ValueError:
        return ResolvedEditPath(scope=PathScope.OUTSIDE, label=target.as_posix())
    text = relative.as_posix()
    return ResolvedEditPath(scope=PathScope.INSIDE, relative=text, label=text)
