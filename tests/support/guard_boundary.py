"""The guard boundary, read from the package's source.

Where control may leave one guard invocation, where a firing is recorded, and
what Click converts before the command's callback runs.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import click

from beadloom.services.cli import main
from tests.support.package_under_test import PACKAGE_ROOT, module_tree, modules_under

if TYPE_CHECKING:
    from pathlib import Path

#: The package under test, asked of the IMPORT and not of this file. Under
#: `mutmut run` the suite is copied beside the mutated sources, so a root built
#: from `__file__` reads the copy; `tests/support/package_under_test.py` resolves it
#: through the imported package and declines mutmut's generated names (BDL-UX
#: #289). This file's populations cannot trip on the second half today — no
#: mutated module holds a `record_firing(` call or a process terminator — so the
#: move keeps its behaviour and removes the shape.
SRC = PACKAGE_ROOT


COMMAND_MODULE = SRC / "services" / "commands" / "guard.py"


GUARDS_PACKAGE = SRC / "application" / "guards"


def module_ast(path: Path) -> ast.Module:
    """*path* parsed without whatever mutmut generated into it."""
    return module_tree(path)


def _calls_named(tree: ast.AST, name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == name)
            or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
        )
    ]


def terminal_name(node: ast.expr | None) -> str:
    """The last component of a dotted expression: ``os._exit`` -> ``_exit``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


#: Call targets that end the process, matched on their LAST component so the
#: module they are reached through cannot disguise them: ``sys.exit``,
#: ``ctx.exit``, ``os._exit`` and a bare ``exit`` are one behaviour.
TERMINATING_CALL_NAMES = frozenset({"exit", "_exit", "quit"})


#: Call targets whose last component is too ordinary to match on its own, so
#: these are matched on the whole dotted target instead.
TERMINATING_CALL_TARGETS = frozenset(
    {
        "os.abort",
        "os.kill",
        "os.execl",
        "os.execlp",
        "os.execv",
        "os.execve",
        "os.execvp",
        "signal.raise_signal",
    }
)


#: Exceptions that end the process rather than being handled by it: ``SystemExit``
#: is not an ``Exception``, and Click turns ``Abort``/``Exit`` into an exit code.
TERMINATING_EXCEPTIONS = frozenset({"SystemExit", "Abort", "Exit"})


