"""Whether Beadloom's own surfaces describe the project being audited.

Two of the audit's declared facts are read out of the **running package**:
``mcp_tool_count`` comes from ``infrastructure.mcp_tools.MCP_TOOL_CATALOG`` and
``cli_command_count`` from the live Click group.  Both are correct statements
about Beadloom and false statements about anybody else, and until BDL-062 both
were collected unconditionally — so in every adopter repository ``docs audit``
declared two facts about the tool as facts about their documentation and counted
them in the denominator of "N of 9 verified" (measured: a project named
``invoice-svc`` was told it had 18 MCP tools and 43 CLI commands).

This module is the gate that decides.  A surface fact may be declared only when
the project under audit **is** the distribution whose surfaces we can introspect,
which is answered by the project's own manifest: the name it declares for itself
against the name of the running package.  Anything else gets the fact declined
with the reason, never a value.

The manifest is read here rather than reused from ``onboarding``'s project
scanner for two reasons.  A domain may not import a peer domain, and the
scanner's reader falls back to the **directory name** when no manifest declares
one — a fallback that would make any clone in a directory called ``beadloom``
identify as this distribution, which is the exact confusion this module exists
to refuse.  Unknown is not a match.
"""

# beadloom:feature=docs-audit

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The distribution whose surfaces this process can introspect, derived from the
#: package this module lives in rather than written out, so a rename cannot leave
#: the identity check comparing against a name that no longer exists.
RUNNING_DISTRIBUTION = __name__.split(".")[0]

_NAME_RE = re.compile(r'^\s*name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def declared_project_name(project_root: Path) -> str | None:
    """The name *project_root* declares for itself, or ``None`` if it declares none.

    Reads ``pyproject.toml`` (``[project]`` or ``[tool.poetry]``),
    ``package.json`` and ``Cargo.toml``, in that order.  There is deliberately no
    directory-name fallback: a project that names itself nowhere is unknown, and
    unknown must not resolve to a name the caller will compare for identity.
    """
    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        match = _NAME_RE.search(_read(pyproject))
        if match:
            return match.group(1)

    package_json = project_root / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(_read(package_json))
        except (json.JSONDecodeError, ValueError):
            logger.warning("Cannot parse %s for the project name", package_json)
            data = None
        if isinstance(data, dict):
            name = data.get("name")
            if name:
                return str(name).split("/")[-1]

    cargo = project_root / "Cargo.toml"
    if cargo.is_file():
        match = _NAME_RE.search(_read(cargo))
        if match:
            return match.group(1)

    return None


def foreign_project_reason(project_root: Path) -> str | None:
    """Why Beadloom's own surfaces do not describe *project_root* — ``None`` if they do.

    ``None`` means the project under audit is this distribution, so a count taken
    from the running package is a fact about that project.  A string is the
    reason it is not, phrased to be shown to the person reading the audit.
    """
    name = declared_project_name(project_root)
    if name is None:
        return "no manifest in this project declares a project name"
    if name == RUNNING_DISTRIBUTION:
        return None
    return f"this project declares itself as {name!r}, not {RUNNING_DISTRIBUTION!r}"


def _read(path: Path) -> str:
    """A manifest's text, or ``""`` when it cannot be decoded as UTF-8 or read.

    A manifest in another encoding leaves the project's name unknown, and
    unknown resolves to a declined fact with its reason — never to a match. The
    ``UnicodeDecodeError`` is caught beside ``OSError`` because ``read_text``
    raises it on the first non-UTF-8 byte, and an identity check must not fall
    over on a file it merely cannot read.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning("Cannot read %s", path)
        return ""
