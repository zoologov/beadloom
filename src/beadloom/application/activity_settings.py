# beadloom:domain=application
# beadloom:feature=reindex
"""The ``activity:`` block of ``.beadloom/config.yml``: the files a project says a machine wrote.

BDL-078 ``beadloom-btkd.1``. Activity counts changed lines, and a file a machine
writes is not work: the lock files of every well-known package manager and the
files git's attributes mark generated or binary are left out by
:mod:`beadloom.infrastructure.git_activity` itself. A project adds its own::

    activity:
      exclude:
        - "*.pb.go"          # a file name, anywhere
        - "web/dist/*"       # a path from the project root; * crosses directories

A key the block does not read, an ``exclude:`` that is not a list and an entry
that is not a pattern are each refused by name, in the shape
:mod:`beadloom.doc_sync.declarations` gives every declaration of this file. A
refused entry is dropped and the usable ones are kept. The refusals reach
``beadloom config-check`` and the Gate's ``config-check`` step, which block on
them: a mistyped ``exlude:`` would otherwise count every generated line as work
without a word, and no project declared this block before it existed.

It belongs to the reindex, which stores the activity every other surface reads
(the node card, ``ctx``, the data file); the debt report and the dashboard,
which measure it again, read the same patterns from here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.doc_sync.declarations import (
    Refusal,
    describe_value,
    mapping_of,
    read_declaration,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The key of ``.beadloom/config.yml`` this module reads.
ACTIVITY_KEY = "activity"

#: The keys the block reads.
_EXCLUDE = "exclude"
_KEYS = (_EXCLUDE,)


def read_activity_exclusions(project_root: Path) -> tuple[tuple[str, ...], tuple[Refusal, ...]]:
    """The patterns *project_root* excludes from activity, and every entry refused."""
    declaration = read_declaration(project_root, ACTIVITY_KEY)
    if declaration.undetermined:
        return (), declaration.refusals
    if not declaration.present:
        return (), ()
    block, refusals = mapping_of(declaration, "the key `exclude:`")
    if block is None:
        return (), refusals
    found = [_unknown_key(str(key)) for key in block if str(key) not in _KEYS]
    patterns: tuple[str, ...] = ()
    if block.get(_EXCLUDE) is not None:
        patterns, refused = _patterns(block[_EXCLUDE])
        found.extend(refused)
    return patterns, tuple(found)


def activity_exclusions(project_root: Path) -> tuple[str, ...]:
    """The usable patterns only: what a reader of activity applies, refusals aside."""
    return read_activity_exclusions(project_root)[0]


def _patterns(value: object) -> tuple[tuple[str, ...], list[Refusal]]:
    where = f"{ACTIVITY_KEY}.{_EXCLUDE}"
    if not isinstance(value, list):
        return (), [
            Refusal(
                where=where,
                why=f"`{_EXCLUDE}:` is {describe_value(value)}, not a list of patterns",
                remediation=f"write `{_EXCLUDE}:` as a list of file-name or path patterns",
            )
        ]
    patterns: list[str] = []
    refusals: list[Refusal] = []
    for index, entry in enumerate(value):
        if isinstance(entry, str) and entry.strip():
            patterns.append(entry.strip())
            continue
        shown = "an empty string" if isinstance(entry, str) else describe_value(entry)
        refusals.append(
            Refusal(
                where=f"{where}[{index}]",
                why=f"the entry is {shown}, not a pattern",
                remediation="write a file-name pattern such as `*.pb.go` or a path such as "
                "`web/dist/*`",
            )
        )
    return tuple(patterns), refusals


def _unknown_key(key: str) -> Refusal:
    known = ", ".join(f"`{name}:`" for name in _KEYS)
    return Refusal(
        where=f"{ACTIVITY_KEY}.{key}",
        why=f"`{key}:` is not a key of `{ACTIVITY_KEY}:`; the block reads {known}",
        remediation=f"rename or remove `{key}:`",
    )
