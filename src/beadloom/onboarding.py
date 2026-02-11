"""Onboarding: project bootstrap, doc import, and initialization."""

# beadloom:domain=onboarding

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

# Known manifest files.
_MANIFESTS = frozenset({
    "pyproject.toml", "package.json", "go.mod", "Cargo.toml",
    "pom.xml", "build.gradle", "Gemfile", "composer.json",
})

# Known source directories.
_SOURCE_DIRS = frozenset({
    "src", "lib", "app", "services", "packages", "cmd", "internal",
    "backend", "frontend", "server", "client", "api", "web", "mobile",
})

# Directories to skip during top-level fallback scan.
_SKIP_DIRS = frozenset({
    "node_modules", "venv", "__pycache__", "dist", "build",
    "target", "vendor", "coverage", "htmlcov", "static", "assets",
    "docs", "test", "tests", "scripts", "bin", "tmp", "log", "logs",
    "mysql-data", "nginx",
})

# Directories to skip during recursive file scanning (inside source dirs).
_RECURSIVE_SKIP = frozenset({
    "node_modules", "__pycache__", "venv", ".venv", "dist", "build",
    "target", "vendor", ".git", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", "htmlcov", "coverage",
})

# Directories to exclude from architecture node generation during clustering.
# These contain generated/third-party/non-code assets, not project architecture.
_CLUSTER_SKIP = frozenset({
    "static", "staticfiles", "templates", "migrations", "fixtures",
    "locale", "locales", "media", "assets", "css", "scss", "fonts",
    "images", "img", "icons",
})

# Code extensions to scan.
_CODE_EXTENSIONS = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".go", ".rs",
    ".java", ".kt", ".rb",
})

# Doc classification patterns.
_ADR_RE = re.compile(r"(decision|status:\s*(accepted|deprecated|superseded))", re.I)
_FEATURE_RE = re.compile(r"(user\s+story|feature|requirement|spec)", re.I)
_ARCH_RE = re.compile(r"(architect|system\s+design|infrastructure|deployment)", re.I)


def _is_in_skip_dir(file_path: Path, base: Path) -> bool:
    """Check if *file_path* is inside a directory that should be skipped."""
    return any(part in _RECURSIVE_SKIP for part in file_path.relative_to(base).parts)


