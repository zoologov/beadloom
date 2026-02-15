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
_MANIFESTS = frozenset(
    {
        "pyproject.toml",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "Gemfile",
        "composer.json",
    }
)

# Known source directories.
_SOURCE_DIRS = frozenset(
    {
        "src",
        "lib",
        "app",
        "services",
        "packages",
        "cmd",
        "internal",
        "backend",
        "frontend",
        "server",
        "client",
        "api",
        "web",
        "mobile",
    }
)

# Directories to skip during top-level fallback scan.
_SKIP_DIRS = frozenset(
    {
        "node_modules",
        "venv",
        "__pycache__",
        "dist",
        "build",
        "target",
        "vendor",
        "coverage",
        "htmlcov",
        "static",
        "assets",
        "docs",
        "test",
        "tests",
        "scripts",
        "bin",
        "tmp",
        "log",
        "logs",
        "mysql-data",
        "nginx",
    }
)

# Directories to skip during recursive file scanning (inside source dirs).
_RECURSIVE_SKIP = frozenset(
    {
        "node_modules",
        "__pycache__",
        "venv",
        ".venv",
        "dist",
        "build",
        "target",
        "vendor",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "htmlcov",
        "coverage",
    }
)

# Directories to exclude from architecture node generation during clustering.
# These contain generated/third-party/non-code assets, not project architecture.
_CLUSTER_SKIP = frozenset(
    {
        "static",
        "staticfiles",
        "templates",
        "migrations",
        "fixtures",
        "locale",
        "locales",
        "media",
        "assets",
        "css",
        "scss",
        "fonts",
        "images",
        "img",
        "icons",
    }
)

# Code extensions to scan.
_CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".vue",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".rb",
    }
)

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
                            child_files.append(str(f.relative_to(project_root)))
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


def _sanitize_ref_id(name: str) -> str:
    """Sanitize a directory name for use as a ref_id.

    Strips parentheses so that names like ``(tabs)`` become ``tabs``.
    """
    return name.replace("(", "").replace(")", "")


def _detect_framework_summary(
    dir_path: Path,
    name: str,
    kind: str,
    file_count: int,
) -> str:
    """Detect framework patterns and return a descriptive summary.

    Checks for known framework markers in the directory and returns
    a framework-aware summary instead of the generic "Kind: name (N files)".
    Summaries are kept under 120 characters.

    Detection order: most specific to least specific to avoid false positives.
    """

    def _safe_read(path: Path) -> str:
        """Read file text, returning empty string on errors."""
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    # --- Highly specific: unique config/marker files ---

    # NestJS: nest-cli.json or *.module.ts pattern
    if (dir_path / "nest-cli.json").exists() or list(dir_path.glob("*.module.ts")):
        return f"NestJS module: {name} ({file_count} files)"

    # Angular: angular.json or *.component.ts pattern
    if (dir_path / "angular.json").exists() or list(dir_path.glob("*.component.ts")):
        return f"Angular app: {name} ({file_count} files)"

    # Next.js: next.config.js / next.config.mjs / next.config.ts
    if (
        (dir_path / "next.config.js").exists()
        or (dir_path / "next.config.mjs").exists()
        or (dir_path / "next.config.ts").exists()
    ):
        return f"Next.js app: {name} ({file_count} files)"

    # Expo / React Native: app.json with "expo" key or react-native in package.json
    app_json = dir_path / "app.json"
    if app_json.exists():
        app_json_text = _safe_read(app_json)
        if '"expo"' in app_json_text:
            return f"Expo app: {name} ({file_count} files)"

    pkg_json = dir_path / "package.json"
    if pkg_json.exists():
        pkg_text = _safe_read(pkg_json)
        if '"react-native"' in pkg_text:
            return f"React Native app: {name} ({file_count} files)"

    # Django app: contains apps.py
    if (dir_path / "apps.py").exists():
        return f"Django app: {name} ({file_count} files)"

    # Spring Boot: pom.xml or build.gradle with spring-boot
    pom_xml = dir_path / "pom.xml"
    if pom_xml.exists():
        pom_text = _safe_read(pom_xml)
        if "spring-boot" in pom_text:
            return f"Spring Boot service: {name} ({file_count} files)"

    build_gradle = dir_path / "build.gradle"
    if build_gradle.exists():
        gradle_text = _safe_read(build_gradle)
        if "spring-boot" in gradle_text or "springframework.boot" in gradle_text:
            return f"Spring Boot service: {name} ({file_count} files)"

    # Actix: Cargo.toml with actix-web
    cargo_toml = dir_path / "Cargo.toml"
    if cargo_toml.exists():
        cargo_text = _safe_read(cargo_toml)
        if "actix-web" in cargo_text:
            return f"Actix service: {name} ({file_count} files)"

    # FastAPI: main.py or app.py with FastAPI imports, or manifest with fastapi
    for entry_file in ("main.py", "app.py"):
        entry = dir_path / entry_file
        if entry.exists():
            entry_text = _safe_read(entry)
            if "FastAPI" in entry_text or "fastapi" in entry_text:
                return f"FastAPI service: {name} ({file_count} files)"

    req_txt = dir_path / "requirements.txt"
    if req_txt.exists():
        req_text = _safe_read(req_txt)
        if "fastapi" in req_text.lower():
            return f"FastAPI service: {name} ({file_count} files)"

    pyproject = dir_path / "pyproject.toml"
    if pyproject.exists():
        pyproject_text = _safe_read(pyproject)
        if "fastapi" in pyproject_text.lower():
            return f"FastAPI service: {name} ({file_count} files)"

    # Flask: app.py with Flask pattern, or requirements.txt with flask
    flask_app = dir_path / "app.py"
    if flask_app.exists():
        flask_text = _safe_read(flask_app)
        if "Flask" in flask_text or "flask" in flask_text:
            return f"Flask app: {name} ({file_count} files)"

    if req_txt.exists():
        req_text = _safe_read(req_txt)
        if "flask" in req_text.lower():
            return f"Flask app: {name} ({file_count} files)"

    # Express: package.json with express dependency
    if pkg_json.exists():
        pkg_text = _safe_read(pkg_json)
        if '"express"' in pkg_text:
            return f"Express service: {name} ({file_count} files)"

    # Vue: *.vue files or vue.config.js
    if (dir_path / "vue.config.js").exists() or list(dir_path.glob("*.vue")):
        return f"Vue app: {name} ({file_count} files)"

    # Gin: Go files with gin-gonic/gin import
    go_files = list(dir_path.glob("*.go"))
    if go_files:
        for go_file in go_files:
            go_text = _safe_read(go_file)
            if "github.com/gin-gonic/gin" in go_text:
                return f"Gin service: {name} ({file_count} files)"

    # SwiftUI: .swift files with import SwiftUI
    swift_files = list(dir_path.glob("*.swift"))
    if swift_files:
        for sf in swift_files:
            sf_text = _safe_read(sf)
            if "import SwiftUI" in sf_text:
                return f"SwiftUI app: {name} ({file_count} files)"

    # Jetpack Compose: .kt files with import androidx.compose
    kt_files = list(dir_path.glob("*.kt"))
    if kt_files:
        for kf in kt_files:
            kf_text = _safe_read(kf)
            if "import androidx.compose" in kf_text:
                return f"Jetpack Compose app: {name} ({file_count} files)"

    # UIKit: .swift or .m files with import UIKit
    uikit_files = list(dir_path.glob("*.swift")) + list(dir_path.glob("*.m"))
    if uikit_files:
        for uf in uikit_files:
            uf_text = _safe_read(uf)
            if "import UIKit" in uf_text:
                return f"UIKit app: {name} ({file_count} files)"

    # React component: contains index.tsx or index.jsx
    if (dir_path / "index.tsx").exists() or (dir_path / "index.jsx").exists():
        return f"React component: {name} ({file_count} files)"

    # Python package: contains __init__.py + (setup.py or pyproject.toml)
    if (dir_path / "__init__.py").exists() and (
        (dir_path / "setup.py").exists() or (dir_path / "pyproject.toml").exists()
    ):
        return f"Python package: {name} ({file_count} files)"

    # Containerized service: contains Dockerfile
    if (dir_path / "Dockerfile").exists():
        return f"Containerized service: {name} ({file_count} files)"

    # Default: use kind label
    kind_label = kind.capitalize()
    return f"{kind_label}: {name} ({file_count} files)"


