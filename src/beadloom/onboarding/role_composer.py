# beadloom:domain=onboarding
# beadloom:feature=role-composer
"""Compose role files from CORE + architecture + stack + project layers.

A role file is no longer one monolith. It is assembled deterministically from:

* **CORE** — the universal role protocol (stack/tool-neutral): the single
  source of truth under ``templates/roles/core/<role>.md.txt``.
* one **ARCHITECTURE** overlay — ``ddd`` or ``fsd`` (peers): the methodology's
  layer/boundary rules + the ``# beadloom:`` annotation vocabulary, under
  ``templates/roles/architecture/<arch>/<role>.md.txt``.
* one+ **STACK** overlays — ``python`` / ``fastapi`` / ``javascript`` /
  ``typescript`` / ``vuejs``: the stack idioms + lint/type/test commands, under
  ``templates/roles/stack/<stack>/<role>.md.txt``.

* the **shared CORE fragments** (:data:`SHARED_ROLE_FRAGMENTS`) — today the
  writing standard, composed into every role straight after its own core, so the
  roles that produce TO-BE documents are held to the same bar as the one that
  produces AS-IS documents. Language-selectable like every other layer (#136).

* a **PROJECT** fragment at ``.beadloom/flow/roles/<role>.md`` in the adopting
  repo — the supported place for a team's standing practices, appended last
  (BDL-061 S3; BDL-UX #139, #152).

:func:`compose_role` concatenates those layers in a fixed, deterministic order
(stack overlays sorted, project last), so the same inputs always yield
byte-identical output. That determinism is what the drift-guard leans on: every
generated adapter must equal ``compose_role(...)`` for the repo's ``flow.yml``
**and** its project layer — which is why a project extension no longer trips
``config-check`` while a change to a shipped fragment still does.

Not every overlay has a fragment for every role (e.g. a framework overlay may
only refine the dev/test roles); a missing fragment contributes nothing, so an
overlay is additive and never breaks an unrelated role.

**A role exists because a core fragment ships for it** (BDL-068 S1.5). The role
population used to be two hand-maintained literals of one fact — ``ROLE_NAMES``
here and ``agentic_flow_setup.AGENT_FILES``, whose own comment said it mirrored
this one — with eight readers between them. Adding a fifth role meant editing
both, and a fifth role added to one is exactly the fifth thing that can drift
(BDL-UX #191's shape). :func:`roles_in` derives the population from the shipped
CORE fragments instead, over a SHAPE rather than a spelling: a fragment is a
role when it opens with front matter naming itself, which is already the stated
difference between a role and the shared ``_writing`` LAYER. Dropping
``explore.md.txt`` into ``roles/core/`` therefore makes ``explore`` a role in
every reader by the same act.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from beadloom.onboarding.composer import (
    SHARED_ROLE_FRAGMENTS,
    compose,
    templates_dir,
)
from beadloom.onboarding.flow_config import (
    DEFAULT_LANGUAGE,
    SUPPORTED_ARCHITECTURES,
    SUPPORTED_STACKS,
    FlowConfig,
    FlowConfigError,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.flow_suppression import FlowSuppression

__all__ = [
    "ROLE_NAMES",
    "SHARED_ROLE_FRAGMENTS",
    "compose_all_roles",
    "compose_role",
    "roles_in",
    "roles_templates_root",
]

#: The suffix every shipped fragment carries.
_FRAGMENT_SUFFIX = ".md.txt"

#: A fragment's opening front matter, and the ``name:`` inside it. This is the
#: SHAPE that separates a role from a layer: every role file is an agent
#: definition and every agent definition declares its own name, while
#: ``_writing`` has no front matter at all. Matching the shape rather than the
#: ``_`` prefix means a layer that forgets the prefix is still a layer.
_FRONT_MATTER_RE = re.compile(
    r"\A\s*---\n(?P<body>.*?)\n---\s*(\n|\Z)", re.DOTALL
)
_NAME_RE = re.compile(r"^name:\s*(?P<name>\S+)\s*$", re.MULTILINE)


def roles_templates_root() -> Path:
    """Directory holding the CORE + overlay role-source fragments."""
    return templates_dir() / "roles"


def fragment_role_name(text: str) -> str | None:
    """The role a CORE fragment declares itself to be, or ``None`` for a layer.

    A layer contributes text to every role and is never written as an adapter,
    so it declares no name — which is what makes the front matter the honest
    discriminator rather than a filename convention.
    """
    front = _FRONT_MATTER_RE.match(text)
    if front is None:
        return None
    named = _NAME_RE.search(front.group("body"))
    return named.group("name") if named is not None else None


def roles_in(core_dir: Path) -> tuple[str, ...]:
    """Every role a directory of CORE fragments ships, in deterministic order.

    Sorted, because the order is read by generators whose output must be
    byte-identical between runs, and a directory listing is not ordered.

    A fragment counts only when its front matter names its own file. The two
    spellings are what every reader keys on, so a fragment that disagrees with
    itself would compose under one name and be written under another. The same
    rule is what keeps a localisation from being a second role: ``scout.ru``
    declares ``name: scout``, which is not the name of its file. That was a
    separate guard until a mutant showed it could not be made to fail — a guard
    nobody can demonstrate is a guard nobody can argue with.
    """
    found: list[str] = []
    for path in sorted(core_dir.glob(f"*{_FRAGMENT_SUFFIX}")):
        name = path.name[: -len(_FRAGMENT_SUFFIX)]
        declared = fragment_role_name(path.read_text(encoding="utf-8"))
        if declared == name:
            found.append(name)
    return tuple(found)


#: Canonical role names, DERIVED from the shipped CORE fragments rather than
#: declared. ``agentic_flow_setup.AGENT_FILES`` is this same tuple, not a copy
#: of it.
ROLE_NAMES: tuple[str, ...] = roles_in(templates_dir() / "roles" / "core")


def compose_role(
    role: str,
    *,
    architecture: str,
    stack: tuple[str, ...] | list[str],
    language: str = DEFAULT_LANGUAGE,
    suppressions: tuple[FlowSuppression, ...] = (),
    project_root: Path | None = None,
) -> str:
    """Compose one role file from CORE + architecture + stack + project layers.

    The output is ``CORE`` then the single ``architecture`` overlay, then each
    ``stack`` overlay in **sorted** order, then the project fragment at
    ``.beadloom/flow/roles/<role>.md`` when ``project_root`` is given —
    deterministic for a given input. Raises :class:`FlowConfigError` for an
    unknown role / architecture / stack (so a bad compose request is loud, not
    a silently-empty file).

    The layering itself lives in :mod:`beadloom.onboarding.composer`, which is
    the single implementation shared by roles, commands and ``CLAUDE.md``; this
    function is the roles-shaped door onto it.
    """
    if role not in ROLE_NAMES:
        msg = f"compose_role: unknown role {role!r} — allowed: {list(ROLE_NAMES)}"
        raise FlowConfigError(msg)
    if architecture not in SUPPORTED_ARCHITECTURES:
        msg = (
            f"compose_role: unknown architecture {architecture!r} — "
            f"allowed: {list(SUPPORTED_ARCHITECTURES)}"
        )
        raise FlowConfigError(msg)
    unknown = [s for s in stack if s not in SUPPORTED_STACKS]
    if unknown:
        msg = (
            f"compose_role: unknown stack {unknown} — "
            f"allowed: {list(SUPPORTED_STACKS)}"
        )
        raise FlowConfigError(msg)

    config = FlowConfig(
        tools=("claude",),
        architecture=architecture,
        stack=tuple(stack),
        language=language,
        suppressions=suppressions,
    )
    return compose("roles", role, config=config, project_root=project_root).text


def compose_all_roles(
    config: FlowConfig, project_root: Path | None = None
) -> dict[str, str]:
    """Compose every role for a :class:`FlowConfig`, including the project layer.

    Returns ``{role: composed_text}`` for all :data:`ROLE_NAMES`, ready to be
    written into each configured tool's adapter directory. ``project_root`` is
    optional: omitting it yields the shipped-only composition, which is exactly
    the baseline a repo without a project layer is checked against.
    """
    return {
        role: compose("roles", role, config=config, project_root=project_root).text
        for role in ROLE_NAMES
    }
