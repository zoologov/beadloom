"""The name a composition of ``CLAUDE.md`` takes for the project, and what declared it.

The shipped core carries a neutral token in its ``## 0.1 Project:`` heading, and
the composer fills in the project's name. Until BDL-083 S2c that name came from a
root manifest or, failing one, from the directory the files sat in, so a project
that names itself in no root manifest composed one body in its main checkout and
was compared against another in a ``git worktree`` and in a clean room of the
same files (measured on a copy of the monorepo fixture: ``config-check`` rc 0, 1
and 1; BDL-UX #334).

The name is now read from what the project declares, in this order:

1. ``.beadloom/config.yml`` ``project_name:`` (RFC D7);
2. a root manifest (``pyproject.toml``, ``package.json``, ``go.mod``, ``Cargo.toml``);
3. the name the project's last composition wrote into the heading of
   ``.claude/CLAUDE.md`` (or of the Cursor core rule) — a tracked file, so the
   checkout, a worktree and a room read the same name;
4. the directory's name, which only a first composition of a project that
   declares nothing can reach.

Only the first two are a declaration. The third is a record, so the heading's
name is not compared by ``config-check`` there, and the report says so.
"""

# beadloom:domain=onboarding
# beadloom:component=project-name

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from beadloom.onboarding.scanner import manifest_project_name
from beadloom.onboarding.tool_reach import cursor_core_rule_relpath

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The ``.beadloom/config.yml`` key a project declares its name under.
PROJECT_NAME_KEY = "project_name"

#: The token the shipped core carries where the project's name goes.
PROJECT_NAME_PLACEHOLDER = "__BEADLOOM_PROJECT_NAME__"

#: The text before the token on the core's project heading line. A test holds
#: the shipped core to it, so the reader cannot drift from the writer.
PROJECT_HEADING_PREFIX = "## 0.1 Project: "

#: The source named when nothing declared or recorded a name.
DIRECTORY_SOURCE = "the directory's name"

_CONFIG_RELPATH = ".beadloom/config.yml"
_CLAUDE_RELPATH = ".claude/CLAUDE.md"


@dataclass(frozen=True)
class ProjectName:
    """A project's name for a composition and where it was read.

    ``declared`` is ``True`` when the project states the name itself
    (``config.yml`` or a root manifest), ``False`` when it is a record of an
    earlier composition or the directory's name.
    """

    value: str
    source: str
    declared: bool


def composition_project_name(project_root: Path) -> ProjectName:
    """The name a composition of ``CLAUDE.md`` takes for *project_root*."""
    configured = _configured_name(project_root)
    if configured is not None:
        return ProjectName(configured, f"{_CONFIG_RELPATH} ({PROJECT_NAME_KEY}:)", True)
    manifest = manifest_project_name(project_root)
    if manifest is not None:
        return ProjectName(manifest[0], manifest[1], True)
    for relpath in (_CLAUDE_RELPATH, str(cursor_core_rule_relpath())):
        recorded = _recorded_name(project_root / relpath)
        if recorded is not None:
            return ProjectName(
                recorded, f"{relpath}, the heading its last composition wrote", False
            )
    return ProjectName(project_root.resolve().name, DIRECTORY_SOURCE, False)


def _configured_name(project_root: Path) -> str | None:
    """``project_name:`` from ``.beadloom/config.yml``, or ``None`` when it names none."""
    path = project_root / _CONFIG_RELPATH
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        logger.warning("Cannot read %s for the project name: %s", path, exc)
        return None
    value = data.get(PROJECT_NAME_KEY) if isinstance(data, dict) else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _recorded_name(path: Path) -> str | None:
    """The name a composed file's project heading carries, or ``None``."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        if line.startswith(PROJECT_HEADING_PREFIX):
            name = line[len(PROJECT_HEADING_PREFIX) :].strip()
            if name and name != PROJECT_NAME_PLACEHOLDER:
                return name
            return None
    return None
