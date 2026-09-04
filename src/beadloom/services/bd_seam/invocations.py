"""One grammar for "this text or this argv invokes ``bd``", used by every consumer.

CONTEXT Q4 decided the shape of the answer to every External ``bd`` finding:
derive our own call sites and assert what each assumes about bd's answer, never
wrap the tool. A wrapper is a second thing to keep in step with upstream; a
derived population fails on a call site added later. This module is the first
half of that — WHERE the calls are — and :mod:`.assumptions` is the second.

**Two channels, because this project instructs ``bd`` far more often than it
invokes it.** `beadloom-0mdo.58` measured the ratio while deriving S5's axes: a
sweep of Python source reaches about a twentieth of the subject. So:

* :func:`python_invocations` reads argv out of the source, from every call to the
  seam's :func:`~beadloom.services.bd_seam.client.run_bd`;
* :func:`text_invocations` reads the artifacts that TELL an agent to run ``bd``
  — the composed flow, the templates this project ships, the shell it writes and
  the git hooks on disk, including the ones it did not write.

**Over a shape, not a spelling, in both directions.** The text channel anchors on
COMMAND POSITION — ``bd`` at the start of a line, or after a backtick, a pipe, a
separator, an opening paren, a ``!`` or a quote — rather than on the word ``bd``
anywhere. Measured over this repository's 65 instructing artifacts, the anchor
returns 266 invocations and no prose: without it the same sweep also reports
``bd verifies``, ``bd checks the``, ``bd is available`` and ``a bd comment with``,
which instruct nobody. The Python channel reads the argument list rather than the
call's spelling, and resolves a module-level string constant, because
``guard_probes`` passes ``CLAIMED_STATUS`` and ``UNLIMITED`` and a literal-only
reader would report its most careful call site as unresolved.

**What it cannot resolve, it says.** An argument that is a runtime value is
counted rather than dropped, and the subcommand it belongs to is still reported:
``run_bd(["close", bead, "--suggest-next"])`` is a ``close`` whose bead id this
derivation cannot know, which is a different fact from a call it could not read.
"""

# beadloom:component=bd-seam

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "CHANNEL_HOOK",
    "CHANNEL_INSTRUCTION",
    "CHANNEL_PYTHON",
    "MAX_SUBCOMMAND_WORDS",
    "SEAM_FUNCTION",
    "UNRESOLVED",
    "BdInvocation",
    "python_invocations",
    "text_invocations",
]

#: The seam every ``bd`` call in this project's Python goes through. Spelled once
#: so a rename reddens one place rather than silently emptying the population.
SEAM_FUNCTION = "run_bd"

#: What stands in for an argument whose value is decided at runtime. It is a
#: placeholder in the recorded text and never a token the flag reader accepts.
UNRESOLVED = "<?>"

#: bd 1.0.4 nests its subcommands one level deep (``dep add``, ``merge-slot
#: acquire``, ``comments add``), taken from its own ``--help``. Two is therefore
#: the bound on how many leading words can name a subcommand, and it is what
#: stops ``bd dep add child parent`` reading its two bead ids as part of the name.
MAX_SUBCOMMAND_WORDS = 2

CHANNEL_PYTHON = "python"
CHANNEL_INSTRUCTION = "instruction"
CHANNEL_HOOK = "hook"

#: ``bd`` in COMMAND POSITION. The look-behinds are the places a command can
#: begin in the artifacts this project actually writes: the start of a line, an
#: opening backtick, a pipe or a shell separator, an opening paren (so ``$(bd
#: …)`` is read), a ``!`` (so ``if ! bd import`` in a git hook is read) and a
#: quote (so a hook's ``echo "Run 'bd import …'"`` is read). Prose ``bd`` is
#: preceded by a word and is therefore not an invocation.
_ANCHOR = r"(?:^|(?P<quote>[`'\"])|[|&;(!])"

#: The command line ends where a Markdown or shell construct ends it: a closing
#: backtick, a comment, a pipe, a separator, a closing paren. ``#`` matters most
#: — ``bd merge-slot release --holder <id>   # the only release form bd verifies``
#: is one invocation and a sentence, and only the first half is an instruction.
_INVOCATION = re.compile(_ANCHOR + r"\s*bd\s+(?P<rest>[a-z][^\n`|;&#)]*)")

#: When the invocation was anchored by a quote, that quote also ENDS it. A git
#: hook's ``echo "Run 'bd import -i $F' manually to see the error"`` is one
#: instruction and then prose about it, and only the first half is the command.
_CLOSING = {"'": "'", '"': '"', "`": "`"}

#: A shell prompt or an ordered-list bullet does not move a command out of
#: command position, so it is removed before the line is scanned.
_LINE_PREFIX = re.compile(r"^\s*(?:\$|>|\d+\.)\s+")

#: A redirection ends the part of the line that is arguments. Only the ``>``
#: forms and a ``<`` followed by space, because ``--holder <bead-id>`` is a
#: PLACEHOLDER and not an input redirect — a rule that cut at every ``<`` read
#: seventeen composed role cores as instructing `bd merge-slot release --holder`
#: with no holder, which is the opposite of what they say.
_REDIRECTION = re.compile(r"\s+\d*>.*$|\s+<\s.*$")

