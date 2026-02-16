"""Deep config reader: extract scripts, workspaces, aliases from project configs."""

# beadloom:domain=onboarding

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

# Gradle regex patterns (compiled once)
# Matches both Groovy: id 'java' and Kotlin DSL: id("java")
_GRADLE_PLUGIN_ID_RE = re.compile(
    r"""id\s*\(\s*['"]([^'"]+)['"]\s*\)|id\s+['"]([^'"]+)['"]""",
)
_GRADLE_DEP_RE = re.compile(
    r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation"""
    r"""|testCompileOnly|testRuntimeOnly)\s*[\('"]([^)'"]+)[\)'"]""",
)


# ---------------------------------------------------------------------------
# TOML parsing (pyproject.toml, Cargo.toml)
# ---------------------------------------------------------------------------


def _read_toml(path: Path) -> dict[str, Any]:
    """Read and parse a TOML file, returning empty dict on failure."""
    import sys

    _tomllib: Any = None
    if sys.version_info >= (3, 11):
        import tomllib

        _tomllib = tomllib
    else:
        try:
            import tomli  # optional fallback for Python <3.11

            _tomllib = tomli
        except ImportError:
            return {}

    try:
        content = path.read_bytes()
        result: dict[str, Any] = _tomllib.loads(content.decode("utf-8"))
        return result
    except (OSError, _tomllib.TOMLDecodeError, UnicodeDecodeError, ValueError):
        return {}


def _parse_pyproject(project_root: Path) -> dict[str, Any]:
    """Extract relevant sections from pyproject.toml.

    Extracts: [project.scripts], [tool.pytest], [tool.ruff], [build-system].
    """
    path = project_root / "pyproject.toml"
    if not path.exists():
        return {}

    data = _read_toml(path)
    if not data:
        return {}

    result: dict[str, Any] = {}

    # [project.scripts]
    project_section = data.get("project", {})
    if isinstance(project_section, dict):
        scripts = project_section.get("scripts")
        if scripts and isinstance(scripts, dict):
            result["scripts"] = dict(scripts)

    # [tool.pytest.ini_options]
    tool = data.get("tool", {})
    if isinstance(tool, dict):
        pytest_config = tool.get("pytest", {})
        if isinstance(pytest_config, dict):
            ini_options = pytest_config.get("ini_options", {})
            if isinstance(ini_options, dict) and ini_options:
                result["pytest"] = dict(ini_options)

        # [tool.ruff]
        ruff_config = tool.get("ruff", {})
        if isinstance(ruff_config, dict) and ruff_config:
            result["ruff"] = dict(ruff_config)

    # [build-system]
    build_system = data.get("build-system", {})
    if isinstance(build_system, dict) and build_system:
        result["build_system"] = dict(build_system)

    return result


def _parse_cargo_toml(project_root: Path) -> dict[str, Any]:
    """Extract relevant sections from Cargo.toml.

    Extracts: [workspace] members, [features].
    """
    path = project_root / "Cargo.toml"
    if not path.exists():
        return {}

    data = _read_toml(path)
    if not data:
        return {}

    result: dict[str, Any] = {}

    # [workspace] members
    workspace = data.get("workspace", {})
    if isinstance(workspace, dict):
        members = workspace.get("members")
        if members and isinstance(members, list):
            result["workspaces"] = list(members)

    # [features]
    features = data.get("features", {})
    if isinstance(features, dict) and features:
        result["features"] = dict(features)

    return result


# ---------------------------------------------------------------------------
# JSON parsing (package.json, tsconfig.json)
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file, returning empty dict on failure."""
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict):
            return data
        return {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return {}


def _parse_package_json(project_root: Path) -> dict[str, Any]:
    """Extract relevant sections from package.json.

    Extracts: scripts, workspaces, engines.
    """
    path = project_root / "package.json"
    if not path.exists():
        return {}

    data = _read_json(path)
    if not data:
        return {}

    result: dict[str, Any] = {}

    # scripts
    scripts = data.get("scripts")
    if scripts and isinstance(scripts, dict):
        result["scripts"] = dict(scripts)

    # workspaces
    workspaces = data.get("workspaces")
    if workspaces:
        if isinstance(workspaces, list):
            result["workspaces"] = list(workspaces)
        elif isinstance(workspaces, dict):
            # Yarn workspaces can be {packages: [...]}
            packages = workspaces.get("packages")
            if packages and isinstance(packages, list):
                result["workspaces"] = list(packages)

    # engines
    engines = data.get("engines")
    if engines and isinstance(engines, dict):
        result["engines"] = dict(engines)

    return result


def _parse_tsconfig(project_root: Path) -> dict[str, Any]:
    """Extract relevant sections from tsconfig.json.

    Extracts: compilerOptions.paths, compilerOptions.baseUrl.
    """
    path = project_root / "tsconfig.json"
    if not path.exists():
        return {}

    data = _read_json(path)
    if not data:
        return {}

    result: dict[str, Any] = {}

    compiler_options = data.get("compilerOptions", {})
    if isinstance(compiler_options, dict):
        # paths (path aliases)
        paths = compiler_options.get("paths")
        if paths and isinstance(paths, dict):
            result["path_aliases"] = dict(paths)

        # baseUrl
        base_url = compiler_options.get("baseUrl")
        if base_url and isinstance(base_url, str):
            result["base_url"] = base_url

    return result


# ---------------------------------------------------------------------------
# Gradle parsing (regex-based)
# ---------------------------------------------------------------------------


def _parse_gradle(project_root: Path) -> dict[str, Any]:
    """Extract plugins and dependencies from build.gradle or build.gradle.kts.

    Uses regex-based extraction (no Groovy/Kotlin parser needed).
    """
    # Try build.gradle first, then build.gradle.kts
    path = project_root / "build.gradle"
    if not path.exists():
        path = project_root / "build.gradle.kts"
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    result: dict[str, Any] = {}

    # Extract plugin IDs (regex returns tuples from alternation groups)
    raw_plugins = _GRADLE_PLUGIN_ID_RE.findall(content)
    plugins = [g1 or g2 for g1, g2 in raw_plugins if g1 or g2]
    if plugins:
        result["gradle_plugins"] = sorted(set(plugins))

    # Extract dependencies
    deps = _GRADLE_DEP_RE.findall(content)
    if deps:
        result["gradle_dependencies"] = sorted(set(deps))

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def read_deep_config(project_root: Path) -> dict[str, Any]:
    """Extract scripts, workspaces, path aliases from project configs.

    Parses:
    - pyproject.toml: [project.scripts], [tool.pytest], [tool.ruff], [build-system]
    - package.json: scripts, workspaces, engines
    - tsconfig.json: compilerOptions.paths, compilerOptions.baseUrl
    - Cargo.toml: [workspace] members, [features]
    - build.gradle / build.gradle.kts: plugins, dependencies (regex-based)

    Parameters
    ----------
    project_root:
        Root of the project to scan.

    Returns
    -------
    dict[str, Any]
        Merged config data from all detected config files.
        Empty dict sections for missing files.

    Note: ``Any`` is justified here because config files have heterogeneous structure.
    """
    result: dict[str, Any] = {}

    # Parse each config format and merge results
    for parser in (
        _parse_pyproject,
        _parse_package_json,
        _parse_tsconfig,
        _parse_cargo_toml,
        _parse_gradle,
    ):
        parsed = parser(project_root)
        for key, value in parsed.items():
            if key == "scripts" and key in result:
                # Merge scripts from multiple sources
                existing = result[key]
                if isinstance(existing, dict) and isinstance(value, dict):
                    existing.update(value)
                    continue
            if key == "workspaces" and key in result:
                # Merge workspaces from multiple sources
                existing = result[key]
                if isinstance(existing, list) and isinstance(value, list):
                    for item in value:
                        if item not in existing:
                            existing.append(item)
                    continue
            result[key] = value

    return result
