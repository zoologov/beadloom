# beadloom:domain=onboarding
# beadloom:feature=config-check
"""AgentConfigAsCode — drift detection for generated agent-config artifacts.

Beadloom's ``setup-rules --refresh`` generator owns three classes of
artifact:

* ``.beadloom/AGENTS.md`` — fully generated (with a preserved ``custom``
  block for user prose);
* the auto-managed sections of ``.claude/CLAUDE.md`` — the content between
  ``<!-- beadloom:auto-start ... -->`` / ``<!-- beadloom:auto-end -->``;
* IDE adapter files (``.cursorrules`` etc.) — thin generated pointers.

:func:`check_config_drift` re-runs that *same* generator in memory and
diffs its output against what is on disk, reporting one :class:`ConfigDrift`
per drifted artifact.  It is a DRY freshness checker — it never
reimplements the generation logic, and it inspects ONLY auto-managed
regions so editing user-authored prose can never trip it (avoids the
``#73`` false-positive class).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.onboarding.agentic_flow_setup import (
    AGENT_FILES,
    COMMAND_FILES,
    _vendored_asset,
    composed_claude_md,
    composed_command,
)
from beadloom.onboarding.composer import (
    CLAUDE_ARTIFACT_NAME,
    COMPOSED_MARKER,
    PROJECT_FLOW_DIRNAME,
)
from beadloom.onboarding.flow_config import (
    FLOW_CONFIG_RELPATH,
    FlowConfigError,
    load_flow_config,
    resolve_flow_config,
)
from beadloom.onboarding.flow_manifest import (
    ArtifactState,
    classify,
    load_manifest,
    state_of,
)
from beadloom.onboarding.role_adapters import TOOL_AGENT_DIRS, generate_adapters
from beadloom.onboarding.role_composer import ROLE_NAMES, compose_all_roles
from beadloom.onboarding.scanner import (
    _RULES_ADAPTER_TEMPLATE,
    _RULES_CONFIGS,
    _detect_project_name,
    _is_beadloom_adapter,
    blank_auto_regions,
    build_agents_md_content,
    refresh_claude_md,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@dataclass(frozen=True)
class ConfigDrift:
    """A single drifted agent-config artifact.

    Attributes
    ----------
    file:
        Project-relative path of the drifted artifact.
    reason:
        Agent-actionable explanation of what is stale.
    severity:
        ``error`` blocks the Gate; ``warn`` is reported and does not. A
        hand-edited or pre-manifest artifact is a ``warn``: it is a real finding
        the adopter must act on, but turning a green project red on upgrade is
        how a check gets switched off wholesale (BDL-061's standing constraint).
    remediation:
        The concrete next command or move; ``None`` falls back to the caller's
        generic advice.
    """

    file: str
    reason: str
    severity: str = "error"
    remediation: str | None = None


_AGENTS_CUSTOM_START = "<!-- beadloom:custom-start -->"
_AGENTS_CUSTOM_END = "<!-- beadloom:custom-end -->"


def _agents_auto_region(text: str) -> str:
    """Return everything in AGENTS.md OUTSIDE the user ``custom`` block.

    The block between ``custom-start``/``custom-end`` is user-authored
    prose and must never participate in the drift diff (the #73
    false-positive class).  When the markers are absent, the whole file
    is auto-managed.
    """
    sidx = text.find(_AGENTS_CUSTOM_START)
    eidx = text.find(_AGENTS_CUSTOM_END)
    if sidx == -1 or eidx == -1 or eidx < sidx:
        return text
    # Keep the markers themselves (they are generator-owned), drop the body.
    return text[: sidx + len(_AGENTS_CUSTOM_START)] + text[eidx:]


def _agents_md_drift(project_root: Path) -> ConfigDrift | None:
    """Drift for the auto-managed body of ``.beadloom/AGENTS.md``.

    Skipped if the file is absent.  Re-runs the SAME generator in memory
    and diffs ONLY the region outside the user ``custom`` block, so
    editing project-specific prose can never trip the check.
    """
    agents_path = project_root / ".beadloom" / "AGENTS.md"
    if not agents_path.is_file():
        return None

    try:
        on_disk = agents_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Re-run the SAME generator in memory (DRY — no reimplementation).
    regenerated = build_agents_md_content(project_root)
    if _agents_auto_region(regenerated) == _agents_auto_region(on_disk):
        return None

    return ConfigDrift(
        file=".beadloom/AGENTS.md",
        reason=(
            "AGENTS.md auto-managed content is stale vs the graph "
            "(architecture rules / MCP tools changed)"
        ),
    )


def _claude_md_drift(project_root: Path) -> ConfigDrift | None:
    """Drift for the auto-managed sections of ``.claude/CLAUDE.md``.

    Reuses ``refresh_claude_md(dry_run=True)`` which returns the names of
    auto-managed sections whose regenerated content differs from disk.
    Content outside the markers is checked separately by
    :func:`_claude_md_body_drift` against the composition result.
    """
    claude_md_path = project_root / ".claude" / "CLAUDE.md"
    if not claude_md_path.is_file():
        return None

    changed = refresh_claude_md(project_root, dry_run=True)
    if not changed:
        return None

    return ConfigDrift(
        file=".claude/CLAUDE.md",
        reason=(
            "auto-managed section(s) stale: "
            f"{', '.join(sorted(changed))}"
        ),
    )


def _claude_md_body_drift(project_root: Path) -> ConfigDrift | None:
    """Drift for the COMPOSED body of ``.claude/CLAUDE.md`` (BDL-UX #177).

    Until BDL-061 S3 nothing checked this file's body at all: ``config-check``
    diffed only the marker-bounded auto-regions, so replacing the entire file
    with a single line still printed ``agent-config in sync`` (measured). The
    body is now compared against ``compose("claude", ...)`` for this repo's
    ``flow.yml`` **including its project layer**, with the auto-region bodies
    blanked because those are generated per project and checked above.

    The three outcomes are three different findings, never one word: recomposable
    (we wrote it, the composition moved), hand-edited (somebody's intent lives
    only in that file — reported, never rewritten), and unmanaged (scaffolded
    before the manifest, so the two cannot be told apart and we say so).
    """
    claude_md_path = project_root / ".claude" / "CLAUDE.md"
    if not claude_md_path.is_file():
        return None
    relpath = ".claude/CLAUDE.md"
    recorded = load_manifest(project_root).get(relpath)
    try:
        raw = claude_md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if recorded is None and COMPOSED_MARKER not in raw:
        # Not a Beadloom-composed CLAUDE.md — a project's own file is not ours
        # to police (the boundary `_is_beadloom_adapter` draws for IDE adapters).
        return None
    try:
        config = resolve_flow_config(project_root)
    except FlowConfigError:
        # Reported by :func:`_flow_config_drift`; don't double-report.
        return None
    project_name = _detect_project_name(project_root)
    expected = blank_auto_regions(
        composed_claude_md(config, project_root, project_name=project_name)
    )
    shipped_only = blank_auto_regions(
        composed_claude_md(config, None, project_name=project_name)
    )
    state = classify(
        on_disk=blank_auto_regions(raw),
        expected=expected,
        recorded=recorded,
        alternates=(shipped_only,),
    )
    return _state_drift(relpath, state, kind="claude", name=CLAUDE_ARTIFACT_NAME)


def _state_drift(
    relpath: str,
    state: ArtifactState,
    *,
    kind: str,
    name: str,
) -> ConfigDrift | None:
    """Project an :class:`ArtifactState` onto a :class:`ConfigDrift` (or ``None``)."""
    if state is ArtifactState.CLEAN:
        return None
    overlay = PROJECT_FLOW_DIRNAME / kind / f"{name}.md"
    if state is ArtifactState.STALE:
        return ConfigDrift(
            file=relpath,
            reason=(
                "composed body is stale vs CORE + the flow.yml overlays + the "
                "project layer"
            ),
            severity="error",
            remediation="run `beadloom setup-agentic-flow` to recompose",
        )
    if state is ArtifactState.HAND_EDITED:
        return ConfigDrift(
            file=relpath,
            reason=(
                "hand-edited: the body differs from the composition AND from "
                "what Beadloom last wrote. It will NOT be rewritten"
            ),
            # Error, not warn: Beadloom wrote this exact file and a human changed
            # it, which is precisely what the drift-guard has always been for. The
            # change since BDL-061 S3 is that the remedy is to MOVE the edit into
            # the project layer, not to have `--fix` delete it (#139, #152).
            severity="error",
            remediation=(
                f"move the additions to {overlay} (the project layer composes "
                "after the shipped core, survives upgrades and does not trip "
                "this check), then re-run `beadloom setup-agentic-flow`"
            ),
        )
    # Warn, not error: this repo was scaffolded before the manifest existed, so
    # an upgrade cannot be told apart from a hand edit — and turning an adopter's
    # green project red on upgrade is how a check gets switched off wholesale.
    return ConfigDrift(
        file=relpath,
        reason=(
            "differs from the composition and predates the flow manifest, so a "
            "hand edit cannot be told apart from an upgrade"
        ),
        severity="warn",
        remediation=(
            f"review it; move anything project-specific to {overlay}, then "
            "re-run `beadloom setup-agentic-flow --force` to adopt the "
            "composed version"
        ),
    )


def _adapter_drifts(project_root: Path) -> list[ConfigDrift]:
    """Drift for generated IDE adapter files.

    Only files that exist AND are recognized beadloom adapters are
    checked; user-authored adapter files are left alone.
    """
    drifts: list[ConfigDrift] = []
    for cfg in _RULES_CONFIGS.values():
        rules_path = project_root / cfg["path"]
        if not rules_path.is_file():
            continue
        if _is_beadloom_adapter(rules_path) is not True:
            # Not ours (user content) or unreadable — skip.
            continue
        try:
            on_disk = rules_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if on_disk == _RULES_ADAPTER_TEMPLATE:
            continue
        drifts.append(
            ConfigDrift(
                file=cfg["path"],
                reason="IDE adapter content is stale vs the current template",
            )
        )
    return drifts


#: Kinds of vendored flow file, paired with their canonical name tuple. The
#: scaffold drops each under ``.claude/<kind>/<name>.md`` byte-identical to the
#: vendored ``<kind>/<name>.md.txt`` template (no per-project tokens — unlike
#: CLAUDE.md, the agents/commands are project-agnostic, so a plain byte compare
#: is exact). Mirrors :data:`agentic_flow_setup.AGENT_FILES`/``COMMAND_FILES``.
_AGENTIC_FLOW_KINDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("agents", AGENT_FILES),
    ("commands", COMMAND_FILES),
)


def _agentic_flow_scaffolded(project_root: Path) -> bool:
    """Whether the agentic flow is scaffolded into ``project_root``.

    True only when EVERY canonical ``.claude/agents/*`` + ``.claude/commands/*``
    file is present — so a repo that never adopted the flow (or has only a
    stray file) is never flagged, and we never force the flow on it.
    """
    for kind, names in _AGENTIC_FLOW_KINDS:
        for name in names:
            if not (project_root / ".claude" / kind / f"{name}.md").is_file():
                return False
    return True


def _agentic_flow_drifts(project_root: Path) -> list[ConfigDrift]:
    """Drift for the scaffolded ``.claude/agents/*`` + ``.claude/commands/*``.

    Only checked when the flow is fully scaffolded (see
    :func:`_agentic_flow_scaffolded`). The **commands** are compared against
    their composition (CORE + the flow.yml overlays + the project layer) rather
    than against the vendored bytes, so a project extension in
    ``.beadloom/flow/commands/`` is part of the expected result while a change
    to the shipped core still differs from it. Agents are the role composer's
    responsibility (:func:`_composed_adapter_drifts`).
    """
    if not _agentic_flow_scaffolded(project_root):
        return []

    flow_yml = (project_root / FLOW_CONFIG_RELPATH).is_file()
    try:
        config = resolve_flow_config(project_root)
    except FlowConfigError:
        # Reported separately by :func:`_flow_config_drift`; don't double-report.
        return []

    drifts: list[ConfigDrift] = []
    manifest = load_manifest(project_root)
    for name in COMMAND_FILES:
        relpath = f".claude/commands/{name}.md"
        expected = composed_command(name, config, project_root)
        state = state_of(
            project_root,
            relpath,
            expected=expected,
            manifest=manifest,
            alternates=(composed_command(name, config, None),),
        )
        drift = _state_drift(relpath, state, kind="commands", name=name)
        if drift is not None:
            drifts.append(drift)

    if not flow_yml:
        # Without a flow.yml the agents are the plain BDL-048 byte-identical
        # scaffold, so the vendored compare is exact for them too.
        for name in AGENT_FILES:
            path = project_root / ".claude" / "agents" / f"{name}.md"
            try:
                on_disk = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if on_disk == _vendored_asset("agents", name):
                continue
            drifts.append(
                ConfigDrift(
                    file=f".claude/agents/{name}.md",
                    reason=(
                        "scaffolded agentic-flow file drifted from the shipped "
                        "template"
                    ),
                    remediation=(
                        "this repo has no .beadloom/flow.yml, so the role files "
                        "are the plain vendored scaffold and there is no project "
                        "layer to hold an addition. Add a flow.yml (`beadloom "
                        "setup-agentic-flow`), then move the edit to "
                        f"{PROJECT_FLOW_DIRNAME / 'roles' / f'{name}.md'}"
                    ),
                )
            )
    return drifts


def _flow_config_drift(project_root: Path) -> ConfigDrift | None:
    """Drift for an invalid ``.beadloom/flow.yml`` (BDL-052 S3).

    Absent ``flow.yml`` is not drift (a repo may never adopt the configurator).
    A *present* one that fails validation (unknown tool / architecture / stack,
    malformed YAML) is reported with the validator's actionable message so
    ``config-check`` surfaces exactly what to fix.
    """
    if not (project_root / FLOW_CONFIG_RELPATH).is_file():
        return None
    try:
        load_flow_config(project_root)
    except FlowConfigError as exc:
        return ConfigDrift(file=str(FLOW_CONFIG_RELPATH), reason=str(exc))
    return None


def _composed_adapter_drifts(project_root: Path) -> list[ConfigDrift]:
    """Drift for composed role adapters vs ``compose_role`` for this flow.yml.

    Only runs when a valid ``.beadloom/flow.yml`` is present. For each tool the
    config names, compares every existing ``<tool-agent-dir>/<role>.md`` against
    the freshly-composed body — CORE + the configured architecture + stack
    overlays + the project fragment at ``.beadloom/flow/roles/<role>.md``. A
    CORE/overlay change without re-running ``setup-agentic-flow`` is reported;
    a project extension is not, because it is part of the expected composition
    (BDL-UX #139, #152).
    """
    if not (project_root / FLOW_CONFIG_RELPATH).is_file():
        return []
    try:
        config = load_flow_config(project_root)
    except FlowConfigError:
        # The invalid-config drift is reported separately; don't double-report.
        return []

    composed = compose_all_roles(config, project_root)
    shipped_only = compose_all_roles(config)
    manifest = load_manifest(project_root)
    drifts: list[ConfigDrift] = []
    for tool in config.tools:
        agent_dir = TOOL_AGENT_DIRS[tool]
        for role in ROLE_NAMES:
            rel = agent_dir / f"{role}.md"
            if not (project_root / rel).is_file():
                continue
            state = state_of(
                project_root,
                str(rel),
                expected=composed[role],
                manifest=manifest,
                alternates=(shipped_only[role],),
            )
            drift = _state_drift(str(rel), state, kind="roles", name=role)
            if drift is not None:
                drifts.append(drift)
    return drifts


def refresh_composed_adapters(project_root: Path) -> list[str]:
    """Recompose + rewrite the per-tool role adapters for this flow.yml.

    The ``config-check --fix`` companion to :func:`_composed_adapter_drifts`:
    when a valid ``.beadloom/flow.yml`` is present, regenerates every configured
    tool's adapter set from CORE + overlays (overwriting drifted files). A
    no-op (returns ``[]``) when ``flow.yml`` is absent or invalid.
    """
    if not (project_root / FLOW_CONFIG_RELPATH).is_file():
        return []
    try:
        config = load_flow_config(project_root)
    except FlowConfigError:
        return []
    result = generate_adapters(config, project_root)
    written: list[str] = []
    for files in result.agents.values():
        written.extend(files)
    written.extend(result.extra)
    return written


def refresh_agentic_flow_files(project_root: Path) -> list[str]:
    """Recompose the scaffolded flow files in a repo that already adopted it.

    The ``config-check --fix`` companion to :func:`_agentic_flow_drifts`: runs
    the scaffold's own non-forcing path, so every file Beadloom wrote and nobody
    touched is recomposed from CORE + overlays + the project layer, while a
    hand-edited file is left exactly as it is and reported with somewhere to put
    the edit. ``--fix`` deleting somebody's only copy of an engineering standard
    is the failure BDL-UX #139 and #152 were filed for; it does not do that any
    more. Returns the file names rewritten.
    """
    if not _agentic_flow_scaffolded(project_root):
        return []
    from beadloom.onboarding.agentic_flow_setup import scaffold

    has_flow = (project_root / FLOW_CONFIG_RELPATH).is_file()
    result = scaffold(project_root, include_agents=not has_flow)
    written = [f"agents/{name}.md" for name in result.agents_written]
    written.extend(f"commands/{name}.md" for name in result.commands_written)
    if result.claude_md is not None:
        written.append("CLAUDE.md")
    return written


def check_config_drift(
    project_root: Path,
    conn: sqlite3.Connection,
) -> list[ConfigDrift]:
    """Report agent-config artifacts that drifted from the generator.

    Regenerates AGENTS.md + the CLAUDE.md auto-managed sections + any
    present IDE adapters in memory and diffs them against disk, and (when a
    repo has the agentic flow fully scaffolded) byte-compares each
    ``.claude/agents/*`` + ``.claude/commands/*`` file against its shipped
    vendored template.  Returns one :class:`ConfigDrift` per drifted artifact
    (deterministically sorted by file path).  Absent targets are skipped —
    not drift; a repo without the flow scaffolded is never flagged for it.

    The ``conn`` parameter is accepted for signature symmetry with the
    ``beadloom ci`` orchestrator; the generator derives everything it
    needs from the on-disk graph (``rules.yml``) and project metadata.
    """
    drifts: list[ConfigDrift] = []

    agents = _agents_md_drift(project_root)
    if agents is not None:
        drifts.append(agents)

    claude = _claude_md_drift(project_root)
    if claude is not None:
        drifts.append(claude)

    body = _claude_md_body_drift(project_root)
    if body is not None:
        drifts.append(body)

    drifts.extend(_adapter_drifts(project_root))
    drifts.extend(_agentic_flow_drifts(project_root))

    flow = _flow_config_drift(project_root)
    if flow is not None:
        drifts.append(flow)
    drifts.extend(_composed_adapter_drifts(project_root))

    return sorted(drifts, key=lambda d: (d.file, d.reason))
