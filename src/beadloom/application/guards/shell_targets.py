# beadloom:domain=application
# beadloom:feature=flow-guards
"""What a shell command line says about itself — a lower bound (BDL-UX #170).

The guard binding used to fire on ``Edit|Write|MultiEdit|NotebookEdit`` only, so
a file written through ``python3 - <<EOF``, ``sed -i`` or a redirection went
through the harness's shell tool and fired nothing at all. Widening the matcher
is one line; the reason it needs this module is the other half of the finding.

**What a shell command writes is not decidable.** ``sh -c "$CMD"``,
``python3 - <<EOF``, a Makefile target and a program compiled ten minutes ago all
write files this module cannot name. So the answer here is deliberately a *lower
bound*: the targets a declared set of write shapes names, and nothing about the
writes those shapes do not cover.

**A derived target therefore never grants an exemption.** It is reported —
:class:`~beadloom.application.guards.paths.PathScope.UNDETERMINED` carries it
into ``not_covered`` and into the firing record — and it is never matched against
an exclusion in ``flow.yml``. The reason is the lower bound itself: ``sed -i
docs/a.md && python3 write_src.py`` names one target this module can see and
performs one it cannot, so an exclusion applied to the visible half would exempt
the invisible one. The guard runs instead, which is the direction that fails
closed.

The shapes below are chosen for one property: the target's *position* is fixed by
the command's own interface rather than guessed from the string. Each is a shape
and not a spelling — ``>f``, ``> f`` and ``1> f`` are one shape, and the
tokenizer, not a regular expression, is what makes them one.

**The program name is read here too, and the leading environment assignments are
dropped whole (``beadloom-0mdo.43``).** The guard's context carries the name
instead of the line, so what the record keeps of ``VAR=value prog args`` must be
``prog``: reading the first token literally would keep exactly the value the
reduction exists to leave out, and ``GITHUB_TOKEN=… gh api …`` is the shape the
review's finding names. Measured on this repository's own record before the
change: 76 of 1 897 stored command lines began with an assignment. The variable
NAME is dropped with its value rather than kept — it is not something the guard
reasons about, and a name is one edit away from being a value again
(``AWS_SESSION_TOKEN`` is a name; ``pass=hunter2`` is the same shape).
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

#: Tokens that end one command and start another. ``(``/``)`` are separators too:
#: a subshell's contents are commands, and treating the parenthesis as an operand
#: would attribute the wrong argument position to whatever precedes it.
_SEPARATORS = frozenset({";", "&&", "||", "|", "|&", "&", "(", ")", "\n"})

#: Redirection operators whose next token is a file the command writes. ``>&`` is
#: absent on purpose: it duplicates a file descriptor and names no file, and the
#: tokenizer emits it as one token, so ``2>&1`` cannot be read as a write to 1.
_WRITE_REDIRECTIONS = frozenset({">", ">>", ">|"})


@dataclass(frozen=True)
class ShellCommand:
    """What a command line was read to be, and why the reading may be short.

    These three fields are the whole of what the guard learns from a shell
    edit, which is why they are also the whole of what its context and its
    firing record carry about one: a value nothing reasons about is a value
    stored for no reason.

    Attributes
    ----------
    name:
        The program the first command runs, as the line spells it, with any
        leading environment assignments dropped. ``""`` when no command word
        could be read — a line that is only a redirection, or one that could
        not be tokenized.
    targets:
        Paths a declared write shape names, deduplicated and sorted. A **lower
        bound** on the command's writes, never the set of them.
    unreadable:
        Why the command line could not be tokenized at all (unbalanced quoting),
        or ``""``. Distinct from an empty ``targets``: "nothing was derived" and
        "nothing could be read" are different facts about the same silence.
    """

    name: str = ""
    targets: tuple[str, ...] = ()
    unreadable: str = ""


#: Options of a declared writer that take their value as the NEXT word. Without
#: this the value is read as an operand, and an operand of a writer is read as a
#: file it writes: ``truncate -s 0 log`` named ``0``, and ``sed -i '' -e
#: 's/a/b/' f`` named the script. A wrong target is only ever a wrong sentence —
#: a derived target gates nothing — but a report that names a file nobody wrote
#: is the kind of confident wrongness this feature exists to stop producing.
_VALUE_OPTIONS = {
    "sed": frozenset({"-e", "-f", "--expression", "--file"}),
    "touch": frozenset({"-d", "-r", "-t", "--date", "--reference", "--time"}),
    "truncate": frozenset({"-s", "-r", "--size", "--reference"}),
    "cp": frozenset({"-t", "--target-directory", "-S", "--suffix"}),
    "mv": frozenset({"-t", "--target-directory", "-S", "--suffix"}),
    "ln": frozenset({"-t", "--target-directory", "-S", "--suffix"}),
    "install": frozenset({"-t", "--target-directory", "-m", "-o", "-g", "-S"}),
}


def _is_option(word: str) -> bool:
    """True for an option word. A lone ``-`` is an operand (it names stdin)."""
    return word.startswith("-") and len(word) > 1


def _partition(words: list[str]) -> tuple[list[str], list[str]]:
    """One command's options and its operands, its own name excluded.

    An option declared to take a separate value consumes the next word, so that
    word is neither an option nor an operand.
    """
    takes_value = _VALUE_OPTIONS.get(words[0].rpartition("/")[2], frozenset())
    options: list[str] = []
    operands: list[str] = []
    rest = iter(words[1:])
    for word in rest:
        if _is_option(word):
            options.append(word)
            if word in takes_value:
                next(rest, None)
        elif word:
            operands.append(word)
    return options, operands


def _sed_targets(words: list[str]) -> list[str]:
    """Files ``sed`` edits in place, or nothing when it is not editing in place.

    ``-i`` may carry its backup suffix attached (``-i.bak``), which is why the
    test is a prefix and not equality. Without an explicit script option the
    first operand is the script rather than a file; with ``-e``/``-f`` every
    operand is a file.
    """
    options, operands = _partition(words)
    if not any(
        option.startswith("-i") or option.startswith("--in-place")
        for option in options
    ):
        return []
    has_script_option = any(
        option in {"-e", "-f", "--expression", "--file"} for option in options
    )
    return operands if has_script_option else operands[1:]


def _destination_target(words: list[str]) -> list[str]:
    """The last operand — the destination of ``cp``, ``mv``, ``install``, ``ln``."""
    _, operands = _partition(words)
    return operands[-1:] if len(operands) >= 2 else []


def _dd_targets(words: list[str]) -> list[str]:
    """``dd``'s ``of=`` operand, which is the only place its output can go."""
    return [
        word.partition("=")[2]
        for word in words[1:]
        if word.startswith("of=") and word.partition("=")[2]
    ]


