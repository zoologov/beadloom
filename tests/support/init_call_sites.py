"""The init command's own source, and the call sites in it that reach the bootstrap."""

from __future__ import annotations

import inspect
from pathlib import Path

import beadloom
from beadloom.application.source_derivation import (
    CallSite,
    call_sites_in,
)
from beadloom.infrastructure.atomic_io import write_yaml_atomic
from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.services.commands import setup as init_command

#: The name of the function that takes the Gate's verdict, read off the function
#: object instead of written out: a rename fails at import here rather than
#: leaving a scan that quietly finds no verdict anywhere and reports every branch
#: as unguarded.
THE_VERDICT = init_command._verdict_on_the_generated_graph.__name__


#: The narrow seed: one writer, and the one this epic started from.
THE_BOOTSTRAP = bootstrap_project.__name__


#: The wide seed, and the reason `.15` exists. Every graph YAML in the product
#: is committed by this one function — `infrastructure/atomic_io.py` states that
#: as its purpose and `TestNoGraphFileIsWrittenPastTheCommitPoint` checks it — so
#: "this function writes a graph file" is answerable from the source instead of
#: from a list. Read off the function object for the same reason `THE_VERDICT`
#: is: a rename must fail at import rather than leave a scan that finds nothing.
THE_GRAPH_COMMIT_POINT = write_yaml_atomic.__name__


#: The command under examination, by the name it has in its module.
THE_COMMAND = "init"


def package_root() -> Path:
    """The product's own source tree, which is what every scan here reads."""
    return Path(inspect.getfile(beadloom)).parent


def bootstrap_call_sites(source: str, reaching: frozenset[str]) -> tuple[CallSite, ...]:
    """The derivation's reading of `init`, bound to this command's own names.

    `source_derivation.call_sites_in` answers "where, in this command, does a
    call from *reaching* sit, and can *marker* still run after it". What this
    module supplies is which command, which marker, and the module terminator
    names are resolved through — all three read off the product's own objects, so
    a rename fails at import here rather than leaving a scan that finds nothing.
    """
    return call_sites_in(
        source,
        reaching,
        command=THE_COMMAND,
        marker=THE_VERDICT,
        resolving_in=init_command,
    )


def the_commands_source() -> str:
    """The source file `init` is defined in, as the imported module resolves it."""
    return Path(inspect.getfile(init_command)).read_text(encoding="utf-8")
