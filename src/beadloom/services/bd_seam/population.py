"""Where to look for ``bd`` call sites in a project, and what that leaves out.

**The reach is measured and it is small.** `beadloom-0mdo.58` counted it while
deriving S5's axes: roughly fourteen ``bd`` call sites are reachable from Python
against about 261 written in prose. The unreachable region is not a remainder,
it is the majority, so this module's job is as much to name what it did not read
as to hand over what it did — :data:`UNREACHED` is part of every answer.

**Four channels, each derived from a declaration rather than listed.** The flow
artifacts come from the flow's own mappings (``TOOL_AGENT_DIRS``,
``COMMAND_FILES``, ``.beadloom/flow``), so a tool added to either is read without
editing anything. The shipped templates come from the two template roots the
composer itself resolves. The Python channel sweeps the installed package, which
is the code that will run against an adopter's tracker. The hook channel reads
``.git/hooks``, which is where an emitted script actually runs — and reaches one
file this project does not write and the RFC recorded as outside the repository:
``post-merge``, written by ``bd init``, carrying `beadloom-l2f2`'s subject.

**A Python string literal that mentions ``bd`` is not a call site.** An error
message (``bd create failed for role``) and a help string (``Skip the `bd export`
jsonl sync``) instruct nobody, and a sweep of literals reports eighteen of them
against a handful of real ones. The scripts this project EMITS are read where
they run instead, which is the hook channel, so nothing is lost by the exclusion
and the noise is.
"""

# beadloom:component=bd-seam

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.services.bd_seam.assumptions import call_sites, report_of
from beadloom.services.bd_seam.invocations import (
    CHANNEL_HOOK,
    python_invocations,
    text_invocations,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.services.bd_seam.assumptions import CallSiteReport

__all__ = [
    "UNREACHED",
    "flow_artifacts",
    "hook_scripts",
    "package_python",
    "project_report",
    "shell_scripts",
    "shipped_templates",
]

#: Git's own examples, which no agent is handed and which name no ``bd``.
_HOOK_SAMPLE_SUFFIX = ".sample"

#: The regions this derivation cannot reach, each with the reason, so a reader
#: can tell a region nobody looked at from one that holds nothing. Stated as
#: data because the report prints them beside the sites it did find.
UNREACHED: tuple[tuple[str, str], ...] = (
    (
        "the coordinator's launch prompt",
        "it is composed in the orchestrating loop and is not a file — `role_duties` "
        "reports `not_inspected` for the same reason",
    ),
    (
        ".claude/development/",
        "it QUOTES call forms as evidence in an issue log and a plan, and instructs "
        "nobody; scanning it would report this project's own bug reports as defects",
    ),
    (
        "a `bd` a person types",
        "no artifact carries it, so no derivation can see it — this is the region "
        "the role duties address and no check can",
    ),
    (
        "string literals inside this project's Python",
        "an error message and a help string mention `bd` and instruct nobody; the "
        "scripts this project emits are read where they run, in `.git/hooks/`",
    ),
)


def flow_artifacts(project_root: Path) -> tuple[tuple[str, str], ...]:
    """Every composed flow artifact an agent is handed, as ``(label, text)``.

    Derived from the flow's own declarations rather than listed: the agent
    directories come from ``TOOL_AGENT_DIRS``, the slash commands from
    ``COMMAND_FILES``, and the project layer is whatever ``.beadloom/flow``
    holds. A tool added to either mapping is therefore read without anyone
    editing this function.

    The composed file on disk is read rather than the composition, because what
    decides an agent's behaviour is the file it is given. A template this
    project ships reaches an agent only through a composition that lands here,
    so fixing a template and never regenerating leaves the instruction wrong and
    the check red, which is the correct verdict.
    """
    from beadloom.onboarding.agentic_flow_setup import COMMAND_FILES
    from beadloom.onboarding.composer import PROJECT_FLOW_DIRNAME
    from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS

    candidates: list[Path] = [project_root / ".claude" / "CLAUDE.md"]
    for agent_dir in TOOL_AGENT_DIRS.values():
        candidates.extend(sorted((project_root / agent_dir).glob("*.md")))
        candidates.extend(
            project_root / agent_dir.parent / "commands" / f"{name}.md"
            for name in COMMAND_FILES
        )
    candidates.extend(sorted((project_root / PROJECT_FLOW_DIRNAME).rglob("*.md")))
    return _read(candidates, project_root)


def shipped_templates() -> tuple[tuple[str, str], ...]:
    """The flow and role templates this project ships to an adopter.

    Read from the two roots the composer itself resolves, so a template added to
    either is swept without editing this function. They are the SOURCE of the
    composed artifacts above: a defect fixed here and never recomposed leaves
    both populations disagreeing, which is what the two channels make visible.
    """
    from beadloom.onboarding.agentic_flow_setup import templates_root
    from beadloom.onboarding.role_composer import roles_templates_root

    roots = (templates_root(), roles_templates_root())
    paths = [path for root in roots for path in sorted(root.rglob("*.txt"))]
    return _read(paths, _package_root().parent)


def shell_scripts() -> tuple[tuple[str, str], ...]:
    """Shell this project ships, where an invocation is executed rather than read."""
    return _read(sorted(_package_root().rglob("*.sh")), _package_root().parent)


def hook_scripts(project_root: Path) -> tuple[tuple[str, str], ...]:
    """The git hooks installed in *project_root*, including ones we did not write.

    Read from disk rather than from the templates that emit them, because a hook
    runs from disk: an adopter's hook may be older than the template, and ``bd
    init`` writes ``post-merge`` here with no template of ours behind it at all.
    """
    hooks = project_root / ".git" / "hooks"
    if not hooks.is_dir():
        return ()
    paths = [
        path
        for path in sorted(hooks.iterdir())
        if path.is_file() and not path.name.endswith(_HOOK_SAMPLE_SUFFIX)
    ]
    return _read(paths, project_root)


def package_python(self_root: Path | None = None) -> tuple[tuple[str, str], ...]:
    """Every module of the installed package — the code that will invoke ``bd``."""
    root = self_root or _package_root()
    return _read(sorted(root.rglob("*.py")), root.parent)


def project_report(project_root: Path) -> CallSiteReport:
    """The whole derived population for *project_root*, with what it did not reach."""
    instructions = (
        *flow_artifacts(project_root),
        *shipped_templates(),
        *shell_scripts(),
    )
    invocations = (
        *python_invocations(package_python()),
        *text_invocations(instructions),
        *text_invocations(hook_scripts(project_root), channel=CHANNEL_HOOK),
    )
    unreached = list(UNREACHED)
    if not (project_root / ".git" / "hooks").is_dir():
        unreached.append(
            (
                "the installed git hooks",
                f"{project_root / '.git' / 'hooks'} does not exist, so the scripts "
                "this project emits were not read where they run",
            )
        )
    return report_of(call_sites(invocations), unreached=unreached)


def _package_root() -> Path:
    """The installed ``beadloom`` package directory."""
    from pathlib import Path

    import beadloom

    return Path(beadloom.__file__).resolve().parent


def _read(paths: list[Path], relative_to: Path) -> tuple[tuple[str, str], ...]:
    """Read *paths* as ``(label, text)``, skipping what cannot be read.

    An artifact that cannot be read is not one that instructs nothing; it is
    absent from the population, and the caller sees that as a gap between the
    paths it handed over and the labels it got back.
    """
    read: list[tuple[str, str]] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            label = str(path.relative_to(relative_to))
        except ValueError:
            label = str(path)
        read.append((label, text))
    return tuple(read)
