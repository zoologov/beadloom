"""Tests for beadloom.onboarding.config_reader — deep config file parsing."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from beadloom.onboarding.config_reader import read_deep_config

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_file(path: Path, content: str = "") -> None:
    """Create parent dirs and write content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# pyproject.toml parsing
# ---------------------------------------------------------------------------


class TestPyprojectToml:
    """Test extraction from pyproject.toml."""

    def test_extracts_scripts(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "pyproject.toml",
            '[project.scripts]\nbeadloom = "beadloom.cli:main"\n',
        )
        result = read_deep_config(tmp_path)
        assert "scripts" in result
        assert result["scripts"]["beadloom"] == "beadloom.cli:main"

    def test_extracts_pytest_config(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "pyproject.toml",
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\nasyncio_mode = "strict"\n',
        )
        result = read_deep_config(tmp_path)
        assert "pytest" in result
        assert result["pytest"]["testpaths"] == ["tests"]

    def test_extracts_ruff_config(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "pyproject.toml",
            '[tool.ruff]\nline-length = 99\n[tool.ruff.lint]\nselect = ["E", "F", "W"]\n',
        )
        result = read_deep_config(tmp_path)
        assert "ruff" in result
        assert result["ruff"]["line-length"] == 99

    def test_extracts_build_system(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "pyproject.toml",
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n',
        )
        result = read_deep_config(tmp_path)
        assert "build_system" in result
        assert "hatchling" in result["build_system"]["requires"]


# ---------------------------------------------------------------------------
# package.json parsing
# ---------------------------------------------------------------------------


class TestPackageJson:
    """Test extraction from package.json."""

    def test_extracts_scripts(self, tmp_path: Path) -> None:
        pkg: dict[str, Any] = {
            "name": "my-app",
            "scripts": {
                "test": "jest",
                "lint": "eslint .",
                "build": "tsc",
            },
        }
        _write_file(tmp_path / "package.json", json.dumps(pkg))
        result = read_deep_config(tmp_path)
        assert "scripts" in result
        assert result["scripts"]["test"] == "jest"
        assert result["scripts"]["lint"] == "eslint ."

    def test_extracts_workspaces(self, tmp_path: Path) -> None:
        pkg: dict[str, Any] = {
            "name": "monorepo",
            "workspaces": ["packages/*", "apps/*"],
        }
        _write_file(tmp_path / "package.json", json.dumps(pkg))
        result = read_deep_config(tmp_path)
        assert "workspaces" in result
        assert "packages/*" in result["workspaces"]

    def test_extracts_engines(self, tmp_path: Path) -> None:
        pkg: dict[str, Any] = {
            "name": "my-app",
            "engines": {"node": ">=18.0.0"},
        }
        _write_file(tmp_path / "package.json", json.dumps(pkg))
        result = read_deep_config(tmp_path)
        assert "engines" in result
        assert result["engines"]["node"] == ">=18.0.0"


# ---------------------------------------------------------------------------
# tsconfig.json parsing
# ---------------------------------------------------------------------------


class TestTsconfigJson:
    """Test extraction from tsconfig.json."""

    def test_extracts_path_aliases(self, tmp_path: Path) -> None:
        tsconfig: dict[str, Any] = {
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {
                    "@/*": ["src/*"],
                    "@components/*": ["src/components/*"],
                },
            },
        }
        _write_file(tmp_path / "tsconfig.json", json.dumps(tsconfig))
        result = read_deep_config(tmp_path)
        assert "path_aliases" in result
        assert "@/*" in result["path_aliases"]

    def test_extracts_base_url(self, tmp_path: Path) -> None:
        tsconfig: dict[str, Any] = {
            "compilerOptions": {
                "baseUrl": "src",
            },
        }
        _write_file(tmp_path / "tsconfig.json", json.dumps(tsconfig))
        result = read_deep_config(tmp_path)
        assert "base_url" in result
        assert result["base_url"] == "src"


# ---------------------------------------------------------------------------
# Cargo.toml parsing
# ---------------------------------------------------------------------------


