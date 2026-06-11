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
    _scaffold_vendored,
    _vendored_asset,
)
from beadloom.onboarding.scanner import (
    _RULES_ADAPTER_TEMPLATE,
    _RULES_CONFIGS,
    _is_beadloom_adapter,
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
    """

    file: str
    reason: str


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
    Content outside the markers (human prose) is never considered.
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
    :func:`_agentic_flow_scaffolded`): each present file is byte-compared
    against its vendored template (the proven flow shipped with Beadloom), and
    any divergent file is reported. Project-specific facts live only in
    CLAUDE.md (checked separately), so the agents/commands compare exactly.
    """
    if not _agentic_flow_scaffolded(project_root):
        return []

    drifts: list[ConfigDrift] = []
    for kind, names in _AGENTIC_FLOW_KINDS:
        for name in names:
            path = project_root / ".claude" / kind / f"{name}.md"
            try:
                on_disk = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if on_disk == _vendored_asset(kind, name):
                continue
            drifts.append(
                ConfigDrift(
                    file=f".claude/{kind}/{name}.md",
                    reason=(
                        "scaffolded agentic-flow file drifted from the shipped "
                        "template (run `beadloom config-check --fix` to restore)"
                    ),
                )
            )
    return drifts


def refresh_agentic_flow_files(project_root: Path) -> list[str]:
    """Re-drop the vendored agentic-flow files into a scaffolded repo.

    The ``config-check --fix`` companion to :func:`_agentic_flow_drifts`:
    restores every drifted ``.claude/agents/*`` + ``.claude/commands/*`` from
    its shipped template (reusing the scaffold's own file-write helper with
    ``force=True``), but ONLY when the flow is already scaffolded — so ``--fix``
    never forces the flow onto a repo that did not adopt it. CLAUDE.md is left
    untouched here (its auto-regions are refreshed by the caller, preserving
    user prose). Returns the file names rewritten.
    """
    if not _agentic_flow_scaffolded(project_root):
        return []
    written: list[str] = []
    for kind, names in _AGENTIC_FLOW_KINDS:
        target_dir = project_root / ".claude" / kind
        done, _skipped = _scaffold_vendored(target_dir, kind, names, force=True)
        written.extend(f"{kind}/{name}.md" for name in done)
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

    drifts.extend(_adapter_drifts(project_root))
    drifts.extend(_agentic_flow_drifts(project_root))

    return sorted(drifts, key=lambda d: d.file)
