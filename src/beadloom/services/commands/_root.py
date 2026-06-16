"""The shared Click ``main`` group + the missing-parser warning helper."""
# beadloom:component=cli-commands

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from beadloom import __version__

if TYPE_CHECKING:
    from pathlib import Path


@click.group()
@click.version_option(version=__version__, prog_name="beadloom")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output (errors only).")
@click.pass_context
def main(ctx: click.Context, *, verbose: bool, quiet: bool) -> None:
    """Beadloom - Context Oracle + Doc Sync Engine."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


def _warn_missing_parsers(project_root: Path) -> None:
    """Print a warning if configured languages lack tree-sitter parsers.

    Reads ``languages`` from ``.beadloom/config.yml`` and checks parser
    availability via ``check_parser_availability``.  When missing parsers
    are detected, emits a ``click.secho`` warning with install instructions.
    """
    config_path = project_root / ".beadloom" / "config.yml"
    if not config_path.exists():
        return

    import yaml

    from beadloom.context_oracle.code_indexer import check_parser_availability

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    languages: list[str] = config.get("languages", [])
    if not languages:
        return

    # Normalise: config may store bare names ("python") or extensions (".py").
    # Map common language names to their canonical extensions.
    name_to_exts: dict[str, list[str]] = {
        "python": [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "go": [".go"],
        "rust": [".rs"],
    }

    extensions: set[str] = set()
    for lang in languages:
        lang_lower = lang.lower().strip()
        if lang_lower.startswith("."):
            extensions.add(lang_lower)
        elif lang_lower in name_to_exts:
            extensions.update(name_to_exts[lang_lower])
        else:
            # Try treating it as an extension anyway.
            extensions.add(f".{lang_lower}")

    if not extensions:
        return

    availability = check_parser_availability(extensions)
    missing = sorted(ext for ext, available in availability.items() if not available)
    if not missing:
        return

    exts_str = ", ".join(missing)
    click.secho(
        f"\u26a0 No parser available for {exts_str} files.",
        fg="yellow",
    )
    click.secho(
        '  Install language support: uv tool install "beadloom[languages]"',
        fg="yellow",
    )
