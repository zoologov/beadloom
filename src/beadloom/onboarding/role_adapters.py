# beadloom:domain=onboarding
# beadloom:feature=role-adapters
"""Generate per-tool role adapters from composed roles (BDL-052 S3).

The role configurator's output stage: given a :class:`FlowConfig`, compose each
role (CORE + architecture + stack overlays) once and write a **per-tool adapter
set** for every configured tool:

* ``claude`` → ``.claude/agents/<role>.md`` (the Claude-Code subagent files).
  The slash-command set (``.claude/commands/*``) is vendored separately by
  :mod:`beadloom.onboarding.agentic_flow_setup` and is not regenerated here.
* ``cursor`` → ``.cursor/agents/<role>.md`` (Cursor subagents — same composed
  body). The composed core and the four commands a Cursor agent reads are
  ``.cursor/rules/*.mdc``, written by the scaffold beside ``.claude/CLAUDE.md``
  and ``.claude/commands/*`` (:mod:`beadloom.onboarding.tool_reach`). Until
  BDL-083 S2h this module wrote a 17-line pointer there instead, which carried
  no layer of the flow (BDL-UX #356).

Every adapter body is exactly ``compose_role(...)`` for the repo's ``flow.yml``
**plus its project layer** (``.beadloom/flow/roles/<role>.md``), so
:func:`generate_adapters` is the single writer the drift-guard verifies against:
a CORE/overlay change without regenerating makes the on-disk file differ from
the recomputed composition and is reported, while a project extension is part of
the expected result and is not (BDL-UX #139, #152). Each write is fingerprinted
in the flow manifest so a later run can tell its own output from a hand edit.

One policy, for every writer
----------------------------
A body Beadloom cannot prove it wrote is **reported and left alone**; everything
it can prove it wrote is recomposed, so an upgrade still lands; ``--force`` is
the single explicit door. That is what ``setup-agentic-flow`` already did for
its slash commands and ``CLAUDE.md`` and did not do here, so one command
answered one hand edit two ways and an adopter could not predict which of their
edits survived (BDL-UX #191).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from beadloom.onboarding.flow_manifest import digest, load_manifest, record
from beadloom.onboarding.role_composer import ROLE_NAMES, compose_all_roles

if TYPE_CHECKING:
    from beadloom.onboarding.flow_config import FlowConfig

#: Where each tool's composed role files live, relative to the project root.
TOOL_AGENT_DIRS: dict[str, Path] = {
    "claude": Path(".claude") / "agents",
    "cursor": Path(".cursor") / "agents",
}

@dataclass
class AdapterResult:
    """Files written per tool by :func:`generate_adapters`.

    ``agents`` maps a tool name to the project-relative role-file paths written;
    ``extra`` lists any non-role files this writer produced -- none since the
    Cursor pointer was retired, kept so a caller's loop over it stays valid;
    ``preserved`` lists the paths a caller asked to be left alone, so a run that
    did not write a file it normally writes says so rather than going quiet.
    """

    agents: dict[str, list[str]] = field(default_factory=dict)
    extra: list[str] = field(default_factory=list)
    preserved: list[str] = field(default_factory=list)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_adapters(
    config: FlowConfig,
    project_root: Path,
    *,
    preserve: frozenset[str] = frozenset(),
) -> AdapterResult:
    """Compose roles for ``config`` and write each configured tool's adapter set.

    For every tool in ``config.tools`` writes ``<tool-agent-dir>/<role>.md`` with
    the composed body. Idempotent — the bytes depend only on ``config`` + the overlay
    sources, so re-running with the same config rewrites identical files.
    Returns an :class:`AdapterResult` of the project-relative paths written.

    ``preserve`` names project-relative paths to leave exactly as they are. The
    caller establishes ownership, not this function, and since BDL-068 `.67`
    both callers establish the same one: an adapter whose body Beadloom cannot
    prove it wrote is preserved, because rewriting it deletes the only copy of
    somebody's intent (BDL-UX #186, #139, #152). ``config-check --fix`` has done
    that since BDL-061 `.59`; ``setup-agentic-flow`` used to pass nothing, on the
    reading that a scaffold is an explicit instruction to compose. That reading
    is retired: the same command already declined for its other two artifact
    kinds, so one command answered one hand edit two ways and nothing said which
    was intended (BDL-UX #191). ``--force`` is the one door, and both callers
    derive their preserve set from
    :func:`~beadloom.onboarding.config_sync.declined_adapter_rewrites`.

    A preserved path is not recorded in the flow manifest either — recording a
    digest we did not write would make the next run believe the edit was ours.
    """
    composed = compose_all_roles(config, project_root)
    result = AdapterResult()
    recorded: dict[str, str] = {}
    for tool in config.tools:
        agent_dir = TOOL_AGENT_DIRS[tool]
        written: list[str] = []
        for role in ROLE_NAMES:
            relpath = agent_dir / f"{role}.md"
            if str(relpath) in preserve:
                result.preserved.append(str(relpath))
                continue
            _write(project_root / relpath, composed[role])
            written.append(str(relpath))
            recorded[str(relpath)] = digest(composed[role])
        result.agents[tool] = written
    record(project_root, recorded)
    return result


#: The phrase every orphan finding carries, so a caller can recognise one
#: without matching a sentence a later reword would break.
ORPHAN_MARKER = "no tool this flow declares claims it"


@dataclass(frozen=True)
class OrphanedAdapter:
    """One role adapter Beadloom wrote for a tool the flow no longer declares.

    Every reader of role adapters takes its population from ``config.tools`` —
    :func:`~beadloom.onboarding.config_sync._adapter_states`,
    :func:`~beadloom.onboarding.config_sync.declined_adapter_rewrites` and
    ``role_duties._role_files_on_disk`` all open with that loop. So narrowing
    ``tools:`` does not add a finding about the files the dropped tool wrote; it
    removes them from the check. Measured on 2026-09-09 with a control: the same
    two lines appended to ``.claude/agents/dev.md`` and to
    ``.cursor/agents/dev.md``, in a project whose flow declares ``claude`` only,
    are an ``error`` on the first and exit 0 on the second.

    ``diverged`` says the body no longer matches the digest the flow manifest
    recorded — the silent change the finding exists for, told apart from the
    file that has merely stopped being watched.
    """

    file: str
    tool: str
    diverged: bool

    @property
    def why(self) -> str:
        """What is wrong, in the words a reader of the file needs."""
        subject = (
            f"orphaned adapter: Beadloom wrote it for the `{self.tool}` tool "
            f"and {ORPHAN_MARKER}"
        )
        if not self.diverged:
            return (
                f"{subject}, so nothing compares it any more while the tool "
                "that reads it still reads it"
            )
        return (
            f"{subject} — and it ALREADY differs from what Beadloom wrote, "
            "which no check reported because dropping the tool removed the "
            "file from the check instead of reporting it"
        )

    @property
    def remediation(self) -> str:
        """The two moves that exist, neither of which Beadloom takes for you."""
        return (
            f"put `{self.tool}` back in `tools:` in .beadloom/flow.yml to bring "
            f"this file back under the drift check, or delete {self.file} — "
            "Beadloom leaves it alone either way, because deleting somebody's "
            "file is not a repair"
        )


def orphaned_adapters(
    project_root: Path, config: FlowConfig
) -> tuple[OrphanedAdapter, ...]:
    """Role adapters this flow's manifest records under an undeclared tool.

    THE POPULATION IS THE MANIFEST, not :data:`TOOL_AGENT_DIRS` crossed with
    :data:`~beadloom.onboarding.role_composer.ROLE_NAMES`. Two consequences,
    both wanted. A file Beadloom never recorded writing is somebody else's — an
    adopter who drives Cursor by hand owns ``.cursor/agents/dev.md`` outright,
    and claiming it would be the false positive ``_adapter_drifts`` avoids by
    checking only adapters it recognises. And a role a later release renames or
    retires is still reported, because the record of the write does not depend
    on the roles this release happens to compose.

    THE STATED LIMIT: provenance comes from the manifest, so a project whose
    ``.beadloom/flow-manifest.json`` was deleted has none and is under-reported
    here. That is deliberate — absent information must not manufacture a claim
    about somebody's file — and it costs little in practice, because the
    manifest is source rather than derived state and the generated ignore block
    does not list it.

    THE NAMED EXCLUSION: ``.cursor/rules/`` -- the pointer 9.0.0 wrote and the
    rules that replaced it. They sit outside the agent directory, so the parent
    test below never reads them as role adapters; a pointer left by 9.0.0 is
    reported by the scaffold as an older layout's file instead.
    """
    declared = set(config.tools)
    manifest = load_manifest(project_root)
    found: list[OrphanedAdapter] = []
    for tool, agent_dir in TOOL_AGENT_DIRS.items():
        if tool in declared:
            continue
        for relpath, recorded in manifest.items():
            candidate = Path(relpath)
            if candidate.parent != agent_dir or candidate.suffix != ".md":
                continue
            path = project_root / candidate
            if not path.is_file():
                # Already deleted. The adopter took one of the two moves the
                # remediation names, and reporting a repair is noise.
                continue
            found.append(
                OrphanedAdapter(
                    file=relpath,
                    tool=tool,
                    diverged=_diverged(path, recorded),
                )
            )
    return tuple(sorted(found, key=lambda orphan: orphan.file))


def _diverged(path: Path, recorded: str) -> bool:
    """Whether the body at ``path`` still matches the digest Beadloom recorded.

    An undecodable body counts as diverged rather than as unknown, and the
    inference is sound rather than defensive: :func:`_write` writes UTF-8, so a
    file that will not decode as UTF-8 is not the body Beadloom wrote. Skipping
    it would answer clean about a file nothing has looked at.
    """
    try:
        return digest(path.read_text(encoding="utf-8")) != recorded
    except (OSError, UnicodeDecodeError):
        return True
