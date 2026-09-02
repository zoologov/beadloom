"""Setup / onboarding / init commands.

Owns the ``setup-*`` family (``setup-mcp``, ``setup-rules``,
``setup-ai-techwriter``, ``setup-agentic-flow``, ``setup-branch-protection``),
plus ``config-check``, ``mcp-serve``, and ``init``.
"""
# beadloom:component=cli-commands

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click

from beadloom.services.commands._root import _warn_missing_parsers, main

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beadloom.application.gate import GateStep
    from beadloom.onboarding.agentic_flow_setup import ScaffoldResult
    from beadloom.onboarding.config_sync import ConfigDrift, FixReport

# beadloom:service=mcp-server
_MCP_TOOL_CONFIGS: dict[str, dict[str, str]] = {
    "claude-code": {"path_template": "{project}/.mcp.json", "scope": "project"},
    "cursor": {"path_template": "{project}/.cursor/mcp.json", "scope": "project"},
    "windsurf": {
        "path_template": "{home}/.codeium/windsurf/mcp_config.json",
        "scope": "global",
    },
}


def _mcp_path_for_editor(editor: str, project_root: Path) -> str:
    """Return the MCP config file path for display."""
    paths = {
        "claude-code": ".mcp.json",
        "cursor": ".cursor/mcp.json",
        "windsurf": "~/.codeium/windsurf/mcp_config.json",
    }
    return paths.get(editor, ".mcp.json")


