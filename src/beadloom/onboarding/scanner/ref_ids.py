"""The ref_id a generated node is written under, handed out once per graph."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from itertools import count
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


class RefIdAllocator:
    """Hands out ref_ids for one run of a writer, and never the same one twice.

    THE INVARIANT, and the reason this is an object rather than a function:

        no two nodes a writer commits to `.beadloom/_graph/` carry one ref_id.

    The graph identifies a node BY its ref_id — the loader inserts by ref_id and
    keeps one node per ref_id — so a writer that emits the name twice does not
    write two nodes. It writes one, and the report it prints counts two. Measured
    on 4.0.0 over a project named `myapp` holding `src/myapp/`, the ordinary
    single-package src-layout: `init --yes --mode bootstrap` reported `Graph: 2
    nodes` and `beadloom status` then reported `Nodes: 1`. The one dropped was
    the node carrying `source: src/myapp/`, so the package the project is named
    after was absent from every answer the graph gave, and `domain-needs-parent`
    went inert instead of red (BDL-UX #214).

    The collision is not a corner. The root's ref_id is the manifest name and a
    cluster's is its source directory, and `src/<project>/` makes those the same
    string. `core`, `api` and `app` are ordinary repository names that also name
    a source directory, so the same shape reaches the monorepo layouts too.

    A function taking a `taken` set would leave the invariant with the caller:
    the defect is precisely a caller that computed a name and did not check it
    against the names already given out. Holding the set here means a writer
    cannot emit a duplicate without going around this object, and there are two
    writers (`bootstrap_project` and `doc_classify.import_docs`) that had already
    drifted apart on a shared post-condition once (BDL-067 `.21`).

    What it does NOT do is decide which of two askers gets the plain name. That
    is the caller's, because it is a judgement about the graph and not about
    strings: the bootstrap gives the root its project's own name first, before
    any cluster asks, because that ref_id is what titles the architecture
    document and what `generate_rules` names as the parent every domain must
    have.
    """

    def __init__(self, taken: Iterable[str] = ()) -> None:
        """*taken* is what the graph already holds — for a writer adding to one.

        `import_docs` seeds it with the ref_ids on disk, because it writes into a
        directory another writer produced; `bootstrap_project` seeds nothing,
        because it produces the whole graph.
        """
        self._taken: set[str] = {str(ref_id) for ref_id in taken}

    @property
    def taken(self) -> set[str]:
        """Every ref_id this allocator will not hand out again.

        A copy: a caller that got the live set back could add to it and leave
        this object describing a graph nobody wrote.
        """
        return set(self._taken)

    def take(self, preferred: str, *, qualifier: str | None = None) -> str:
        """Reserve and return a ref_id for a node that would like to be *preferred*.

        *preferred* is returned unchanged whenever it is free, which is every
        node on every project the collision does not touch. When it is taken,
        *qualifier* is appended — callers pass the node's kind, so the second
        `myapp` is written as `myapp-domain` and reads as what it is. A number is
        the last resort rather than the first, because a number is unique and
        says nothing.

        The numbered form starts at 2: `myapp-2` is the second `myapp`, and a
        `-1` would claim a first that is not named that way.
        """
        for candidate in self._candidates(preferred, qualifier):
            if candidate not in self._taken:
                self._taken.add(candidate)
                return candidate
        raise AssertionError("unreachable: _candidates does not end")  # pragma: no cover

    def _candidates(self, preferred: str, qualifier: str | None) -> Iterator[str]:
        """*preferred*, then its qualified form, then numbered forms without end.

        The sequence is infinite so that `take` terminates: the set of taken
        ref_ids is finite, so some candidate is always free. A bounded sequence
        would need an error path nothing could provoke on purpose.
        """
        yield preferred
        if qualifier and qualifier != preferred:
            yield f"{preferred}-{qualifier}"
        for nth in count(2):
            if qualifier and qualifier != preferred:
                yield f"{preferred}-{qualifier}-{nth}"
            else:
                yield f"{preferred}-{nth}"
