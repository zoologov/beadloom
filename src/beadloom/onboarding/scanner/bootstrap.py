"""Bootstrap orchestration: scan -> cluster -> graph YAML + config."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from beadloom.infrastructure.atomic_io import write_yaml_atomic
from beadloom.onboarding.ignore_block import ensure_ignore_block
from beadloom.onboarding.scanner.agents_md import (
    generate_agents_md,
    setup_mcp_auto,
    setup_rules_auto,
)
from beadloom.onboarding.scanner.constants import _sanitize_ref_id
from beadloom.onboarding.scanner.entry_points import _discover_entry_points
from beadloom.onboarding.scanner.import_scan import _quick_import_scan
from beadloom.onboarding.scanner.parent_edges import missing_parent_edges, parented_by
from beadloom.onboarding.scanner.project_scan import (
    _cluster_with_children,
    _detect_project_name,
    _read_manifest_deps,
    scan_project,
)
from beadloom.onboarding.scanner.readme import _ingest_readme
from beadloom.onboarding.scanner.ref_ids import RefIdAllocator
from beadloom.onboarding.scanner.rules_gen import generate_rules
from beadloom.onboarding.scanner.summary import _build_contextual_summary

if TYPE_CHECKING:
    from pathlib import Path


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
    from beadloom.onboarding.presets import PRESETS, detect_preset

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
        project_root,
        source_dirs=scan["source_dirs"] or None,
    )

    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []

    # The ref_id of every node this function writes is handed out by one object,
    # so that no two of them can be the same string. The root takes its name
    # FIRST, before any cluster asks: on the classic `src/<project>/` layout the
    # root and the single package want one name, and the root is the one that
    # must keep it — `doc_generator` titles the architecture document with the
    # root's ref_id and `generate_rules` names it as the parent every domain must
    # have. The package is then written as `<project>-<kind>`. Until BDL-069 both
    # took the plain name, the loader kept one node, and the one it dropped was
    # the one carrying `source:` (BDL-UX #214).
    project_name = _detect_project_name(project_root)
    ref_ids = RefIdAllocator()
    root_ref_id = ref_ids.take(project_name)

    #: The ref_id each generated node was written under, keyed by the name it
    #: asked for. Three later passes build edges by recomputing a cluster's
    #: ref_id from its directory name; with a rename possible, a recomputed name
    #: can name no node at all, which trades a lost node for a dangling edge.
    #: The root is deliberately absent: a manifest dependency resolves to a
    #: package, never to the project the packages sit in, which is what the
    #: `seen_ref_ids` set this map replaced also did (it was built before the
    #: root node existed).
    ref_by_name: dict[str, str] = {}
    #: The same, keyed by cluster name — exact where `ref_by_name` is not, since
    #: two cluster names can sanitize to one string.
    cluster_refs: dict[str, str] = {}

    # Discover entry points early so they can enrich cluster summaries.
    all_entry_points = _discover_entry_points(project_root, scan["source_dirs"] or [])

    for name, info in clusters.items():
        kind, confidence = preset.classify_dir(name)
        all_files: list[str] = info["files"]
        children: dict[str, list[str]] = info["children"]
        source_dir: str = info["source_dir"]

        # Top-level node — contextual summary with symbols, README, entry points.
        preferred = _sanitize_ref_id(name)
        ref_id = ref_ids.take(preferred, qualifier=kind)
        ref_by_name[preferred] = ref_id
        cluster_refs[name] = ref_id
        dir_path = project_root / source_dir / name
        summary = _build_contextual_summary(
            dir_path,
            name,
            kind,
            all_files,
            project_root,
            entry_points=all_entry_points,
        )
        nodes.append(
            {
                "ref_id": ref_id,
                "kind": kind,
                "summary": summary,
                "confidence": confidence,
                "source": f"{source_dir}/{name}/",
            }
        )

        # Child nodes (level 2) + part_of edges.
        if preset.infer_part_of and children:
            for child_name, child_files in children.items():
                child_kind, child_conf = preset.classify_dir(child_name)
                child_preferred = f"{_sanitize_ref_id(name)}-{_sanitize_ref_id(child_name)}"
                child_ref_id = ref_ids.take(child_preferred, qualifier=child_kind)
                ref_by_name[child_preferred] = child_ref_id
                child_dir_path = project_root / source_dir / name / child_name
                child_summary = _build_contextual_summary(
                    child_dir_path,
                    child_name,
                    child_kind,
                    child_files,
                    project_root,
                    entry_points=all_entry_points,
                )
                nodes.append(
                    {
                        "ref_id": child_ref_id,
                        "kind": child_kind,
                        "summary": child_summary,
                        "confidence": child_conf,
                        "source": f"{source_dir}/{name}/{child_name}/",
                    }
                )
                edges.append(
                    {
                        "src": child_ref_id,
                        "dst": ref_id,
                        "kind": "part_of",
                    }
                )

    # Fallback: no clusters found, create minimal nodes from scan.
    if not nodes and scan["source_dirs"]:
        for sd in scan["source_dirs"]:
            sd_ref_id = ref_ids.take(sd, qualifier=preset.default_kind)
            ref_by_name[sd] = sd_ref_id
            nodes.append(
                {
                    "ref_id": sd_ref_id,
                    "kind": preset.default_kind,
                    "summary": f"Source directory: {sd}",
                    "confidence": "low",
                    "source": f"{sd}/",
                }
            )

    # Monorepo: infer depends_on edges from manifest files.
    if preset.infer_deps_from_manifests:
        for name, info in clusters.items():
            source_dir = info["source_dir"]
            pkg_dir = project_root / source_dir / name
            dep_names = _read_manifest_deps(pkg_dir)
            src_ref_id = cluster_refs[name]
            for dep in dep_names:
                dep_ref_id = ref_by_name.get(_sanitize_ref_id(dep))
                if dep_ref_id is not None and dep_ref_id != src_ref_id:
                    edges.append(
                        {
                            "src": src_ref_id,
                            "dst": dep_ref_id,
                            "kind": "depends_on",
                        }
                    )

    # Quick import scan for additional depends_on edges.
    import_edges = _quick_import_scan(project_root, clusters, cluster_refs)
    edges.extend(import_edges)

    # Create root node + part_of edges from top-level nodes.
    if nodes:
        root_node: dict[str, str] = {
            "ref_id": root_ref_id,
            "kind": "service",
            "summary": f"Root: {project_name}",
            "source": "",
        }
        nodes.insert(0, root_node)

        # Attach entry points to root (discovered earlier for cluster summaries).
        if all_entry_points:
            root_extra = json.loads(root_node.get("extra", "{}"))
            root_extra["entry_points"] = all_entry_points
            root_node["extra"] = json.dumps(root_extra, ensure_ascii=False)

        # Ingest deep config (scripts, workspaces, path aliases) into root node.
        from beadloom.onboarding.config_reader import read_deep_config

        deep_config = read_deep_config(project_root)
        root_extra = json.loads(root_node.get("extra", "{}"))
        root_extra["config"] = deep_config
        root_node["extra"] = json.dumps(root_extra, ensure_ascii=False)

        # Ingest README/doc metadata into root node.
        readme_data = _ingest_readme(project_root)
        if readme_data:
            existing_extra = json.loads(root_node.get("extra", "{}"))
            existing_extra.update(readme_data)
            root_node["extra"] = json.dumps(existing_extra, ensure_ascii=False)

            # Update summary with description.
            if readme_data.get("readme_description"):
                desc = str(readme_data["readme_description"])
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                tech = readme_data.get("tech_stack")
                if tech and isinstance(tech, list):
                    tech_str = ", ".join(
                        kw.capitalize() if kw != "aws" and kw != "gcp" else kw.upper()
                        for kw in tech[:5]
                    )
                    root_node["summary"] = f"{project_name}: {desc} ({tech_str})"
                else:
                    root_node["summary"] = f"{project_name}: {desc}"
            elif readme_data.get("tech_stack"):
                tech = readme_data["tech_stack"]
                if isinstance(tech, list):
                    tech_str = ", ".join(
                        kw.capitalize() if kw != "aws" and kw != "gcp" else kw.upper()
                        for kw in tech[:5]
                    )
                    root_node["summary"] = f"Root: {project_name} ({tech_str})"

        # Top-level cluster nodes → part_of root. The edge names the ref_id the
        # cluster was WRITTEN under, not one recomputed from its directory name.
        # Until BDL-069 this loop skipped the cluster whose sanitized name equals
        # the project's, because attaching it would have been a self-edge; that
        # carve-out is gone with the collision it worked around, and the
        # self-edge itself stays refused where it is decided for both writers
        # (`parent_edges.missing_parent_edges`).
        for cluster_name in clusters:
            edges.append(
                {"src": cluster_refs[cluster_name], "dst": root_ref_id, "kind": "part_of"}
            )

        # Post-condition: no node leaves this function without a parent.
        # The loop above only reaches nodes that came from `clusters`; this
        # reaches every node the function wrote, whichever branch wrote it.
        # The rule itself lives in `parent_edges` and is shared with the other
        # writer of nodes (`doc_classify.import_docs`), because the two of them
        # held one invariant in two bodies and had already drifted apart once
        # (the review of BDL-067 `.20`, major 3). What stays here is the only
        # part that is this writer's own: which ref_ids already have a parent.
        # The bootstrap produces the whole graph, so it reads that off the edges
        # it is about to write; the importer adds to a graph and reads it off
        # the one on disk.
        edges.extend(
            missing_parent_edges(nodes, root_node["ref_id"], parented_by(edges))
        )

    # Write YAML graph.
    if nodes:
        graph_data: dict[str, Any] = {"nodes": nodes}
        if edges:
            graph_data["edges"] = edges
        write_yaml_atomic(
            graph_dir / "services.yml",
            graph_data,
            default_flow_style=False,
            allow_unicode=True,
        )

    # Generate rules.yml (only if it doesn't already exist).
    rules_path = graph_dir / "rules.yml"
    if nodes and not rules_path.exists():
        rules_count = generate_rules(nodes, edges, project_name, rules_path)
    else:
        rules_count = 0

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
    write_yaml_atomic(
        beadloom_dir / "config.yml",
        config,
        default_flow_style=False,
        allow_unicode=True,
    )

    # Generate AGENTS.md.
    generate_agents_md(project_root)

    # Auto-configure MCP for detected editor.
    mcp_editor = setup_mcp_auto(project_root)

    # Auto-create IDE rules files.
    rules_created = setup_rules_auto(project_root)

    # Name the derived state this directory now holds, so the adopter does not
    # inherit untracked churn from the first reindex or the first guarded edit.
    # Bootstrap owns it because bootstrap is what creates the working set.
    ignore = ensure_ignore_block(project_root)

    return {
        "project_name": project_name,
        "nodes_generated": len(nodes),
        "edges_generated": len(edges),
        "rules_generated": rules_count,
        "preset": preset.name,
        "config_created": True,
        "agents_md_created": True,
        "mcp_editor": mcp_editor,
        "rules_files": rules_created,
        "scan": scan,
        "nodes": nodes,
        "edges": edges,
        "ignore_added": ignore.added,
        "ignore_skipped_reason": ignore.skipped_reason,
    }
