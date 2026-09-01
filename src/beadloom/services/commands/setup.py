"""Setup / onboarding / init commands.

Owns the ``setup-*`` family (``setup-mcp``, ``setup-rules``,
``setup-ai-techwriter``, ``setup-agentic-flow``, ``setup-branch-protection``),
plus ``config-check``, ``mcp-serve``, and ``init``.
"""
# beadloom:component=cli-commands

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from beadloom.services.commands._root import _warn_missing_parsers, main

if TYPE_CHECKING:
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


#: The line the wizard prints before its failure report, withdrawing the success
#: it has already claimed. `interactive_init` prints `Initialization complete!`,
#: `Generated:` and `Next steps:` before it returns, so by the time `init` takes
#: the verdict the claim has been made; the `--bootstrap` branch takes its
#: verdict first and never makes it, which is why only the wizard passes this.
#: One line is cheaper than moving the verdict inside `interactive_init`, which
#: would put a services-layer concern in the onboarding domain (the review of
#: BDL-067 `.8`, minor 2).
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


def _wrote_the_rules_file(bootstrap_summary: dict[str, Any]) -> bool:
    """Whether this run authored `rules.yml`, or merely found one on disk.

    `bootstrap_project` returns `rules_generated`, which is 0 exactly when the
    file was already there — the same condition, read off the result instead of
    re-tested against the filesystem. An `init` that ran in `import` mode has no
    bootstrap summary at all and wrote no rules, which the empty default covers.
    """
    return bool(bootstrap_summary.get("rules_generated", 0))


def _verdict_on_the_generated_graph(
    project_root: Path,
    *,
    bootstrap_wrote_the_rules: bool,
    claim_to_withdraw: str | None = None,
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

    WHOSE rules those are is a separate question, and `bootstrap_wrote_the_rules`
    is the answer to it. `bootstrap_project` writes `rules.yml` only when the file
    is not already there, so on a re-init, or over rules an earlier Beadloom or a
    hand edit left behind, the failing rule is the adopter's own and none of this
    command's business to be blamed for. `.6` established exactly that fact and
    applied it to the unloadable-rules branch alone, which is how the evaluated-
    rules branch went on telling adopters that their own hand-written
    `service-needs-parent` was "a defect in Beadloom's bootstrap" — measured by
    the review of `.8` on a scratch TypeScript project. Callers pass
    `rules_generated`, not a second look at the filesystem, because the file
    exists by the time the verdict runs either way.

    Two shapes of red reach this point and they are not the same news, so they
    are reported separately: rules that were evaluated and failed name their
    rules, and a `rules.yml` that would not load names the loader's complaint
    instead (`_report_rules_that_would_not_load`).

    `claim_to_withdraw`, when given, is printed before the report. Only the
    wizard branch passes it, because only the wizard has already claimed success
    by the time it gets here.

    Called from every branch of `init` that writes a bootstrap graph — `--yes`,
    `--bootstrap`, and the default interactive wizard — which is three branches
    reached through two bindings of `bootstrap_project`. The wizard shipped
    unguarded for exactly as long as those two numbers were confused for one
    another (BDL-067 `.6`).
    """
    from beadloom.application.gate import RULES_CONFIG_ERROR, lint_step

    step = lint_step(project_root)
    if step.passed:
        return

    click.echo("", err=True)
    if claim_to_withdraw:
        click.echo(claim_to_withdraw, err=True)
    if step.summary == RULES_CONFIG_ERROR:
        _report_rules_that_would_not_load(step)
    else:
        _report_rules_the_graph_fails(
            step, bootstrap_wrote_the_rules=bootstrap_wrote_the_rules
        )
    click.echo(f"`beadloom ci` will report this as: lint \u2014 {step.summary}.", err=True)
    sys.exit(1)


def _report_rules_the_graph_fails(
    step: GateStep, *, bootstrap_wrote_the_rules: bool
) -> None:
    """Name each error-severity rule the graph `init` just wrote violates.

    The rule names are the same either way; the sentence around them is not.
    Telling an adopter that their own hand-written rule is "a defect in
    Beadloom's bootstrap" costs them a bug report against a project that did not
    write it, so the blame — and the request to report — are printed only when
    this run authored `rules.yml`.
    """
    rules = sorted(
        {str(f["rule"]) for f in step.findings if f.get("severity") == "error"}
    )
    if bootstrap_wrote_the_rules:
        headline = (
            "Error: the graph this command just wrote does not pass the rules "
            "this command wrote alongside it."
        )
        advice = (
            "The scaffold is on disk and can be edited by hand "
            "(.beadloom/_graph/services.yml, .beadloom/_graph/rules.yml). This is a "
            "defect in Beadloom's bootstrap rather than in your project \u2014 please "
            "report it with the rule name(s) above."
        )
    else:
        headline = (
            "Error: the graph this command just wrote does not pass the rules "
            "already in .beadloom/_graph/rules.yml."
        )
        advice = (
            "This command did not write .beadloom/_graph/rules.yml \u2014 the file was "
            "already there \u2014 so the rule(s) above are your project's. The scaffold "
            "is on disk: edit .beadloom/_graph/services.yml to satisfy them, or the "
            "rules file to match your architecture."
        )
    click.echo(headline, err=True)
    for rule in rules:
        click.echo(f"  {rule}", err=True)
    click.echo(advice, err=True)


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
        _verdict_on_the_generated_graph(
            project_root,
            bootstrap_wrote_the_rules=_wrote_the_rules_file(result.get("bootstrap", {})),
        )
        return

    if bootstrap:
        result = bootstrap_project(project_root, preset_name=preset)

        # Generate doc skeletons.
        from beadloom.onboarding.doc_generator import generate_skeletons

        docs_result = generate_skeletons(project_root, result["nodes"], result["edges"])

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

        _verdict_on_the_generated_graph(
            project_root,
            bootstrap_wrote_the_rules=_wrote_the_rules_file(result),
        )

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
        click.echo("Next: review .beadloom/_graph/imported.yml, then run `beadloom reindex`")
        return

    # Default: interactive mode.
    from beadloom.onboarding import interactive_init

    result = interactive_init(project_root)
    if result["mode"] == "cancelled":
        sys.exit(0)
    # The third branch that writes a bootstrap graph, and the one a human adopter
    # meets first. It was left out when the verdict landed (BDL-067 `.2`) because
    # the test that covered the other two was parametrised over the two BINDINGS
    # of `bootstrap_project` — and the wizard shares the `--yes` binding, so two
    # bindings read as two branches and this one was never counted. The review of
    # `.4` reproduced #192's exact shape here: wizard rc 0, `lint --strict` rc 1,
    # `ci` rc 1.
    #
    # `review == "edit"` is the one bootstrap path that takes no verdict: the
    # wizard has just handed the graph to the user to edit by hand and told them
    # to run `beadloom reindex` afterwards, so the tree is unfinished by
    # agreement, and nothing has re-indexed since. Judging it there would report a
    # state the user is in the middle of leaving.
    if result["mode"] in ("bootstrap", "both") and result.get("review") != "edit":
        # `claim_to_withdraw` is passed here and nowhere else: `interactive_init`
        # prints `Initialization complete!` before it returns, so this branch —
        # and only this branch — reports a failure under a success it has already
        # announced (the review of `.8`, minor 2).
        _verdict_on_the_generated_graph(
            project_root,
            bootstrap_wrote_the_rules=_wrote_the_rules_file(result.get("bootstrap", {})),
            claim_to_withdraw=WITHDRAWN_COMPLETION_CLAIM,
        )
