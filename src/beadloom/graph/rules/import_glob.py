# beadloom:domain=graph
# beadloom:feature=rule-engine
"""What a ``to:`` glob of an import rule can match, decided apart from what it matches now.

**One responsibility:** tell a ``to:`` glob that can match no import path at all from one
that can, and state the second when the index holds nothing it matches today. Both
``forbid_import`` (:mod:`.evaluators`) and ``test_import_boundary``
(:mod:`.test_import_boundary`) ask it, so the two rule types say the same two sentences.

Why it exists (BDL-083 D2, BDL-UX #328): liveness reported ``to: os/**`` on a project that
imports no ``os`` as a rule that "cannot fire", in the sentence a mistyped glob gets, while
``import os`` fired the same rule. Two reviews concluded the boundary was unchecked. The two
cases are different facts: a glob no import path can satisfy is a configuration defect, and
a glob with nothing to ban today is a live rule.

**The matcher is the oracle.** Whether a glob can match is decided by
:func:`~beadloom.graph.rules.types.matches_import_target`, the function the rule fires
with, run on a path built from the glob: its literal prefix first (``os/**`` gives ``os``,
``bcrypt*`` gives ``bcrypt``), then the glob with every wildcard filled in. A second reading
of the glob is what disagreed with the matcher on the appended "/" in #328, so there is none.

**What makes a glob unmatchable**, in the order the reasons are stated:

* its first complete segment is a *source root*: a directory holding the project's indexed
  source files that no indexed import path begins with (``src`` in ``src/pkg/db/**``,
  ``backend`` in ``backend/src/digest/**``). ``to:`` names modules, never files;
* it holds a literal ``.``: an import path is matched with its dots turned into ``/``;
* the matcher accepts neither path built from it.

**The limit, stated.** A source root is inferred from the index: a directory is one when
files sit under it and no import path begins with its name. A flat project whose top-level
package nothing imports would read that package as a source root, and so would a scanned
``tests`` directory nothing imports, where ``import tests.x`` fires a ``to: tests/**`` rule.
A package any module imports is not one, which is the case for every multi-module project
this was measured on. The sentence a reader sees says it is an inference and names the one
import that would prove it wrong (S1R Minor 4), because the docstring is not where a user
reads the limit. Its headline makes the same claim (S1R second pass Minor 2): a reason
resting on that inference reads "looks unmatchable" under "looks unable to fire", where a
certain one reads "can match none" under "cannot fire" (:attr:`GlobReach.claim`,
:func:`fire_headline`). It stays ``warn``: where the inference holds the glob is a file
path written for a module, and the rule checks nothing.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.graph.rules.types import (
    INFO_SEVERITY,
    NOTHING_TO_BAN_RULE_TYPE,
    Violation,
    matches_import_target,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

#: What a ``*`` or a ``?`` is filled with when the literal prefix alone does not match.
_FILLER = "x"

#: The characters tried, in order, for a ``[...]`` class: the first the class accepts.
_CLASS_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_-"

#: The kinds a glob is read into, the way :mod:`fnmatch` reads it.
_LITERAL = "literal"
_WILDCARD = "wildcard"
_CLASS = "class"


@dataclass(frozen=True)
class GlobReach:
    """What one ``to:`` glob can match: an import path that fires it, or why none can."""

    #: An import path, slash form, that the matcher accepts — ``None`` when unmatchable.
    example: str | None
    #: Why no import path can match the glob — ``None`` when it can.
    unmatchable: str | None
    #: The reason rests on a source root inferred from the index, not on the matcher alone.
    inferred: bool = False

    @property
    def claim(self) -> str:
        """The lead-in an unmatchable reason is stated under: hedged exactly when it is."""
        return "looks unmatchable" if self.inferred else "can match none"


def fire_headline(rule_name: str, *, inferred: bool) -> str:
    """The headline of a rule that cannot fire, hedged when its only reason is an inference."""
    return f"Rule '{rule_name}' {'looks unable to fire' if inferred else 'cannot fire'}"


def _class_end(glob: str, start: int) -> int | None:
    """Index of the ``]`` closing the class opened at *start*, as :mod:`fnmatch` reads it."""
    end = start + 1
    if end < len(glob) and glob[end] == "!":
        end += 1
    if end < len(glob) and glob[end] == "]":
        end += 1
    while end < len(glob) and glob[end] != "]":
        end += 1
    return end if end < len(glob) else None


def _tokens(glob: str) -> list[tuple[str, str]]:
    """The glob as literals, wildcards and classes; an unclosed ``[`` is a literal."""
    tokens: list[tuple[str, str]] = []
    index = 0
    while index < len(glob):
        char = glob[index]
        end = _class_end(glob, index) if char == "[" else None
        if end is not None:
            tokens.append((_CLASS, glob[index : end + 1]))
            index = end + 1
            continue
        tokens.append((_WILDCARD if char in "*?" else _LITERAL, char))
        index += 1
    return tokens


def _class_member(pattern: str) -> str:
    """One character the class *pattern* accepts, or its first listed one."""
    for char in _CLASS_ALPHABET:
        if fnmatch.fnmatchcase(char, pattern):
            return char
    listed = pattern[1:-1].lstrip("!")
    return listed[:1] or _FILLER


def _literal_prefix(tokens: list[tuple[str, str]]) -> str:
    prefix: list[str] = []
    for kind, text in tokens:
        if kind != _LITERAL:
            break
        prefix.append(text)
    return "".join(prefix)


def _filled(tokens: list[tuple[str, str]]) -> str:
    fill = {_LITERAL: lambda text: text, _WILDCARD: lambda _text: _FILLER, _CLASS: _class_member}
    return "".join(fill[kind](text) for kind, text in tokens)


def _first_segment(prefix: str, *, whole_glob: bool) -> str | None:
    """The glob's first segment when the literal prefix holds all of it, else ``None``."""
    if "/" in prefix:
        return prefix.split("/", 1)[0]
    return prefix if whole_glob and prefix else None


def to_glob_reach(glob: str, *, source_roots: frozenset[str]) -> GlobReach:
    """Whether *glob* can match an import path, by the matcher on paths built from it."""
    tokens = _tokens(glob)
    prefix = _literal_prefix(tokens)
    segment = _first_segment(prefix, whole_glob=len(prefix) == len(glob))
    if segment is not None and segment in source_roots:
        return GlobReach(
            example=None,
            unmatchable=(
                f"it begins with '{segment}', a directory of the project's source files "
                "that no indexed import begins with — inferred from the index, so an "
                f"importable package named '{segment}' would still fire it; `to:` names "
                "modules, never files"
            ),
            inferred=True,
        )
    if any(kind == _LITERAL and text == "." for kind, text in tokens):
        return GlobReach(
            example=None,
            unmatchable=(
                "it holds a '.', and an import path is matched with its dots turned into "
                "'/', so the '.' never matches"
            ),
        )
    for candidate in (prefix.rstrip("/"), _filled(tokens).rstrip("/")):
        if candidate and "." not in candidate and matches_import_target(candidate, glob):
            return GlobReach(example=candidate, unmatchable=None)
    return GlobReach(example=None, unmatchable="the matcher accepts no import path built from it")


def source_roots(file_paths: Iterable[str], targets: Iterable[str]) -> frozenset[str]:
    """Directories of indexed source files that no indexed import path begins with.

    *targets* are in the slash form ``to:`` globs are matched against. The first segment of
    each is subtracted, so a flat layout (``pkg/a.py`` imported as ``pkg.a``) has none.
    """
    directories = {path.split("/", 1)[0] for path in file_paths if "/" in path}
    imported = {target.split("/", 1)[0] for target in targets}
    return frozenset(directories - imported)


def nothing_to_ban_finding(
    *, rule_name: str, rule_description: str, glob: str, example: str, searched: str
) -> Violation:
    """The statement of a live rule whose ``to:`` glob matches no import today, at info.

    *searched* is the population the glob was matched against, as the rule counts it
    (``0 of 16 indexed import paths``). The remediation is the one thing a reader can
    still get wrong: the example names what the glob bans, so a mistyped module shows.
    """
    module = example.replace("/", ".")
    return Violation(
        rule_name=rule_name,
        rule_description=rule_description,
        rule_type=NOTHING_TO_BAN_RULE_TYPE,
        severity=INFO_SEVERITY,
        file_path=None,
        line_number=None,
        from_ref_id=None,
        to_ref_id=None,
        message=(
            f"0 imports of `{glob}` in the project; the rule is live: its `to` glob "
            f"'{glob}' matches {searched}, and an import of `{module}` would fire it"
        ),
        remediation=(
            "nothing to fix while the rule bans what you meant: it fires on the first "
            f"import its `to` glob matches. If `{module}` is not the module you meant to "
            "ban, correct the glob"
        ),
    )
