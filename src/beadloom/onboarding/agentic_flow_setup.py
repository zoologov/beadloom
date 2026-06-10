# beadloom:domain=onboarding
"""Scaffold Beadloom's proven multi-agent dev flow into any repo (BDL-048).

``beadloom setup-agentic-flow`` makes the flow that built this codebase
reproducible on a fresh repo in one command. The flow's effectiveness lives in
the EXACT wording of ``.claude/agents/*.md`` + ``.claude/commands/*.md`` (the
role protocols + coordinator playbook), refined over ~46 epics — so we
**preserve it 1:1**, never rewrite or condense (the owner's hard requirement).

Vendor-1:1 + drift-guard
------------------------
The scaffold's templates for ``agents/*`` + ``commands/*`` are **vendored
byte-identical copies** of Beadloom's own live ``.claude/`` (Beadloom is the
reference implementation), shipped as inert ``*.md.txt`` package data so they
are not picked up as docs/linted as live config. :func:`sync_agentic_flow`
copies the live ``.claude/`` -> templates, and a drift-guard test asserts each
vendored template byte-matches the live file (mirrors the F4.1
``sync_vendored_harness`` pattern). If the live flow improves, the test fails
until re-vendored, so the scaffold always ships the latest proven flow.

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
from pathlib import Path

from beadloom.onboarding.scanner import _detect_project_name, refresh_claude_md

#: Role subagent files vendored byte-identical from the live ``.claude/agents/``.
AGENT_FILES: tuple[str, ...] = ("dev", "test", "review", "tech-writer")

#: Slash-skill command files vendored byte-identical from ``.claude/commands/``.
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


def templates_root() -> Path:
    """Directory holding the packaged agentic-flow scaffold assets."""
    return Path(__file__).resolve().parent / "templates" / "agentic_flow"


def vendored_flow_root() -> Path:
    """Directory holding the vendored ``agents/`` + ``commands/`` assets."""
    return templates_root()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _vendored_asset(kind: str, name: str) -> str:
    """Read a vendored ``agents/`` or ``commands/`` asset (``*.md.txt``)."""
    return (vendored_flow_root() / kind / f"{name}.md.txt").read_text(encoding="utf-8")


def _claude_md_base(project_name: str) -> str:
    """The base ``CLAUDE.md`` with the project name substituted in.

    The vendored asset carries a neutral ``__BEADLOOM_PROJECT_NAME__`` token in
    the ``## 0.1 Project:`` heading; the target's detected name is filled in
    here so the scaffold never hardcodes Beadloom's own name.
    """
    text = (vendored_flow_root() / _CLAUDE_MD_ASSET).read_text(encoding="utf-8")
    return text.replace(_PROJECT_NAME_PLACEHOLDER, project_name)


def _scaffold_vendored(
    target_dir: Path,
    kind: str,
    names: tuple[str, ...],
    *,
    force: bool,
) -> tuple[list[str], list[str]]:
    """Drop the vendored ``*.md`` files for one kind; return (written, skipped).

    Idempotent: an existing file whose content already matches is left alone
    (reported as written-stable); a divergent file is only overwritten with
    ``force`` (otherwise skipped so user edits are not silently clobbered).
    """
    written: list[str] = []
    skipped: list[str] = []
    for name in names:
        content = _vendored_asset(kind, name)
        dest = target_dir / f"{name}.md"
        if dest.is_file() and not force:
            if dest.read_text(encoding="utf-8") == content:
                written.append(name)
            else:
                skipped.append(name)
            continue
        _write(dest, content)
        written.append(name)
    return written, skipped


def _scaffold_claude_md(project_root: Path, *, force: bool) -> tuple[Path, list[str]]:
    """Write/refresh ``.claude/CLAUDE.md`` with per-project auto-regions.

    Drops the base ``CLAUDE.md`` (only when absent, or when ``force``) then
    reuses :func:`refresh_claude_md` to regenerate the ``project-info``
    auto-region with the TARGET project's facts. User prose outside the
    auto-regions is preserved verbatim (``refresh_claude_md`` only touches the
    marker-bounded regions).
    """
    claude_md = project_root / ".claude" / "CLAUDE.md"
    project_name = _detect_project_name(project_root)
    if force or not claude_md.is_file():
        _write(claude_md, _claude_md_base(project_name))
    changed = refresh_claude_md(project_root)
    return claude_md, changed


def scaffold(project_root: Path, *, force: bool = False) -> ScaffoldResult:
    """Scaffold the agentic flow into ``project_root``.

    Idempotently drops the vendored ``agents/*`` + ``commands/*`` into
    ``.claude/`` (byte-identical to the live proven flow) and generates the
    ``.claude/CLAUDE.md`` auto-regions for the target project. Safe to re-run;
    ``force`` overwrites hand-edited scaffolded files.
    """
    result = ScaffoldResult()
    agents_dir = project_root / ".claude" / "agents"
    result.agents_written, result.agents_skipped = _scaffold_vendored(
        agents_dir, "agents", AGENT_FILES, force=force
    )
    commands_dir = project_root / ".claude" / "commands"
    result.commands_written, result.commands_skipped = _scaffold_vendored(
        commands_dir, "commands", COMMAND_FILES, force=force
    )
    result.claude_md, result.claude_md_sections_changed = _scaffold_claude_md(
        project_root, force=force
    )
    return result


def sync_agentic_flow(live_claude_root: Path) -> list[str]:
    """Refresh the packaged ``*.md.txt`` assets from the live ``.claude/``.

    Drift guard (preserve the flow 1:1): copies every live ``agents/*.md`` +
    ``commands/*.md`` into the package as inert ``.md.txt`` data, and snapshots
    the live ``CLAUDE.md`` as the base asset with the project name replaced by a
    neutral token. Returns the asset names written (project-relative to the
    templates root). Asserted byte-for-byte in the test suite.
    """
    root = vendored_flow_root()
    written: list[str] = []
    for kind, names in (("agents", AGENT_FILES), ("commands", COMMAND_FILES)):
        dest_dir = root / kind
        dest_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            content = (live_claude_root / kind / f"{name}.md").read_text(
                encoding="utf-8"
            )
            (dest_dir / f"{name}.md.txt").write_text(content, encoding="utf-8")
            written.append(f"{kind}/{name}.md.txt")
    root.mkdir(parents=True, exist_ok=True)
    claude_md = (live_claude_root / "CLAUDE.md").read_text(encoding="utf-8")
    claude_md = claude_md.replace(
        _LIVE_PROJECT_HEADING, f"## 0.1 Project: {_PROJECT_NAME_PLACEHOLDER}"
    )
    (root / _CLAUDE_MD_ASSET).write_text(claude_md, encoding="utf-8")
    written.append(_CLAUDE_MD_ASSET)
    return written