def process_terminators(tree: ast.AST) -> list[str]:
    """Every construct in *tree* that can end the process, however it is spelled.

    A ``raise`` is read from its exception *node* rather than from a call, so a
    bare ``raise SystemExit`` counts like the rest — ``.29``'s pin could not see
    one, because there ``node.exc`` is a ``Name`` and not a ``Call``.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if (
                terminal_name(node.func) in TERMINATING_CALL_NAMES
                or ast.unparse(node.func) in TERMINATING_CALL_TARGETS
            ):
                found.append(ast.unparse(node))
        elif isinstance(node, ast.Raise) and node.exc is not None:
            raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if terminal_name(raised) in TERMINATING_EXCEPTIONS:
                found.append(ast.unparse(node))
    return found


def boundary_path_modules() -> tuple[Path, ...]:
    """Every module one guard invocation passes control through.

    Discovered from the package rather than listed, because a listed scope is
    what ``.30`` walked past: the boundary module itself was never read.
    """
    return (COMMAND_MODULE, *modules_under(GUARDS_PACKAGE))


def terminators_on_the_boundary_path() -> list[tuple[str, str]]:
    """``(module, spelling)`` for every way control can leave that path."""
    return [
        (path.name, spelling)
        for path in boundary_path_modules()
        for spelling in process_terminators(module_ast(path))
    ]


#: The one place control is allowed to leave: module, and the statement itself.
THE_ONE_WAY_OUT = ("guard.py", "sys.exit(result.exit_code)")


#: The subcommand under test, spelled the way an operator types it.
GUARD_COMMAND = "guard"


def parameters_click_converts() -> list[tuple[str, click.Command, click.Parameter]]:
    """``(where, command, parameter)`` for everything Click parses on the way in.

    Read from the command Click will DISPATCH for ``beadloom guard`` rather than
    from a symbol this module imports, so a parameter added through a shared
    decorator, an ``add_command`` or a plugin is inside the pin on the day it
    lands. The group's own options are here too, because a validator on
    ``beadloom --x`` exits before this callback exactly as one on
    ``beadloom guard --x`` does.
    """
    command = main.commands[GUARD_COMMAND]
    return [
        *(("beadloom", main, param) for param in main.params),
        *((f"beadloom {GUARD_COMMAND}", command, param) for param in command.params),
    ]


def parses_an_argv_value(param: click.Parameter) -> bool:
    """Whether Click ever runs an argv string through *param*'s conversion.

    A flag's value is a constant Click supplies itself, so no argv string
    reaches its type. Everything else is probed — fail-closed, so a parameter
    kind nobody anticipated is probed rather than excused.
    """
    return not getattr(param, "is_flag", False)


def _option_spelling(param: click.Parameter) -> str:
    """The long spelling if there is one: ``--opt=value`` cannot be mistaken for
    a second option when the value itself begins with a dash."""
    return next((opt for opt in param.opts if opt.startswith("--")), param.opts[0])


def click_refuses(
    command: click.Command,
    param: click.Parameter,
    value: str,
    *,
    subcommand: str | None = None,
) -> str | None:
    """How Click ended the invocation instead of reaching the callback, if it did.

    ``make_context`` is exactly the parse Click performs before ``invoke``: it
    converts every parameter and runs their callbacks, and it does *not* call
    the command's own callback. So "this returned" is precisely "control got as
    far as the boundary", measured through Click's own machinery rather than
    inferred from the name of a type.
    """
    if isinstance(param, click.Argument):
        argv = ["--", value]
    elif _option_spelling(param).startswith("--"):
        argv = [f"{_option_spelling(param)}={value}"]
    else:  # pragma: no cover — no short-only option exists today
        argv = [_option_spelling(param), value]
    if subcommand is not None:
        argv.append(subcommand)

    context = None
    try:
        context = command.make_context(command.name or "?", argv)
    except BaseException as exc:  # a usage error, an exit, a raising converter
        return f"{type(exc).__name__}: {exc}"
    finally:
        if context is not None:
            context.close()
    return None


def declared_conversion(param: click.Parameter) -> str:
    """The conversion *param* declares, read from the runtime object.

    From the object and not from the source, so a type built through an alias,
    a helper or a variable is described as what it IS. A ``click.Path`` is
    written out as the refusals it can make, because that — not the constructor
    name — is what decides whether Click exits before the callback.
    """
    kind = param.type
    if isinstance(kind, click.Path):
        refusals = [
            name
            for name, applies in (
                ("exists", kind.exists),
                ("file_okay=False", not kind.file_okay),
                ("dir_okay=False", not kind.dir_okay),
                ("readable", getattr(kind, "readable", False)),
                ("writable", getattr(kind, "writable", False)),
                ("executable", getattr(kind, "executable", False)),
            )
            if applies
        ]
        path_type = getattr(kind.type, "__name__", repr(kind.type))
        return (
            f"click.Path({', '.join(refusals) or 'nothing it can refuse'}, path_type={path_type})"
        )
    return repr(kind)


def declared_conversions() -> dict[str, str]:
    """Every conversion an argv string can meet on the way to the callback."""
    return {
        f"{where} {param.name}": declared_conversion(param)
        for where, _command, param in parameters_click_converts()
        if parses_an_argv_value(param)
    }


def source_modules() -> tuple[Path, ...]:
    """Every module in the package — the scope of the "one writer" pin."""
    return modules_under(SRC)


def record_firing_sites() -> list[tuple[str, str]]:
    """Every call of the recorder, anywhere in the source tree."""
    return [
        (path.relative_to(SRC).as_posix(), ast.unparse(call))
        for path in source_modules()
        for call in _calls_named(module_ast(path), "record_firing")
    ]
