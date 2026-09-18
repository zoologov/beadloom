"""Where the package under test is, and which of its names are its own.

One responsibility, and it has to be one place: a test that answers this
question for itself answers it wrongly under mutation, and the wrong answer is
invisible on the tree. It cost nine nights of measurement — BDL-UX #289, a
``mutmut run`` that reached a verdict on 0 of 7187 mutants because one guard
derived its scan root from ``__file__``.

**Both halves are needed and neither is enough.** Measured in mutmut 3.7.0
itself: ``setup_source_paths`` (``mutmut/__main__.py:262-276``) inserts
``mutants/src`` on ``sys.path`` and removes the original, and the pool runs
under ``change_cwd("mutants")`` (``:479``).

* A path built from a test's own ``__file__`` points into ``mutants/tests``, so
  the root it derives is the copy. Resolving through the IMPORTED package fixes
  where a reader looks.
* It does not fix what the reader finds, because the imported package is the
  mutated one. ``mutants/src/beadloom/doc_sync/tables.py`` holds the declared
  ``cells_of`` AND ``x_cells_of__mutmut_orig`` beside it and one
  ``x_cells_of__mutmut_N`` per mutant. A population collected from that tree
  holds names the package never declared.

So :func:`module_tree` prunes the generated definitions, and the declared
function — which mutmut leaves under its own name, decorated — survives. On an
unmutated tree there is nothing to prune and the helper is a plain parse, which
is asserted in ``test_the_suite_reads_the_package_under_test.py``.

Copy-safe ROOT idioms already existed in four places
(``tests/acceptance/steps/test_audit_self_facts_steps.py:32``,
``test_ignore_block_drift_steps.py:39``, ``test_package_description_steps.py:39``,
``tests/test_rules_docstring_references.py:50``). None of them declines a
generated name, which is why this module exists rather than a fifth copy of the
first half.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import beadloom

#: The package under test, resolved through the import rather than through this
#: file's location. Under ``mutmut run`` this is ``mutants/src/beadloom`` — the
#: package genuinely being measured, mutant bodies included.
PACKAGE_ROOT: Path = Path(beadloom.__file__).resolve().parent

#: A name mutmut generated. Two spellings, both taken from
#: ``mutmut/mutation/trampoline_templates.py:17-24``: a top-level function is
#: mangled ``x_<name>``, a method ``xǁ<Class>ǁ<method>``, each suffixed
#: ``__mutmut_orig`` or ``__mutmut_<n>``. The per-function dictionary the module
#: gains is the same stem under a ``mutants_`` prefix.
#:
#: It keys on ``__mutmut`` and not on the prefix alone: a real ``x_axis`` must
#: stay in the population, because a predicate that quietly widens empties every
#: guard built on it.
_GENERATED_NAME = re.compile(r"^(?:mutants_)?x(?:_|ǁ).*__mutmut(?:_(?:orig|\d+))?$")


#: The modules the import mutmut injects can name. MEASURED in mutmut 3.7.0
#: rather than guessed: ``mutation/trampoline_templates.py:52-54`` holds the only
#: text the generator prepends to a module it rewrites, and it names ONE module —
#: ``from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated,
#: MutantDict``. A set rather than a string, so a second injected module is one
#: entry here instead of a second predicate.
#:
#: Matched by equality and not by prefix, because a prefix also drops a
#: dependency named ``mutmut_anything`` — a population that lost an entry in
#: silence, which is the failure class this module exists to remove. If a later
#: mutmut renames the module, the injected line survives the prune and arrives in
#: a population as an undeclared import: a red that names itself, not a silence.
INJECTED_IMPORT_MODULES = frozenset({"mutmut.mutation.trampoline"})


def is_generated_name(name: str) -> bool:
    """Whether *name* was written by mutmut rather than by this package."""
    return _GENERATED_NAME.match(name) is not None


def modules_under(root: Path) -> tuple[Path, ...]:
    """Every Python module under *root*, in a stable order."""
    return tuple(sorted(root.rglob("*.py")))


def module_tree(path: Path) -> ast.Module:
    """*path* parsed, with everything mutmut generated removed.

    What is removed is named by :func:`is_generated_name`: the mutant functions,
    the ``__mutmut_orig`` copy of the body, the per-function mutants dictionary
    and the decorator mutmut puts on the declared function. What survives is
    what the package declares.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    _prune(tree)
    return tree


def _prune(node: ast.AST) -> None:
    """Drop every generated statement from each body under *node*, in place."""
    for field, value in ast.iter_fields(node):
        if not isinstance(value, list):
            continue
        kept = [item for item in value if not _is_generated(item)]
        setattr(node, field, kept)
        for item in kept:
            if isinstance(item, ast.AST):
                _prune(item)


def _is_generated(item: object) -> bool:
    """Whether *item* is a statement (or decorator) mutmut wrote."""
    if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return is_generated_name(item.name)
    if isinstance(item, ast.AnnAssign):
        return isinstance(item.target, ast.Name) and is_generated_name(item.target.id)
    if isinstance(item, ast.Assign):
        return any(_names_a_generated_target(target) for target in item.targets)
    if isinstance(item, ast.ImportFrom):
        return item.module in INJECTED_IMPORT_MODULES
    if isinstance(item, ast.Call):  # a decorator: ``@_mutmut_mutated(<dict>)``
        return isinstance(item.func, ast.Name) and item.func.id == "_mutmut_mutated"
    return False


def _names_a_generated_target(target: ast.expr) -> bool:
    """Whether an assignment target is a generated name or an index into one."""
    if isinstance(target, ast.Name):
        return is_generated_name(target.id)
    if isinstance(target, ast.Subscript):
        return isinstance(target.value, ast.Name) and is_generated_name(target.value.id)
    return False
