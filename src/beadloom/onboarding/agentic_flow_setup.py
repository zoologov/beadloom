# beadloom:domain=onboarding
# beadloom:feature=agentic-flow-setup
"""Scaffold Beadloom's proven multi-agent dev flow into any repo (BDL-048).

``beadloom setup-agentic-flow`` makes the flow that built this codebase
reproducible on a fresh repo in one command. The flow's effectiveness lives in
the EXACT wording of ``.claude/agents/*.md`` + ``.claude/commands/*.md`` (the
role protocols + coordinator playbook), refined over ~46 epics — so we
**preserve it 1:1**, never rewrite or condense (the owner's hard requirement).

Composed, never copied
----------------------
Every artifact this module writes is COMPOSED from authored package data plus
the overlays the target project's own ``flow.yml`` selects — the slash commands
and ``CLAUDE.md`` from ``templates/agentic_flow/``, the role protocols from
``templates/roles/`` through
:func:`~beadloom.onboarding.role_composer.compose_all_roles`.

The role protocols were the exception until BDL-068 `beadloom-iur5`. Five
``templates/agentic_flow/agents/*.md.txt`` assets were a byte-snapshot of THIS
repository's live ``.claude/agents/``, refreshed by a ``sync_agentic_flow``
function that no production code called and held byte-identical by two tests.
That is BDL-UX #177's shape — the shipped artifact defined as a copy of one
project's local file — left standing on the one leg BDL-061 S3 did not reach.
It was harmless only while this repository declared no
``.beadloom/flow/roles/`` fragment, because the snapshot then happened to equal
the pure shipped composition; a fragment added here would have been written
into the package by the next refresh and shipped to every adopter, silently and
byte-identically to what the tests asserted. It also had a cost that needed no
fragment: the snapshot was ONE composition — this project's DDD and Python — so
a project declaring anything else received role protocols for an architecture it
does not use.

Per-project facts, never hardcoded
-----------------------------------
The agents/commands are already project-agnostic (they describe the *process*,
not Beadloom's domains). The only project-specific content — project name,
stack, version, package list — lives in the ``.claude/CLAUDE.md``
**auto-regions** (``<!-- beadloom:auto-start ... -->`` /
``<!-- beadloom:auto-end -->``), which :func:`~beadloom.onboarding.scanner.refresh_claude_md`
already generates per-project. The scaffold drops a base ``CLAUDE.md`` (the
live one with the project name templated) and then reuses that machinery to
fill in the TARGET project's facts — so Beadloom's own facts never leak into a
scaffolded repo.

One policy for every artifact this command writes
-------------------------------------------------
The command writes three kinds of artifact into a repository it does not own:
the composed role adapters (``.claude/agents/*``, written by
:func:`~beadloom.onboarding.role_adapters.generate_adapters`), the slash
commands, and ``CLAUDE.md``. All three answer a hand edit the same way — a body
the flow manifest cannot prove Beadloom wrote is REPORTED with somewhere to move
the edit and left exactly as it is, everything Beadloom did write is recomposed
so an upgrade lands, and ``--force`` is the single explicit door.

That was true of two of the three until BDL-068 `.67`. Measured on a scratch
project scaffolded by the shipped command, with the same two lines appended to
one file of each kind and one re-run with no flags: the commands and
``CLAUDE.md`` were preserved and reported, ``.claude/agents/dev.md`` was
recomposed over, and the run printed ``Wrote .claude/agents/dev.md`` for the
file it had just eaten. ``config-check`` printed "It will NOT be rewritten" over
both of the first two under a remediation that says to re-run this command, so
following that remediation literally destroyed the edit it was printed to
protect (BDL-UX #191, the #139/#151/#186 shape in the sibling command).

Honest boundary (G4/G5)
-----------------------
The scaffolded ``CLAUDE.md`` and the command's next-steps state the boundary
honestly: the coordinator + ``Agent``-spawn are Claude-Code-native
(orchestration stays in the harness); the Beadloom **MCP process-tools** are
the deterministic, tool-agnostic substrate the flow calls; and the single
source of *true* enforcement remains ``beadloom ci`` in CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.onboarding.composer import (
    CLAUDE_ARTIFACT_NAME,
    PROJECT_FLOW_DIRNAME,
    compose,
    templates_dir,
)
from beadloom.onboarding.flow_config import (
    FlowConfig,
    persist_flow_config,
    resolve_flow_config,
)
from beadloom.onboarding.flow_manifest import (
    ArtifactState,
    classify,
    digest,
    load_manifest,
    record,
    state_of,
)
from beadloom.onboarding.role_composer import ROLE_NAMES, compose_all_roles
from beadloom.onboarding.scanner import (
    _detect_project_name,
    blank_auto_regions,
    refresh_claude_md,
)

if TYPE_CHECKING:
    from pathlib import Path

#: The role subagents this flow composes.
#: This is :data:`~beadloom.onboarding.role_composer.ROLE_NAMES` itself and not
#: a copy of it: until BDL-068 S1.5 the two were separate literals whose comments
#: each claimed to mirror the other, with eight readers between them, so a fifth
#: role reached the composer and not the scaffold — present to ``compose_role``
#: and absent from the present/missing split ``config-check`` reports (BDL-UX
#: #191's shape). The population is derived from the shipped CORE fragments;
#: adding one adds the role here too, by the same act.
AGENT_FILES: tuple[str, ...] = ROLE_NAMES

#: The slash-skill command files this flow composes.
COMMAND_FILES: tuple[str, ...] = ("coordinator", "task-init", "checkpoint", "templates")

#: Asset name for the vendored base ``CLAUDE.md`` (project name templated out).
_CLAUDE_MD_ASSET = "CLAUDE.md.txt"

#: Placeholder substituted with the target project's detected name in the
#: ``## 0.1 Project: ...`` heading (a per-project fact, not a Beadloom fact).
_PROJECT_NAME_PLACEHOLDER = "__BEADLOOM_PROJECT_NAME__"

#: The live heading line in Beadloom's own CLAUDE.md, replaced with the token
#: when vendoring so the base asset carries no project-specific name.
_LIVE_PROJECT_HEADING = "## 0.1 Project: Beadloom"


@dataclass
class ScaffoldResult:
    """Structured outcome of :func:`scaffold` (files written/skipped)."""

    agents_written: list[str] = field(default_factory=list)
    agents_skipped: list[str] = field(default_factory=list)
    commands_written: list[str] = field(default_factory=list)
    commands_skipped: list[str] = field(default_factory=list)
    claude_md: Path | None = None
    claude_md_sections_changed: list[str] = field(default_factory=list)
    #: True when the ``CLAUDE.md`` BODY was left alone (hand-edited or
    #: unverified); its auto-regions are refreshed either way, so ``claude_md``
    #: still names the file. Carried as its own field because the skip used to
    #: travel in ``commands_skipped``, where the caller rendered it through the
    #: commands path template and printed ``.claude/commands/CLAUDE.md.md`` —
    #: a path that exists in no project — beside a ``Wrote .claude/CLAUDE.md``
    #: line for the same run that had preserved it.
    claude_md_skipped: bool = False
    #: Files from a PRIOR flow layout that this version no longer owns, with the
    #: exact cleanup command. Reported, never deleted (BDL-UX #137).
    orphans: list[str] = field(default_factory=list)
    #: Hand-edited vendored files that were left alone, with where to move the
    #: edit so it survives (BDL-UX #137, #152).
    migration_notes: list[str] = field(default_factory=list)
    #: ``.beadloom/flow.yml`` when this run wrote it (a first scaffold), ``None``
    #: when the project already declared one. Naming it matters: it is the file
    #: every composed artifact is built from, and it used to be resolved in
    #: memory and never recorded (BDL-UX #187).
    flow_config_written: Path | None = None


def templates_root() -> Path:
    """Directory holding the packaged agentic-flow scaffold assets."""
    return templates_dir() / "agentic_flow"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def composed_command(name: str, config: FlowConfig, project_root: Path | None) -> str:
    """The composed body of one slash command (CORE + overlays + project)."""
    return compose("commands", name, config=config, project_root=project_root).text


def composed_claude_md(
    config: FlowConfig, project_root: Path | None, *, project_name: str
) -> str:
    """The composed ``CLAUDE.md`` body with the project name substituted in.

    The shipped CORE carries a neutral ``__BEADLOOM_PROJECT_NAME__`` token in
    the ``## 0.1 Project:`` heading; the target's detected name is filled in
    here so the scaffold never hardcodes Beadloom's own name. Since BDL-061 S3
    the CORE is **authored package data**, not a snapshot of Beadloom's own live
    file — see :func:`sync_agentic_flow`.
    """
    text = compose(
        "claude", CLAUDE_ARTIFACT_NAME, config=config, project_root=project_root
    ).text
    return text.replace(_PROJECT_NAME_PLACEHOLDER, project_name)


def _claude_md_base(project_name: str, project_root: Path | None = None) -> str:
    """Back-compatible door onto :func:`composed_claude_md` (shipped layers only)."""
    config = (
        resolve_flow_config(project_root)
        if project_root is not None
        else FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
    )
    return composed_claude_md(config, project_root, project_name=project_name)


#: Files a PRIOR flow layout put in ``.claude/commands/`` that this layout no
#: longer owns: the four roles moved to ``.claude/agents/`` and ``epic-init``
#: was superseded by ``task-init``. Reported on re-init, never deleted (#137).
SUPERSEDED_COMMAND_FILES: tuple[str, ...] = (*AGENT_FILES, "epic-init")


def _hand_edit_note(relpath: str, kind: str, name: str) -> str:
    """Migration guidance for a file we will NOT rewrite."""
    overlay = PROJECT_FLOW_DIRNAME / kind / f"{name}.md"
    return (
        f"{relpath}: hand-edited, left untouched. Move your additions to "
        f"{overlay} — the project layer composes AFTER the shipped core, so "
        "the edit survives every upgrade and does not trip `config-check`. "
        f"Then delete the edit from {relpath} and re-run "
        "`beadloom setup-agentic-flow`."
    )


def _unverified_note(relpath: str, kind: str, name: str) -> str:
    """Guidance for a file nothing accounts for — no manifest, no provenance stamp."""
    overlay = PROJECT_FLOW_DIRNAME / kind / f"{name}.md"
    return (
        f"{relpath}: unverified — differs from the composition, and nothing "
        "records whether Beadloom wrote it, so it cannot be told apart from a hand edit — left "
        f"untouched. Review it; move anything project-specific to {overlay}, "
        "then re-run with `--force` to adopt the composed version."
    )


def _scaffold_composed(
    project_root: Path,
    kind: str,
    names: tuple[str, ...],
    bodies: dict[str, str],
    *,
    target_subdir: str,
    force: bool,
) -> tuple[list[str], list[str], list[str]]:
    """Write one kind's composed files; return (written, skipped, notes).

    A file we last wrote and nobody touched is recomposed in place. A file that
    differs from BOTH the composition and our recorded digest was edited by a
    human: it is skipped and reported with somewhere to put the edit, and is
    only overwritten under ``force``. That is the difference between an
    idempotent generator and one that eats work.
    """
    written: list[str] = []
    skipped: list[str] = []
    notes: list[str] = []
    manifest = load_manifest(project_root)
    recorded: dict[str, str] = {}
    for name in names:
        content = bodies[name]
        relpath = f".claude/{target_subdir}/{name}.md"
        dest = project_root / ".claude" / target_subdir / f"{name}.md"
        state = state_of(project_root, relpath, expected=content, manifest=manifest)
        if state is ArtifactState.CLEAN:
            written.append(name)
            recorded[relpath] = digest(content)
            continue
        if not force and state is ArtifactState.HAND_EDITED:
            skipped.append(name)
            notes.append(_hand_edit_note(relpath, kind, name))
            continue
        if not force and state is ArtifactState.UNVERIFIED and dest.is_file():
            skipped.append(name)
            notes.append(_unverified_note(relpath, kind, name))
            continue
        _write(dest, content)
        written.append(name)
        recorded[relpath] = digest(content)
    record(project_root, recorded)
    return written, skipped, notes


def orphaned_flow_files(project_root: Path) -> list[str]:
    """Files a PRIOR flow layout left behind, with the exact cleanup command.

    A cross-major re-init used to write the new layout and say nothing about the
    old one, leaving four role files and ``epic-init`` in ``.claude/commands/``
    that no longer mean anything (BDL-UX #137). They are REPORTED, never
    removed: deleting a file the adopter may have edited is not ours to decide.
    """
    commands_dir = project_root / ".claude" / "commands"
    orphans: list[str] = []
    for name in SUPERSEDED_COMMAND_FILES:
        path = commands_dir / f"{name}.md"
        if path.is_file():
            relpath = f".claude/commands/{name}.md"
            moved = (
                f" (this role now lives at .claude/agents/{name}.md)"
                if name in AGENT_FILES
                else " (superseded by .claude/commands/task-init.md)"
            )
            orphans.append(f"{relpath}: left by an older flow layout{moved} — "
                           f"remove with `rm -f {relpath}`")
    return orphans


def _scaffold_claude_md(
    project_root: Path,
    config: FlowConfig,
    *,
    force: bool,
) -> tuple[Path, list[str], list[str], list[str]]:
    """Write/refresh ``.claude/CLAUDE.md``; return (path, changed, skipped, notes).

    The composed body is written when the file is absent, or when it still
    matches what we last wrote (so an upgrade or a new project-layer fragment
    lands), then :func:`refresh_claude_md` regenerates the per-project
    auto-regions. A body that differs from BOTH the composition and the recorded
    digest is a hand edit: reported with migration guidance and left alone.

    Comparison is over the composition with the auto-region bodies blanked —
    those are generated per project and are checked separately, so including
    them would report drift on facts that are supposed to move.
    """
    claude_md = project_root / ".claude" / "CLAUDE.md"
    relpath = ".claude/CLAUDE.md"
    project_name = _detect_project_name(project_root)
    expected = blank_auto_regions(
        composed_claude_md(config, project_root, project_name=project_name)
    )
    on_disk = (
        blank_auto_regions(claude_md.read_text(encoding="utf-8"))
        if claude_md.is_file()
        else None
    )
    state = classify(
        on_disk=on_disk,
        expected=expected,
        recorded=load_manifest(project_root).get(relpath),
    )
    skipped: list[str] = []
    notes: list[str] = []
    if not force and state is ArtifactState.HAND_EDITED:
        skipped.append("CLAUDE.md")
        notes.append(_hand_edit_note(relpath, "claude", CLAUDE_ARTIFACT_NAME))
    elif not force and state is ArtifactState.UNVERIFIED and claude_md.is_file():
        skipped.append("CLAUDE.md")
        notes.append(_unverified_note(relpath, "claude", CLAUDE_ARTIFACT_NAME))
    elif state is not ArtifactState.CLEAN:
        _write(
            claude_md, composed_claude_md(config, project_root, project_name=project_name)
        )
    changed = refresh_claude_md(project_root)
    if not skipped:
        record(
            project_root,
            {relpath: digest(blank_auto_regions(claude_md.read_text(encoding="utf-8")))},
        )
    return claude_md, changed, skipped, notes


def scaffold(
    project_root: Path,
    *,
    force: bool = False,
    include_agents: bool = True,
    config: FlowConfig | None = None,
) -> ScaffoldResult:
    """Scaffold the agentic flow into ``project_root``.

    Composes the slash commands and ``CLAUDE.md`` from CORE + the architecture
    and stack overlays this repo's ``flow.yml`` selects + the project layer in
    ``.beadloom/flow/``, then generates the ``CLAUDE.md`` auto-regions for the
    target project. Safe to re-run: a file untouched since we wrote it is
    recomposed, a hand-edited one is reported and left alone, and ``force``
    overwrites regardless.

    Since BDL-052 S3 the role files (``.claude/agents/*``) are **composed** by
    :func:`~beadloom.onboarding.role_adapters.generate_adapters` (the source of
    truth for those files), which writes one adapter set per configured tool.
    Pass ``include_agents=False`` so this function leaves them to it — the CLI
    does. The default writes the single ``.claude/agents/`` set for the one
    caller that has no adapter generator to defer to:
    :func:`~beadloom.onboarding.config_sync.refresh_agentic_flow_files`, for a
    repository that adopted the flow before ``.beadloom/flow.yml`` existed.
    Since ``beadloom-iur5`` those bodies are the same composition every other
    writer produces, rather than a snapshot of this repository's own role files.
    """
    result = ScaffoldResult()
    # A caller that already resolved the config (the CLI, with its flags) passes
    # it in. Re-resolving from disk here ignored `--architecture`/`--stack`, so a
    # flagged run composed the ROLE adapters for one selection and the commands +
    # CLAUDE.md for another (BDL-UX #187, found while closing it).
    if config is None:
        config = resolve_flow_config(project_root)
    result.flow_config_written = persist_flow_config(project_root, config)
    result.orphans = orphaned_flow_files(project_root)
    agent_notes: list[str] = []
    if include_agents:
        (
            result.agents_written,
            result.agents_skipped,
            agent_notes,
        ) = _scaffold_composed(
            project_root,
            "roles",
            AGENT_FILES,
            compose_all_roles(config, project_root),
            target_subdir="agents",
            force=force,
        )
    bodies = {
        name: composed_command(name, config, project_root) for name in COMMAND_FILES
    }
    (
        result.commands_written,
        result.commands_skipped,
        command_notes,
    ) = _scaffold_composed(
        project_root,
        "commands",
        COMMAND_FILES,
        bodies,
        target_subdir="commands",
        force=force,
    )
    (
        result.claude_md,
        result.claude_md_sections_changed,
        claude_skipped,
        claude_notes,
    ) = _scaffold_claude_md(project_root, config, force=force)
    result.claude_md_skipped = bool(claude_skipped)
    result.migration_notes = [*agent_notes, *command_notes, *claude_notes]
    return result
