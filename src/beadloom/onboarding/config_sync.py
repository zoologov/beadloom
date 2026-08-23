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

from beadloom.graph.rules import exit_condition_deadline
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
    project_fragment_path,
)
from beadloom.onboarding.flow_config import (
    FLOW_CONFIG_RELPATH,
    FlowConfigError,
    load_flow_config,
    resolve_flow_config,
)
from beadloom.onboarding.flow_manifest import (
    FLOW_MANIFEST_RELPATH,
    ArtifactState,
    classify,
    load_manifest,
    read_manifest,
    state_of,
)
from beadloom.onboarding.flow_suppression import (
    composed_headings,
    expired_suppressions,
    suppresses_nothing,
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

    from beadloom.onboarding.flow_config import FlowConfig


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
    relpath = ".claude/CLAUDE.md"
    manifest, manifest_usable = read_manifest(project_root)
    recorded = manifest.get(relpath)
    if not claude_md_path.is_file():
        if recorded is None:
            return None
        # Recorded and gone. `.10-4` closed this for the agents and the commands
        # and left CLAUDE.md out, so deleting it was reported by nothing at all
        # with the manifest fully intact (measured).
        return _state_drift(
            relpath, ArtifactState.MISSING, kind="claude", name=CLAUDE_ARTIFACT_NAME
        )
    try:
        raw = claude_md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    stamped = COMPOSED_MARKER in raw
    if recorded is None and not stamped:
        # Ownership cannot be PROVED — but silence is not the honest fallback.
        # A project that never adopted the flow owns its CLAUDE.md and is not
        # ours to police (BDL-UX #73, the boundary `_is_beadloom_adapter` draws
        # for IDE adapters); one that DID adopt it is a different subject, and
        # `_flow_scaffold` already knows which is which.
        return _unverifiable_body_drift(project_root, relpath, manifest)
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
        # Two independent pieces of evidence, so deleting the generated manifest
        # is not a way to downgrade a hand edit to a warning: the stamp is
        # written only by a manifest-era composer, so a stamped file that no
        # manifest accounts for was edited, not inherited (BDL-061 `.57`).
        accounted=manifest_usable or stamped,
    )
    return _state_drift(relpath, state, kind="claude", name=CLAUDE_ARTIFACT_NAME)