def _detect_project_name(project_root: Path) -> str:
    """Detect project name from manifest files or directory name.

    Checks (in order): pyproject.toml, package.json, go.mod, Cargo.toml.
    Falls back to the directory name.
    """
    # pyproject.toml — [project] or [tool.poetry] name.
    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if match:
            return match.group(1)

    # package.json.
    pkg_json = project_root / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            name = data.get("name", "")
            if name:
                # Handle scoped packages: @org/name → name.
                return str(name).split("/")[-1]
        except (json.JSONDecodeError, KeyError):
            pass

    # go.mod.
    go_mod = project_root / "go.mod"
    if go_mod.is_file():
        text = go_mod.read_text(encoding="utf-8")
        match = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
        if match:
            # Handle full paths: github.com/org/name → name.
            return match.group(1).split("/")[-1]

    # Cargo.toml.
    cargo = project_root / "Cargo.toml"
    if cargo.is_file():
        text = cargo.read_text(encoding="utf-8")
        match = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if match:
            return match.group(1)

    # Fallback: directory name.
    return project_root.name


def generate_rules(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    project_name: str,
    rules_path: Path,
) -> int:
    """Generate ``rules.yml`` from discovered graph structure.

    Only creates structural *require* rules — no *deny* rules by default.
    Returns the number of rules written.
    """
    kinds = {n["kind"] for n in nodes}
    rules: list[dict[str, Any]] = []

    # Rule 1: every domain must have a part_of edge (to any node).
    # Using an empty matcher so sub-domains pointing at a parent domain
    # (rather than the root) are not flagged as violations.
    if "domain" in kinds:
        rules.append(
            {
                "name": "domain-needs-parent",
                "description": "Every domain must have a part_of edge",
                "require": {
                    "for": {"kind": "domain"},
                    "has_edge_to": {},
                    "edge_kind": "part_of",
                },
            }
        )

    # Rule 2: every feature must be part_of a domain.
    if "feature" in kinds:
        rules.append(
            {
                "name": "feature-needs-domain",
                "description": "Every feature must be part_of a domain",
                "require": {
                    "for": {"kind": "feature"},
                    "has_edge_to": {"kind": "domain"},
                    "edge_kind": "part_of",
                },
            }
        )

    # Rule 3: every service must have a part_of edge to a parent.
    if "service" in kinds:
        rules.append(
            {
                "name": "service-needs-parent",
                "description": "Every service must have a part_of edge to a parent",
                "require": {
                    "for": {"kind": "service"},
                    "has_edge_to": {},
                    "edge_kind": "part_of",
                },
            }
        )

    if not rules:
        return 0

    data: dict[str, Any] = {"version": 1, "rules": rules}
    rules_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return len(rules)


