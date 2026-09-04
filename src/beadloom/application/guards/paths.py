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
no C0 control character or ``DEL``, no directory separator this platform does
not use, no leading ``~``, no component this platform's own name layer would
rewrite, and can be encoded for this filesystem (:func:`os.fsencode`). Each rule
removes a spelling that means one file to this guard and a different one to
whoever writes it: a NUL ends the name in the C layer, ``~`` is expanded by a
shell and not by us, and a string the filesystem cannot encode names nothing at
all. Anything outside the shape is :attr:`PathScope.MALFORMED` — refused with a
stated reason, never repaired, never resolved, and never matched against an
exclusion. What is NOT part of the shape, deliberately: a length limit (a long
path resolves to exactly what it says; the OS enforces its own maximum) and
percent-encoding (nothing here decodes it, so ``%2e%2e`` names a directory
called ``%2e%2e``).

**The two platform rules are stated over a SHAPE, not over a spelling
(``beadloom-mr2l.60``).** Until this fix the module refused a backslash
unconditionally, on the reasoning that it "separates directories on the harness's
platform and is an ordinary file-name character on this one" — two clauses that
are each true and that describe two different platforms, while the guard runs in
the harness's own process tree, where there is one. Measured there rather than
argued: this module reads no ``sys.platform`` and no ``os.name``, and the refusal
returns before :func:`os.fsencode`, so it was one code path on every operating
system — and on Windows, where ``os.path.join`` produces exactly that spelling,
every edit target was ``MALFORMED`` and every guarded edit an ``error`` at exit 2,
with a remediation ("supply the target as a POSIX path") the harness there cannot
carry out. What the rule is actually about is the SEPARATOR: a spelling this
platform reads as one names the file the writer will touch, and a spelling it
does not names a file whose reading the guard cannot settle. So the refusal is now
over :data:`SEPARATOR_SPELLINGS` minus this platform's own, which on a POSIX
machine is the same single character as before and on Windows is nothing.

