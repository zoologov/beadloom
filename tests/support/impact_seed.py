"""The commit point impact is seeded from, and what a narrow and a wide seed report over it."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

from beadloom.application.source_derivation import (
    CallSite,
    call_sites_in,
    callables_that_reach,
    writers_that_build,
)
from beadloom.infrastructure.atomic_io import write_yaml_atomic

if TYPE_CHECKING:
    from pathlib import Path

#: The commit point every graph YAML routes through, read off the function object
#: so a rename fails here rather than leaving a scan that finds no writer at all.
THE_COMMIT_POINT = write_yaml_atomic.__name__


#: The marker names a function that does not exist on the 2026-08-31 tree, because
#: `_verdict_on_the_generated_graph` was written inside BDL-067. Every
#: `reaches_marker` there is therefore False, which is that tree's true state. The
#: branch COUNT does not depend on it: guards are read off the call sites.
A_MARKER_THAT_TREE_HAS_NOT_GOT = "_verdict_on_the_generated_graph"


#: Terminator names are resolved through this. Faithful for the tree under
#: examination: `setup.py` imports `sys` at module level and declares no
#: `NoReturn` helper, so `sys.exit` is the only way out that is not a `return`.
THE_RESOLVER = SimpleNamespace(sys=sys)


#: What the derivations report at `af26750d`, per seed. Measured on macOS
#: (Darwin 25.6.0, CPython 3.13.7), in the foreground, with the lifted package
#: imported from `430d9ae`. The two rows are the whole finding.
THE_WIDE_SEED_ANSWER = (2, 4)


THE_NARROW_SEED_ANSWER = (0, 3)


def _branches_of(source: str, root: Path, seed: str, command: str) -> set[tuple[str, ...]]:
    """The distinct branches of *command* that reach anything reaching *seed*.

    The guards themselves rather than their number, because a count cannot say
    WHICH branch a narrow seed lost and that is the half worth knowing.
    """
    sites: tuple[CallSite, ...] = call_sites_in(
        source,
        callables_that_reach(root, seed),
        command=command,
        marker=A_MARKER_THAT_TREE_HAS_NOT_GOT,
        resolving_in=THE_RESOLVER,
    )
    return {site.guard for site in sites}


def seed_answer(
    source: str, root: Path, seed: str, command: str
) -> tuple[int, int]:
    """The pair the finding is stated in: writers found, branches found."""
    writers = writers_that_build(root, key="nodes", commit_point=seed)
    return len(writers), len(_branches_of(source, root, seed, command))