# MCP config paths per editor (mirrors _MCP_TOOL_CONFIGS in cli.py).
_MCP_EDITOR_MARKERS: tuple[tuple[str, str], ...] = (
    (".cursor", "cursor"),
    (".windsurfrules", "windsurf"),
    (".claude", "claude-code"),
    ("CLAUDE.md", "claude-code"),
)

_MCP_DEFAULT_EDITOR = "claude-code"


def setup_mcp_auto(project_root: Path) -> str | None:
    """Auto-detect editor and create MCP config.

    Returns editor name on success, or *None* if config already exists.
    """
    import shutil

    # Detect editor (most specific marker first).
    editor = _MCP_DEFAULT_EDITOR
    for marker, name in _MCP_EDITOR_MARKERS:
        if (project_root / marker).exists():
            editor = name
            break

    # Resolve MCP config path.
    from pathlib import Path as _Path

    paths: dict[str, Path] = {
        "claude-code": project_root / ".mcp.json",
        "cursor": project_root / ".cursor" / "mcp.json",
        "windsurf": _Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
    }
    mcp_path = paths[editor]

    # Never overwrite existing config.
    if mcp_path.exists():
        return None

    mcp_path.parent.mkdir(parents=True, exist_ok=True)

    beadloom_cmd = shutil.which("beadloom") or "beadloom"
    args: list[str] = ["mcp-serve"]
    if editor == "windsurf":
        args.extend(["--project", str(project_root.resolve())])

    data = {
        "mcpServers": {
            "beadloom": {
                "command": beadloom_cmd,
                "args": args,
            }
        }
    }

    mcp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return editor


# IDE rules adapter template — thin pointer to AGENTS.md.
_RULES_ADAPTER_TEMPLATE = """\
# Generated by Beadloom — do not edit manually
# See .beadloom/AGENTS.md for the source of truth

Read the file .beadloom/AGENTS.md before starting any work on this project.
It contains architecture rules, available MCP tools, and coding conventions.
"""

# Markers that identify a file as a beadloom-generated adapter.
_BEADLOOM_ADAPTER_MARKERS = ("beadloom", ".beadloom/AGENTS.md")

# IDE rules file paths and detection markers.
_RULES_CONFIGS: dict[str, dict[str, str]] = {
    "cursor": {
        "path": ".cursorrules",
        "marker": ".cursor",
    },
    "windsurf": {
        "path": ".windsurfrules",
        "marker": ".windsurfrules",
    },
    "cline": {
        "path": ".clinerules",
        "marker": ".clinerules",
    },
}


def _is_beadloom_adapter(path: Path) -> bool | None:
    """Check whether *path* contains beadloom adapter content.

    Returns ``True`` if the file is a beadloom adapter, ``False`` if
    it contains unrelated content, or ``None`` if the file cannot be read.
    """
    try:
        content = path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return None
    return any(marker in content for marker in _BEADLOOM_ADAPTER_MARKERS)


def setup_rules_auto(project_root: Path) -> list[str]:
    """Auto-detect IDEs and create adapter files.

    Adapter files are thin pointers that tell the AI agent
    to read .beadloom/AGENTS.md before starting work.

    Content-aware logic:

    - File does not exist -> create adapter.
    - File exists and is a beadloom adapter -> update (safe overwrite).
    - File exists with non-beadloom content -> skip (user content).
    - File exists but unreadable -> skip (graceful degradation).

    Returns list of created/updated file names.
    """
    created: list[str] = []

    for _ide, cfg in _RULES_CONFIGS.items():
        marker_path = project_root / cfg["marker"]
        rules_path = project_root / cfg["path"]

        if not marker_path.exists():
            continue

        if rules_path.exists():
            is_ours = _is_beadloom_adapter(rules_path)
            if is_ours is True:
                # Our adapter — safe to update.
                rules_path.write_text(_RULES_ADAPTER_TEMPLATE, encoding="utf-8")
                created.append(cfg["path"])
            # is_ours is False (user content) or None (unreadable) — skip.
        else:
            # File doesn't exist — create new adapter.
            rules_path.write_text(_RULES_ADAPTER_TEMPLATE, encoding="utf-8")
            created.append(cfg["path"])

    return created


_AGENTS_MD_TEMPLATE_V2 = """\
# Beadloom — Agent Instructions

> Auto-generated by `beadloom init`. Safe to edit.
> Sections below `## Custom` are preserved on regeneration.

## Before starting work

- Call MCP tool `prime` to get current project context
- Or run `beadloom prime` in terminal
- For specific feature/domain: `beadloom ctx <ref-id>` or MCP `get_context(ref_id)`
- Search the codebase: `beadloom search "<query>"`
- If no ref_id is given: `list_nodes()` to discover the graph

## After changing code

1. `beadloom reindex` — update the index
2. `beadloom sync-check` — check for stale docs
3. If stale: update docs, then `beadloom reindex` again
4. `beadloom lint --strict` — verify architecture boundaries

## Conventions

- Feature IDs: DOMAIN-NNN (e.g., AUTH-001)
- Annotations: `# beadloom:feature=REF_ID` in code files
- Documentation: `docs/` directory
- Graph YAML: `.beadloom/_graph/`

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `prime` | Compact project context for session start |
| `get_context` | Full context bundle (graph + docs + code) |
| `get_graph` | Subgraph around a node |
| `list_nodes` | List nodes, optionally by kind |
| `sync_check` | Check doc-code freshness |
| `get_status` | Index statistics and coverage |
| `search` | Full-text search across nodes and docs |
| `update_node` | Update node summary or source |
| `mark_synced` | Mark doc-code pair as synchronized |
| `generate_docs` | Enrichment data for AI doc polish |

{rules_section}## Custom

<!-- Add project-specific instructions below this line -->
"""


