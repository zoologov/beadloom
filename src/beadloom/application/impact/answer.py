# beadloom:domain=application
# beadloom:feature=impact
"""What `impact` returns, and the order the four axes are derived in.

One function assembles the answer. It exists so that the CLI, the JSON and any
later check read ONE computation rather than three that can disagree — the
defect class this epic exists to remove, applied to this epic's own instrument.

The order is not arbitrary. The seed is derived first, because every axis below
it is a property of the seed and not of the tree: BDL-068 `.3` measured the same
derivations reporting two writers and four branches under one seed and none and
three under another, on one tree, on one day. So the seed comes first, it is
named in the answer, and where the rule finds none the co-writer axis reports
that it is UNRESOLVED rather than reporting an empty list.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.application.impact.axes import (
    THE_CALLER_SEAT,
    callers_of_the_target,
    co_writers,
    commands_in,
)
from beadloom.application.impact.boundary import GraphBoundary, open_boundary
from beadloom.application.impact.seeds import (
    THE_EFFECT_RULES,
    THE_SEED_RULE,
    THE_SEED_RULE_STATEMENT,
    names_the_target_calls,
    seeds_for,
)
from beadloom.application.impact.unresolved import (
    Unresolved,
    ambiguous_names,
    unnameable_calls,
    unparsed_modules,
    unresolved_terminators,
)
from beadloom.application.source_derivation import (
    ModuleSweep,
    calls_by_name,
    functions_in,
    located_calls,
    python_files,
    sweep_modules,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from collections.abc import Set as AbstractSet

    from beadloom.application.impact.axes import Command
    from beadloom.application.impact.seeds import Seed
    from beadloom.application.source_derivation import FoundFunction

#: The directory name a source root sits under in a src-layout project.
_SRC = "src"

#: Directory names the walk up stops BELOW. ``src`` is not a package: a sweep
#: that swallowed it would answer about a whole repository for a target inside
#: one package of it.
_SOURCE_ROOT_NAMES = frozenset({_SRC})

#: The file whose presence marks a directory as a project root rather than a
#: package. Only one, and deliberately not ``setup.py`` — this repository ships
#: ``services/commands/setup.py``, and a marker that matched it would stop the
#: walk four directories below the package it is looking for.
_PROJECT_MARKER = "pyproject.toml"


class NoSuchTargetError(LookupError):
    """The argument names neither a file on disk nor a symbol defined under the root."""


@dataclass(frozen=True)
class Site:
    """One function the answer found, where it is, and which node owns it."""

    name: str
    path: str
    lineno: int
    node: str | None
    domain: str | None


@dataclass(frozen=True)
class Population:
    """One axis's findings, and whether the axis had a population at all.

    ``resolved=False`` with an empty ``sites`` is NOT the same statement as
    ``resolved=True`` with an empty ``sites``, and conflating them is how a
    derivation that knows nothing reads as a derivation that found nothing.
    """

    resolved: bool
    sites: tuple[Site, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class Boundary:
    """Which nodes the answer touched, and whether it left the target's own."""

    resolved: bool
    target_node: str | None
    target_domain: str | None
    nodes_touched: tuple[str, ...]
    domains_touched: tuple[str, ...]
    leaves_the_target_node: bool
    leaves_the_target_domain: bool


@dataclass(frozen=True)
class ImpactAnswer:
    """The whole answer: the seed it was derived from, four axes and the gaps."""

    target: str
    root: str
    seed_rule: str
    seed_rule_statement: str
    effect_rules: tuple[tuple[str, str], ...]
    seeds: tuple[Seed, ...]
    co_writers: Population
    callers: Population
    commands: tuple[Command, ...]
    boundary: Boundary
    unresolved: tuple[Unresolved, ...] = field(default_factory=tuple)