@main.command("setup-mcp")
@click.option("--remove", is_flag=True, help="Remove beadloom from MCP config.")
@click.option(
    "--tool",
    "tool_name",
    type=click.Choice(["claude-code", "cursor", "windsurf"]),
    default="claude-code",
    help="Editor/tool to configure (default: claude-code).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def setup_mcp(*, remove: bool, tool_name: str, project: Path | None) -> None:
    """Create or update MCP config for beadloom MCP server.

    Supports Claude Code (.mcp.json), Cursor (.cursor/mcp.json),
    and Windsurf (~/.codeium/windsurf/mcp_config.json).
    """
    import shutil

    project_root = project or Path.cwd()
    tool_cfg = _MCP_TOOL_CONFIGS[tool_name]

    mcp_json_path = Path(
        tool_cfg["path_template"].format(
            project=project_root,
            home=Path.home(),
        )
    )

    # Ensure parent directory exists.
    mcp_json_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing or create new.
    if mcp_json_path.exists():
        data = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    else:
        data = {"mcpServers": {}}

    if "mcpServers" not in data:
        data["mcpServers"] = {}

    if remove:
        data["mcpServers"].pop("beadloom", None)
        mcp_json_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        click.echo(f"Removed beadloom from {mcp_json_path}")
        return

    # Find beadloom command path.
    beadloom_path = shutil.which("beadloom") or "beadloom"

    args: list[str] = ["mcp-serve"]
    # Global configs need explicit --project path.
    if tool_cfg["scope"] == "global":
        args.extend(["--project", str(project_root.resolve())])

    data["mcpServers"]["beadloom"] = {
        "command": beadloom_path,
        "args": args,
    }

    mcp_json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    click.echo(f"Updated {mcp_json_path}")


@main.command("setup-rules")
@click.option(
    "--tool",
    "tool_name",
    type=click.Choice(["cursor", "windsurf", "cline"]),
    default=None,
    help="Target IDE (default: auto-detect all).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--refresh",
    is_flag=True,
    default=False,
    help="Refresh auto-managed sections in .claude/CLAUDE.md and regenerate AGENTS.md.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what --refresh would change without modifying files.",
)
def setup_rules(
    *,
    tool_name: str | None,
    project: Path | None,
    refresh: bool,
    dry_run: bool,
) -> None:
    """Create IDE rules files that reference .beadloom/AGENTS.md.

    Auto-detects installed IDEs (Cursor, Windsurf, Cline) by marker
    files and creates thin adapter files. Does not overwrite existing files.

    With --refresh, also refreshes auto-managed sections in .claude/CLAUDE.md
    and regenerates .beadloom/AGENTS.md.  Use --dry-run with --refresh to
    preview changes without writing.
    """
    from beadloom.onboarding.scanner import (
        _RULES_ADAPTER_TEMPLATE,
        _RULES_CONFIGS,
        generate_agents_md,
        refresh_claude_md,
        setup_rules_auto,
    )

    project_root = project or Path.cwd()

    if dry_run and not refresh:
        click.echo("Error: --dry-run requires --refresh.", err=True)
        raise SystemExit(1)

    if refresh:
        # Refresh CLAUDE.md auto-managed sections.
        changed = refresh_claude_md(project_root, dry_run=dry_run)
        if changed:
            verb = "Would update" if dry_run else "Updated"
            click.echo(f"{verb} .claude/CLAUDE.md sections: {', '.join(changed)}")
        else:
            click.echo(".claude/CLAUDE.md: no changes needed.")

        # Regenerate AGENTS.md (unless dry-run).
        if not dry_run:
            agents_path = generate_agents_md(project_root)
            click.echo(f"Regenerated {agents_path.relative_to(project_root)}")
        else:
            click.echo("Would regenerate .beadloom/AGENTS.md")
        return

    if tool_name:
        # Explicit IDE specified — create without marker detection.
        cfg = _RULES_CONFIGS[tool_name]
        rules_path = project_root / cfg["path"]
        if rules_path.exists():
            click.echo(f"Skipped: {cfg['path']} already exists.")
            return
        rules_path.write_text(_RULES_ADAPTER_TEMPLATE, encoding="utf-8")
        click.echo(f"Created {cfg['path']}")
    else:
        # Auto-detect.
        created = setup_rules_auto(project_root)
        if created:
            for f in created:
                click.echo(f"Created {f}")
        else:
            click.echo("No IDE markers detected. Use --tool to specify.")


# beadloom:domain=onboarding
@main.command("setup-ai-techwriter")
@click.option(
    "--platform",
    type=click.Choice(["github", "gitlab"]),
    required=True,
    help="CI platform to scaffold for (github or gitlab).",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def setup_ai_techwriter(*, platform: str, project: Path | None) -> None:
    """Scaffold the AI tech-writer into this repo (BDL-047 / F4.1, G8).

    In the setup-* family (alongside setup-mcp / setup-rules). The harness ships
    inside the installed ``beadloom`` package (BDL-051 / S2), so this no longer
    vendors any Python: it idempotently drops the chosen platform's CI wrapper
    (which invokes ``python -m beadloom.ai_agents.ai_techwriter``), the operator
    artifacts ``tools/ai_techwriter/{recipe.yaml,provision-runner.sh}`` (copied
    from package data for reference + runner provisioning), and the
    getting-started guide ``docs/guides/ai-techwriter.md``. Re-running cleanly
    overwrites the generated files.
    """
    from beadloom.onboarding.ai_techwriter_setup import scaffold

    project_root = project or Path.cwd()
    created = scaffold(project_root, platform=platform)
    for path in created:
        click.echo(f"Wrote {path.relative_to(project_root)}")
    click.echo(
        "Next: 1) pick a box (>=4 GB RAM), 2) get a runner registration token + "
        "add the QWEN_API_KEY secret/variable, 3) on the VPS run "
        "./tools/ai_techwriter/provision-runner.sh --platform <github|gitlab> "
        "--repo <url> --token <tok>, then commit + enable the pipeline. "
        "See docs/guides/ai-techwriter.md."
    )


# beadloom:domain=onboarding
@main.command("setup-agentic-flow")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite hand-edited scaffolded flow files (default: preserve them).",
)
@click.option(
    "--tool",
    "tools",
    multiple=True,
    type=click.Choice(["claude", "cursor"]),
    help="Tool adapter set(s) to generate (repeatable). Default: flow.yml or claude.",
)
@click.option(
    "--architecture",
    "architecture",
    type=click.Choice(["ddd", "fsd"]),
    default=None,
    help="Architecture methodology overlay. Default: flow.yml or ddd.",
)
@click.option(
    "--stack",
    "stack",
    default=None,
    help=(
        "Comma-separated stack overlays "
        "(python,fastapi,javascript,typescript,vuejs). Default: flow.yml or "
        "auto-detected."
    ),
)
def setup_agentic_flow(
    *,
    project: Path | None,
    force: bool,
    tools: tuple[str, ...],
    architecture: str | None,
    stack: str | None,
) -> None:
    """Scaffold Beadloom's proven multi-agent dev flow into this repo (BDL-048/052).

    In the setup-* family (alongside setup-rules / setup-mcp). Composes the role
    subagents from CORE + the selected architecture overlay (``ddd``/``fsd``) +
    the selected stack overlays, then writes the per-tool adapter set(s) — for
    ``claude`` to ``.claude/agents/*`` (+ ``.claude/commands/*`` + a per-project
    ``.claude/CLAUDE.md``), for ``cursor`` to ``.cursor/agents/*`` (+ a Cursor
    orchestrator pointer). Selection comes from ``.beadloom/flow.yml`` (or the
    ``--tool``/``--architecture``/``--stack`` flags, which override it; defaults
    are ``claude`` / ``ddd`` / auto-detected stack). A drift-guard test keeps
    every generated adapter byte-identical to its composition. User prose
    outside CLAUDE.md auto-regions is never touched; --force overwrites
    hand-edited Claude flow files.
    """
    from beadloom.application.guards.checks import GUARD_NAMES
    from beadloom.onboarding.agentic_flow_setup import scaffold
    from beadloom.onboarding.flow_config import FlowConfigError, resolve_flow_config
    from beadloom.onboarding.guard_hooks import scaffold_guard_hooks
    from beadloom.onboarding.ignore_block import ensure_ignore_block
    from beadloom.onboarding.role_adapters import generate_adapters

    project_root = project or Path.cwd()
    stack_tuple = (
        tuple(s.strip() for s in stack.split(",") if s.strip()) if stack is not None else ()
    )
    try:
        config = resolve_flow_config(
            project_root,
            tools=tools,
            architecture=architecture,
            stack=stack_tuple,
        )
    except FlowConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"Composing roles: architecture={config.architecture}, "
        f"stack={','.join(config.stack)}, tools={','.join(config.tools)}"
    )
    adapters = generate_adapters(config, project_root)
    for tool, files in adapters.agents.items():
        for rel in files:
            click.echo(f"Wrote {rel} ({tool})")
    for rel in adapters.extra:
        click.echo(f"Wrote {rel}")

    result = scaffold(
        project_root, force=force, include_agents=False, config=config
    )

    if result.flow_config_written is not None:
        click.echo(
            f"Wrote {result.flow_config_written.relative_to(project_root)} "
            "(the selection above, recorded; yours to edit, never rewritten)"
        )
    for name in result.commands_written:
        click.echo(f"Wrote .claude/commands/{name}.md")
    for name in result.commands_skipped:
        click.echo(f"Skipped .claude/commands/{name}.md (hand-edited)")
    if result.claude_md is not None:
        click.echo(f"Wrote {result.claude_md.relative_to(project_root)}")
    _echo_scaffold_findings(result)

    # The guard hook adapter: the harness binding for the tool-agnostic
    # `beadloom guard` primitive. The names come from the registry, so a guard
    # shipped by a later release is wired by re-running this command.
    # Same whole-working-set call `init` makes, repeated here for a project that was
    # initialised by a Beadloom older than the block: the guards' firing record is one
    # entry in that set, not a special case owned by the guard scaffolder.
    ignore = ensure_ignore_block(project_root)
    if ignore.added:
        click.echo(
            f"Wrote .gitignore ({len(ignore.added)} generated path(s); "
            "yours to edit, never rewritten)"
        )

    hooks = scaffold_guard_hooks(project_root, guard_names=GUARD_NAMES)
    if hooks.script is not None:
        click.echo(f"Wrote {hooks.script.relative_to(project_root)} (guard hook adapter)")
    for name in hooks.guards_registered:
        click.echo(f"Registered guard hook: {name}")
    if hooks.settings_skipped_reason:
        click.echo(f"Skipped guard-hook registration: {hooks.settings_skipped_reason}")

    click.echo(
        "\nHonest boundary: the coordinator + Agent-spawn are Claude-Code-native "
        "(orchestration stays in the harness). The Beadloom MCP process-tools are "
        "the deterministic, tool-agnostic substrate the flow calls — MCP serves "
        "tools, not orchestration. The single source of TRUE enforcement remains "
        "`beadloom ci` in CI (lint/sync-check/config-check/doctor); the in-flow "
        "gates are advisory-strong, not a substitute for CI."
    )
    click.echo(
        "Next: 1) `beadloom config-check` keeps the scaffolded flow + CLAUDE.md "
        "auto-regions honest, 2) `beadloom setup-mcp` wires the process-tools for "
        "your IDE, 3) start work with `/task-init` then `/coordinator`."
    )