**And what the shape gate then owes on Windows, which it never asked.** The
Win32 name layer REWRITES what it is handed: it strips a trailing dot or space,
and it resolves a reserved device name (``CON``, ``NUL``, ``LPT1``…) to a
character device in whatever directory it appears. Both are the guard-and-writer
divergence this module exists for, and each is a stronger argument for a refusal
than the backslash ever was. Deliberately NOT refused there: the characters
Win32 forbids outright (``<>:"|?*``). A write to such a name FAILS, loudly, so
the guard and the writer do not end up looking at different files — nothing is
written at all — and refusing it here would be the guard inventing a policy about
names rather than protecting its own answer.

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

import ntpath
import os
import posixpath
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING

from beadloom.application.guards.models import exception_detail

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class PathFlavour:
    """How one platform reads a file name, as the three facts this gate needs.

    A flavour is an ARGUMENT rather than a lookup, so the rules below can be
    exercised for a platform this project has no runner for: ``beadloom-mr2l.64``
    withdrew the ``tests-windows`` leg on a measured cost, and a rule that can
    only be reasoned about there is how the refusal this bead repairs survived
    for a release. It is the same technique ``tests/room_simulation.py`` applies
    to a CI leg — the platform is a substitutable input, so its answer is
    measured on the machine at hand instead of predicted.

    ``parser`` is the stdlib's own reader for that platform, so what counts as a
    component is :mod:`pathlib`'s answer and not a hand-rolled split.
    ``separators`` comes from :mod:`ntpath` / :mod:`posixpath`, so the spellings
    are the ones the platform declares. ``rewrites_names`` is the one fact with
    no stdlib spelling: whether the platform's name layer changes a name on its
    way to the filesystem — Win32 strips a trailing dot or space and redirects a
    reserved device name, while the POSIX layer passes the bytes through.
    """

    parser: type[PurePath]
    separators: frozenset[str]
    rewrites_names: bool


#: The two flavours Python itself implements. Both are importable everywhere,
#: which is what makes the other platform's rules measurable on this one.
POSIX_PATHS = PathFlavour(
    parser=PurePosixPath,
    separators=frozenset({posixpath.sep}),
    rewrites_names=False,
)
WINDOWS_PATHS = PathFlavour(
    parser=PureWindowsPath,
    separators=frozenset({ntpath.sep, ntpath.altsep}),
    rewrites_names=True,
)

#: The flavour the guard and the writer share, derived from what :mod:`os`
#: declares about this platform rather than from its name. ``os.sep`` is the
#: whole test: the platform that separates directories with a backslash is the
#: one whose name layer rewrites names, and there is exactly one.
NATIVE_PATHS = WINDOWS_PATHS if os.sep == ntpath.sep else POSIX_PATHS

#: Every spelling of a directory separator, as the union of what the two
#: flavours declare — derived, so a third flavour would widen it by being added
#: rather than by someone remembering to.
SEPARATOR_SPELLINGS = POSIX_PATHS.separators | WINDOWS_PATHS.separators


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

#: How to get past a refusal — stated, because a verdict nobody can act on is
#: noise, and stated in this platform's own spellings, because a remediation
#: naming a platform is a way out only on that one. It used to read "supply the
#: target as a POSIX path", which on Windows names something the harness there
#: cannot produce.
MALFORMED_REMEDIATION_TEMPLATE = (
    "supply the target as a path this platform spells literally ({separators} "
    "between directories, no control characters, no leading '~'{extra}), or set "
    "this guard's strictness to 'off' in flow.yml if such a name is legitimate "
    "in this project"
)

#: The clause the template adds where the platform's name layer rewrites names.
REWRITING_REMEDIATION_CLAUSE = (
    ", and no component this platform's name layer would rewrite — a reserved "
    "device name, or a trailing dot or space"
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
FOREIGN_SEPARATOR_REJECTION = (
    "it contains {name}, which separates directories on the platform that "
    "spelling comes from and is an ordinary file-name character on this one, so "
    "the guard cannot tell whether it names one file or several, and it refuses "
    "rather than choose"
)
TRAILING_REJECTION = (
    "the component {component} ends in {ending}, which this platform's name "
    "layer strips before the write reaches the filesystem, so the guard would "
    "record one file and the writer would create another"
)
RESERVED_DEVICE_REJECTION = (
    "the component {component} is a reserved device name on this platform, so "
    "the write would reach that device rather than any file the guard could name"
)
HOME_PREFIX_REJECTION = (
    "it starts with '~', a shell abbreviation this guard does not expand"
)
UNENCODABLE_REJECTION = "it cannot be encoded for this filesystem ({detail})"
UNRESOLVABLE_REJECTION = "it could not be resolved ({detail})"

#: How each separator spelling is named to a human. A rule quantified over a set
#: of characters still has to print one, and ``'\\\\'`` in a hook's stderr is not
#: a word a reader can act on.
SEPARATOR_NAMES = {"\\": "a backslash", "/": "a forward slash"}

#: The endings the Win32 name layer removes, named the same way and for the same
#: reason. A trailing tab is not here: it is already a C0 control character.
REWRITTEN_ENDINGS = {".": "a dot", " ": "a space"}

#: The names Win32 resolves to a character device wherever they appear — in any
#: directory, and whatever extension follows (``CON.md`` is the console too).
#: Written as ranges rather than as twenty-two literals, because a range is what
#: the platform documents and a literal list is a thing to keep in step with it.
RESERVED_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)

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


def malformed_remediation(flavour: PathFlavour = NATIVE_PATHS) -> str:
    """How to spell a target *flavour* accepts, as a sentence a human can act on."""
    separators = " or ".join(repr(spelling) for spelling in sorted(flavour.separators))
    extra = REWRITING_REMEDIATION_CLAUSE if flavour.rewrites_names else ""
    return MALFORMED_REMEDIATION_TEMPLATE.format(separators=separators, extra=extra)


def _foreign_separator(raw: str, flavour: PathFlavour) -> str:
    """Why *raw* carries a separator spelling *flavour* does not read as one."""
    for spelling in sorted(SEPARATOR_SPELLINGS - flavour.separators):
        if spelling in raw:
            return FOREIGN_SEPARATOR_REJECTION.format(name=SEPARATOR_NAMES[spelling])
    return ""


def _rewritten_component(raw: str, flavour: PathFlavour) -> str:
    """Why a component of *raw* is one *flavour*'s name layer would not keep.

    Every component, not only the last: a directory called ``src.`` is stripped
    to ``src`` by the same layer, and a device name resolves to the device in
    whatever position it appears. The components are :mod:`pathlib`'s, taken
    through the flavour's own parser, so what counts as one is the platform's
    answer rather than a split written here.
    """
    for component in flavour.parser(raw).parts:
        ending = REWRITTEN_ENDINGS.get(component[-1:], "")
        if ending:
            return TRAILING_REJECTION.format(component=repr(component), ending=ending)
        if component.partition(".")[0].upper() in RESERVED_DEVICE_NAMES:
            return RESERVED_DEVICE_REJECTION.format(component=repr(component))
    return ""


def rejection_reason(raw: str, *, flavour: PathFlavour = NATIVE_PATHS) -> str:
    """Why *raw* is outside the accepted shape, or ``""`` when it is inside it.

    Purely lexical, and deliberately so: it runs *before* anything touches the
    filesystem, which is where the NUL crash came from. Order is by cost of
    being wrong, not by likelihood — and the two platform rules are decided
    before :func:`os.fsencode`, the one call here whose behaviour a platform
    owns, so their answer for *flavour* is the same on whatever machine asks.
    That is what lets the Windows rules be measured without a Windows kernel,
    which is the only way they are measured at all (``beadloom-mr2l.64``).
    """
    for index, char in enumerate(raw):
        code = ord(char)
        if code <= _LAST_CONTROL or code == _DELETE:
            return CONTROL_CHARACTER_REJECTION.format(
                code=f"U+{code:04X}", index=index
            )
    foreign = _foreign_separator(raw, flavour)
    if foreign:
        return foreign
    if raw.startswith("~"):
        return HOME_PREFIX_REJECTION
    if flavour.rewrites_names:
        rewritten = _rewritten_component(raw, flavour)
        if rewritten:
            return rewritten
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


def resolve_edit_path(
    raw: str | None, project_root: Path, *, flavour: PathFlavour = NATIVE_PATHS
) -> ResolvedEditPath:
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
    rejection = rejection_reason(supplied, flavour=flavour)
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
