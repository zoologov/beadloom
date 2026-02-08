"""Onboarding: project bootstrap, doc import, and initialization."""

from __future__ import annotations

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
})

# Code extensions to scan.
_CODE_EXTENSIONS = frozenset({
    ".py", ".ts", ".js", ".go", ".rs", ".java", ".kt", ".rb",
})

# Doc classification patterns.
_ADR_RE = re.compile(r"(decision|status:\s*(accepted|deprecated|superseded))", re.I)
_FEATURE_RE = re.compile(r"(user\s+story|feature|requirement|spec)", re.I)
_ARCH_RE = re.compile(r"(architect|system\s+design|infrastructure|deployment)", re.I)


def scan_project(project_root: Path) -> dict[str, Any]:
    """Scan project structure and return summary.

    Returns dict with manifests, source_dirs, file_count, languages.
    """
    manifests: list[str] = []
    source_dirs: list[str] = []
    file_count = 0
    extensions: set[str] = set()

    for item in sorted(project_root.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_file() and item.name in _MANIFESTS:
            manifests.append(item.name)
        if item.is_dir() and item.name in _SOURCE_DIRS:
            source_dirs.append(item.name)
            for f in item.rglob("*"):
                if f.is_file() and f.suffix in _CODE_EXTENSIONS:
                    file_count += 1
                    extensions.add(f.suffix)

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


def _cluster_by_dirs(project_root: Path) -> dict[str, list[str]]:
    """Cluster source files by top-level subdirectories.

    Returns dict of dir_name → list of code file paths (relative).
    """
    clusters: dict[str, list[str]] = {}

    for src_dir_name in _SOURCE_DIRS:
        src_dir = project_root / src_dir_name
        if not src_dir.is_dir():
            continue

        for sub in sorted(src_dir.iterdir()):
            if sub.is_dir() and not sub.name.startswith("_"):
                files = []
                for f in sub.rglob("*"):
                    if f.is_file() and f.suffix in _CODE_EXTENSIONS:
                        files.append(str(f.relative_to(project_root)))
                if files:
                    clusters[sub.name] = files

    return clusters


def bootstrap_project(project_root: Path) -> dict[str, Any]:
    """Bootstrap a project: scan, cluster, generate YAML graph and config.

    Returns summary dict with generated file counts.
    """
    beadloom_dir = project_root / ".beadloom"
    graph_dir = beadloom_dir / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    scan = scan_project(project_root)
    clusters = _cluster_by_dirs(project_root)

    # Generate nodes from clusters.
    nodes: list[dict[str, str]] = []
    for name, files in clusters.items():
        nodes.append({
            "ref_id": name,
            "kind": "service",
            "summary": f"Service: {name} ({len(files)} files)",
            "confidence": "medium",
            "source": f"src/{name}/",
        })

    # If no clusters found, create a minimal node from scan.
    if not nodes and scan["source_dirs"]:
        for sd in scan["source_dirs"]:
            nodes.append({
                "ref_id": sd,
                "kind": "service",
                "summary": f"Source directory: {sd}",
                "confidence": "low",
                "source": f"{sd}/",
            })

    # Write YAML graph.
    if nodes:
        graph_data = {"nodes": nodes}
        (graph_dir / "services.yml").write_text(
            yaml.dump(graph_data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    # Create config.
    config = {
        "scan_paths": scan["source_dirs"] or ["src"],
        "languages": scan["languages"] or ["python"],
        "sync": {"hook_mode": "warn"},
    }
    (beadloom_dir / "config.yml").write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    return {
        "nodes_generated": len(nodes),
        "config_created": True,
        "scan": scan,
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
        graph_data = {"nodes": nodes}
        (graph_dir / "imported.yml").write_text(
            yaml.dump(graph_data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    return results
