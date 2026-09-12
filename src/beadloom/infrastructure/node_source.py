"""Whether a file lies under a node's declared source, by path component.

A node's ``source`` is a path a person typed into a graph file: a directory, with
or without its trailing slash, or one file. A file lies under it when the file's
path IS that path — a single-file source — or continues it past a ``/``. Nothing
else: ``src/ledger/`` does not hold ``src/ledger_archive/`` or ``src/ledger.py``,
though both start with the same characters, and a source that declares nothing
holds nothing, though the empty string starts every string.

The rule was written three times, in three domains, before BDL-069 `beadloom-rqma.4`
gave it one body: `doc_generator._symbols_for_node` and `git_activity._map_file_to_node`
by path component, and `reindex`'s route attribution by string prefix, which gave a
node its sibling's routes. All three call this now.

It lives in `infrastructure` because `git_activity` does, and the lowest layer
imports nothing above it. `onboarding` may not import `infrastructure`
(`onboarding-no-direct-infra`), so its one caller reaches this module through a
stated exemption in ``rules.yml``: a path predicate opens no index and runs no git,
which is the meaning that rule's other exemptions wait for it to be re-scoped to.

This is not ownership. :func:`beadloom.infrastructure.repository.source_covers`
answers which node OWNS a file — a package facade covers its package there — and a
caller asking that question calls that function.

The FILE path is compared as given, in the form the indexer, the route scan and
``git log`` produce it: relative to the project root, with ``/`` separators. Only
the declared source is normalised, once per node, because it is the side a person
writes.
"""

# beadloom:domain=infrastructure
# beadloom:component=node-source

from __future__ import annotations

from pathlib import PurePosixPath


class NodeSource:
    """A node's declared source, normalised, and the files that lie under it."""

    __slots__ = ("_below", "_path")

    def __init__(self, declared: str | None) -> None:
        self._path = _normalised(declared)
        self._below = f"{self._path}/"

    @property
    def path(self) -> str:
        """The source as a POSIX path without a trailing ``/``; ``""`` when none is declared."""
        return self._path

    def holds(self, file_path: str) -> bool:
        """Whether *file_path* is this source or continues it past a ``/``."""
        if not self._path:
            return False
        return file_path == self._path or file_path.startswith(self._below)

    def __repr__(self) -> str:
        return f"NodeSource({self._path!r})"


def _normalised(declared: str | None) -> str:
    """*declared* without surrounding whitespace, ``.`` segments or a trailing ``/``."""
    text = (declared or "").strip()
    if not text:
        return ""
    return str(PurePosixPath(text)).rstrip("/")
