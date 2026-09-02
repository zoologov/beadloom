# beadloom:domain=application
# beadloom:component=source-derivation
"""Which function bodies have a named shape, read off the calls they make.

The question is *who else writes this*, and the answer must be over a SHAPE
rather than over a spelling. That distinction is not a preference, it is a
measurement: BDL-067 `.25` found that a reader detector asking for
``glob("*.yml")`` and ``yaml.safe_load`` BY NAME walked past five bodies that
read the same directory with `iterdir`, `rglob`, a pattern held in a variable,
`os.listdir`, or `yaml.load` with an explicit loader. Each of those five would
have carried a sixth skip policy into the product unseen.

So each shape here is a pair of questions about what a body DOES — it lists a
directory AND parses YAML; it builds a payload AND commits it — and each half is
matched over every name the standard library offers for that act.

The widening is not free and the trade-off is stated. A narrow shape
UNDER-reports, which ships the defect. A wide shape may OVER-report: a body that
lists a directory of documents and parses YAML front matter for some other
purpose is named here too. MEASURED on this repository, the wide form names
exactly the same one body the narrow form does, so there is nothing to exempt
today — and an over-report fails in front of the person adding the body rather
than at an adopter. If a genuine non-reader is ever named, the answer is an
exemption recorded with its reason, not a narrower shape.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from beadloom.application.source_derivation.calls import called_names
from beadloom.application.source_derivation.source_tree import (
    FoundFunction,
    functions_in,
    module_tree,
    python_files,
)

if TYPE_CHECKING:
    from pathlib import Path

#: Listing a directory, by every name the standard library offers for it.
LISTS_A_DIRECTORY = frozenset({"glob", "rglob", "iterdir", "listdir", "scandir", "walk"})

#: Parsing YAML, by every loader PyYAML offers. `load` and `unsafe_load` are in
#: the set for the same reason `safe_load` is: what matters here is that the body
#: turns a file into data, and this project's own rule against `yaml.load` is
#: enforced elsewhere.
PARSES_YAML = frozenset(
    {"safe_load", "safe_load_all", "load", "load_all", "full_load", "unsafe_load"}
)

#: Turning data into YAML text, and putting bytes on disk. A body that does both
#: without going through a commit point is a writer no commit-point-seeded scan
#: can see.
SERIALISES_YAML = frozenset({"dump", "safe_dump"})
PUTS_BYTES_ON_DISK = frozenset({"write_text", "write_bytes", "open"})


def builds_a_payload_holding(function: ast.AST, key: str) -> bool:
    """Whether *function* constructs a mapping literal with a *key* entry.

    This is what separates a writer that CREATES the thing under *key* from one
    that patches something somebody else created: a patcher reads the key out of
    a file it loaded and puts it back, and never builds it. A body that builds it
    is a body that decides what is there.
    """
    return any(
        isinstance(node, ast.Dict)
        and any(
            isinstance(literal, ast.Constant) and literal.value == key
            for literal in node.keys
        )
        for node in ast.walk(function)
    )


def writers_that_build(
    root: Path, *, key: str, commit_point: str
) -> dict[str, FoundFunction]:
    """Every function under *root* that builds a *key* payload and commits it.

    Both halves must be in ONE body, and that is the ceiling: a writer that
    builds the payload and hands the commit to a helper is invisible here. It is
    not invisible to a commit-point-seeded call graph, where the helper shows up
    as a new direct caller of *commit_point*.
    """
    found: dict[str, FoundFunction] = {}
    for path in python_files(root):
        for function in functions_in(module_tree(path)):
            if commit_point not in called_names(function):
                continue
            if builds_a_payload_holding(function, key):
                found[function.name] = FoundFunction(function.name, path, function.lineno)
    return found


def yaml_directory_readers_in(source: str) -> list[str]:
    """The functions in *source* that both list a directory and parse YAML.

    The two halves are what makes a body a reader of a directory of YAML files.
    A body holding one half — listing and parsing nothing, or parsing one file it
    was handed — is not named, because a detector whose findings are noise is a
    detector somebody exempts their way out of.
    """
    return [
        function.name
        for function in functions_in(ast.parse(source))
        for calls in [called_names(function)]
        if calls & LISTS_A_DIRECTORY and calls & PARSES_YAML
    ]


def functions_that_serialise_yaml_to_disk(root: Path) -> dict[str, FoundFunction]:
    """Every function under *root* that turns data into YAML and writes it itself.

    A commit-point-seeded derivation is only sound while the commit point is the
    only way out. This is how that premise is checked rather than trusted.
    """
    return {
        function.name: FoundFunction(function.name, path, function.lineno)
        for path in python_files(root)
        for function in functions_in(module_tree(path))
        for calls in [called_names(function)]
        if calls & SERIALISES_YAML and calls & PUTS_BYTES_ON_DISK
    }