def _build_rules_section(project_root: Path) -> str:
    """Build architecture rules section from rules.yml for AGENTS.md."""
    rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"
    if not rules_path.exists():
        return ""

    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if not data or not data.get("rules"):
        return ""

    lines = ["## Architecture Rules\n"]
    for rule in data["rules"]:
        name = rule.get("name", "unnamed")
        description = rule.get("description", "")
        rule_type = "require" if "require" in rule else "deny"
        if description:
            lines.append(f"- **{name}** ({rule_type}): {description}")
        else:
            lines.append(f"- **{name}** ({rule_type})")
    lines.append("")
    return "\n".join(lines) + "\n"


def generate_agents_md(project_root: Path) -> Path:
    """Generate .beadloom/AGENTS.md with agent instructions.

    Preserves user content below '## Custom' marker on regeneration.
    Returns the path to the generated file.
    """
    beadloom_dir = project_root / ".beadloom"
    beadloom_dir.mkdir(parents=True, exist_ok=True)
    agents_path = beadloom_dir / "AGENTS.md"

    # Preserve user content below ## Custom
    custom_content = ""
    if agents_path.exists():
        text = agents_path.read_text(encoding="utf-8")
        marker = "## Custom"
        idx = text.find(marker)
        if idx != -1:
            custom_content = text[idx + len(marker) :]

    # Build rules section from rules.yml
    rules_section = _build_rules_section(project_root)

    # Render template
    content = _AGENTS_MD_TEMPLATE_V2.format(rules_section=rules_section)

    # Append preserved custom content
    if custom_content:
        content = content.rstrip() + "\n" + custom_content

    agents_path.write_text(content, encoding="utf-8")
    return agents_path


# ---------------------------------------------------------------------------
# prime_context — compact project context for AI agent injection
# ---------------------------------------------------------------------------


def _read_rules_data(project_root: Path) -> list[dict[str, str]]:
    """Read architecture rules from rules.yml as structured data."""
    rules_path = project_root / ".beadloom" / "_graph" / "rules.yml"
    if not rules_path.exists():
        return []
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if not data or not data.get("rules"):
        return []
    result: list[dict[str, str]] = []
    for rule in data["rules"]:
        rule_type = "require" if "require" in rule else "deny"
        result.append(
            {
                "name": rule.get("name", "unnamed"),
                "type": rule_type,
                "description": rule.get("description", ""),
            }
        )
    return result


def _get_lint_violations(project_root: Path) -> list[dict[str, str]]:
    """Get lint violations without reindexing (fast path)."""
    try:
        from beadloom.graph.linter import lint as run_lint

        result = run_lint(project_root, reindex_before=False)
        return [
            {
                "rule": v.rule_name,
                "node": v.from_ref_id or "",
                "message": v.message,
            }
            for v in result.violations
        ]
    except Exception:  # graceful degradation
        return []


def _format_prime_markdown(
    project_name: str,
    rules: list[dict[str, str]],
    dynamic: dict[str, Any],
) -> str:
    """Format prime context as compact Markdown."""
    lines: list[str] = [f"# Project: {project_name}", ""]

    if not dynamic:
        lines.append("Warning: Database not found. Run `beadloom reindex` for full context.")
        lines.append("")
    else:
        # Architecture summary
        kc: dict[str, int] = dynamic["kind_counts"]
        parts: list[str] = []
        for kind in ("domain", "service", "feature", "entity"):
            count = kc.get(kind, 0)
            if count:
                parts.append(f"{count} {kind}s")
        arch_str = ", ".join(parts) if parts else "no nodes"
        lines.append(f"Architecture: {arch_str} | {dynamic['symbols']} symbols")

        stale_count = len(dynamic.get("stale_docs", []))
        violations_count = len(dynamic.get("violations", []))
        last_reindex = dynamic.get("last_reindex", "never")
        lines.append(
            f"Health: {stale_count} stale docs,"
            f" {violations_count} lint violations"
            f" | Last reindex: {last_reindex}"
        )
        lines.append("")

    # Architecture Rules
    if rules:
        lines.append("## Architecture Rules")
        for rule in rules:
            desc = rule["description"]
            if desc:
                lines.append(f"- {rule['name']} ({rule['type']}): {desc}")
            else:
                lines.append(f"- {rule['name']} ({rule['type']})")
        lines.append("")

    # Key Commands
    lines.append("## Key Commands")
    lines.append("| Command | Description |")
    lines.append("|---------|-------------|")
    lines.append("| `beadloom ctx <ref_id>` | Full context bundle for a node |")
    lines.append('| `beadloom search "<query>"` | FTS5 search across nodes and docs |')
    lines.append("| `beadloom lint --strict` | Architecture boundary validation |")
    lines.append("| `beadloom sync-check` | Check doc-code freshness |")
    lines.append("")

    # Agent Instructions
    lines.append("## Agent Instructions")
    lines.append("- Before work: call `get_context(ref_id)` or `prime` MCP tool")
    lines.append("- After code changes: call `sync_check()`, update stale docs")
    lines.append("- New features: add `# beadloom:feature=REF_ID` annotations")
    lines.append("- Graph changes: run `beadloom reindex` after editing YAML")
    lines.append("")

    # Domains
    if dynamic and dynamic.get("domains"):
        lines.append("## Domains")
        for d in dynamic["domains"]:
            lines.append(f"- {d['ref_id']}: {d['summary']}")
        lines.append("")

    # Stale docs
    if dynamic:
        stale: list[dict[str, str]] = dynamic.get("stale_docs", [])
        lines.append("## Stale Docs")
        if stale:
            for s in stale:
                lines.append(f"- {s['doc_path']} ({s['ref_id']})")
        else:
            lines.append("(none)")
        lines.append("")

    # Lint violations
    if dynamic:
        violations: list[dict[str, str]] = dynamic.get("violations", [])
        lines.append("## Lint Violations")
        if violations:
            for v in violations:
                lines.append(f"- [{v['rule']}] {v['node']}: {v['message']}")
        else:
            lines.append("(none)")
        lines.append("")

    return "\n".join(lines)