# beadloom:domain=onboarding
@main.command("setup-branch-protection")
@click.option(
    "--repo",
    "repo_slug",
    required=True,
    metavar="OWNER/NAME",
    help="GitHub repository as owner/name (e.g. acme/widget).",
)
@click.option(
    "--branch",
    default="main",
    show_default=True,
    help="Branch to protect (the trunk).",
)
@click.option(
    "--check",
    "contexts",
    multiple=True,
    metavar="CONTEXT",
    help=(
        "Required status-check context name (repeatable; replaces the default "
        "entirely). Default: the consolidated ci.yml job check-runs — 'gate', "
        "'tests (3.10)', 'tests (3.11)', 'tests (3.12)', 'tests (3.13)', "
        "'tests-locale (C)', 'tests-locale (en_US.ISO-8859-1)', "
        "'site-build', 'ai-techwriter' (these are ci.yml's "
        "job names + matrix legs). A "
        "context MUST match a real GitHub check-run name EXACTLY and "
        "must NOT be a path-filtered workflow's check (it would not run on every "
        "PR, which stalls PRs under strict checks)."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the exact `gh api` call + payload without invoking GitHub.",
)
def setup_branch_protection(
    *,
    repo_slug: str,
    branch: str,
    contexts: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Configure trunk-based branch protection on ``main`` via ``gh api`` (BDL-049).

    Idempotently sets `main` (or ``--branch``) protection so the trunk-based flow
    is enforced: a PR is required (no direct push), the consolidated ``ci.yml``
    checks (``gate`` / ``tests (3.10..3.13)`` / ``tests-locale (C)`` /
    ``tests-locale (en_US.ISO-8859-1)`` / ``site-build`` / ``ai-techwriter`` —
    ci.yml's job names + matrix legs) are REQUIRED status
    checks, ``enforce_admins: true`` + 0 required reviews so the owner is never
    locked out (can self-merge). Safe to re-run (a declarative PUT).
    ``--dry-run`` documents the exact call without touching GitHub.

    Required check contexts must match real GitHub check-run names EXACTLY and
    must NOT be path-filtered workflow checks (they would not run on every PR, so
    under ``strict`` the PR/``main`` would never become mergeable). Override the
    default with repeatable ``--check``.
    """
    from beadloom.onboarding.branch_protection import (
        DEFAULT_STATUS_CHECK_CONTEXTS,
        BranchProtectionRequest,
        apply_branch_protection,
    )

    if "/" not in repo_slug or repo_slug.count("/") != 1 or repo_slug.startswith("/"):
        raise click.BadParameter("--repo must be OWNER/NAME (e.g. acme/widget).")
    owner, repo = repo_slug.split("/", 1)
    if not owner or not repo:
        raise click.BadParameter("--repo must be OWNER/NAME (e.g. acme/widget).")
    check_contexts = contexts or DEFAULT_STATUS_CHECK_CONTEXTS

    if dry_run:
        request = BranchProtectionRequest(
            owner=owner,
            repo=repo,
            branch=branch,
            status_check_contexts=tuple(check_contexts),
        )
        click.echo("gh " + " ".join(request.gh_args()))
        click.echo("--- payload (stdin) ---")
        click.echo(request.payload_json())
        return

    apply_branch_protection(
        owner,
        repo,
        branch=branch,
        status_check_contexts=tuple(check_contexts),
    )
    click.echo(
        f"Protected {owner}/{repo}@{branch}: PR required, "
        f"{', '.join(check_contexts)} a required check, owner still mergeable."
    )


# beadloom:domain=onboarding
@main.command("config-check")
@click.option(
    "--fix",
    is_flag=True,
    default=False,
    help="Regenerate drifted agent-config artifacts, then re-check.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def config_check(*, fix: bool, project: Path | None) -> None:
    """Check that generated agent-config is in sync with the graph.

    Regenerates AGENTS.md + the auto-managed sections of CLAUDE.md + IDE
    adapters in memory and diffs them against disk.  Exits 1 on drift,
    0 when clean.  With --fix, regenerates what Beadloom itself wrote, names
    every file it changed, declines to overwrite any body it cannot prove is
    its own, and re-checks.
    """
    from beadloom.application.mutation_scope import check_mutation_scope
    from beadloom.infrastructure.db import connection
    from beadloom.onboarding import check_config_drift
    from beadloom.onboarding.config_sync import FixReport, apply_config_fixes

    project_root = project or Path.cwd()

    report = FixReport()
    if fix:
        report = apply_config_fixes(project_root)
        _echo_fix_report(report)

    db_path = project_root / ".beadloom" / "beadloom.db"
    with connection(db_path) as conn:
        drifts = check_config_drift(project_root, conn)

    blocking = [d for d in drifts if d.severity == "error"]
    warnings = [d for d in drifts if d.severity != "error"]

    for drift in warnings:
        click.echo(f"  ! {drift.file}: {drift.reason}", err=True)
        if drift.remediation:
            click.echo(f"    -> {drift.remediation}", err=True)

    # The declared mutation scope, checked against the project it describes.
    # Warn-only and printed here rather than in a step of its own: Beadloom owns
    # no mutation runner to hang one on (CONTEXT Q5).
    for scope in check_mutation_scope(project_root):
        click.echo(f"  ! {scope.target}: {scope.why}", err=True)
        click.echo(f"    -> {scope.remediation}", err=True)

    if not blocking:
        # A warning is a real finding and is printed above; it does not block,
        # because a green project going red on upgrade is how a check gets
        # switched off wholesale.
        notes = []
        if report.changed:
            notes.append(f"{len(report.changed)} file(s) changed, named above")
        if warnings:
            notes.append(f"{len(warnings)} warning(s) — see above")
        suffix = f" ({'; '.join(notes)})" if notes else ""
        click.echo(f"Agent-config in sync — no blocking drift{suffix}.")
        _echo_weakened_verdicts(warnings)
        return

    click.echo(f"Agent-config drift detected ({len(blocking)}):", err=True)
    for drift in blocking:
        click.echo(f"  - {drift.file}: {drift.reason}", err=True)
        if drift.remediation:
            click.echo(f"    -> {drift.remediation}", err=True)
    _echo_closing_advice(blocking)
    _echo_weakened_verdicts(warnings)
    raise SystemExit(1)


def _echo_scaffold_findings(result: ScaffoldResult) -> None:
    """Print what the scaffold FOUND, not just what it wrote (BDL-UX #188).

    ``orphaned_flow_files()`` and ``ScaffoldResult.migration_notes`` were
    computed on every run and read by nothing outside the library: BDL-UX #137
    is recorded as closed by the orphan report and S3's criterion "a hand-edited
    vendored file is reported with migration guidance" as met, and both claims
    were true of ``scaffold()`` and false of the command anybody runs. What the
    user actually saw was ``(hand-edited; use --force)`` — advice to run the
    destructive flag, never naming the project layer where the edit could safely
    go. NO CALLER, NO CAPABILITY: this is the caller.
    """
    if result.migration_notes:
        click.echo(
            f"\nLeft alone ({len(result.migration_notes)}) — your edits are the "
            "only copy of an intent, so Beadloom did not recompose over them:",
            err=True,
        )
        for note in result.migration_notes:
            click.echo(f"  = {note}", err=True)
    if result.orphans:
        click.echo(
            f"\nLeft by an older flow layout ({len(result.orphans)}) — reported, "
            "never deleted:",
            err=True,
        )
        for orphan in result.orphans:
            click.echo(f"  ? {orphan}", err=True)


def _echo_weakened_verdicts(warnings: list[ConfigDrift]) -> None:
    """Say when this pass is WEAKER than it would be, and why.

    CONTEXT's constraint is one-directional: no adopter's green project turns
    red on upgrade. Review `.11` measured the other direction — a repo that used
    to block starts passing, because a release that added provenance cannot
    account for files written before it. That is the worse of the two: a red is
    loud, a downgrade is silent, and the evidence the project ever failed is
    gone. The exit code deliberately does not change (a warn must not block);
    what changes is that the reduction is stated, counted, and given the command
    that restores the blocking verdict.
    """
    weakened = [d for d in warnings if d.weakened_from == "error"]
    if not weakened:
        return
    click.echo(
        f"  This pass is WEAKER than it would be: {len(weakened)} finding(s) "
        "are `warn` only because Beadloom cannot prove what it wrote — each "
        "would be an `error` with the evidence. A verdict that got quieter "
        "across an upgrade is a finding, not a pass.",
        err=True,
    )
    click.echo(
        "    -> restore `.beadloom/flow-manifest.json` (re-run "
        "`beadloom setup-agentic-flow`) to get the blocking verdict back.",
        err=True,
    )


def _echo_fix_report(report: FixReport) -> None:
    """Name every file the ``--fix`` pass changed, and every one it declined.

    BDL-UX #186: ``--fix`` restored a hand-edited role adapter byte-for-byte and
    closed with "Agent-config in sync — no blocking drift" at exit 0, mentioning
    nothing. A destructive act that reports success is the same class as a check
    that reports clean without checking, and worse — so the run now says what it
    did, in the output rather than in a document.
    """
    if report.created:
        click.echo(f"Created {len(report.created)} agent-config file(s):")
        for path in report.created:
            click.echo(f"  + {path}")
    if report.rewritten:
        click.echo(
            f"Rewrote {len(report.rewritten)} agent-config file(s) — each body was "
            "Beadloom's own output and is recomposed from CORE + the flow.yml "
            "overlays + the project layer, so nothing hand-written was in them:"
        )
        for path in report.rewritten:
            click.echo(f"  ~ {path}")
    if report.declined:
        click.echo(
            f"Declined to rewrite {len(report.declined)} file(s) — Beadloom did "
            "not write the body that is there, so rewriting it would delete it:",
            err=True,
        )
        for declined in report.declined:
            click.echo(f"  = {declined.file}", err=True)


def _echo_closing_advice(blocking: list[ConfigDrift]) -> None:
    """Offer ``--fix`` only for the findings it will actually repair.

    The command used to print "It will NOT be rewritten" about a hand edit and
    then close by recommending ``config-check --fix``; doing what the last line
    said undid what the line above promised (BDL-UX #186). ``--fix`` now honours
    the sentence, so the advice must stop naming it for the findings it declines.
    """
    declines = [d for d in blocking if not d.fixable]
    if declines:
        click.echo(
            f"  {len(declines)} of these will NOT be rewritten: the body on disk "
            "is not Beadloom's output, so repairing it would mean deleting it. "
            "Follow the `->` line under each.",
            err=True,
        )
    if len(declines) == len(blocking):
        return
    rest = " for the rest" if declines else " to fix"
    click.echo(
        f"  Run `beadloom setup-rules --refresh` (or `config-check --fix`){rest}.",
        err=True,
    )


# beadloom:service=mcp-server
@main.command("mcp-serve")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def mcp_serve(*, project: Path | None) -> None:
    """Run the beadloom MCP server (stdio transport)."""
    import anyio

    from beadloom.services.mcp_server import create_server

    project_root = project or Path.cwd()
    db_path = project_root / ".beadloom" / "beadloom.db"

    if not db_path.exists():
        click.echo("Error: database not found. Run `beadloom reindex` first.", err=True)
        sys.exit(1)

    server = create_server(project_root)

    async def _run() -> None:
        from mcp import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    anyio.run(_run)


#: The line `init` prints before its failure report, withdrawing the success it
#: has already claimed. EVERY branch has claimed something by the time the
#: verdict runs: the wizard prints `Initialization complete!`, `--bootstrap`
#: prints four check marks, `--yes` prints `Initialized beadloom (mode: ...)` and
#: its summary, and `--import` prints `Classified N documents`. So the withdrawal
#: is printed by `_verdict_on_the_generated_graph` itself rather than passed in
#: by a caller that remembers to.
#:
#: Until BDL-067 `.17` it was a `claim_to_withdraw` argument, and one of the four
#: call sites passed it. The docstring here justified the other three by asserting
#: that `--bootstrap` "takes its verdict first and never makes the claim" — it
#: makes it, four check marks before the error, measured by the review of `.16`
#: (major 3), and `--yes` makes it too. An instrument that answers a question
#: about one call site is how the omission looked deliberate for two waves; this
#: one ranges over every caller because no caller can decline it.
#:
#: One string precedes BOTH report shapes, so it may say only what is true of
#: both. It is silent about who wrote the rules, because
#: `_report_rules_the_graph_fails` is where that distinction is made; and silent
#: about whether any rule was evaluated, because over a `rules.yml` that will not
#: load none was. Until BDL-067 `.12` it read "it does not pass the rules it is
#: checked against:" and opened the unloadable-rules report, whose next two lines
#: say the graph was not checked and that nothing was evaluated — the review of
#: `.11`, major 1, measured on two different unloadable files. The colon went with
#: it: it promised the list of failing rules that `_report_rules_the_graph_fails`
#: prints, and what follows on the other branch is a parse error. What is true of
#: both shapes is that the check did not pass, which is also the fact the rc
#: reports.
WITHDRAWN_COMPLETION_CLAIM = (
    "The scaffold above was written, but the check that follows it did not pass."
)


def _graph_files_now(project_root: Path) -> dict[str, str]:
    """Digest every file under `.beadloom/_graph/`, keyed by file name.

    Sampled once before `init` writes anything and once when it takes its
    verdict; the difference is the set of graph files THIS RUN wrote. Read off
    the directory rather than off any writer's return value, for the reason
    `_graph_file_of_each_node` gives: the point is to cover writers this module
    does not know about, and `init` gained a second one (`import_docs`) four
    waves into BDL-067 without this side of the question noticing.

    Nothing here parses YAML: the question is whether the bytes changed, so the
    digest is taken over the bytes.

    Two limitations, stated because both are real. A file this run rewrote
    byte-for-byte with what was already there reads as one it did not write —
    in that case the file this run would have written and the file on disk hold
    the same content, so the two answers name the same rules and the same nodes.
    And a file that cannot be read is left OUT of the mapping rather than
    digested, so a file unreadable before the run and readable after it reads as
    one this run wrote. A missing directory is an empty mapping, which is the
    virgin case and the common one.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    digests: dict[str, str] = {}
    if not graph_dir.is_dir():
        return digests
    for yml in sorted(graph_dir.glob("*.yml")):
        try:
            digests[yml.name] = hashlib.sha256(yml.read_bytes()).hexdigest()
        except OSError:
            continue
    return digests


def _graph_nodes_now(project_root: Path) -> dict[str, str]:
    """Digest every node under `.beadloom/_graph/`, keyed by ref_id.

    The finer of the report's two grains, and the one the graph half of
    `_ATTRIBUTION` is keyed on. Sampled beside `_graph_files_now` and compared
    the same way: a ref_id absent before, or a node whose content differs, is a
    node THIS RUN wrote.

    The file grain could not answer this question, and the review of BDL-067
    `.23` decided it at this one. `generate_skeletons` writes a README for every
    node in the tree that has none and patches `docs:` back into the file that
    node sits in, so a run that only ANNOTATED an inherited file changed its
    bytes — and every node in it, including ones no writer in this run produced,
    read as this run's. That is the corner that asks the adopter for a bug
    report, on the common path, which is the defect BDL-067 `.9` was created to
    remove one level up.

    CREATED-OR-CHANGED rather than CREATED. Created alone fixes the same corner
    and mis-attributes in the opposite direction: a node this run rewrote into
    failing — a `kind` or `source` change on a ref_id that was already there —
    would read as the adopter's, so the instrument's error direction would become
    "hide our own defect", which is what this epic exists because of.

    The node is digested over a canonical JSON rendering rather than compared as
    a mapping, so that key order in the file is not a change and the sample stays
    small. `default=str` covers the scalars YAML produces that JSON does not
    carry — a date, most often — because the question is whether the value
    moved, not what type it loaded as.

    The limitation `_graph_files_now` states carries over at this grain and is
    re-stated because it is now about a node: a file that will not parse is in
    neither sample, so a node in a file unreadable before the run and readable
    after it reads as one this run wrote, and a node whose entry is rewritten to
    the same content reads as one it did not.
    """
    from beadloom.onboarding.graph_files import each_graph_file

    graph_dir = project_root / ".beadloom" / "_graph"
    digests: dict[str, str] = {}
    for _yml, data in each_graph_file(graph_dir):
        for node in data.get("nodes") or []:
            ref_id = node.get("ref_id")
            if ref_id is None:
                continue
            rendered = json.dumps(node, sort_keys=True, default=str)
            digests[str(ref_id)] = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    return digests


@dataclass(frozen=True)
class GraphSample:
    """`.beadloom/_graph/` at one moment, at both grains the report needs.

    Two instruments, sampled together so that no branch can take one and forget
    the other, and so that "before" means the same instant for both. They answer
    different questions and neither can answer the other's: the FILE grain
    answers whether this run changed the adopter's tree at all (the verdict's
    precondition) and whether it wrote `rules.yml` (which holds no nodes, so the
    file is its grain); the NODE grain answers whether this run produced the node
    that fails.
    """

    files: Mapping[str, str]
    nodes: Mapping[str, str]


def _graph_sample(project_root: Path) -> GraphSample:
    """Both grains of `.beadloom/_graph/`, taken at one moment."""
    return GraphSample(
        files=_graph_files_now(project_root), nodes=_graph_nodes_now(project_root)
    )


def _graph_files_this_run_wrote(
    before: Mapping[str, str], after: Mapping[str, str]
) -> frozenset[str]:
    """The `_graph/*.yml` names whose bytes this run created or changed."""
    return frozenset(name for name, digest in after.items() if before.get(name) != digest)


def _nodes_this_run_wrote(
    before: Mapping[str, str], after: Mapping[str, str]
) -> frozenset[str]:
    """The ref_ids this run created or changed. Same comparison, finer grain."""
    return frozenset(ref for ref, digest in after.items() if before.get(ref) != digest)


def _this_run_wrote_a_graph_file(project_root: Path, graph_before: GraphSample) -> bool:
    """Whether anything under `.beadloom/_graph/` changed since the run started.

    The precondition of the verdict, asked of the TREE rather than of the branch
    that is about to take it. `init` used to answer it by position — a branch
    that wrote called the verdict, a branch that did not returned above it — and
    that is how the wizard's `cancel` answer came to write `services.yml` and
    `rules.yml`, exit 0 and report nothing (BDL-UX #192's sixth instance, the
    review of BDL-067 `.20`, major 2). It is also why `interactive_init`'s OTHER
    cancelled answer must not be judged: the re-init prompt is put before any
    writer runs, so answering it leaves the adopter's tree exactly as it was, and
    a report there would name an existing tree's failures under a withdrawal line
    that says a scaffold was written.

    One fact, read in one place, so a branch cannot get it wrong by forgetting to
    return.
    """
    return bool(
        _graph_files_this_run_wrote(graph_before.files, _graph_files_now(project_root))
    )


#: The headline's two halves, each chosen by one fact about the tree rather than
#: by the branch that is reporting. Keyed by "this run wrote it": the graph file
#: the failing node came from, and `rules.yml`. Written as a mapping over the
#: full product so that a case cannot be left out — the report used to carry two
#: sentences chosen by one boolean, which said "the graph this command just
#: wrote" about nodes from a file written by an earlier run (the review of
#: BDL-067 `.16`, major 2, measured over `init --yes --mode import` followed by
#: the wizard).
_GRAPH_HALF = {
    True: "the graph this command just wrote",
    False: "the graph already in .beadloom/_graph/",
}
_RULES_HALF = {
    True: "the rules this command wrote alongside it",
    False: "the rules already in .beadloom/_graph/rules.yml",
}

#: What follows the rule lines, keyed by `(this run wrote the graph file the
#: failing node came from, this run wrote rules.yml)`. Only the corner where both
#: are this run's is a contradiction Beadloom produced, and only that corner asks
#: for a bug report: an adopter sent to file one about a writer that did not run
#: pays for our attribution error.
_ATTRIBUTION = {
    (True, True): (
        "This is a defect in Beadloom's bootstrap rather than in your project "
        "\u2014 please report it with the rule name(s) above."
    ),
    (True, False): (
        "This command did not write .beadloom/_graph/rules.yml \u2014 the file was "
        "already there \u2014 so the rule(s) above are your project's."
    ),
    (False, True): (
        "This command did not write the graph file(s) named beside the node(s) "
        "above \u2014 they were already on disk \u2014 so the rule(s) this command "
        "wrote are meeting a graph that predates them."
    ),
    (False, False): (
        "This command wrote neither the rule(s) above nor the graph file(s) they "
        "name \u2014 both were already on disk \u2014 so nothing this run produced "
        "is what fails."
    ),
}

#: Where to go next, true of every corner of the table above.
_REPAIR_ADVICE = (
    "The scaffold is on disk and can be edited by hand \u2014 the graph file named "
    "beside each node above, or .beadloom/_graph/rules.yml."
)


def _verdict_on_the_generated_graph(
    project_root: Path,
    *,
    graph_before: GraphSample,
) -> None:
    """Exit non-zero when the graph `init` just wrote fails the rules on disk.

    `init` writes the graph and then writes `rules.yml` from it, and until
    BDL-067 it never checked that the second agrees with the first: a virgin
    `init --yes --mode bootstrap` printed `Graph: 2 nodes, 0 edges`, returned 0,
    and the adopter's next command — `beadloom ci` — was red on
    `domain-needs-parent`, a rule that same command had written one step earlier
    (BDL-UX #192). `.1` closed that instance in the bootstrap; this closes the
    class, so the next divergence between what `init` writes and what `init`
    requires is visible here rather than at the adopter's first Gate run.

    The verdict is the Gate's own lint step, not a second implementation of it,
    so the two cannot drift. The rc is non-zero rather than a loud zero because a
    zero would let a scripted `init && ci` run on to the point where the cause is
    no longer in view. The scaffold is left on disk either way — the rc reports
    the state, it does not withdraw the graph.

    *graph_before* is `.beadloom/_graph/` sampled before this run wrote anything,
    and it answers WHOSE the failure is — for `rules.yml` at the file grain and
    for each failing node at the node grain. It is one sample taken in one place,
    so no branch can ask the question at one grain and forget the other.
    Until BDL-067 `.17` the caller passed a single boolean about `rules.yml`,
    read off `bootstrap_project`'s return value, and there was no counterpart for
    the node: an `init` that bootstrapped over an `imported.yml` a previous run
    had left behind announced "the graph this command just wrote" about nodes it
    had not written and asked the adopter to report a bootstrap defect for a
    writer that had not run (the review of `.16`, major 2). Sampling the
    directory covers writers this module does not know about, which is the same
    reason `_graph_file_of_each_node` reads the files rather than a return value.

    Two shapes of red reach this point and they are not the same news, so they
    are reported separately: rules that were evaluated and failed name their
    rules, and a `rules.yml` that would not load names the loader's complaint
    instead (`_report_rules_that_would_not_load`).

    The completion claim is withdrawn here rather than by the caller. Every
    branch that reaches this point has already announced a scaffold above it, so
    there is no branch for which the withdrawal would be false, and no branch
    that can forget to ask for it.

    Called from every branch of `init` that writes a scaffold — `--yes`,
    `--bootstrap`, `--import`, and the default interactive wizard. The
    enumeration is over branches that WRITE, not over branches that bootstrap:
    `--mode import` writes `imported.yml` into a tree whose `rules.yml` may
    already be there, and the run that created an unparented node is the run that
    should report it.
    """
    from beadloom.application.gate import RULES_CONFIG_ERROR, lint_step

    after = _graph_sample(project_root)
    written = _graph_files_this_run_wrote(graph_before.files, after.files)
    if not written:
        return

    step = lint_step(project_root)
    if step.passed:
        return

    click.echo("", err=True)
    click.echo(WITHDRAWN_COMPLETION_CLAIM, err=True)
    if step.summary == RULES_CONFIG_ERROR:
        _report_rules_that_would_not_load(step)
    else:
        _report_rules_the_graph_fails(
            step,
            project_root=project_root,
            files_this_run_wrote=written,
            nodes_this_run_wrote=_nodes_this_run_wrote(graph_before.nodes, after.nodes),
        )
    # The fact, not one renderer's spelling of it. `ci` picks `rich` on a TTY and
    # `github` otherwise, and the github renderer builds its own step line, so the
    # quoted `[FAIL] lint: ...` was wrong in exactly the scripted context `--yes`
    # serves: the same tree printed `::notice::lint FAIL: ...` (the review of
    # BDL-067 `.16`, the minor). The step's name and summary are what every
    # renderer reads, so a sentence built from those two survives all of them and
    # any renderer added later.
    click.echo(
        f"`beadloom ci` will fail its {step.name} step: {step.summary}",
        err=True,
    )
    sys.exit(1)


def _graph_file_of_each_node(project_root: Path) -> dict[str, str]:
    """Map every node in `.beadloom/_graph/` to the file that holds it.

    Read off the files rather than off any writer's return value, because the
    point is to cover writers this function does not know about. A file that is
    not readable YAML is skipped: the adopter is being handed a failure report,
    and a traceback from the reporter is a worse answer than one unattributed
    node. That skip is `each_graph_file`'s since BDL-067 `.24`, which is also
    where the other three readers of this directory now take it from.
    """
    from beadloom.onboarding.graph_files import each_graph_file

    graph_dir = project_root / ".beadloom" / "_graph"
    source_of: dict[str, str] = {}
    for yml, data in each_graph_file(graph_dir):
        for node in data.get("nodes") or []:
            ref_id = node.get("ref_id")
            if ref_id and ref_id not in source_of:
                source_of[str(ref_id)] = f".beadloom/_graph/{yml.name}"
    return source_of


def _failing_rule_lines(step: GateStep, source_of: dict[str, str]) -> list[str]:
    """One line per error-severity finding: the rule, the node, and its file.

    A finding that is about no single node keeps the bare rule name, and a node
    no graph file claims keeps the rule and the node: an unattributed line is
    still true, and a guessed file is not.
    """
    lines: set[str] = set()
    for finding in step.findings:
        if finding.get("severity") != "error":
            continue
        rule = str(finding["rule"])
        node = finding.get("node")
        if not node:
            lines.add(rule)
            continue
        where = source_of.get(str(node))
        lines.add(f"{rule}: {node} ({where})" if where else f"{rule}: {node}")
    return sorted(lines)


def _this_run_wrote_the_node_that_fails(
    step: GateStep,
    source_of: Mapping[str, str],
    nodes_this_run_wrote: frozenset[str],
    files_this_run_wrote: frozenset[str],
) -> bool:
    """Whether a failing node is one this run created or changed.

    The finest attribution the report has is per node, and until BDL-067 `.24`
    it was not asked per node: the question was whether this run wrote the FILE
    the failing node came from. `generate_skeletons` annotates inherited files by
    default, so any node sharing a file with a node that gained a `docs:` field
    read as this run's — including the one corner that asks the adopter to file a
    bug report (the review of `.23`, major 4, which decided this grain).

    When no error-severity finding names a node any graph file claims — a
    rule-level finding, or a node no file holds — there is nothing to attribute
    at that grain, and the question falls back to the coarsest fact available:
    did this run write any graph file at all. On a virgin bootstrap it did, which
    is the answer a rule-level finding needs. That fallback is why the file grain
    is still a parameter here.

    *source_of* decides which findings are attributable and
    *nodes_this_run_wrote* decides the answer. The two agree on their population
    by construction: both are read off `.beadloom/_graph/` through
    `each_graph_file`, so a node one of them can see is a node the other can.
    """
    attributable = [
        str(finding["node"])
        for finding in step.findings
        if finding.get("severity") == "error"
        and finding.get("node")
        and str(finding["node"]) in source_of
    ]
    if not attributable:
        return bool(files_this_run_wrote)
    return any(ref_id in nodes_this_run_wrote for ref_id in attributable)


def _report_rules_the_graph_fails(
    step: GateStep,
    *,
    project_root: Path,
    files_this_run_wrote: frozenset[str],
    nodes_this_run_wrote: frozenset[str],
) -> None:
    """Name each error-severity rule the graph violates, and say whose it is.

    The rule names are the same whoever wrote them; the sentence around them is
    not. Telling an adopter that their own hand-written rule is "a defect in
    Beadloom's bootstrap" costs them a bug report against a project that did not
    write it, and telling them "the graph this command just wrote" about a node
    an earlier run left in `imported.yml` costs them the same twice over.

    Both halves of the headline and the sentence under it are chosen from the
    same pair of facts — did this run write `rules.yml`, and did it write the
    failing node — through `_GRAPH_HALF`, `_RULES_HALF` and `_ATTRIBUTION`. The
    two facts are read at two different grains on purpose: `rules.yml` holds no
    nodes, so the file is its grain, and the node is the grain of the other half
    since BDL-067 `.24`. A table over the product cannot leave a corner unwritten,
    which the previous shape did: one boolean about `rules.yml` chose both
    sentences, so the corner where the rule is ours and the node is not printed
    the corner where both are (the review of BDL-067 `.16`, major 2, measured by
    running `init --yes --mode import` and then the wizard over one tree).

    Each line also names the graph file its node came from, and the advice sends
    the adopter to those files rather than to `services.yml` by habit. The review
    of BDL-067 `.13` measured the habit: the failing node was `payments`, written
    into `imported.yml` by the import step, and the report pointed at
    `services.yml` and `rules.yml`, neither of which contains it.
    """
    source_of = _graph_file_of_each_node(project_root)
    rules = _failing_rule_lines(step, source_of)
    graph_is_this_run_s = _this_run_wrote_the_node_that_fails(
        step, source_of, nodes_this_run_wrote, files_this_run_wrote
    )
    rules_are_this_run_s = "rules.yml" in files_this_run_wrote

    click.echo(
        f"Error: {_GRAPH_HALF[graph_is_this_run_s]} does not pass "
        f"{_RULES_HALF[rules_are_this_run_s]}.",
        err=True,
    )
    for rule in rules:
        click.echo(f"  {rule}", err=True)
    click.echo(_ATTRIBUTION[graph_is_this_run_s, rules_are_this_run_s], err=True)
    click.echo(_REPAIR_ADVICE, err=True)


def _report_rules_that_would_not_load(step: GateStep) -> None:
    """Say what is wrong with `rules.yml`, which is not the name of a rule.

    The Gate reports an unloadable rules file through its `LintError` branch, and
    that finding's `rule` is the literal `lint` — the step's own name — while the
    loader's complaint sits in `why`. Printing the name the way the rule branch
    does told an adopter whose hand-edited `rules.yml` will not parse that a rule
    called `lint` had failed, and never showed them the parse error (BDL-067 `.6`,
    the review's minor 4). `bootstrap_project` leaves an existing rules file
    alone, so the file that did not load is usually the adopter's own edit: this
    branch names neither a rule nor the bootstrap, because nothing was evaluated
    and nothing is known to be wrong with the graph.
    """
    click.echo(
        "Error: .beadloom/_graph/rules.yml could not be read, so the graph this "
        "command wrote was not checked against it.",
        err=True,
    )
    for finding in step.findings:
        click.echo(f"  {finding['why']}", err=True)
    click.echo(
        "No rule was evaluated, so the graph is unchecked rather than wrong. "
        "Repair .beadloom/_graph/rules.yml and run `beadloom lint --strict` again.",
        err=True,
    )


# beadloom:domain=onboarding
@main.command()
@click.option("--bootstrap", is_flag=True, help="Bootstrap: generate graph from code.")
@click.option(
    "--preset",
    type=click.Choice(["monolith", "microservices", "monorepo"]),
    default=None,
    help="Architecture preset (auto-detected if omitted).",
)
@click.option(
    "--import",
    "import_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Import: classify existing documentation from directory.",
)
@click.option(
    "--mode",
    "init_mode",
    type=click.Choice(["bootstrap", "import", "both"]),
    default=None,
    help="Init mode for non-interactive usage.",
)
@click.option(
    "--yes",
    "-y",
    "non_interactive",
    is_flag=True,
    help="Non-interactive mode: no prompts, use defaults.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing .beadloom/ directory.",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (default: current directory).",
)
def init(
    *,
    bootstrap: bool,
    preset: str | None,
    import_path: Path | None,
    init_mode: str | None,
    non_interactive: bool,
    force: bool,
    project: Path | None,
) -> None:
    """Initialize beadloom in a project."""
    from beadloom.onboarding import bootstrap_project, import_docs

    project_root = project or Path.cwd()
    # Sampled before any writer runs, in ONE place, so every branch below is
    # judged by the same instrument: the difference against the same directory
    # at verdict time is what this run wrote. Both grains at once — the files,
    # for the verdict's precondition and for `rules.yml`, and the nodes, for the
    # attribution of the failing node. See `GraphSample`.
    graph_before = _graph_sample(project_root)

    # Non-interactive mode: --yes / -y flag.
    if non_interactive:
        from beadloom.onboarding.scanner import non_interactive_init

        mode = init_mode or "bootstrap"
        result = non_interactive_init(project_root, mode=mode, force=force)

        if result["mode"] == "skipped":
            click.echo("Warning: .beadloom/ already exists. Use --force to overwrite.")
            return

        # Print summary for non-interactive mode.
        click.echo(f"Initialized beadloom (mode: {result['mode']})")
        if "bootstrap" in result:
            bs = result["bootstrap"]
            click.echo(
                f"  Graph: {bs['nodes_generated']} nodes, "
                f"{bs['edges_generated']} edges (preset: {bs['preset']})"
            )
        if result.get("reindex"):
            ri = result["reindex"]
            click.echo(f"  Index: {ri['symbols']} symbols, {ri['imports']} imports")
        if result.get("import"):
            click.echo(f"  Imported: {len(result['import'])} documents")
        # Every mode is judged, `import` included. The guard used to be
        # `if "bootstrap" in result`, which asked whether one writer had run
        # rather than whether this run had written anything: `--mode import`
        # leaves unparented nodes in `imported.yml`, the wizard's re-init does
        # not delete `.beadloom/`, and the NEXT run wrote the rule those nodes
        # fail — so #192's shape was deferred by one command instead of
        # prevented, and reported by a run that had not written the nodes (the
        # review of BDL-067 `.16`, major 2). `non_interactive_init` re-indexes
        # after every mode, so the verdict reads an index that holds what this
        # run wrote.
        _verdict_on_the_generated_graph(project_root, graph_before=graph_before)
        return

    if bootstrap:
        result = bootstrap_project(project_root, preset_name=preset)

        # Generate doc skeletons. From the tree, like every other caller: this
        # branch passed `result["nodes"], result["edges"]` until BDL-067 `.21`,
        # so on a project that already carried a graph file it rendered
        # `docs/architecture.md` from the bootstrap's nodes alone and wrote no
        # skeleton for anything an earlier run had left. One declared mode, two
        # entry points, two different trees (BDL-UX #216, the review of `.20`).
        from beadloom.onboarding.doc_generator import generate_skeletons

        docs_result = generate_skeletons(project_root)

        # Auto-reindex to populate import analysis and depends_on edges.
        from beadloom.application.reindex import reindex as do_reindex

        ri = do_reindex(project_root)

        # Count dependency edges from DB.
        dep_count = 0
        if ri.imports_indexed > 0:
            from beadloom.infrastructure.db import open_db

            db_path = project_root / ".beadloom" / "beadloom.db"
            conn = open_db(db_path)
            dep_count = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE kind = 'depends_on'"
            ).fetchone()[0]
            conn.close()

        # Print summary.
        click.echo("")
        click.echo(
            f"\u2713 Graph: {result['nodes_generated']} nodes, "
            f"{result['edges_generated']} edges (preset: {result['preset']})"
        )
        if result.get("rules_generated", 0) > 0:
            click.echo(
                f"\u2713 Rules: {result['rules_generated']} rules in .beadloom/_graph/rules.yml"
            )
        if docs_result["files_skipped"] > 0:
            click.echo(
                f"\u2713 Docs: {docs_result['files_created']} skeletons created, "
                f"{docs_result['files_skipped']} skipped (pre-existing)"
            )
        else:
            click.echo(f"\u2713 Docs: {docs_result['files_created']} skeletons created")
        if result.get("mcp_editor"):
            click.echo(
                f"\u2713 MCP: configured for {result['mcp_editor']} "
                f"({_mcp_path_for_editor(result['mcp_editor'], project_root)})"
            )
        if result.get("rules_files"):
            for rf in result["rules_files"]:
                click.echo(f"\u2713 IDE rules: {rf}")
        if result.get("ignore_added"):
            click.echo(
                f"\u2713 Ignored: {len(result['ignore_added'])} generated path(s) "
                "appended to .gitignore (yours to edit; never rewritten)"
            )
        click.echo(
            f"\u2713 Index: {ri.symbols_indexed} symbols, "
            f"{ri.imports_indexed} imports"
            + (f", {dep_count} dependency edges" if dep_count else "")
        )

        # Warn about missing language parsers when symbols == 0.
        if ri.symbols_indexed == 0:
            _warn_missing_parsers(project_root)

        _verdict_on_the_generated_graph(project_root, graph_before=graph_before)

        click.echo("")
        click.echo("Next steps:")
        click.echo("  1. Review docs/ and .beadloom/_graph/services.yml")
        click.echo("  2. Run 'beadloom lint' to validate architecture")
        click.echo("  3. Run 'beadloom docs polish' with your AI agent for richer docs")
        return

    if import_path:
        results = import_docs(project_root, import_path)
        click.echo(f"Classified {len(results)} documents:")
        for r in results:
            click.echo(f"  [{r['kind']}] {r['path']}")
        click.echo("")
        click.echo("Next: review .beadloom/_graph/imported.yml")
        # This branch writes a graph file, so it is judged like the other three.
        # It re-indexes first for the reason `.14` established: `lint_step` reads
        # the index without rebuilding it, and a verdict over an index that
        # predates the file this branch just wrote is the stale-index defect
        # again. Every other branch already re-indexed before returning; this was
        # the one that told the adopter to do it by hand instead.
        from beadloom.application.reindex import reindex as do_reindex

        do_reindex(project_root)
        _verdict_on_the_generated_graph(project_root, graph_before=graph_before)
        return

    # Default: interactive mode.
    from beadloom.onboarding import interactive_init

    result = interactive_init(project_root)
    # The branch a human adopter meets first. It was left out when the verdict
    # landed (BDL-067 `.2`) because the test that covered the other two was
    # parametrised over the two BINDINGS of `bootstrap_project` — and the wizard
    # shares the `--yes` binding, so two bindings read as two branches and this
    # one was never counted. The review of `.4` reproduced #192's exact shape
    # here: wizard rc 0, `lint --strict` rc 1, `ci` rc 1.
    #
    # The mode is no longer part of the guard. `import` writes `imported.yml` and
    # the wizard re-indexes after every mode, so an import-only wizard run is a
    # run that wrote a graph file and is judged like any other (the review of
    # `.16`, major 2). `review == "edit"` stays the one carve-out: the wizard has
    # just handed the graph to the user to edit by hand and told them to run
    # `beadloom reindex` afterwards, so the tree is unfinished by agreement and
    # nothing has re-indexed since. Judging it there would report a state the
    # user is in the middle of leaving.
    if result.get("review") != "edit":
        # The wizard can return above the reindex it ends with — `cancel` at the
        # graph review does — and `lint_step` reads the index read-only, so a
        # verdict there would judge an index that predates the graph already on
        # disk. That is `.14`'s stale-index defect from the other side. The
        # question is put to the wizard's own return value rather than to the
        # answer that caused it: `reindex` is recorded when the reindex ran, so
        # a fourth review answer that leaves early is covered by this same line.
        if "reindex" not in result and _this_run_wrote_a_graph_file(
            project_root, graph_before
        ):
            from beadloom.application.reindex import reindex as do_reindex

            do_reindex(project_root)
        _verdict_on_the_generated_graph(project_root, graph_before=graph_before)