def scan_project(project_root: Path) -> dict[str, Any]:
    """Scan project structure and return summary.

    Returns dict with manifests, source_dirs, file_count, languages.

    Discovery strategy:
    1. Look for directories matching ``_SOURCE_DIRS`` (known names).
    2. If none found, fall back to scanning all non-hidden, non-vendor
       directories for code files.
    """
    manifests: list[str] = []
    source_dirs: list[str] = []
    file_count = 0
    extensions: set[str] = set()

    all_dirs: list[str] = []

    for item in sorted(project_root.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_file() and item.name in _MANIFESTS:
            manifests.append(item.name)
        if item.is_dir():
            if item.name in _SOURCE_DIRS:
                source_dirs.append(item.name)
                for f in item.rglob("*"):
                    if (
                        f.is_file()
                        and f.suffix in _CODE_EXTENSIONS
                        and not _is_in_skip_dir(f, item)
                    ):
                        file_count += 1
                        extensions.add(f.suffix)
            elif item.name not in _SKIP_DIRS:
                all_dirs.append(item.name)

    # Fallback: no known source dirs found — scan all non-skipped dirs.
    if not source_dirs:
        for dir_name in all_dirs:
            dir_path = project_root / dir_name
            count = 0
            for f in dir_path.rglob("*"):
                if (
                    f.is_file()
                    and f.suffix in _CODE_EXTENSIONS
                    and not _is_in_skip_dir(f, dir_path)
                ):
                    count += 1
                    extensions.add(f.suffix)
            if count > 0:
                source_dirs.append(dir_name)
                file_count += count

    return {
        "manifests": manifests,
        "source_dirs": source_dirs,
        "file_count": file_count,
        "languages": sorted(extensions),
    }


def classify_doc(doc_path: Path) -> str:
    """Classify a markdown document by content heuristics."""
    text = doc_path.read_text(encoding="utf-8")

    if _ADR_RE.search(text):
        return "adr"
    if _FEATURE_RE.search(text):
        return "feature"
    if _ARCH_RE.search(text):
        return "architecture"
    return "other"


def _cluster_by_dirs(
    project_root: Path,
    source_dirs: list[str] | None = None,
) -> dict[str, list[str]]:
    """Cluster source files by top-level subdirectories.

    Parameters
    ----------
    project_root:
        Root of the project.
    source_dirs:
        Discovered source directories.  When *None*, falls back to
        ``_SOURCE_DIRS`` for backwards compatibility.

    Returns dict of dir_name -> list of code file paths (relative).
    """
    clusters: dict[str, list[str]] = {}
    dirs_to_scan = source_dirs if source_dirs is not None else list(_SOURCE_DIRS)

    for src_dir_name in dirs_to_scan:
        src_dir = project_root / src_dir_name
        if not src_dir.is_dir():
            continue

        for sub in sorted(src_dir.iterdir()):
            if (
                sub.is_dir()
                and not sub.name.startswith("_")
                and sub.name not in _RECURSIVE_SKIP
                and sub.name not in _CLUSTER_SKIP
            ):
                files = []
                for f in sub.rglob("*"):
                    if (
                        f.is_file()
                        and f.suffix in _CODE_EXTENSIONS
                        and not _is_in_skip_dir(f, sub)
                    ):
                        files.append(str(f.relative_to(project_root)))
                if files:
                    clusters[sub.name] = files

    return clusters


def _cluster_with_children(
    project_root: Path,
    source_dirs: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Two-level directory scan for preset-aware bootstrap.

    Parameters
    ----------
    project_root:
        Root of the project.
    source_dirs:
        Discovered source directories.  When *None*, falls back to
        ``_SOURCE_DIRS`` for backwards compatibility.

    Returns dict of dir_name -> {files, children, source_dir} where
    children is a dict of child_name -> {files}.
    """
    result: dict[str, dict[str, Any]] = {}
    dirs_to_scan = source_dirs if source_dirs is not None else list(_SOURCE_DIRS)

    for src_dir_name in dirs_to_scan:
        src_dir = project_root / src_dir_name
        if not src_dir.is_dir():
            continue

        for sub in sorted(src_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("_"):
                continue
            if sub.name in _RECURSIVE_SKIP or sub.name in _CLUSTER_SKIP:
                continue

            files: list[str] = []
            children: dict[str, list[str]] = {}

            for item in sorted(sub.iterdir()):
                if item.is_file() and item.suffix in _CODE_EXTENSIONS:
                    files.append(str(item.relative_to(project_root)))
                elif item.is_dir() and not item.name.startswith("_"):
                    if item.name in _RECURSIVE_SKIP or item.name in _CLUSTER_SKIP:
                        continue
                    child_files = []
                    for f in item.rglob("*"):
                        if (
                            f.is_file()
                            and f.suffix in _CODE_EXTENSIONS
                            and not _is_in_skip_dir(f, item)
                        ):
                            child_files.append(
                                str(f.relative_to(project_root))
                            )
                    if child_files:
                        children[item.name] = child_files
                        files.extend(child_files)

            if files:
                result[sub.name] = {
                    "files": files,
                    "children": children,
                    "source_dir": src_dir_name,
                }

    return result


def _read_manifest_deps(package_dir: Path) -> list[str]:
    """Read internal dependency names from a package manifest.

    Supports package.json workspace/file/link dependencies.
    Returns only names that look like local/workspace packages.
    """
    deps: list[str] = []

    pkg_json = package_dir / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            for key in ("dependencies", "devDependencies"):
                for dep_name, ver in (data.get(key) or {}).items():
                    if isinstance(ver, str) and (
                        ver.startswith("workspace:")
                        or ver.startswith("file:")
                        or ver.startswith("link:")
                    ):
                        clean = dep_name.split("/")[-1]
                        deps.append(clean)
        except (json.JSONDecodeError, KeyError):
            pass

    return deps


_AGENTS_MD_TEMPLATE = """\
# Beadloom — Agent Instructions

> Auto-generated by `beadloom init`. Edit freely to match your project conventions.

## Before starting work

- Call `get_context(ref_id)` for the feature/domain you're working on
- Review the context bundle: graph, docs, code symbols
- If no ref_id is given, call `list_nodes()` to find relevant nodes

## After changing code

- Call `sync_check()` to see if any docs are now stale
- If stale docs are found, update them as part of your current task
- Use `get_context(ref_id)` to understand what the doc should say

## When creating new features

- Add `# beadloom:feature=REF_ID` annotations to new code files
- If creating a new domain/service, add a node to `.beadloom/_graph/`

## Conventions

- Feature IDs follow the pattern: DOMAIN-NNN (e.g., AUTH-001)
- Documentation lives in `docs/`
- Graph YAML lives in `.beadloom/_graph/`

## Available MCP tools

| Tool | Description |
|------|-------------|
| `get_context` | Context bundle for a ref_id (graph + docs + code symbols) |
| `get_graph` | Subgraph around a node (nodes and edges as JSON) |
| `list_nodes` | List graph nodes, optionally filtered by kind |
| `sync_check` | Check if documentation is up-to-date with code |
| `get_status` | Documentation coverage and index statistics |
"""


def generate_agents_md(project_root: Path) -> Path:
    """Generate .beadloom/AGENTS.md with agent instructions.

    Returns the path to the generated file.
    """
    beadloom_dir = project_root / ".beadloom"
    beadloom_dir.mkdir(parents=True, exist_ok=True)
    agents_path = beadloom_dir / "AGENTS.md"
    agents_path.write_text(_AGENTS_MD_TEMPLATE, encoding="utf-8")
    return agents_path


def bootstrap_project(
    project_root: Path,
    *,
    preset_name: str | None = None,
) -> dict[str, Any]:
    """Bootstrap a project: scan, cluster, generate YAML graph and config.

    When *preset_name* is given (or auto-detected), the bootstrap uses
    architecture-aware rules for node kind classification and edge inference.

    Returns summary dict with generated file counts.
    """
    from beadloom.presets import PRESETS, detect_preset

    beadloom_dir = project_root / ".beadloom"
    graph_dir = beadloom_dir / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    scan = scan_project(project_root)

    # Resolve preset.
    if preset_name and preset_name in PRESETS:
        preset = PRESETS[preset_name]
    else:
        preset = detect_preset(project_root)

    clusters = _cluster_with_children(
        project_root, source_dirs=scan["source_dirs"] or None,
    )

    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    seen_ref_ids: set[str] = set()

    for name, info in clusters.items():
        kind, confidence = preset.classify_dir(name)
        all_files: list[str] = info["files"]
        children: dict[str, list[str]] = info["children"]
        source_dir: str = info["source_dir"]

        # Top-level node.
        ref_id = name
        kind_label = kind.capitalize()
        nodes.append({
            "ref_id": ref_id,
            "kind": kind,
            "summary": f"{kind_label}: {name} ({len(all_files)} files)",
            "confidence": confidence,
            "source": f"{source_dir}/{name}/",
        })
        seen_ref_ids.add(ref_id)

        # Child nodes (level 2) + part_of edges.
        if preset.infer_part_of and children:
            for child_name, child_files in children.items():
                child_kind, child_conf = preset.classify_dir(child_name)
                child_ref_id = f"{name}-{child_name}"
                nodes.append({
                    "ref_id": child_ref_id,
                    "kind": child_kind,
                    "summary": (
                        f"{child_kind.capitalize()}: "
                        f"{child_name} ({len(child_files)} files)"
                    ),
                    "confidence": child_conf,
                    "source": f"{source_dir}/{name}/{child_name}/",
                })
                seen_ref_ids.add(child_ref_id)
                edges.append({
                    "src": child_ref_id,
                    "dst": ref_id,
                    "kind": "part_of",
                })

    # Fallback: no clusters found, create minimal nodes from scan.
    if not nodes and scan["source_dirs"]:
        for sd in scan["source_dirs"]:
            nodes.append({
                "ref_id": sd,
                "kind": preset.default_kind,
                "summary": f"Source directory: {sd}",
                "confidence": "low",
                "source": f"{sd}/",
            })
            seen_ref_ids.add(sd)

    # Monorepo: infer depends_on edges from manifest files.
    if preset.infer_deps_from_manifests:
        for name, info in clusters.items():
            source_dir = info["source_dir"]
            pkg_dir = project_root / source_dir / name
            dep_names = _read_manifest_deps(pkg_dir)
            for dep in dep_names:
                if dep in seen_ref_ids and dep != name:
                    edges.append({
                        "src": name,
                        "dst": dep,
                        "kind": "depends_on",
                    })

    # Write YAML graph.
    if nodes:
        graph_data: dict[str, Any] = {"nodes": nodes}
        if edges:
            graph_data["edges"] = edges
        (graph_dir / "services.yml").write_text(
            yaml.dump(
                graph_data,
                default_flow_style=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

    # Check for docs.
    docs_dir = project_root / "docs"
    has_docs = docs_dir.is_dir() and any(docs_dir.rglob("*.md"))

    # Create config.
    config: dict[str, Any] = {
        "scan_paths": scan["source_dirs"] or ["src"],
        "languages": scan["languages"] or ["python"],
        "sync": {"hook_mode": "warn"},
        "preset": preset.name,
    }
    if not has_docs:
        config["docs_dir"] = None
    (beadloom_dir / "config.yml").write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    # Generate AGENTS.md.
    generate_agents_md(project_root)

    return {
        "nodes_generated": len(nodes),
        "edges_generated": len(edges),
        "preset": preset.name,
        "config_created": True,
        "agents_md_created": True,
        "scan": scan,
        "nodes": nodes,
        "edges": edges,
    }


def import_docs(
    project_root: Path,
    docs_dir: Path,
) -> list[dict[str, str]]:
    """Import and classify existing documentation.

    Returns list of dicts with path, kind for each classified doc.
    """
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str]] = []
    nodes: list[dict[str, Any]] = []

    for md_path in sorted(docs_dir.rglob("*.md")):
        if not md_path.is_file():
            continue
        kind = classify_doc(md_path)
        rel_path = str(md_path.relative_to(docs_dir))
        results.append({"path": rel_path, "kind": kind})

        # Generate a node for classifiable docs.
        ref_id = md_path.stem.replace(" ", "-").lower()
        nodes.append({
            "ref_id": ref_id,
            "kind": kind if kind in ("feature", "adr", "domain", "service") else "domain",
            "summary": f"Imported from {rel_path}",
            "docs": [f"docs/{rel_path}"],
        })

    if nodes:
        graph_data: dict[str, Any] = {"nodes": nodes}
        (graph_dir / "imported.yml").write_text(
            yaml.dump(graph_data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    return results


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
        lines.append(
            f"    {n['ref_id']:30s} {n['kind']:10s} {n.get('source', '')}{conf_tag}"
        )

    if edges:
        lines.append(f"\n  Edges ({len(edges)}):")
        for e in edges:
            lines.append(f"    {e['src']} --{e['kind']}--> {e['dst']}")

    return "\n".join(lines)


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
        console.print(
            "\n[dim]No docs/ directory found — that's fine![/dim]"
        )
        console.print(
            "[dim]Beadloom works great with code-only: "
            "graph, annotations, context oracle.[/dim]"
        )
        console.print(
            "[dim]Add docs later when you need "
            "doc-sync tracking.[/dim]"
        )

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
        console.print(
            f"  Generated {len(nodes)} nodes, {len(edges)} edges"
        )

        # Interactive review.
        if nodes:
            console.print(
                f"\n{_format_review_table(nodes, edges)}"
            )
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
                graph_path = (
                    project_root / ".beadloom" / "_graph" / "services.yml"
                )
                console.print(
                    f"\n[bold]Edit:[/bold] {graph_path}"
                )
                console.print(
                    "Edit the file, then run "
                    "[bold]beadloom reindex[/bold]."
                )
                result["review"] = "edit"
                # Generate AGENTS.md before early return.
                generate_agents_md(project_root)
                result["agents_md_created"] = True
                return result

        console.print("  Config: .beadloom/config.yml")

    if mode in ("import", "both"):
        if not has_docs:
            import_dir_str = Prompt.ask(
                "Documentation directory", default="docs"
            )
            import_dir = project_root / import_dir_str
        else:
            import_dir = docs_dir

        if import_dir.is_dir():
            console.print(
                f"\n[bold]Importing docs from {import_dir.name}/...[/bold]"
            )
            docs_result = import_docs(project_root, import_dir)
            result["import"] = docs_result
            console.print(f"  Classified {len(docs_result)} documents")
        else:
            console.print(
                f"[red]Directory {import_dir} does not exist.[/red]"
            )

    # Generate AGENTS.md.
    generate_agents_md(project_root)
    result["agents_md_created"] = True

    # Auto-reindex: populate DB with imports, edges, FTS.
    console.print("\n[bold]Running reindex...[/bold]")
    from beadloom.reindex import reindex as do_reindex

    ri = do_reindex(project_root)
    console.print(
        f"  Indexed {ri.symbols_indexed} symbols, "
        f"{ri.imports_indexed} imports"
    )
    result["reindex"] = {
        "symbols": ri.symbols_indexed,
        "imports": ri.imports_indexed,
        "edges": ri.edges_loaded,
    }

    # Final instructions.
    console.print("\n[green bold]Initialization complete![/green bold]")
    console.print("\nGenerated:")
    console.print(
        "  .beadloom/AGENTS.md — agent instructions for MCP tools"
    )
    console.print("\nNext steps:")
    console.print("  1. Review .beadloom/_graph/*.yml")
    console.print("  2. Run [bold]beadloom doctor[/bold] to verify")

    return result