def package_root_of(path: Path, *, project_root: Path | None = None) -> Path:
    """The outermost package the *path* sits in, or its own directory.

    Derived from the target rather than configured, so an invocation naming one
    file needs nothing else to know how wide to sweep.

    The walk does NOT require ``__init__.py`` on the way up, and BDL-068 `.15`
    is why. A PEP 420 namespace package carries none, so the old walk stopped at
    the first subpackage, and a caller one directory across was reported as
    "none found." — resolved, empty and wrong, on every adopter tree and on none
    of this repository's own. The walk stops instead where a source tree stops:
    below a directory named ``src``, below one carrying a project marker, and
    never above *project_root*.
    """
    directory = path.parent if path.is_file() else path
    ceiling = _ceiling_for(directory, project_root)
    while _still_the_same_tree(directory.parent, ceiling):
        directory = directory.parent
    return directory


def _ceiling_for(directory: Path, project_root: Path | None) -> Path:
    """How far up the walk may go: the project root, or the nearest marked ancestor."""
    here = directory.resolve()
    if project_root is not None:
        root = project_root.resolve()
        if root == here or root in here.parents:
            return root
    marked = (
        parent for parent in (here, *here.parents) if (parent / _PROJECT_MARKER).exists()
    )
    return next(marked, here)


def _still_the_same_tree(directory: Path, ceiling: Path) -> bool:
    """Whether the walk may step up into *directory* and keep sweeping one package."""
    here = directory.resolve()
    if ceiling not in here.parents:
        return False
    return here.name not in _SOURCE_ROOT_NAMES and not (here / _PROJECT_MARKER).exists()


def source_root_of(project_root: Path) -> Path:
    """The single top-level package under ``src/``, or the project root itself.

    A child of ``src/`` is a package when it HOLDS Python, at any depth, rather
    than when it carries ``__init__.py``. Reading a PEP 420 namespace package as
    "not a package" made this function answer the whole project for a tree whose
    source root is one directory down, which is how the same target answered
    differently spelled as a path and spelled as a symbol.
    """
    source = project_root / _SRC
    if source.is_dir():
        packages = sorted(
            child for child in source.iterdir() if child.is_dir() and _holds_python(child)
        )
        if len(packages) == 1:
            return packages[0]
    return project_root


def _holds_python(directory: Path) -> bool:
    """Whether *directory* holds a Python file at any depth."""
    return any(directory.rglob("*.py"))


def _is_under(path: Path, root: Path) -> bool:
    """Whether *path* is *root* itself or lies beneath it."""
    here, there = path.resolve(), root.resolve()
    return here == there or there in here.parents


def _targets_for(
    argument: str, project_root: Path, root: Path | None
) -> tuple[frozenset[Path], Path, str]:
    """Resolve the argument to the files the answer is about, and the root to sweep."""
    candidate = Path(argument)
    if not candidate.is_absolute():
        candidate = project_root / argument
    if candidate.exists():
        swept = root or package_root_of(candidate, project_root=project_root)
        files = frozenset(python_files(candidate) if candidate.is_dir() else [candidate])
        return files, swept, argument
    swept = root or source_root_of(project_root)
    holding = frozenset(
        path
        for path, tree in sweep_modules(swept).parsed
        for function in functions_in(tree)
        if function.name == argument
    )
    if not holding:
        message = f"no file and no symbol named {argument!r} under {swept}"
        raise NoSuchTargetError(message)
    return holding, swept, argument


