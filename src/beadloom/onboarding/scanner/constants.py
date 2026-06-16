"""Shared file-system scanning vocabulary for the onboarding scanner."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING

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
        # React Native / Expo common directories.
        "components",
        "hooks",
        "contexts",
        "modules",
        "screens",
        "navigation",
        "store",
        "providers",
        "features",
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


def _is_in_skip_dir(file_path: Path, base: Path) -> bool:
    """Check if *file_path* is inside a directory that should be skipped."""
    return any(part in _RECURSIVE_SKIP for part in file_path.relative_to(base).parts)


def _sanitize_ref_id(name: str) -> str:
    """Sanitize a directory name for use as a ref_id.

    Strips parentheses so that names like ``(tabs)`` become ``tabs``.
    """
    return name.replace("(", "").replace(")", "")
