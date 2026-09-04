# Typed Surface (component)

The files a project declares type-checked, derived from its own mypy configuration, and the
three sentences a check over them has.

**Source:** `src/beadloom/application/typed_surface.py`

---

## Overview

A type check is a claim about the files it was handed. Hand it more than the project declares
typed and every commit is red for reasons nobody signed up to; the one commit that carries a
genuine violation prints the same sentence as the rest and is scrolled past with them.

This repository measured that on its own pre-commit hook. The hook ran `mypy` over every staged
`.py` under `src/` or `tests/`, while `pyproject` declares `packages = ["beadloom"]` with
`mypy_path = "src"` and `ci.yml` runs `uv run mypy src/`. Measured: `uv run mypy tests/` reports
970 errors in 90 files, and not one of them is a violation of anything the project claims.

Measured over all 24 commits of `features/BDL-068` at `b7c9476..49c2ebe`, each against its own
tree: 7 commits staged Python at all, 63 paths between them, and 31 of those 63 are inside the
declared surface. The old hook warned on 4 of the 7 commits and all 4 warnings were false. A
surface-scoped check is clean on all 7. Under the blocking hook template those same 4 commits
would have been refused, which is why block mode was unusable on this repository.

## The surface is derived, never listed

| Read from | What it declares |
|-----------|------------------|
| `[tool.mypy] packages` | dotted package names, resolved against the search path |
| `[tool.mypy] modules` | dotted module names, resolved to one `.py` file each |
| `[tool.mypy] files` | paths, and a glob when it names exactly one root |
| `[tool.mypy] mypy_path` | the search path, split on `:` and `,`, with the project root appended |

`beadloom-mr2l.82` was the first attempt at scoping this check, and it wrote the surface into the
hook template. The mypy configuration then moved and the template did not. A second list is a
second thing to forget, so the surface is asked for at the moment the gate asks, from the
declaration that decides it.

`[[tool.mypy.overrides]]` is outside the section this reads, by construction: an override changes
which findings are reported, never which files are in the surface.

## Three sentences, not two

`SurfacePartition.describe()` renders one line, and which line it is carries the fact:

| State | The sentence |
|-------|--------------|
| The surface could not be derived | `Typed surface: NOT CHECKED -- <reason>` |
| Derived, and nothing staged is inside it | `Typed surface (src/beadloom): NOTHING TO CHECK -- 0 of 2 staged Python file(s) are inside it, 2 outside.` |
| Derived, with files to check | `Typed surface (src/beadloom): 2 of 5 staged Python file(s) inside it, 3 outside.` |

A check whose population is empty reading as a check that passed is the phantom gate BDL-068 is
named for, so the second and third sentences are deliberately different sentences rather than the
same sentence with a zero in it. The count is a count of files actually handed to the checker.

**A surface that could not be derived is NOT CHECKED, never "everything".** Falling back to
checking whatever was staged is the behaviour being removed. Falling back to checking nothing
while saying nothing is the failure one level down.

## What could not be resolved is part of the answer

A derivation that drops what it could not read hands back a clean list, and a clean list is
trusted and stopped at. Each of these is reported with its reason rather than omitted:

- a package or module name that resolves to no directory and no `.py` file under the search path;
- a `files` glob that matches nothing, or that matches several roots;
- a declared `exclude` pattern, which is **not applied** here because mypy does not apply it to
  files named on the command line, and that is how the gate invokes mypy;
- a `mypy.ini`, `.mypy.ini`, `setup.cfg` or `tox.ini` beside the `pyproject.toml`, each of which
  can declare a mypy surface and none of which this derivation reads.

## The declaration is read without a TOML parser

`tomllib` is 3.11+ and `tomli` is not a runtime dependency, so a parse answers differently on
3.10 than on 3.13. A module whose subject is *what a check actually covers* must not have a
room-dependent answer. This is the reasoning `application/rooms.py` states about the packaging
metadata, applied to a handful of string arrays and two scalars out of one known table. Anything
in that table this reader cannot turn into a surface is reported, not assumed away.

## Containment is over path segments

`src/beadloom_extra/mod.py` is **not** inside `src/beadloom`. A prefix match would put a sibling
directory into the surface and make the check red for a file nobody declared. A backslash
separator is read as the same path, so a staged path reported by git on Windows resolves.

## Who consumes it

- `beadloom typed-surface` — the command, in `src/beadloom/services/commands/typed_surface.py`.
  `--filter` reads staged paths on standard input and prints the ones inside the surface, led by
  a verdict line marked with `beadloom.application.declared_scope.VERDICT_MARKER`.
- The pre-commit hook `beadloom install-hooks` writes, in both its warn and its blocking mode.
  The hook calls `--filter`, prints the verdict whatever it says, and hands only the filtered
  paths to `mypy`.

## The gate that reaches this derivation

A rule stated as a shape is worth what the filter in front of it admits. `beadloom-gsal` derived
this surface from the project's own declaration and the pre-commit hook still selected the files
it would ask about with `grep -E '^(src|tests)/.*[.]py$'` — a second list beside the declaration,
which is the thing the derivation exists to remove. On the flat layout, where the package sits at
the repository root, that regex admits no package file at all: a commit with no `tests/` directory
printed no typed-surface line whatsoever — not a verdict, not `NOTHING TO CHECK`, not
`NOT CHECKED` — and a commit with one printed a confident sentence about a population the package
was not in. The ruff leg beside it reads the same variable and was equally blind.

Since `beadloom-0mdo.42` (BDL-UX #240) the hook's `staged_py` states which **kind** of file the
commit stages and never where code lives, and each leg narrows that population by its own
declaration. This repository is src-layout and could not observe the defect, which is why five
waves passed over it; `tests/test_the_gate_checks_the_surface_the_project_declared.py` now drives
the real emitted template through a real `/bin/sh` over five layouts — src, flat, flat without a
`tests/` directory, a source directory not called `src`, and a single module at the root declared
through `files` — of which this repository can show one.

## What the gate does with a failure

The hook runs `mypy` with `2>&1`, not `2>/dev/null`, and prints what came back. The old block
kept `2>/dev/null`, which does not hide mypy's findings — those go to standard output — but does
hide the diagnostics of a mypy that could not **start**, so "found errors" and "could not run"
printed one identical sentence.

`NOT CHECKED` never blocks, in either hook mode. A surface that could not be derived is a check
that did not happen, and turning a missing `PATH` entry into a refused commit is how a gate comes
to be answered with `--no-verify`.