def impact_of(
    argument: str, *, project_root: Path, root: Path | None = None
) -> ImpactAnswer:
    """Answer the four questions about *argument*, from the source.

    *project_root* supplies the boundary and nothing else. *root* overrides the
    swept tree; left alone it is derived from the target, which is what lets an
    invocation carry no knowledge of the tree it is asking about.
    """
    targets, swept, shown = _targets_for(argument, project_root, root)
    sweep = sweep_modules(swept)
    located = located_calls(sweep)
    calls = calls_by_name(located)
    first_hop = names_the_target_calls(sweep, targets)
    seeds = seeds_for(sweep, first_hop=first_hop, calls=calls)
    seed_names = frozenset(seed.name for seed in seeds)

    defined_in_target = frozenset(
        function.name
        for path, tree in sweep.parsed
        if path in targets
        for function in functions_in(tree)
    )
    boundary = open_boundary(project_root)

    def site(name: str, path: Path, lineno: int) -> Site:
        relative = _relative(path, project_root)
        owner = boundary.owner_of(relative)
        return Site(name, relative, lineno, owner.node, owner.domain)

    written = tuple(
        site(found.name, found.path, found.lineno)
        for found in co_writers(located, seed_names)
    )
    found_calling = callers_of_the_target(located, defined_in_target, targets)
    calling = tuple(
        site(found.name, found.path, found.lineno) for found in found_calling
    )

    def owner(path: Path) -> tuple[str | None, str | None]:
        found = boundary.owner_of(_relative(path, project_root))
        return found.node, found.domain

    commands = tuple(
        replace(command, path=Path(_relative(command.path, project_root)))
        for command in (
            *_target_commands(targets, seed_names=seed_names, calls=calls, owner=owner),
            *_caller_commands(
                found_calling,
                targets=targets,
                seed_names=seed_names,
                calls=calls,
                owner=owner,
            ),
        )
    )
    outside = tuple(
        _relative(path, project_root)
        for path in sorted(targets)
        if not _is_under(path, swept)
    )
    gaps = _gaps(
        sweep=sweep,
        swept=swept,
        source_root=source_root_of(project_root),
        project_root=project_root,
        outside=outside,
        targets=targets,
        seeds_found=bool(seeds),
        boundary_readable=boundary.readable,
        named=seed_names | {found.name for found in written} | defined_in_target,
        sites=(*written, *calling),
    )
    return ImpactAnswer(
        target=shown,
        root=_relative(swept, project_root),
        seed_rule=THE_SEED_RULE,
        seed_rule_statement=THE_SEED_RULE_STATEMENT,
        effect_rules=tuple((rule.name, rule.statement) for rule in THE_EFFECT_RULES),
        seeds=tuple(
            replace(seed, path=Path(_relative(seed.path, project_root))) for seed in seeds
        ),
        co_writers=Population(bool(seeds), written, "" if seeds else _NO_SEED),
        callers=Population(
            not outside,
            calling,
            "" if not outside else _outside_the_sweep(_relative(swept, project_root), outside),
        ),
        commands=commands,
        boundary=_boundary_of(boundary, targets, project_root, (*written, *calling)),
        unresolved=gaps,
    )


#: Why the co-writer axis has no population when no seed was derived.
_NO_SEED = (
    "no declared effect rule found a sink this target reaches, so there is no "
    "commit point to ask who else writes through"
)


def _outside_the_sweep(swept: str, outside: tuple[str, ...]) -> str:
    """Why the caller axis has no population when the sweep does not hold the target."""
    return (
        f"the swept root {swept} holds none of {', '.join(outside)}, so nothing the "
        f"target defines was read and no caller of it could be found"
    )


def _target_commands(
    targets: frozenset[Path],
    *,
    seed_names: frozenset[str],
    calls: Mapping[str, AbstractSet[str]],
    owner: Callable[[Path], tuple[str | None, str | None]],
) -> tuple[Command, ...]:
    """The branch axis for the target's own files."""
    return tuple(
        command
        for path in sorted(targets)
        for command in commands_in(path, seed_names=seed_names, calls=calls, owner=owner)
    )


def _caller_commands(
    calling: Iterable[FoundFunction],
    *,
    targets: frozenset[Path],
    seed_names: frozenset[str],
    calls: Mapping[str, AbstractSet[str]],
    owner: Callable[[Path], tuple[str | None, str | None]],
) -> tuple[Command, ...]:
    """The branch axis for the callers this answer has already named.

    BDL-068 `.15`, MAJOR 2. Scoped to the target's own file, the axis answered
    from the wrong seat: `impact bootstrap.py --section` wrote
    `bootstrap_project: 3 branch(es)` while `init` — named one row above as a
    caller — had four branches that appeared nowhere. Three is the number this
    project carried for nine review passes, and it was arithmetically right for
    the function it named, which is what made it a recall failure rather than an
    error.

    Only the caller functions the answer already found are kept, not every
    function in their files: a whole-file reading would bury the row that
    matters under the rest of a 1,300-line command module.
    """
    by_file: dict[Path, set[str]] = {}
    for found in calling:
        if found.path not in targets:
            by_file.setdefault(found.path, set()).add(found.name)
    return tuple(
        replace(command, seat=THE_CALLER_SEAT)
        for path in sorted(by_file)
        for command in commands_in(path, seed_names=seed_names, calls=calls, owner=owner)
        if command.name in by_file[path]
    )