def _format_prime_json(
    project_name: str,
    version: str,
    rules: list[dict[str, str]],
    dynamic: dict[str, Any],
) -> dict[str, Any]:
    """Format prime context as structured JSON dict."""
    result: dict[str, Any] = {
        "project": project_name,
        "version": version,
    }

    if dynamic:
        kc: dict[str, int] = dynamic["kind_counts"]
        result["architecture"] = {
            "domains": kc.get("domain", 0),
            "services": kc.get("service", 0),
            "features": kc.get("feature", 0),
            "symbols": dynamic["symbols"],
        }
        result["health"] = {
            "stale_docs": dynamic.get("stale_docs", []),
            "lint_violations": dynamic.get("violations", []),
            "last_reindex": dynamic.get("last_reindex", "never"),
        }
        result["domains"] = dynamic.get("domains", [])
    else:
        result["warning"] = "Database not found. Run `beadloom reindex` for full context."

    result["rules"] = rules
    result["instructions"] = (
        "Before work: call get_context(ref_id) or prime MCP tool. "
        "After code changes: call sync_check(), update stale docs. "
        "New features: add # beadloom:feature=REF_ID annotations. "
        "Graph changes: run beadloom reindex after editing YAML."
    )

    return result


def prime_context(
    project_root: Path,
    *,
    fmt: str = "markdown",
) -> str | dict[str, Any]:
    """Build compact project context for AI agent injection.

    Three layers:

    1. **Static** — ``AGENTS.md`` instructions, ``rules.yml``, ``config.yml``
    2. **Dynamic** — DB queries (nodes, stale docs, lint violations, symbols)
    3. **Format** — markdown or JSON output

    Works gracefully without DB (static-only mode).
    Target: <=2000 tokens output.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.beadloom/`` lives).
    fmt:
        Output format — ``"markdown"`` (default) or ``"json"``.

    Returns
    -------
    str | dict[str, Any]
        Compact Markdown string or structured dict.
    """
    from beadloom import __version__

    # 1. Static layer
    project_name = _detect_project_name(project_root)
    rules = _read_rules_data(project_root)

    # 2. Dynamic layer (requires DB)
    db_path = project_root / ".beadloom" / "beadloom.db"
    dynamic: dict[str, Any] = {}

    if db_path.exists():
        from beadloom.infrastructure.db import get_meta, open_db

        conn = open_db(db_path)
        try:
            # Node counts by kind
            kind_rows = conn.execute(
                "SELECT kind, count(*) AS cnt FROM nodes GROUP BY kind"
            ).fetchall()
            kind_counts: dict[str, int] = {str(r["kind"]): int(r["cnt"]) for r in kind_rows}

            # Symbols count
            symbols: int = int(conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0])

            # Domain list
            domain_rows = conn.execute(
                "SELECT ref_id, summary FROM nodes WHERE kind = 'domain' ORDER BY ref_id"
            ).fetchall()
            domains: list[dict[str, str]] = [
                {"ref_id": str(r["ref_id"]), "summary": str(r["summary"] or "")}
                for r in domain_rows
            ]

            # Stale docs
            stale_rows = conn.execute(
                "SELECT doc_path, code_path, ref_id FROM sync_state WHERE status = 'stale'"
            ).fetchall()
            stale_docs: list[dict[str, str]] = [
                {
                    "doc_path": str(r["doc_path"]),
                    "code_path": str(r["code_path"]),
                    "ref_id": str(r["ref_id"]),
                }
                for r in stale_rows
            ]

            # Lint violations (fast, no reindex)
            violations = _get_lint_violations(project_root)

            # Last reindex
            last_reindex = get_meta(conn, "last_reindex_at", "never")

            dynamic = {
                "kind_counts": kind_counts,
                "symbols": symbols,
                "domains": domains,
                "stale_docs": stale_docs,
                "violations": violations,
                "last_reindex": last_reindex,
            }
        finally:
            conn.close()

    # 3. Format output
    if fmt == "json":
        return _format_prime_json(project_name, __version__, rules, dynamic)
    return _format_prime_markdown(project_name, rules, dynamic)


