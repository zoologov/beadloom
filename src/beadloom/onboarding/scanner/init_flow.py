"""Init orchestration — interactive wizard + non-interactive bootstrap/import."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from beadloom.onboarding.scanner.agents_md import generate_agents_md
from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.onboarding.scanner.doc_classify import auto_link_docs, import_docs
from beadloom.onboarding.scanner.project_scan import scan_project

if TYPE_CHECKING:
    from pathlib import Path


def _format_review_table(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
) -> str:
    """Format nodes and edges as a plain-text review table."""
    lines: list[str] = []

    lines.append(f"  Nodes ({len(nodes)}):")
    for n in nodes:
        conf = n.get("confidence", "")
        conf_tag = f" [{conf}]" if conf else ""
        lines.append(f"    {n['ref_id']:30s} {n['kind']:10s} {n.get('source', '')}{conf_tag}")

    if edges:
        lines.append(f"\n  Edges ({len(edges)}):")
        for e in edges:
            lines.append(f"    {e['src']} --{e['kind']}--> {e['dst']}")

    return "\n".join(lines)


def non_interactive_init(
    project_root: Path,
    *,
    mode: str = "bootstrap",
    force: bool = False,
) -> dict[str, Any]:
    """Run non-interactive initialization (no prompts).

    Parameters
    ----------
    project_root:
        Root of the project.
    mode:
        Init mode — ``"bootstrap"`` (default), ``"import"``, or ``"both"``.
    force:
        When *True*, delete existing ``.beadloom/`` directory before init.

    Returns
    -------
    dict[str, Any]
        Summary of what was done, including ``mode``, ``bootstrap``, ``import`` keys.
    """
    import shutil

    beadloom_dir = project_root / ".beadloom"

    result: dict[str, Any] = {"mode": mode}

    # Handle existing .beadloom/ directory.
    if beadloom_dir.exists():
        if force:
            shutil.rmtree(beadloom_dir)
        else:
            result["mode"] = "skipped"
            result["reason"] = "exists"
            return result

    # Execute chosen mode.
    if mode in ("bootstrap", "both"):
        bs_result = bootstrap_project(project_root)
        result["bootstrap"] = bs_result

        nodes = bs_result.get("nodes", [])
        edges = bs_result.get("edges", [])

        # Auto-link existing docs to graph nodes before skeleton generation.
        linked = auto_link_docs(project_root, nodes)
        result["docs_linked"] = linked

        # Generate doc skeletons.
        from beadloom.onboarding.doc_generator import generate_skeletons

        docs_result = generate_skeletons(project_root, nodes, edges)
        result["docs_generated"] = docs_result

        # Auto-reindex to populate import analysis and depends_on edges.
        from beadloom.application.reindex import reindex as do_reindex

        ri = do_reindex(project_root)
        result["reindex"] = {
            "symbols": ri.symbols_indexed,
            "imports": ri.imports_indexed,
            "edges": ri.edges_loaded,
        }

    if mode in ("import", "both"):
        docs_dir = project_root / "docs"
        if docs_dir.is_dir():
            docs_imported = import_docs(project_root, docs_dir)
            result["import"] = docs_imported
        else:
            result["import"] = []

    # Generate AGENTS.md.
    generate_agents_md(project_root)
    result["agents_md_created"] = True

    return result


def interactive_init(project_root: Path) -> dict[str, Any]:
    """Run interactive initialization wizard.

    Shows a menu to choose init mode, handles re-init detection,
    and guides the user through the setup process.

    Returns dict with summary of what was done.
    """
    from rich.console import Console
    from rich.prompt import Prompt

    console = Console()
    beadloom_dir = project_root / ".beadloom"

    result: dict[str, Any] = {"mode": None, "reinit": False}

    # Re-init detection.
    if beadloom_dir.exists():
        console.print("\n[yellow]Warning: .beadloom/ already exists.[/yellow]\n")
        choice = Prompt.ask(
            "What would you like to do?",
            choices=["overwrite", "cancel"],
            default="cancel",
        )
        if choice == "cancel":
            console.print("Cancelled.")
            result["mode"] = "cancelled"
            return result
        result["reinit"] = True

    # Show project scan summary.
    scan = scan_project(project_root)
    console.print("\n[bold]Project scan:[/bold]")
    if scan["manifests"]:
        console.print(f"  Manifests: {', '.join(scan['manifests'])}")
    if scan["source_dirs"]:
        console.print(f"  Source dirs: {', '.join(scan['source_dirs'])}")
    console.print(f"  Code files: {scan['file_count']}")
    if scan["languages"]:
        console.print(f"  Languages: {', '.join(scan['languages'])}")

    # Check for existing docs.
    docs_dir = project_root / "docs"
    has_docs = docs_dir.is_dir() and any(docs_dir.rglob("*.md"))

    if not has_docs:
        console.print("\n[dim]No docs/ directory found — that's fine![/dim]")
        console.print(
            "[dim]Beadloom works great with code-only: graph, annotations, context oracle.[/dim]"
        )
        console.print("[dim]Add docs later when you need doc-sync tracking.[/dim]")

    console.print("")

    # Mode selection.
    if has_docs and scan["file_count"] > 0:
        mode = Prompt.ask(
            "Choose init mode",
            choices=["bootstrap", "import", "both"],
            default="both",
        )
    elif has_docs:
        mode = Prompt.ask(
            "Choose init mode",
            choices=["import", "bootstrap"],
            default="import",
        )
    elif scan["file_count"] > 0:
        mode = Prompt.ask(
            "Choose init mode",
            choices=["bootstrap"],
            default="bootstrap",
        )
    else:
        console.print("[yellow]No source files or docs found.[/yellow]")
        mode = Prompt.ask(
            "Choose init mode",
            choices=["bootstrap", "import"],
            default="bootstrap",
        )

    result["mode"] = mode

    # Execute chosen mode.
    if mode in ("bootstrap", "both"):
        console.print("\n[bold]Bootstrapping from code...[/bold]")
        bs_result = bootstrap_project(project_root)
        result["bootstrap"] = bs_result

        nodes = bs_result.get("nodes", [])
        edges = bs_result.get("edges", [])
        preset_name = bs_result.get("preset", "monolith")
        console.print(f"  Preset: {preset_name}")
        console.print(f"  Generated {len(nodes)} nodes, {len(edges)} edges")

        # Interactive review.
        if nodes:
            console.print(f"\n{_format_review_table(nodes, edges)}")
            console.print("")
            review = Prompt.ask(
                "Proceed with this graph?",
                choices=["yes", "edit", "cancel"],
                default="yes",
            )
            if review == "cancel":
                console.print("Cancelled.")
                result["mode"] = "cancelled"
                return result
            if review == "edit":
                graph_path = project_root / ".beadloom" / "_graph" / "services.yml"
                console.print(f"\n[bold]Edit:[/bold] {graph_path}")
                console.print("Edit the file, then run [bold]beadloom reindex[/bold].")
                result["review"] = "edit"
                # Generate AGENTS.md before early return.
                generate_agents_md(project_root)
                result["agents_md_created"] = True
                return result

        console.print("  Config: .beadloom/config.yml")

        # Auto-link existing docs to graph nodes before skeleton generation.
        linked = auto_link_docs(project_root, nodes)
        if linked > 0:
            console.print(f"  Auto-linked {linked} existing doc(s) to graph nodes")
        result["docs_linked"] = linked

    if mode in ("import", "both"):
        if not has_docs:
            import_dir_str = Prompt.ask("Documentation directory", default="docs")
            import_dir = project_root / import_dir_str
        else:
            import_dir = docs_dir

        if import_dir.is_dir():
            console.print(f"\n[bold]Importing docs from {import_dir.name}/...[/bold]")
            docs_result = import_docs(project_root, import_dir)
            result["import"] = docs_result
            console.print(f"  Classified {len(docs_result)} documents")
        else:
            console.print(f"[red]Directory {import_dir} does not exist.[/red]")

    # Generate AGENTS.md.
    generate_agents_md(project_root)
    result["agents_md_created"] = True

    # Auto-reindex: populate DB with imports, edges, FTS.
    console.print("\n[bold]Running reindex...[/bold]")
    from beadloom.application.reindex import reindex as do_reindex

    ri = do_reindex(project_root)
    console.print(f"  Indexed {ri.symbols_indexed} symbols, {ri.imports_indexed} imports")
    result["reindex"] = {
        "symbols": ri.symbols_indexed,
        "imports": ri.imports_indexed,
        "edges": ri.edges_loaded,
    }

    # Doc skeleton generation (only for bootstrap/both modes that have a graph).
    if mode in ("bootstrap", "both"):
        from rich.prompt import Confirm

        from beadloom.onboarding.doc_generator import generate_skeletons

        should_generate = Confirm.ask("Generate doc skeletons?", default=True)
        if should_generate:
            skel_result = generate_skeletons(project_root)
            result["docs"] = skel_result
            console.print(
                f"  Docs: {skel_result['files_created']} skeletons created"
                + (
                    f", {skel_result['files_skipped']} skipped (pre-existing)"
                    if skel_result["files_skipped"] > 0
                    else ""
                )
            )
            # Re-index to pick up newly created doc files.
            if skel_result["files_created"] > 0:
                ri2 = do_reindex(project_root)
                console.print(f"  Re-indexed: {ri2.docs_indexed} docs")

    # Final instructions.
    console.print("\n[green bold]Initialization complete![/green bold]")
    console.print("\nGenerated:")
    console.print("  .beadloom/AGENTS.md — agent instructions for MCP tools")
    console.print("\nNext steps:")
    console.print("  1. Review .beadloom/_graph/*.yml")
    console.print("  2. Run [bold]beadloom doctor[/bold] to verify")

    return result
