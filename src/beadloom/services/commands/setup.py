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

import click

from beadloom.services.commands._root import _warn_missing_parsers, main

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
    from beadloom.onboarding.agentic_flow_setup import scaffold
    from beadloom.onboarding.flow_config import FlowConfigError, resolve_flow_config
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

    result = scaffold(project_root, force=force, include_agents=False)

    for name in result.commands_written:
        click.echo(f"Wrote .claude/commands/{name}.md")
    for name in result.commands_skipped:
        click.echo(f"Skipped .claude/commands/{name}.md (hand-edited; use --force)")
    if result.claude_md is not None:
        click.echo(f"Wrote {result.claude_md.relative_to(project_root)}")

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
        "'site-build', 'ai-techwriter' (these are ci.yml's job names + matrix "
        "legs). A context MUST match a real GitHub check-run name EXACTLY and "
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
    checks (``gate`` / ``tests (3.10..3.13)`` / ``site-build`` /
    ``ai-techwriter`` — ci.yml's job names + matrix legs) are REQUIRED status
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
    0 when clean.  With --fix, regenerates via ``setup-rules --refresh``
    and re-checks.
    """
    from beadloom.infrastructure.db import connection
    from beadloom.onboarding import check_config_drift
    from beadloom.onboarding.scanner import generate_agents_md, refresh_claude_md

    project_root = project or Path.cwd()

    if fix:
        # Regenerate via the same refresh path used by `setup-rules --refresh`.
        refresh_claude_md(project_root)
        generate_agents_md(project_root)
        from beadloom.onboarding.scanner import setup_rules_auto

        setup_rules_auto(project_root)

        # Re-drop drifted agentic-flow files (only if the flow is scaffolded —
        # never force the flow onto a repo that did not adopt it). Restores the
        # vendored agents/commands; CLAUDE.md regions are already refreshed
        # above, so user prose outside the auto-regions is preserved.
        from beadloom.onboarding.config_sync import (
            refresh_agentic_flow_files,
            refresh_composed_adapters,
        )

        refresh_agentic_flow_files(project_root)
        # Recompose the per-tool role adapters from .beadloom/flow.yml (no-op
        # when flow.yml is absent/invalid). The composer owns .claude/agents/*
        # + .cursor/agents/* once a flow.yml exists.
        refresh_composed_adapters(project_root)

    db_path = project_root / ".beadloom" / "beadloom.db"
    with connection(db_path) as conn:
        drifts = check_config_drift(project_root, conn)

    if not drifts:
        click.echo("Agent-config in sync — no drift.")
        return

    click.echo(f"Agent-config drift detected ({len(drifts)}):", err=True)
    for drift in drifts:
        click.echo(f"  - {drift.file}: {drift.reason}", err=True)
    click.echo(
        "  Run `beadloom setup-rules --refresh` (or `config-check --fix`) to fix.",
        err=True,
    )
    raise SystemExit(1)


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
        click.echo(
            f"\u2713 Index: {ri.symbols_indexed} symbols, "
            f"{ri.imports_indexed} imports"
            + (f", {dep_count} dependency edges" if dep_count else "")
        )

        # Warn about missing language parsers when symbols == 0.
        if ri.symbols_indexed == 0:
            _warn_missing_parsers(project_root)

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