# Technology keywords for README scanning (lowercase).
_TECH_KEYWORDS = frozenset(
    {
        "python",
        "javascript",
        "typescript",
        "react",
        "vue",
        "angular",
        "django",
        "flask",
        "fastapi",
        "express",
        "nestjs",
        "nextjs",
        "docker",
        "kubernetes",
        "postgres",
        "mysql",
        "redis",
        "mongodb",
        "graphql",
        "rest",
        "grpc",
        "golang",
        "rust",
        "swift",
        "kotlin",
        "java",
        "spring",
        "aws",
        "gcp",
        "azure",
        "terraform",
        "node",
        "deno",
        "bun",
        "vite",
        "webpack",
    }
)


def _extract_first_paragraph(text: str) -> str:
    """Extract the first non-heading, non-empty paragraph from markdown text."""
    lines = text.splitlines()
    paragraph_lines: list[str] = []
    found_content = False

    for line in lines:
        stripped = line.strip()
        # Skip blank lines before finding content.
        if not stripped:
            if found_content:
                break
            continue
        # Skip heading lines.
        if stripped.startswith("#"):
            if found_content:
                break
            continue
        # Found a content line.
        found_content = True
        paragraph_lines.append(stripped)

    return " ".join(paragraph_lines)


def _detect_tech_stack(text: str) -> list[str]:
    """Detect technology keywords in text using word boundary matching."""
    found: list[str] = []
    text_lower = text.lower()
    for kw in sorted(_TECH_KEYWORDS):
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            found.append(kw)
    return found


def _extract_non_heading_content(text: str, max_chars: int) -> str:
    """Extract non-heading content from markdown, truncated to max_chars."""
    lines = text.splitlines()
    content_lines: list[str] = []
    total = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        content_lines.append(stripped)
        total += len(stripped) + 1  # +1 for joining space
        if total >= max_chars:
            break

    result = " ".join(content_lines)
    return result[:max_chars]


def _ingest_readme(project_root: Path) -> dict[str, str | list[str]]:
    """Extract project metadata from README and documentation files.

    Parses: README.md, CONTRIBUTING.md, ARCHITECTURE.md, docs/README.md

    Returns dict with:
    - readme_description: first non-heading paragraph from README
    - tech_stack: list of detected technology mentions
    - architecture_notes: summary from ARCHITECTURE.md if present
    """
    result: dict[str, str | list[str]] = {}

    # Find README content — try root first, then docs/README.md.
    readme_text = ""
    for readme_path in [
        project_root / "README.md",
        project_root / "docs" / "README.md",
    ]:
        if readme_path.is_file():
            readme_text = readme_path.read_text(encoding="utf-8")
            break

    if readme_text:
        # Extract first paragraph.
        desc = _extract_first_paragraph(readme_text)
        if desc:
            result["readme_description"] = desc

        # Detect tech stack from all readme content.
        tech = _detect_tech_stack(readme_text)
        if tech:
            result["tech_stack"] = tech

    # Also scan CONTRIBUTING.md for tech keywords.
    contributing_path = project_root / "CONTRIBUTING.md"
    if contributing_path.is_file():
        contrib_text = contributing_path.read_text(encoding="utf-8")
        extra_tech = _detect_tech_stack(contrib_text)
        existing_tech = list(result.get("tech_stack", []))
        merged = sorted(set(existing_tech) | set(extra_tech))
        if merged:
            result["tech_stack"] = merged

    # Extract architecture notes.
    arch_path = project_root / "ARCHITECTURE.md"
    if arch_path.is_file():
        arch_text = arch_path.read_text(encoding="utf-8")
        notes = _extract_non_heading_content(arch_text, 500)
        if notes:
            result["architecture_notes"] = notes

    return result


# Entry-point detection patterns (compiled once).
_EP_IF_NAME_RE = re.compile(
    r"""if\s+__name__\s*==\s*['"]__main__['"]""",
)
_EP_CLICK_RE = re.compile(r"@click\.(command|group)")
_EP_TYPER_RE = re.compile(r"typer\.Typer\(\)")
_EP_ARGPARSE_RE = re.compile(r"argparse\.ArgumentParser")
_EP_GO_MAIN_RE = re.compile(r"func\s+main\(\)")
_EP_RUST_MAIN_RE = re.compile(r"fn\s+main\(\)")
_EP_JAVA_MAIN_RE = re.compile(r"public\s+static\s+void\s+main")
_EP_KOTLIN_MAIN_RE = re.compile(r"fun\s+main\(")
_EP_SWIFT_MAIN_RE = re.compile(r"@main")
_EP_SERVER_RE = re.compile(r"(uvicorn\.run|app\.run\(|\.listen\()")

# Max files per extension to avoid slow scans.
_EP_MAX_FILES_PER_EXT = 50
# Max total entry points to return.
_EP_MAX_RESULTS = 20

# Extensions eligible for entry-point scanning.
_EP_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".js": "javascript",
    ".ts": "typescript",
}