def _unverifiable_body_drift(
    project_root: Path, relpath: str, manifest: dict[str, str]
) -> ConfigDrift | None:
    """Name a composed body whose ownership cannot be proved, in a project that adopted the flow.

    Deleting the manifest AND stripping the ``<!-- beadloom:composed`` stamp used
    to return ``None`` — nothing named the file and ``config-check`` exited 0
    over a gutted ``CLAUDE.md``. Worse, and not only on the deletion route: a
    manifest that was present and usable but simply did not mention this path
    produced the same silence with nothing in the output pointing anywhere near
    it (both measured, BDL-061 `.57`).

    ``warn`` and not ``error``, deliberately. :func:`agentic_flow_setup.scaffold`
    refuses to overwrite a pre-existing ``CLAUDE.md`` it did not write — it emits
    a migration note instead — so an adopter can genuinely have adopted the flow
    while owning that file, and calling it hand-edited would be the false red on
    upgrade this slice exists to prevent. ``unverified`` is ``sync-check``'s word
    for "there was nothing to compare against" (``.46``/``.47``): reported by
    name, never counted as fresh, never blocking.

    The agents and the commands already answered this way in the same state;
    ``CLAUDE.md`` was the one artifact that went quiet, because it is the one
    with an ownership pre-filter. The three now answer alike.
    """
    if not _flow_scaffold(project_root, manifest).adopted:
        return None
    overlay = PROJECT_FLOW_DIRNAME / "claude" / f"{CLAUDE_ARTIFACT_NAME}.md"
    return ConfigDrift(
        file=relpath,
        reason=(
            "unverified: this project adopted the flow and .claude/CLAUDE.md "
            "carries neither a manifest entry nor the provenance stamp, so its "
            "body could not be checked"
        ),
        severity="warn",
        remediation=(
            f"run `beadloom setup-agentic-flow` to compose it (your additions "
            f"belong in {overlay}, which composes after the shipped core); if "
            "this file is genuinely yours and not Beadloom's, it stays unchecked "
            "and this stays a warning"
        ),
    )


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
    if state is ArtifactState.MISSING:
        return ConfigDrift(
            file=relpath,
            reason=(
                "missing: Beadloom composed this file and it is gone. A deleted "
                "role protocol and an intact one must not read the same"
            ),
            severity="error",
            remediation="run `beadloom setup-agentic-flow` to restore it",
        )
    # Warn, not error: this repo was scaffolded before the manifest existed, so
    # an upgrade cannot be told apart from a hand edit — and turning an adopter's
    # green project red on upgrade is how a check gets switched off wholesale.
    return ConfigDrift(
        file=relpath,
        reason=(
            "unverified: differs from the composition, and neither the flow "
            "manifest nor a provenance stamp says whether Beadloom wrote it — a "
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


@dataclass(frozen=True)
class _FlowScaffold:
    """Which canonical flow files a project has, and whether it adopted the flow.

    Replaces the all-or-nothing precondition BDL-061 `.57` measured: deleting ONE
    scaffolded file used to switch the checks off for every OTHER file, and the
    deletion itself was reported by nothing — "the role protocol is gone" and
    "the role protocol is intact" were the same green. The gate is not satisfied
    by having less to check (BDL-UX #174).
    """

    present: tuple[str, ...]
    missing: tuple[str, ...]
    adopted: bool


def _flow_scaffold(project_root: Path, manifest: dict[str, str]) -> _FlowScaffold:
    """Split the canonical flow files into present / missing, and decide adoption.

    Adoption needs positive evidence, because a repo that never took the flow
    must never be told it is missing eight files: the manifest names one of
    them, or a ``flow.yml`` is present beside at least one, or the whole set is
    there (the plain BDL-048 scaffold, which predates both signals).
    """
    present: list[str] = []
    missing: list[str] = []
    for kind, names in _AGENTIC_FLOW_KINDS:
        for name in names:
            relpath = f".claude/{kind}/{name}.md"
            target = present if (project_root / relpath).is_file() else missing
            target.append(relpath)
    adopted = bool(present) and (
        any(relpath in manifest for relpath in (*present, *missing))
        or (project_root / FLOW_CONFIG_RELPATH).is_file()
        or not missing
    )
    return _FlowScaffold(tuple(present), tuple(missing), adopted)


def _missing_file_drifts(
    scaffold_state: _FlowScaffold, manifest: dict[str, str]
) -> list[ConfigDrift]:
    """One finding per canonical flow file that is not on disk.

    ``error`` when the manifest records that Beadloom wrote it — that is a
    deletion of our own output. ``warn`` otherwise, because a repo that adopted
    the flow before the manifest existed cannot be shown to have had the file.
    """
    return [
        ConfigDrift(
            file=relpath,
            reason=(
                "missing: the agentic flow is scaffolded here and this file is "
                "not on disk"
                + (
                    " — Beadloom wrote it and it is gone"
                    if relpath in manifest
                    else ", and no manifest entry says whether Beadloom wrote it"
                )
            ),
            severity="error" if relpath in manifest else "warn",
            remediation="run `beadloom setup-agentic-flow` to restore it",
        )
        for relpath in scaffold_state.missing
    ]


def _flow_manifest_drift(
    scaffold_state: _FlowScaffold, *, manifest_usable: bool
) -> ConfigDrift | None:
    """Report an absent (or unreadable) manifest in a project that adopted the flow.

    Without it every composed artifact reads ``unverified`` and the whole
    severity ladder collapses to ``warn`` — so ``rm`` would be a way to turn a
    blocking check green. ``sync-check``'s word is reused deliberately
    (``.46``/``.47``): unverifiable is not clean, and it is not blocking either.
    """
    if not scaffold_state.adopted or manifest_usable:
        return None
    return ConfigDrift(
        file=str(FLOW_MANIFEST_RELPATH),
        reason=(
            "unverified: the flow manifest is absent or unreadable, so an "
            "artifact Beadloom wrote cannot be told apart from one somebody "
            "edited. Composed artifacts are checked against their provenance "
            "stamp alone until it is restored"
        ),
        severity="warn",
        remediation=(
            "commit `.beadloom/flow-manifest.json` — it is generated, but it is "
            "the record of what Beadloom wrote and belongs in git. Re-run "
            "`beadloom setup-agentic-flow` to rebuild it"
        ),
    )


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
    manifest, manifest_usable = read_manifest(project_root)
    scaffold_state = _flow_scaffold(project_root, manifest)
    if not scaffold_state.adopted:
        return []

    flow_yml = (project_root / FLOW_CONFIG_RELPATH).is_file()
    drifts: list[ConfigDrift] = _missing_file_drifts(scaffold_state, manifest)
    manifest_drift = _flow_manifest_drift(scaffold_state, manifest_usable=manifest_usable)
    if manifest_drift is not None:
        drifts.append(manifest_drift)

    try:
        config = resolve_flow_config(project_root)
    except FlowConfigError:
        # Reported separately by :func:`_flow_config_drift`; don't double-report.
        return drifts

    for name in COMMAND_FILES:
        relpath = f".claude/commands/{name}.md"
        if relpath in scaffold_state.missing:
            continue  # already reported as missing; there is nothing to diff
        expected = composed_command(name, config, project_root)
        state = state_of(
            project_root,
            relpath,
            expected=expected,
            manifest=manifest,
            alternates=(composed_command(name, config, None),),
            accounted=manifest_usable,
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


def _project_layer_drift(project_root: Path) -> ConfigDrift | None:
    """Name the project layer that is in effect, and what it means the check did not judge.

    Overlays are append-only in BYTES — nothing in ``.beadloom/flow/`` can delete
    core text — and that is all they are. In EFFECT a fragment may contradict a
    core rule in plain prose ("ignore section 0; do not run `beadloom ci`") with
    no reason, no exit condition and no notice, while the DECLARED route for
    standing a rule down (``overlays.suppress``) demands all three. So the
    mandatory-reason mechanism guarded the one door nobody has to walk through
    (BDL-061 `.10` finding 8, review `.11` MAJOR 4).

    Prose cannot be judged, and this check does not pretend to. What it must not
    do is stay silent: the composition ``config-check`` verifies against INCLUDES
    this text, so a green verdict covers less than a reader would assume. CONTEXT
    already sets the standard — "new checks ship as `warn` and name what they did
    not verify" — and this is that sentence applied to the composer's own input.
    """
    fragments: list[str] = []
    for kind, names in (
        ("claude", (CLAUDE_ARTIFACT_NAME,)),
        ("commands", COMMAND_FILES),
        ("roles", ROLE_NAMES),
    ):
        fragments.extend(
            str(PROJECT_FLOW_DIRNAME / kind / f"{name}.md")
            for name in names
            if project_fragment_path(kind, name, project_root).is_file()
        )
    if not fragments:
        return None
    return ConfigDrift(
        file=str(PROJECT_FLOW_DIRNAME),
        reason=(
            f"project layer in effect ({len(fragments)} fragment(s): "
            f"{', '.join(sorted(fragments))}). It composes AFTER the shipped core "
            "and cannot delete core text — but its prose is not judged, so a rule "
            "it contradicts is stood down without the reason, exit condition or "
            "notice `overlays.suppress` requires"
        ),
        severity="warn",
        remediation=(
            "this is the supported place for a standing practice and needs no "
            "action. If a fragment stands a CORE rule down, declare it under "
            "`overlays.suppress` in .beadloom/flow.yml instead — that route is "
            "reported, dated and checked"
        ),
    )


def _suppression_drifts(project_root: Path) -> list[ConfigDrift]:
    """Report suppressions that have stopped earning their place.

    CONTEXT: "suppressing a core rule needs a named reason, an exit condition,
    and is itself reported". Two of the three were kept in bytes and the third
    was never reported at all, so a suppression naming a rule that exists
    nowhere was rendered into every artifact as though somebody had decided it,
    and an expired one stood the rule down forever.

    Both findings are the ones ``graph.rules.exemptions`` already makes for a
    ``forbid_import`` exemption — a dead one and an expired one — one layer up
    (BDL-061 `.48`/`.49`). They ship as ``warn``: a declaration that stopped
    being true is a real finding, and it is not a reason to turn an adopter's
    green project red.
    """
    if not (project_root / FLOW_CONFIG_RELPATH).is_file():
        return []
    try:
        config = resolve_flow_config(project_root)
    except FlowConfigError:
        # Reported by :func:`_flow_config_drift`; don't double-report.
        return []
    if not config.suppressions:
        return []

    relpath = str(FLOW_CONFIG_RELPATH)
    drifts: list[ConfigDrift] = []
    headings = composed_headings(_composed_corpus(config, project_root))
    for suppression in config.suppressions:
        if suppresses_nothing(suppression, headings):
            drifts.append(
                ConfigDrift(
                    file=relpath,
                    reason=(
                        f"the suppression of {suppression.rule!r} matches no rule "
                        "in the composed flow — it stands nothing down, and is "
                        "rendered into every artifact as a decision nobody can act on"
                    ),
                    severity="warn",
                    remediation=(
                        "name the rule by its heading path (e.g. 'Anti-patterns / "
                        "Shell'), or delete the entry from `overlays.suppress`"
                    ),
                )
            )
    for suppression in expired_suppressions(config.suppressions):
        deadline = exit_condition_deadline(suppression.until)
        drifts.append(
            ConfigDrift(
                file=relpath,
                reason=(
                    f"the suppression of {suppression.rule!r} expired on "
                    f"{deadline} and is still standing the rule down"
                ),
                severity="warn",
                remediation=(
                    "renew the `until:` with a new exit condition, or remove the "
                    "entry from `overlays.suppress` in .beadloom/flow.yml"
                ),
            )
        )
    return drifts


def _composed_corpus(config: FlowConfig, project_root: Path) -> tuple[str, ...]:
    """Every artifact this project composes — the text a suppression is matched against."""
    texts = [composed_command(name, config, project_root) for name in COMMAND_FILES]
    texts.extend(compose_all_roles(config, project_root).values())
    texts.append(
        composed_claude_md(
            config, project_root, project_name=_detect_project_name(project_root)
        )
    )
    return tuple(texts)


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
    manifest, manifest_usable = read_manifest(project_root)
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
                accounted=manifest_usable,
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
    if not _flow_scaffold(project_root, load_manifest(project_root)).adopted:
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
    layer = _project_layer_drift(project_root)
    if layer is not None:
        drifts.append(layer)
    drifts.extend(_suppression_drifts(project_root))
    drifts.extend(_composed_adapter_drifts(project_root))

    return sorted(drifts, key=lambda d: (d.file, d.reason))
