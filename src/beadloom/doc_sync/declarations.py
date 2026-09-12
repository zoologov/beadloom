# beadloom:domain=doc-sync
# beadloom:component=config-declarations
"""One declaration read out of ``.beadloom/config.yml``, and what about it was unusable.

Two Gate legs are opt-in: ``issue-log`` reads ``issue_log:`` and ``readme-pair``
reads ``document_pairs:``. Both used to answer one question — is there a usable
declaration here? — and a project that had written one and mistyped a key got
the same answer as a project that had written none. The refusal went to
``logging``, which the Gate does not render, so four ways of opting in badly
reached the verdict ``skipped — no document pair is declared`` (BDL-069,
``beadloom-rqma.7``; the same shape in the neighbouring leg is BDL-UX #270).

**Absence and refusal are different answers, and this module keeps them apart.**
A declaration is in one of four states, and a caller that has to pick one cannot
collapse two of them by accident:

``ABSENT``
    No config file, or no such key in it. The project opted out and is not
    judged — the constraint every opt-in leg of this epic is built under.
``EMPTY``
    The key is there with nothing under it. A different act from absence and the
    same conclusion: a block holding nothing declares nothing.
``PRESENT``
    The key is there and holds something. Whatever that something is, it was the
    project opting IN, so an entry that cannot be used is a defect in the
    declaration and is reported as one rather than dropped.
``UNREADABLE``
    The config file itself could not be read or parsed, so whether the key is
    there is unknown. This is neither of the other three: reporting it as
    absence tells an adopter they opted out, and reporting it as a broken
    declaration reddens a project that may never have written the key at all.

**A refusal names the entry, not the file.** ``document_pairs[1]`` with the keys
the entry actually has is what makes a one-letter typo visible; "the block is
malformed" is the sentence this module exists to stop being printed.

**Nothing here decides a verdict.** The refusals travel to the caller's report
and the caller's Gate step renders them, for the same reason the comparison in
:mod:`beadloom.doc_sync.document_pairs` does not: a module that both finds a
problem and decides what it costs has two responsibilities and one of them is
invisible to tests of the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

#: No config file, or no such key in it: the project opted out.
ABSENT = "absent"
#: The key is there and holds nothing (``document_pairs:`` and then a blank
#: line). Kept apart from ``ABSENT`` because it is a different act — writing the
#: key and leaving it empty — even though every caller so far draws the same
#: conclusion from it: a block holding nothing declares nothing, so the project
#: is not judged. An adopter's existing config in this shape must not turn red
#: on the upgrade that ships a leg.
EMPTY = "empty"
#: The key is there and holds something, whatever shape that something has.
PRESENT = "present"
#: The config file could not be read, so the key's presence is unknown.
UNREADABLE = "unreadable"

_CONFIG_RELATIVE = ".beadloom/config.yml"


@dataclass(frozen=True)
class Refusal:
    """One declaration that was written and could not be used.

    ``where`` names the entry in the config's own terms (``document_pairs[1]``,
    ``issue_log``) so a reader can go to the line. ``why`` states what was wrong
    with THAT entry, including the keys it does have, which is how a misspelled
    key shows itself.
    """

    where: str
    why: str
    remediation: str


@dataclass(frozen=True)
class Declaration:
    """What one key of ``.beadloom/config.yml`` holds, and whether it holds anything."""

    key: str
    state: str
    value: object = None
    refusals: tuple[Refusal, ...] = ()

    @property
    def present(self) -> bool:
        """The key is there and holds something.

        False for an empty key as well as for absence and an unreadable config:
        a caller asking this is asking whether there is anything to read.
        """
        return self.state == PRESENT

    @property
    def undetermined(self) -> bool:
        """Whether the project opted in could not be established."""
        return self.state == UNREADABLE


def read_declaration(project_root: Path, key: str) -> Declaration:
    """The value *project_root* declares under *key*, or why that could not be read."""
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.is_file():
        return Declaration(key=key, state=ABSENT)
    try:
        raw = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _unreadable(key, f"it could not be read ({exc.__class__.__name__})")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return _unreadable(key, "it could not be parsed as YAML")
    if data is None:
        return Declaration(key=key, state=ABSENT)
    if not isinstance(data, dict):
        return _unreadable(key, "its top level is not a mapping, so it holds no keys")
    if key not in data:
        return Declaration(key=key, state=ABSENT)
    if data[key] is None:
        return Declaration(key=key, state=EMPTY)
    return Declaration(key=key, state=PRESENT, value=data[key])


def _unreadable(key: str, why: str) -> Declaration:
    return Declaration(
        key=key,
        state=UNREADABLE,
        refusals=(
            Refusal(
                where=_CONFIG_RELATIVE,
                why=f"{_CONFIG_RELATIVE} could not be read: {why}",
                remediation=(
                    f"repair {_CONFIG_RELATIVE} so it parses as a YAML mapping, then run "
                    "the gate again"
                ),
            ),
        ),
    )


def entries_of(
    declaration: Declaration, shape: str
) -> tuple[tuple[object, ...], tuple[Refusal, ...]]:
    """A present declaration's entries when it is a list, or one refusal about its shape.

    *shape* describes what the list should hold, and goes into the refusal so a
    project that wrote a scalar is told what to write instead.
    """
    value = declaration.value
    if isinstance(value, list):
        return tuple(value), ()
    return (), (
        Refusal(
            where=declaration.key,
            why=(
                f"`{declaration.key}:` is {describe_value(value)}, not a list of {shape}"
            ),
            remediation=f"write `{declaration.key}:` as a list of {shape}",
        ),
    )


def mapping_of(
    declaration: Declaration, shape: str
) -> tuple[dict[str, object] | None, tuple[Refusal, ...]]:
    """A present declaration's mapping, or one refusal about its shape."""
    value = declaration.value
    if isinstance(value, dict):
        return value, ()
    return None, (
        Refusal(
            where=declaration.key,
            why=f"`{declaration.key}:` is {describe_value(value)}, not a mapping with {shape}",
            remediation=f"write `{declaration.key}:` as a mapping with {shape}",
        ),
    )


