# beadloom:domain=application
# beadloom:component=source-derivation
"""Answer questions about code from the source, not from a list.

Three questions, one technique. *Who else writes this* is
:mod:`.body_shapes`; *who else calls this* is :mod:`.call_graph`; *how many
branches does this have, and how many ways does it end* is :mod:`.branches` over
:mod:`.termination`. :mod:`.calls` and :mod:`.source_tree` are the vocabulary
the other three are written in.

Each of the three was written inside BDL-067 as a test, because each was needed
to answer a question about a defect that a hand-maintained list had already got
wrong. They are here so that production code — `beadloom impact` first — can ask
the same questions, and so that the answer to "is this list still true?" is
computed rather than remembered.

**The rule the whole package is built to.** A check that asks for one way of
writing something is a check that five other spellings walk past, and that is
measured on this repository rather than supposed. Every shape here is therefore
stated over what a body DOES, and every widening of one carries the measurement
that justified it.

**What this is not.** It is not a graph walk. Not one of the axes BDL-067 needed
is a fact of the architecture graph — the writers of a directory, the branches of
a command, its exit forms, the readers and their policies all live INSIDE one
node, and a graph walk would answer confidently and miss all of them. The graph
supplies the boundary a found site falls in; the source supplies the sites.
"""

from __future__ import annotations

from beadloom.application.source_derivation.body_shapes import (
    LISTS_A_DIRECTORY,
    PARSES_YAML,
    PUTS_BYTES_ON_DISK,
    SERIALISES_YAML,
    bodies_calling,
    builds_a_payload_holding,
    functions_that_serialise_yaml_to_disk,
    writers_that_build,
    yaml_directory_readers_in,
)
from beadloom.application.source_derivation.branches import (
    CallSite,
    call_sites_in,
    statement_trail,
)
from beadloom.application.source_derivation.call_graph import (
    callables_that_reach,
    callers_among,
    callers_of,
    calls_by_name,
    direct_callers_of,
    functions_to_their_calls,
    located_calls,
    names_reached_from,
    names_that_reach,
    reversed_calls,
)
from beadloom.application.source_derivation.calls import (
    called_names,
    callee_name,
    dotted_name,
)
from beadloom.application.source_derivation.source_tree import (
    FoundFunction,
    FunctionNode,
    ModuleSweep,
    NoSuchFunctionError,
    UnparsedModule,
    definitions_named,
    function_named,
    functions_in,
    imports_in,
    module_tree,
    python_files,
    sweep_modules,
)
from beadloom.application.source_derivation.termination import (
    THE_EXITS_THAT_CARRY_NO_ANNOTATION,
    THE_NO_RETURN_ANNOTATIONS,
    ResolvedNames,
    ends_the_branch,
    exit_forms,
    never_returns,
    stdlib_names_of,
)

__all__ = [
    "LISTS_A_DIRECTORY",
    "PARSES_YAML",
    "PUTS_BYTES_ON_DISK",
    "SERIALISES_YAML",
    "THE_EXITS_THAT_CARRY_NO_ANNOTATION",
    "THE_NO_RETURN_ANNOTATIONS",
    "CallSite",
    "FoundFunction",
    "FunctionNode",
    "ModuleSweep",
    "NoSuchFunctionError",
    "ResolvedNames",
    "UnparsedModule",
    "bodies_calling",
    "builds_a_payload_holding",
    "call_sites_in",
    "callables_that_reach",
    "called_names",
    "callee_name",
    "callers_among",
    "callers_of",
    "calls_by_name",
    "definitions_named",
    "direct_callers_of",
    "dotted_name",
    "ends_the_branch",
    "exit_forms",
    "function_named",
    "functions_in",
    "functions_that_serialise_yaml_to_disk",
    "functions_to_their_calls",
    "imports_in",
    "located_calls",
    "module_tree",
    "names_reached_from",
    "names_that_reach",
    "never_returns",
    "python_files",
    "reversed_calls",
    "statement_trail",
    "stdlib_names_of",
    "sweep_modules",
    "writers_that_build",
    "yaml_directory_readers_in",
]
