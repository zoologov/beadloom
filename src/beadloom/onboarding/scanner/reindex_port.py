"""What onboarding needs from the layer above it, stated as a type it owns.

``init`` has to re-index: it writes graph files, and the verdict it then takes
reads the index without re-indexing, so a run that skipped it would report
success over a graph the command had not finished writing (BDL-067 `.14`).

The re-index itself is an application use case, and the declared direction is
``services -> application -> domains -> infrastructure``. Onboarding is a
domain, so it cannot import :mod:`beadloom.application.reindex`; until BDL-070
`beadloom-46am` it did, twice, function-locally, and that was the only
reverse-direction edge of the 357 that inheritance through ``part_of`` brings
into the layer check's scope on this repository.

The direction is inverted here rather than worked around. This module states
WHAT onboarding needs — something callable with a project root that reports how
much it indexed — and the caller supplies it. ``services/commands/setup.py``
imports both sides, which is downward from a service to an application use case
and downward again to a domain.

Deliberately not a dodge. ``importlib.import_module`` would remove the edge by
hiding the import from the scanner, which is the BDL-059 S3 workaround that
``tests/test_no_domain_package_imports_application.py`` exists to prevent.
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class IndexCounts(Protocol):
    """The four counts ``init`` reports out of a re-index.

    Read-only members, so any object carrying the three — a mutable dataclass
    such as ``application.reindex.ReindexResult``, a frozen one, or a stub in a
    test — satisfies it. Onboarding names only what it reads: a wider type would
    make this module a second declaration of the application's result shape,
    which is the coupling the port is here to remove.
    """

    @property
    def symbols_indexed(self) -> int:
        """Code symbols the run indexed."""

    @property
    def imports_indexed(self) -> int:
        """Import statements the run indexed."""

    @property
    def edges_loaded(self) -> int:
        """Graph edges the run loaded."""

    @property
    def docs_indexed(self) -> int:
        """Documents the run indexed. Reported by the wizard alone, after the
        doc skeletons it just generated are picked up."""


#: Re-index a project and report what it indexed. Supplied by the caller —
#: ``beadloom.application.reindex.reindex`` satisfies it — and never resolved
#: from inside this domain.
Reindexer: TypeAlias = "Callable[[Path], IndexCounts]"