#: A positional word that can be part of a subcommand name. Lowercase with
#: hyphens, which is every subcommand bd 1.0.4 declares (``merge-slot``,
#: ``find-duplicates``, ``set-state``); a placeholder like ``<bead-id>``, a bead
#: id like ``beadloom-0mdo.51`` and a quoted title are all correctly not words.
_WORD = re.compile(r"^[a-z][a-z-]*$")


@dataclass(frozen=True)
class BdInvocation:
    """One place this project invokes or instructs ``bd``, before any judgement.

    ``words`` is the leading positional words, at most
    :data:`MAX_SUBCOMMAND_WORDS` of them, which is what :mod:`.assumptions`
    resolves a subcommand name from — the grammar deliberately does not know
    which names bd has, so the vocabulary lives with the measurements that
    judge it. ``flags`` is every ``-``-leading token with any ``=value`` cut off,
    so ``--limit=0`` and ``--limit 0`` are the same fact.

    ``unresolved_arguments`` counts the arguments whose value is decided at
    runtime. It is never a reason to omit the site: a ``close`` whose bead id
    this derivation cannot know is still a ``close``.
    """

    source: str
    line: int
    channel: str
    text: str
    words: tuple[str, ...]
    flags: tuple[str, ...]
    unresolved_arguments: int


def _tokens_of(argv: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split *argv* into its leading subcommand words and its flags."""
    words: list[str] = []
    flags: list[str] = []
    reading_words = True
    for token in argv:
        if token.startswith("-"):
            reading_words = False
            flags.append(token.split("=", 1)[0])
            continue
        if reading_words and len(words) < MAX_SUBCOMMAND_WORDS and _WORD.match(token):
            words.append(token)
            continue
        reading_words = False
    return tuple(words), tuple(flags)


def text_invocations(
    sources: Iterable[tuple[str, str]], *, channel: str = CHANNEL_INSTRUCTION
) -> tuple[BdInvocation, ...]:
    """Every ``bd`` invocation in *sources*, as ``(label, text)`` per artifact.

    Taken as data rather than as paths, like every other observation this
    project's checks read, so the derivation runs without a repository, without
    a scaffolded flow and without ``bd`` installed. Order is the order the
    artifacts were handed over and then by line, so a diff of two runs is a diff
    of the instructions.
    """
    found: list[BdInvocation] = []
    for label, text in sources:
        for number, raw in enumerate(text.splitlines(), start=1):
            line = _LINE_PREFIX.sub("", raw)
            for match in _INVOCATION.finditer(line):
                rest = match.group("rest")
                closing = _CLOSING.get(match.group("quote") or "")
                if closing is not None and closing in rest:
                    rest = rest[: rest.index(closing)]
                rest = _REDIRECTION.sub("", rest).strip()
                words, flags = _tokens_of(rest.split())
                if not words:
                    continue
                found.append(
                    BdInvocation(
                        source=label,
                        line=number,
                        channel=channel,
                        text=f"bd {rest}",
                        words=words,
                        flags=flags,
                        unresolved_arguments=0,
                    )
                )
    return tuple(found)


def _string_constants(tree: ast.Module) -> dict[str, str | list[str]]:
    """Module-level names bound to a string, or to a list this reader can read.

    Only module level, and only literals: a name assigned inside a function or
    computed at import time is a runtime value, and reporting it as resolved
    would be the false confidence this epic exists to remove.
    """
    resolved: dict[str, str | list[str]] = {}
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if not isinstance(target, ast.Name) or value is None:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            resolved[target.id] = value.value
        elif isinstance(value, ast.List):
            items = [
                element.value
                for element in value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            if len(items) == len(value.elts):
                resolved[target.id] = items
    return resolved


def _argv_of(
    call: ast.Call, constants: dict[str, str | list[str]]
) -> tuple[list[str], int] | None:
    """The argv of one ``run_bd`` call, with the count it could not resolve."""
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Name):
        bound = constants.get(first.id)
        return (list(bound), 0) if isinstance(bound, list) else None
    if not isinstance(first, ast.List):
        return None
    argv: list[str] = []
    unresolved = 0
    for element in first.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            argv.append(element.value)
            continue
        if isinstance(element, ast.Name):
            bound = constants.get(element.id)
            if isinstance(bound, str):
                argv.append(bound)
                continue
        argv.append(UNRESOLVED)
        unresolved += 1
    return argv, unresolved


def python_invocations(sources: Iterable[tuple[str, str]]) -> tuple[BdInvocation, ...]:
    """Every call to the seam in *sources*, as ``(label, source text)`` per module.

    A module this reader cannot parse is skipped rather than guessed at; the
    caller counts what it handed over, so a skipped module is visible as a gap
    between the two numbers rather than as a clean answer.
    """
    found: list[BdInvocation] = []
    for label, text in sources:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        constants = _string_constants(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name != SEAM_FUNCTION:
                continue
            read = _argv_of(node, constants)
            if read is None:
                continue
            argv, unresolved = read
            words, flags = _tokens_of(argv)
            if not words:
                continue
            found.append(
                BdInvocation(
                    source=label,
                    line=node.lineno,
                    channel=CHANNEL_PYTHON,
                    text="bd " + " ".join(argv),
                    words=words,
                    flags=flags,
                    unresolved_arguments=unresolved,
                )
            )
    return tuple(found)
