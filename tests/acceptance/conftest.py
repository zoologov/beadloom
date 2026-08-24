"""Acceptance-suite configuration: binding tags are data, not pytest markers.

``pytest-bdd`` turns every Gherkin tag into a pytest marker, and this repository
runs with ``--strict-markers`` — so ``@bead:beadloom-mr2l.13`` would fail
collection unless every bead id and every ref_id were registered in advance,
which is a list nobody can keep true.

The binding tags are not selectors; they are the scenario's statement of which
work and which node it belongs to, read by ``beadloom lint`` from the file. So
the hook below tells pytest-bdd they are already handled. Any OTHER tag still
becomes a marker, and still has to be registered — a tag meant for selection
keeps its usual meaning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

#: Tag prefixes that carry a binding rather than a selection.
_BINDING_PREFIXES = ("bead:", "node:")


def pytest_bdd_apply_tag(tag: str, function: Callable[..., object]) -> bool | None:
    """Consume the binding tags; let pytest-bdd handle everything else."""
    if tag.startswith(_BINDING_PREFIXES):
        return True
    return None
