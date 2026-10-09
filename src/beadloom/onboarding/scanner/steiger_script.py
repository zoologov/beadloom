"""The ``lint:fsd`` script ``init`` gives a Feature-Sliced frontend that runs no Steiger.

BDL-080 S3c. Steiger, the official Feature-Sliced Design linter, judges the files: its
``recommended`` set is the reference the FSD rules of :mod:`.rules_gen` judge the graph
by. The two halves belong together, so ``init`` on an FSD project writes
``"lint:fsd": "steiger <fsd root>"`` into ``package.json`` when no script there runs
Steiger yet, and says what it wrote and what is left to install.

**Never replaced:** a script already named ``lint:fsd``, or any script whose command
runs ``steiger``. **Never rewritten:** a ``package.json`` that is not a JSON object;
the sentence names it instead. The file is written back the way ``npm`` writes one: its
keys in their order and in the indentation it already has, read from its second line
(two spaces for a file on one line), so the diff is the one script. It is written whole or
not at all (:func:`~beadloom.infrastructure.atomic_io.write_text_atomic`) and keeps its
permissions, which the atomic writer's temporary file does not carry (BDL-080 S3f).
"""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

import json
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.infrastructure.atomic_io import write_text_atomic

if TYPE_CHECKING:
    from pathlib import Path

SCRIPT_NAME = "lint:fsd"
_STEIGER = "steiger"
_PACKAGES = ("steiger", "@feature-sliced/steiger-plugin")
_PACKAGE_JSON = "package.json"

#: The indentation of a file whose second line gives none: npm's own default.
_DEFAULT_INDENT = "  "


@dataclass(frozen=True)
class SteigerScript:
    """What ``init`` did about Steiger, and the one sentence it prints about it.

    *kept* names the script that already runs Steiger (or holds the name) when nothing
    was written; *missing* lists the packages ``package.json`` does not declare;
    *unreadable* is the reason a ``package.json`` was left alone.
    """

    written: bool = False
    command: str = ""
    kept: str = ""
    missing: tuple[str, ...] = ()
    unreadable: str = ""

    def sentence(self) -> str:
        """What ``init`` says; ``""`` when the project has no ``package.json``."""
        if self.unreadable:
            return f"Steiger: {_PACKAGE_JSON} left alone ({self.unreadable}); no script written"
        if self.kept:
            return f"Steiger: {_PACKAGE_JSON} already runs it (script '{self.kept}'); kept as is"
        if not self.written:
            return ""
        said = (
            f"Steiger: wrote the script '{SCRIPT_NAME}' ('{self.command}') into "
            f"{_PACKAGE_JSON}, the file-level half of the FSD rules"
        )
        if self.missing:
            said += (
                f"; install it with `npm install -D {' '.join(self.missing)}` and add a "
                "steiger.config.js with the plugin's recommended set"
            )
        return said


def _command(fsd_root: str) -> str:
    return f"{_STEIGER} ./{fsd_root}" if fsd_root else f"{_STEIGER} ."


def _declared_packages(package: dict[str, object]) -> set[str]:
    declared: set[str] = set()
    for key in ("dependencies", "devDependencies"):
        block = package.get(key)
        if isinstance(block, dict):
            declared.update(str(name) for name in block)
    return declared


def _running_steiger(scripts: dict[str, object]) -> str:
    """The script already holding the name, or running Steiger; ``""`` when none does."""
    if SCRIPT_NAME in scripts:
        return SCRIPT_NAME
    for name, command in scripts.items():
        if isinstance(command, str) and _STEIGER in command.split():
            return name
    return ""


def _indent_of(text: str) -> str:
    """The indentation *text* is written in: the leading whitespace of its second line."""
    lines = text.splitlines()
    if len(lines) < 2:
        return _DEFAULT_INDENT
    second = lines[1]
    return second[: len(second) - len(second.lstrip(" \t"))] or _DEFAULT_INDENT


def _write_back(path: Path, package: dict[str, object], indent: str) -> None:
    """Write *package* to *path* whole, in *indent*, keeping the file's permissions."""
    mode = stat.S_IMODE(path.stat().st_mode)
    write_text_atomic(path, json.dumps(package, indent=indent, ensure_ascii=False) + "\n")
    path.chmod(mode)


def ensure_steiger_script(project_root: Path, fsd_root: str) -> SteigerScript:
    """Write ``lint:fsd`` into *project_root*'s ``package.json`` unless a script runs Steiger.

    *fsd_root* is the project-relative folder holding the FSD layers, ``""`` for the root.
    """
    path = project_root / _PACKAGE_JSON
    if not path.is_file():
        return SteigerScript()
    try:
        text = path.read_text(encoding="utf-8")
        package = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return SteigerScript(unreadable=f"not readable as JSON: {error}")
    if not isinstance(package, dict):
        return SteigerScript(unreadable="not a JSON object")
    scripts = package.get("scripts")
    if scripts is None:
        scripts = {}
    if not isinstance(scripts, dict):
        return SteigerScript(unreadable="its 'scripts' is not an object")
    kept = _running_steiger(scripts)
    if kept:
        return SteigerScript(kept=kept)
    command = _command(fsd_root)
    package["scripts"] = {**scripts, SCRIPT_NAME: command}
    _write_back(path, package, _indent_of(text))
    declared = _declared_packages(package)
    missing = tuple(name for name in _PACKAGES if name not in declared)
    return SteigerScript(written=True, command=command, missing=missing)
