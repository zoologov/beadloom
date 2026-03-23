"""Cross-repo node identity for federation (BDL-037).

A graph ref may name a node in *another* repo using the ``@<repo>:<ref_id>``
form (e.g. ``@integration-service:plans``). A plain ref (no leading ``@``) is
local, exactly as before — federation is purely additive.

This module owns the :class:`FederatedRef` value type and the :func:`parse_ref`
parser. Malformed foreign refs raise :class:`FederationRefError` so the loader
can record them in ``result.errors`` instead of silently dropping them.
"""

# beadloom:domain=graph

from __future__ import annotations

from dataclasses import dataclass

# Marker that introduces a foreign (cross-repo) reference.
_FOREIGN_MARKER = "@"


class FederationRefError(ValueError):
    """Raised when a ``@...`` foreign ref is malformed.

    A leading ``@`` signals the author intended a cross-repo reference, so a
    broken shape is an error to surface — never a silently-accepted local ref.
    Malformed examples: ``@:x`` (empty repo), ``@repo:`` (empty ref_id),
    ``@repo`` (no separator), ``@``.
    """


@dataclass(frozen=True)
class FederatedRef:
    """A graph reference that may point at another repo.

    ``repo is None`` means a local reference (the common case). Otherwise the
    ref names node ``ref_id`` in satellite repo ``repo``; it resolves against
    the federated union at the hub, not during a single-repo load.
    """

    repo: str | None
    ref_id: str

    @property
    def is_foreign(self) -> bool:
        """True when this ref targets another repo."""
        return self.repo is not None

    @property
    def qualified(self) -> str:
        """Canonical string form: ``@repo:ref_id`` (foreign) or ``ref_id`` (local)."""
        if self.repo is None:
            return self.ref_id
        return f"{_FOREIGN_MARKER}{self.repo}:{self.ref_id}"


def is_foreign_ref(raw: str) -> bool:
    """Cheap check: does *raw* look like a foreign ref (leading ``@``)?

    Does not validate the shape — use :func:`parse_ref` for that.
    """
    return raw.startswith(_FOREIGN_MARKER)


def parse_ref(raw: str) -> FederatedRef:
    """Parse a graph ref into a :class:`FederatedRef`.

    - ``"routing"``            -> local ``FederatedRef(None, "routing")``
    - ``"@repo:plans"``        -> foreign ``FederatedRef("repo", "plans")``
    - malformed ``@...``       -> :class:`FederationRefError`

    Only the first ``:`` after the marker separates repo from ref_id, so a
    foreign ref_id may itself contain colons (``@repo:ns:thing``). A plain ref
    with a colon and no leading ``@`` stays local untouched.
    """
    if not raw.startswith(_FOREIGN_MARKER):
        if not raw:
            raise FederationRefError("Empty ref is not a valid node reference.")
        return FederatedRef(repo=None, ref_id=raw)

    body = raw[len(_FOREIGN_MARKER) :]
    repo, sep, ref_id = body.partition(":")
    if not sep or not repo or not ref_id:
        raise FederationRefError(
            f"Malformed foreign ref '{raw}': expected '@<repo>:<ref_id>' "
            f"with non-empty repo and ref_id."
        )
    return FederatedRef(repo=repo, ref_id=ref_id)
