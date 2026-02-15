"""Tests for _discover_entry_points and bootstrap_project integration (BEAD-03)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_src_tree(tmp_path: Path) -> Path:
    """Create a minimal src tree so bootstrap_project creates nodes."""
    src = tmp_path / "src"
    src.mkdir()

    auth = src / "auth"
    auth.mkdir()
    (auth / "login.py").write_text("def login(): pass\n")
    models = auth / "models"
    models.mkdir()
    (models / "user.py").write_text("class User: pass\n")

    billing = src / "billing"
    billing.mkdir()
    (billing / "invoice.py").write_text("def create_invoice(): pass\n")

    return src


# ---------------------------------------------------------------------------
# _discover_entry_points — unit tests
# ---------------------------------------------------------------------------


class TestDiscoverEntryPoints:
    """Tests for _discover_entry_points() function."""

    def test_detects_python_dunder_main(self, tmp_path: Path) -> None:
        """__main__.py files are detected as CLI entry points."""
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__main__.py").write_text("print('hello')\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) >= 1
        ep = next(r for r in results if "__main__.py" in r["file_path"])
        assert ep["kind"] == "cli"
        assert "__main__.py" in ep["description"]

    def test_detects_if_name_main(self, tmp_path: Path) -> None:
        """Files with if __name__ == '__main__' are detected as scripts."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "run.py").write_text(
            "def main():\n    pass\n\nif __name__ == '__main__':\n    main()\n"
        )

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "script"
        assert "__main__" in results[0]["description"]

    def test_detects_click_cli(self, tmp_path: Path) -> None:
        """Files with @click.command or @click.group are detected as CLI."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "cli.py").write_text("import click\n\n@click.command()\ndef main():\n    pass\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "cli"
        assert "Click" in results[0]["description"]

    def test_detects_typer_cli(self, tmp_path: Path) -> None:
        """Files with typer.Typer() are detected as CLI."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "cli.py").write_text("import typer\napp = typer.Typer()\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "cli"
        assert "Typer" in results[0]["description"]

    def test_detects_argparse_cli(self, tmp_path: Path) -> None:
        """Files with argparse.ArgumentParser are detected as CLI."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("import argparse\nparser = argparse.ArgumentParser()\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "cli"
        assert "argparse" in results[0]["description"]

    def test_detects_go_main(self, tmp_path: Path) -> None:
        """Go files with func main() are detected as app entry points."""
        src = tmp_path / "cmd"
        src.mkdir()
        (src / "main.go").write_text(
            'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("hi")\n}\n'
        )

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["cmd"])
        assert len(results) == 1
        assert results[0]["kind"] == "app"
        assert "Go" in results[0]["description"]

    def test_detects_rust_main(self, tmp_path: Path) -> None:
        """Rust main.rs with fn main() is detected as app entry point."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.rs").write_text('fn main() {\n    println!("hi");\n}\n')

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "app"
        assert "Rust" in results[0]["description"]

    def test_detects_java_main(self, tmp_path: Path) -> None:
        """Java files with public static void main are detected as app."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "App.java").write_text(
            "public class App {\n"
            "    public static void main(String[] args) {\n"
            '        System.out.println("hi");\n'
            "    }\n"
            "}\n"
        )

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "app"
        assert "Java" in results[0]["description"]

    def test_detects_kotlin_main(self, tmp_path: Path) -> None:
        """Kotlin files with fun main( are detected as app."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "Main.kt").write_text('fun main(args: Array<String>) {\n    println("hi")\n}\n')

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "app"
        assert "Kotlin" in results[0]["description"]

    def test_detects_swift_main(self, tmp_path: Path) -> None:
        """Swift files with @main are detected as app."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "App.swift").write_text("@main\nstruct MyApp {\n    static func main() {}\n}\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "app"
        assert "Swift" in results[0]["description"]

    def test_detects_uvicorn_server(self, tmp_path: Path) -> None:
        """Files with uvicorn.run are detected as server entry points."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "server.py").write_text(
            "import uvicorn\nuvicorn.run(app, host='0.0.0.0', port=8000)\n"
        )

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "server"
        assert "Server" in results[0]["description"]

    def test_detects_express_listen_server(self, tmp_path: Path) -> None:
        """JS/TS files with .listen( are detected as server entry points."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "index.ts").write_text("const app = express();\napp.listen(3000);\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "server"
        assert "Server" in results[0]["description"]

    def test_empty_project_returns_empty(self, tmp_path: Path) -> None:
        """An empty project with no source dirs returns no entry points."""
        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, [])
        assert results == []

    def test_empty_source_dirs_returns_empty(self, tmp_path: Path) -> None:
        """Source dirs that don't exist return no entry points."""
        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["nonexistent"])
        assert results == []

    def test_cap_at_20_entries(self, tmp_path: Path) -> None:
        """Results are capped at 20 entries even with more entry points."""
        src = tmp_path / "src"
        src.mkdir()
        # Create 25 Python scripts with if __name__ == "__main__".
        for i in range(25):
            (src / f"script_{i:02d}.py").write_text(
                f"def main_{i}():\n    pass\n\nif __name__ == '__main__':\n    main_{i}()\n"
            )

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 20

    def test_skips_recursive_skip_dirs(self, tmp_path: Path) -> None:
        """Files in _RECURSIVE_SKIP directories are not scanned."""
        src = tmp_path / "src"
        src.mkdir()
        venv = src / ".venv"
        venv.mkdir()
        (venv / "cli.py").write_text("import click\n\n@click.command()\ndef main():\n    pass\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert results == []

    def test_click_takes_priority_over_if_name(self, tmp_path: Path) -> None:
        """A file with both @click.command and if __name__ is classified as CLI, not script."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "cli.py").write_text(
            "import click\n\n"
            "@click.command()\n"
            "def main():\n    pass\n\n"
            "if __name__ == '__main__':\n    main()\n"
        )

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        assert len(results) == 1
        assert results[0]["kind"] == "cli"
        assert "Click" in results[0]["description"]

    def test_handles_unreadable_file(self, tmp_path: Path) -> None:
        """Unreadable files are skipped without errors."""
        src = tmp_path / "src"
        src.mkdir()
        bad_file = src / "bad.py"
        bad_file.write_bytes(b"\x80\x81\x82" * 100)
        # Also add a valid file to verify scanning continues.
        (src / "good.py").write_text("if __name__ == '__main__':\n    pass\n")

        from beadloom.onboarding.scanner import _discover_entry_points

        results = _discover_entry_points(tmp_path, ["src"])
        # Should find at least the good file; bad file is skipped.
        good_results = [r for r in results if "good.py" in r["file_path"]]
        assert len(good_results) == 1


# ---------------------------------------------------------------------------
# bootstrap_project — entry points integration
# ---------------------------------------------------------------------------


class TestBootstrapEntryPointsIntegration:
    """Tests for entry_points in bootstrap_project root node extra."""

    def test_bootstrap_stores_entry_points_in_extra(self, tmp_path: Path) -> None:
        """bootstrap_project stores entry_points in root node's extra field."""
        _make_src_tree(tmp_path)
        # Add a script with if __name__ block.
        src = tmp_path / "src"
        (src / "auth" / "cli.py").write_text(
            "import click\n\n@click.command()\ndef main():\n    pass\n"
        )

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        assert "extra" in root
        extra = json.loads(root["extra"])
        assert "entry_points" in extra
        eps = extra["entry_points"]
        assert len(eps) >= 1
        assert any(ep["kind"] == "cli" for ep in eps)

    def test_bootstrap_entry_points_coexist_with_readme(self, tmp_path: Path) -> None:
        """Entry points and README data both appear in extra after bootstrap."""
        _make_src_tree(tmp_path)
        (tmp_path / "README.md").write_text(
            "# Test Project\n\nA test project built with Python.\n"
        )
        # Add a Click CLI.
        src = tmp_path / "src"
        (src / "auth" / "cli.py").write_text(
            "import click\n\n@click.command()\ndef main():\n    pass\n"
        )

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        extra = json.loads(root["extra"])
        # Both entry_points and readme data present.
        assert "entry_points" in extra
        assert "readme_description" in extra

    def test_bootstrap_no_entry_points_no_extra_key(self, tmp_path: Path) -> None:
        """When no entry points found, extra does not have entry_points key."""
        _make_src_tree(tmp_path)
        # No entry point files — just plain modules.

        from beadloom.onboarding.scanner import bootstrap_project

        result = bootstrap_project(tmp_path)
        root = result["nodes"][0]
        if "extra" in root:
            extra = json.loads(root["extra"])
            assert "entry_points" not in extra