def _all_operands(words: list[str]) -> list[str]:
    """Every operand — for commands whose operands are all files they write."""
    return _partition(words)[1]


#: Command name -> how to read its write targets out of its own argument list.
#: A command absent here contributes no target, which is the honest default: an
#: unknown command is not a command that writes nothing.
_WRITERS = {
    "tee": _all_operands,
    "touch": _all_operands,
    "truncate": _all_operands,
    "sed": _sed_targets,
    "cp": _destination_target,
    "mv": _destination_target,
    "install": _destination_target,
    "ln": _destination_target,
    "dd": _dd_targets,
}


#: A shell variable assignment prefixing a command: a POSIX name, then ``=``.
#: Anchored, because ``of=b.img`` is ``dd``'s operand and not an assignment —
#: only a word BEFORE the command word is one.
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _without_environment(words: list[str]) -> list[str]:
    """One command's words with its leading ``VAR=value`` prefix removed.

    Every reading of a command starts here, so the prefix is invisible to both
    of them: ``TZ=UTC touch a.py`` is ``touch`` writing ``a.py``, and while the
    assignment counted as the command word it was neither.
    """
    index = 0
    while index < len(words) and _ASSIGNMENT.match(words[index]):
        index += 1
    return words[index:]


def _program_name(commands: list[list[str]]) -> str:
    """The program the first command runs, with its environment prefix dropped.

    ``""`` when the line runs no command at all — ``> out`` is a redirection the
    shell performs, and ``FOO=bar`` on its own sets a variable and runs nothing.
    """
    for words in commands:
        stripped = _without_environment(words)
        if stripped:
            return stripped[0]
    return ""


def _tokenize(command: str) -> list[str]:
    """Split *command* into words and shell punctuation, honouring quoting."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def _split_commands(tokens: list[str]) -> tuple[list[list[str]], list[str]]:
    """Group tokens into one list per command, plus the shell's redirection targets.

    Redirection targets are collected as they are met rather than left in the
    word list, so a command's operand positions are the ones its own interface
    defines: in ``cp a > log b``, ``log`` belongs to the shell and ``b`` is
    still ``cp``'s destination. They come back separately because they are the
    shell's writes, not any command's.
    """
    commands: list[list[str]] = [[]]
    redirected: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _SEPARATORS:
            commands.append([])
        elif token in _WRITE_REDIRECTIONS:
            index += 1
            if index < len(tokens) and tokens[index] not in _SEPARATORS:
                redirected.append(tokens[index])
        else:
            commands[-1].append(token)
        index += 1
    return [command for command in commands if command], redirected


def _command_targets(words: list[str]) -> list[str]:
    """Targets named by one command's own interface."""
    invocation = _without_environment(words)
    if not invocation:
        return []
    reader = _WRITERS.get(invocation[0].rpartition("/")[2])
    return reader(invocation) if reader is not None else []


def read_shell_command(command: str) -> ShellCommand:
    """What *command* names: the program it runs and the files it is seen to write.

    An empty ``targets`` never means "this command writes nothing" — it means no
    declared shape named a file, which is the ordinary case for an interpreter
    invocation. Callers state that in ``not_covered`` rather than reading it as
    coverage.

    One reading rather than two, because the name and the targets come out of the
    same tokenization: deriving them separately would be two answers about one
    line that a quoting change could make disagree.
    """
    if not command.strip():
        return ShellCommand()
    try:
        tokens = _tokenize(command)
    except ValueError as exc:
        return ShellCommand(unreadable=str(exc))
    commands, redirected = _split_commands(tokens)
    found = {target for target in redirected if target}
    for words in commands:
        found.update(target for target in _command_targets(words) if target)
    return ShellCommand(
        name=_program_name(commands), targets=tuple(sorted(found))
    )