def _discover_entry_points(
    project_root: Path,
    source_dirs: list[str],
) -> list[dict[str, str]]:
    """Discover application entry points across source directories.

    Detects:
    - __main__.py files (Python CLI entry)
    - if __name__ == "__main__" blocks (Python scripts)
    - Click/Typer/argparse CLI definitions
    - main() in Go/Rust/Java/Kotlin files
    - @main in Swift
    - Server bootstrap patterns (uvicorn, gunicorn, express.listen, etc.)

    Returns list of dicts with: file_path (relative), kind (cli|script|server|app),
    description.
    """
    results: list[dict[str, str]] = []
    seen_paths: set[str] = set()

    def _add(rel: str, kind: str, desc: str) -> None:
        if rel not in seen_paths and len(results) < _EP_MAX_RESULTS:
            seen_paths.add(rel)
            results.append({"file_path": rel, "kind": kind, "description": desc})

    # Collect files per extension, capped.
    files_by_ext: dict[str, list[Path]] = {}
    for sd_name in source_dirs:
        sd = project_root / sd_name
        if not sd.is_dir():
            continue
        for f in sd.rglob("*"):
            if not f.is_file():
                continue
            if any(part in _RECURSIVE_SKIP for part in f.relative_to(project_root).parts):
                continue
            ext = f.suffix
            if ext not in _EP_EXTENSIONS:
                continue
            bucket = files_by_ext.setdefault(ext, [])
            if len(bucket) < _EP_MAX_FILES_PER_EXT:
                bucket.append(f)

    # 1. Python __main__.py detection (file existence).
    for py_file in files_by_ext.get(".py", []):
        if py_file.name == "__main__.py":
            rel = str(py_file.relative_to(project_root))
            _add(rel, "cli", "Python CLI entry (__main__.py)")

    # 2-5. Python content patterns.
    for py_file in files_by_ext.get(".py", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        rel = str(py_file.relative_to(project_root))
        if rel in seen_paths:
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        # Click CLI.
        if _EP_CLICK_RE.search(text):
            _add(rel, "cli", "Click CLI definition")
            continue
        # Typer CLI.
        if _EP_TYPER_RE.search(text):
            _add(rel, "cli", "Typer CLI definition")
            continue
        # argparse CLI.
        if _EP_ARGPARSE_RE.search(text):
            _add(rel, "cli", "argparse CLI definition")
            continue
        # Server bootstrap.
        if _EP_SERVER_RE.search(text):
            _add(rel, "server", "Server bootstrap (Python)")
            continue
        # if __name__ == "__main__".
        if _EP_IF_NAME_RE.search(text):
            _add(rel, "script", 'Python script (if __name__ == "__main__")')
            continue

    # 6. Go main.
    for go_file in files_by_ext.get(".go", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = go_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_GO_MAIN_RE.search(text):
            rel = str(go_file.relative_to(project_root))
            _add(rel, "app", "Go application entry (func main)")

    # 7. Rust main.
    for rs_file in files_by_ext.get(".rs", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        if rs_file.name != "main.rs":
            continue
        try:
            text = rs_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_RUST_MAIN_RE.search(text):
            rel = str(rs_file.relative_to(project_root))
            _add(rel, "app", "Rust application entry (fn main)")

    # 8. Java main.
    for java_file in files_by_ext.get(".java", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = java_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_JAVA_MAIN_RE.search(text):
            rel = str(java_file.relative_to(project_root))
            _add(rel, "app", "Java application entry (public static void main)")

    # 9. Kotlin main.
    for kt_file in files_by_ext.get(".kt", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = kt_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_KOTLIN_MAIN_RE.search(text):
            rel = str(kt_file.relative_to(project_root))
            _add(rel, "app", "Kotlin application entry (fun main)")

    # 10. Swift @main.
    for swift_file in files_by_ext.get(".swift", []):
        if len(results) >= _EP_MAX_RESULTS:
            break
        try:
            text = swift_file.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if _EP_SWIFT_MAIN_RE.search(text):
            rel = str(swift_file.relative_to(project_root))
            _add(rel, "app", "Swift application entry (@main)")

    # 11. Server bootstrap in JS/TS.
    for ext in (".js", ".ts"):
        for js_file in files_by_ext.get(ext, []):
            if len(results) >= _EP_MAX_RESULTS:
                break
            try:
                text = js_file.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue
            if _EP_SERVER_RE.search(text):
                rel = str(js_file.relative_to(project_root))
                _add(rel, "server", "Server bootstrap (JS/TS)")

    return results


# Maximum number of import-based edges to avoid overwhelming the graph.
_MAX_IMPORT_EDGES = 50


def _quick_import_scan(
    project_root: Path,
    clusters: dict[str, dict[str, Any]],
    seen_ref_ids: set[str],
) -> list[dict[str, str]]:
    """Quick import scan to infer depends_on edges between clusters.

    For each cluster, scans a sample of code files, extracts imports
    using import_resolver.extract_imports(), and maps them to other
    clusters to create depends_on edges.

    Returns list of edge dicts: {src, dst, kind: "depends_on"}.
    """
    try:
        from beadloom.graph.import_resolver import extract_imports
    except ImportError:
        # tree-sitter or grammar packages not installed.
        return []

    # Build a mapping: relative file path -> cluster ref_id.
    file_to_cluster: dict[str, str] = {}
    for name, info in clusters.items():
        ref_id = _sanitize_ref_id(name)
        for fpath in info["files"]:
            file_to_cluster[fpath] = ref_id

    # Build set of known cluster ref_ids for fast lookup.
    cluster_ref_ids: set[str] = {_sanitize_ref_id(n) for n in clusters}

    seen_edges: set[tuple[str, str]] = set()
    edges: list[dict[str, str]] = []

    for name, info in clusters.items():
        src_ref_id = _sanitize_ref_id(name)
        # Sample up to 10 code files per cluster.
        sample_files = info["files"][:10]

        for rel_path in sample_files:
            abs_path = project_root / rel_path
            if not abs_path.is_file():
                continue

            try:
                imports = extract_imports(abs_path)
            except Exception:  # noqa: S112
                # Unreadable file or tree-sitter error; skip.
                continue

            for imp in imports:
                # Try to resolve the import path to a cluster.
                # Strategy: convert dotted import path to path segments
                # and check if any segment matches a cluster ref_id.
                parts = imp.import_path.replace(".", "/").split("/")
                for part in parts:
                    sanitized_part = _sanitize_ref_id(part)
                    if (
                        sanitized_part in cluster_ref_ids
                        and sanitized_part in seen_ref_ids
                        and sanitized_part != src_ref_id
                    ):
                        edge_key = (src_ref_id, sanitized_part)
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            edges.append(
                                {
                                    "src": src_ref_id,
                                    "dst": sanitized_part,
                                    "kind": "depends_on",
                                }
                            )
                            if len(edges) >= _MAX_IMPORT_EDGES:
                                return edges
                        break  # One match per import is enough.

    return edges


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
    seen_ref_ids: set[str] = set()

    for name, info in clusters.items():
        kind, confidence = preset.classify_dir(name)
        all_files: list[str] = info["files"]
        children: dict[str, list[str]] = info["children"]
        source_dir: str = info["source_dir"]

        # Top-level node.
        ref_id = _sanitize_ref_id(name)
        dir_path = project_root / source_dir / name
        summary = _detect_framework_summary(dir_path, name, kind, len(all_files))
        nodes.append(
            {
                "ref_id": ref_id,
                "kind": kind,
                "summary": summary,
                "confidence": confidence,
                "source": f"{source_dir}/{name}/",
            }
        )
        seen_ref_ids.add(ref_id)

        # Child nodes (level 2) + part_of edges.
        if preset.infer_part_of and children:
            for child_name, child_files in children.items():
                child_kind, child_conf = preset.classify_dir(child_name)
                child_ref_id = f"{_sanitize_ref_id(name)}-{_sanitize_ref_id(child_name)}"
                child_dir_path = project_root / source_dir / name / child_name
                child_summary = _detect_framework_summary(
                    child_dir_path, child_name, child_kind, len(child_files)
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
                seen_ref_ids.add(child_ref_id)
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
            nodes.append(
                {
                    "ref_id": sd,
                    "kind": preset.default_kind,
                    "summary": f"Source directory: {sd}",
                    "confidence": "low",
                    "source": f"{sd}/",
                }
            )
            seen_ref_ids.add(sd)

    # Monorepo: infer depends_on edges from manifest files.
    if preset.infer_deps_from_manifests:
        for name, info in clusters.items():
            source_dir = info["source_dir"]
            pkg_dir = project_root / source_dir / name
            dep_names = _read_manifest_deps(pkg_dir)
            sanitized_name = _sanitize_ref_id(name)
            for dep in dep_names:
                sanitized_dep = _sanitize_ref_id(dep)
                if sanitized_dep in seen_ref_ids and sanitized_dep != sanitized_name:
                    edges.append(
                        {
                            "src": sanitized_name,
                            "dst": sanitized_dep,
                            "kind": "depends_on",
                        }
                    )

    # Quick import scan for additional depends_on edges.
    import_edges = _quick_import_scan(project_root, clusters, seen_ref_ids)
    edges.extend(import_edges)

    # Create root node + part_of edges from top-level nodes.
    project_name = _detect_project_name(project_root)
    if nodes:
        root_node: dict[str, str] = {
            "ref_id": project_name,
            "kind": "service",
            "summary": f"Root: {project_name}",
            "source": "",
        }
        nodes.insert(0, root_node)
        seen_ref_ids.add(project_name)

        # Discover entry points.
        entry_points = _discover_entry_points(project_root, scan["source_dirs"] or [])
        if entry_points:
            root_extra = json.loads(root_node.get("extra", "{}"))
            root_extra["entry_points"] = entry_points
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

        # Top-level cluster nodes → part_of root.
        for cluster_name in clusters:
            sanitized_cluster = _sanitize_ref_id(cluster_name)
            if sanitized_cluster != project_name:
                edges.append({"src": sanitized_cluster, "dst": project_name, "kind": "part_of"})

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
    (beadloom_dir / "config.yml").write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    # Generate AGENTS.md.
    generate_agents_md(project_root)

    # Auto-configure MCP for detected editor.
    mcp_editor = setup_mcp_auto(project_root)

    # Auto-create IDE rules files.
    rules_created = setup_rules_auto(project_root)

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
        nodes.append(
            {
                "ref_id": ref_id,
                "kind": kind if kind in ("feature", "adr", "domain", "service") else "domain",
                "summary": f"Imported from {rel_path}",
                "docs": [f"docs/{rel_path}"],
            }
        )

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
        lines.append(f"    {n['ref_id']:30s} {n['kind']:10s} {n.get('source', '')}{conf_tag}")

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
    from beadloom.infrastructure.reindex import reindex as do_reindex

    ri = do_reindex(project_root)
    console.print(f"  Indexed {ri.symbols_indexed} symbols, {ri.imports_indexed} imports")
    result["reindex"] = {
        "symbols": ri.symbols_indexed,
        "imports": ri.imports_indexed,
        "edges": ri.edges_loaded,
    }

    # Final instructions.
    console.print("\n[green bold]Initialization complete![/green bold]")
    console.print("\nGenerated:")
    console.print("  .beadloom/AGENTS.md — agent instructions for MCP tools")
    console.print("\nNext steps:")
    console.print("  1. Review .beadloom/_graph/*.yml")
    console.print("  2. Run [bold]beadloom doctor[/bold] to verify")

    return result