def string_field(
    entry: dict[str, object], field: str, *, where: str, needs: Sequence[str]
) -> tuple[str | None, Refusal | None]:
    """*entry*'s *field* as a string, or the refusal that says why it is not one.

    The refusal lists the keys the entry DOES carry. A missing key and a
    misspelled one are the same absence to a reader of the code and not at all
    the same thing to the person who wrote the config, and the list of siblings
    is what tells them apart without this module guessing at spellings.
    """
    value = entry.get(field)
    if isinstance(value, str):
        return value, None
    held = ", ".join(f"`{key}:`" for key in entry) or "no key at all"
    wanted = ", ".join(f"`{key}:`" for key in needs)
    why = (
        f"`{field}:` is {describe_value(value)}"
        if field in entry
        else f"it has no `{field}:` key; it has {held}"
    )
    return None, Refusal(
        where=where,
        why=why,
        remediation=f"give the entry {wanted}, each a path relative to the project root",
    )


def inside_project(
    project_root: Path, declared: str, *, where: str, field: str
) -> tuple[Path | None, Refusal | None]:
    """*declared* resolved under *project_root*, or the refusal that it escapes it."""
    candidate = project_root / declared
    try:
        candidate.resolve().relative_to(project_root.resolve())
    except ValueError:
        return None, Refusal(
            where=where,
            why=f"`{field}: {declared}` resolves outside the project root",
            remediation="point it at a path inside the project",
        )
    return candidate, None


def fold(where: str, refusals: Sequence[Refusal]) -> Refusal | None:
    """Every problem with ONE declaration, as one refusal, or ``None`` when there is none.

    One refusal per unusable entry, never one per problem: the count a verdict
    prints is "how many declarations could not be used", and an entry that is
    wrong in two ways is still one entry. Both reasons are kept, so a reader
    repairing the entry sees everything wrong with it in one run rather than
    discovering the second problem after fixing the first.
    """
    kept = tuple(refusals)
    if not kept:
        return None
    if len(kept) == 1:
        return kept[0]
    return Refusal(
        where=where,
        why="; ".join(refusal.why for refusal in kept),
        remediation="; ".join(dict.fromkeys(refusal.remediation for refusal in kept)),
    )


def describe_value(value: object) -> str:
    """What a wrongly-shaped value is, in words a config author recognises.

    ``bool`` is tested before ``int`` because it is a subclass of it, and
    ``document_pairs: true`` described as "a number" is a sentence that sends a
    reader looking for a number.
    """
    if value is None:
        return "empty"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "a mapping"
    return "not a value this key accepts"