class TestCargoToml:
    """Test extraction from Cargo.toml."""

    def test_extracts_workspace_members(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "Cargo.toml",
            '[workspace]\nmembers = ["crates/core", "crates/cli"]\n',
        )
        result = read_deep_config(tmp_path)
        assert "workspaces" in result
        assert "crates/core" in result["workspaces"]

    def test_extracts_features(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "Cargo.toml",
            '[features]\ndefault = ["std"]\nstd = []\nasync = ["tokio"]\n',
        )
        result = read_deep_config(tmp_path)
        assert "features" in result
        assert "default" in result["features"]
        assert "std" in result["features"]["default"]


# ---------------------------------------------------------------------------
# build.gradle / build.gradle.kts parsing
# ---------------------------------------------------------------------------


class TestBuildGradle:
    """Test extraction from Gradle build files (regex-based)."""

    def test_extracts_plugins(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "build.gradle",
            "plugins {\n    id 'java'\n    id 'org.springframework.boot' version '3.1.0'\n}\n",
        )
        result = read_deep_config(tmp_path)
        assert "gradle_plugins" in result
        assert "java" in result["gradle_plugins"]

    def test_extracts_dependencies(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "build.gradle",
            "dependencies {\n"
            "    implementation 'org.springframework.boot:spring-boot-starter-web'\n"
            "    testImplementation 'org.junit.jupiter:junit-jupiter'\n"
            "}\n",
        )
        result = read_deep_config(tmp_path)
        assert "gradle_dependencies" in result
        assert len(result["gradle_dependencies"]) >= 1

    def test_extracts_kts_plugins(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "build.gradle.kts",
            'plugins {\n    id("java")\n    id("org.springframework.boot") version "3.1.0"\n}\n',
        )
        result = read_deep_config(tmp_path)
        assert "gradle_plugins" in result
        assert "java" in result["gradle_plugins"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test graceful handling of missing and malformed files."""

    def test_missing_files(self, tmp_path: Path) -> None:
        """No config files at all should return empty dict."""
        result = read_deep_config(tmp_path)
        assert isinstance(result, dict)
        # Should not crash, may be empty or contain only empty sections
        assert "error" not in result

    def test_malformed_toml(self, tmp_path: Path) -> None:
        """Malformed TOML should be handled gracefully."""
        _write_file(
            tmp_path / "pyproject.toml",
            "this is not valid toml [[[",
        )
        result = read_deep_config(tmp_path)
        # Should not crash
        assert isinstance(result, dict)

    def test_malformed_json(self, tmp_path: Path) -> None:
        """Malformed JSON should be handled gracefully."""
        _write_file(
            tmp_path / "package.json",
            "{not valid json",
        )
        result = read_deep_config(tmp_path)
        assert isinstance(result, dict)

    def test_malformed_gradle(self, tmp_path: Path) -> None:
        """Malformed Gradle file should be handled gracefully."""
        _write_file(
            tmp_path / "build.gradle",
            "this is just random text with no structure",
        )
        result = read_deep_config(tmp_path)
        assert isinstance(result, dict)

    def test_multiple_configs_combined(self, tmp_path: Path) -> None:
        """Multiple config files should all be read."""
        _write_file(
            tmp_path / "pyproject.toml",
            '[project.scripts]\nstart = "python main.py"\n',
        )
        pkg: dict[str, Any] = {
            "name": "my-app",
            "scripts": {"test": "jest"},
        }
        _write_file(tmp_path / "package.json", json.dumps(pkg))
        result = read_deep_config(tmp_path)
        # Both should be present (package.json scripts merge with pyproject scripts)
        assert "scripts" in result
        assert isinstance(result["scripts"], dict)

    def test_empty_config_files(self, tmp_path: Path) -> None:
        """Empty config files should be handled gracefully."""
        _write_file(tmp_path / "pyproject.toml", "")
        _write_file(tmp_path / "package.json", "{}")
        result = read_deep_config(tmp_path)
        assert isinstance(result, dict)