def _relative(path: Path, project_root: Path) -> str:
    """*path* as the project spells it, or absolute when it is outside the project."""
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _gaps(
    *,
    sweep: ModuleSweep,
    swept: Path,
    source_root: Path,
    project_root: Path,
    outside: tuple[str, ...],
    targets: frozenset[Path],
    seeds_found: bool,
    boundary_readable: bool,
    named: frozenset[str],
    sites: tuple[Site, ...],
) -> tuple[Unresolved, ...]:
    """Everything this answer could not resolve, in one population.

    The two sweep-shaped entries come first because they qualify every axis
    below them. An answer derived over less than the project cannot be read as
    an answer about the project, and before BDL-068 `.15` nothing in this
    population said so.
    """
    gaps: list[Unresolved] = _sweep_gaps(swept, source_root, project_root, outside)
    if not seeds_found:
        gaps.append(Unresolved(kind="no-seed", detail=_NO_SEED))
    if not boundary_readable:
        gaps.append(
            Unresolved(
                kind="no-graph-index",
                detail=(
                    "no .beadloom/beadloom.db to read ownership from, so no site's "
                    "boundary is known — run `beadloom reindex`"
                ),
            )
        )
    gaps.extend(unparsed_modules(sweep, swept))
    gaps.extend(unnameable_calls(sweep, targets, swept))
    gaps.extend(unresolved_terminators(sweep, targets, swept))
    gaps.extend(ambiguous_names(sweep, named, swept))
    gaps.extend(
        Unresolved(
            kind="no-node-for-path",
            detail=f"{found.name} is in no node the graph declares",
            where=f"{found.path}:{found.lineno}",
        )
        for found in sites
        if boundary_readable and found.node is None
    )
    return tuple(gaps)


def _sweep_gaps(
    swept: Path, source_root: Path, project_root: Path, outside: tuple[str, ...]
) -> list[Unresolved]:
    """How the swept root limits this answer, stated rather than left to be noticed."""
    here = _relative(swept, project_root)
    whole = _relative(source_root, project_root)
    gaps = [
        Unresolved(
            kind="target-outside-the-sweep",
            detail=f"{path} is not under the swept root, so no axis was computed over it",
            where=here,
        )
        for path in outside
    ]
    if swept.resolve() != source_root.resolve():
        gaps.append(
            Unresolved(
                kind="sweep-narrower-than-the-project",
                detail=(
                    f"the sweep covers {here} and this project's source root is {whole}, "
                    f"so a caller or a writer outside {here} is not in this answer"
                ),
                where=f"{here} < {whole}",
            )
        )
    return gaps


def _boundary_of(
    boundary: GraphBoundary,
    targets: frozenset[Path],
    project_root: Path,
    sites: tuple[Site, ...],
) -> Boundary:
    """The bounded contexts the answer touched, read off the sites it found."""
    owners = [boundary.owner_of(_relative(path, project_root)) for path in sorted(targets)]
    target_node = next((owner.node for owner in owners if owner.node), None)
    target_domain = next((owner.domain for owner in owners if owner.domain), None)
    nodes = {site.node for site in sites if site.node} | {
        owner.node for owner in owners if owner.node
    }
    domains = {site.domain for site in sites if site.domain} | {
        owner.domain for owner in owners if owner.domain
    }
    return Boundary(
        resolved=boundary.readable,
        target_node=target_node,
        target_domain=target_domain,
        nodes_touched=tuple(sorted(nodes)),
        domains_touched=tuple(sorted(domains)),
        leaves_the_target_node=bool(nodes - {target_node}),
        leaves_the_target_domain=bool(domains - {target_domain}),
    )
