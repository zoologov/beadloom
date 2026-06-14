# beadloom:domain=onboarding
# beadloom:feature=role-composer
"""Compose role files from CORE + architecture + stack overlays (BDL-052 S3).

A role file is no longer one monolith. It is assembled deterministically from:

* **CORE** — the universal role protocol (stack/tool-neutral): the single
  source of truth under ``templates/roles/core/<role>.md.txt``.
* one **ARCHITECTURE** overlay — ``ddd`` or ``fsd`` (peers): the methodology's
  layer/boundary rules + the ``# beadloom:`` annotation vocabulary, under
  ``templates/roles/architecture/<arch>/<role>.md.txt``.
* one+ **STACK** overlays — ``python`` / ``fastapi`` / ``javascript`` /
  ``typescript`` / ``vuejs``: the stack idioms + lint/type/test commands, under
  ``templates/roles/stack/<stack>/<role>.md.txt``.

:func:`compose_role` concatenates ``CORE + architecture + stack`` in a fixed,
deterministic order (stack overlays sorted), so the same ``(role, architecture,
stack)`` always yields byte-identical output. That determinism is what the
drift-guard test leans on: every generated adapter must equal
``compose_role(...)`` for the repo's ``flow.yml``.

Not every overlay has a fragment for every role (e.g. a framework overlay may
only refine the dev/test roles); a missing fragment contributes nothing, so an
overlay is additive and never breaks an unrelated role.
"""

from __future__ import annotations

from pathlib import Path

from beadloom.onboarding.flow_config import (
    SUPPORTED_ARCHITECTURES,
    SUPPORTED_STACKS,
    FlowConfig,
    FlowConfigError,
)

#: Canonical role names (mirrors ``agentic_flow_setup.AGENT_FILES``).
ROLE_NAMES: tuple[str, ...] = ("dev", "test", "review", "tech-writer")


def roles_templates_root() -> Path:
    """Directory holding the CORE + overlay role-source fragments."""
    return Path(__file__).resolve().parent / "templates" / "roles"


def _core_path(role: str) -> Path:
    return roles_templates_root() / "core" / f"{role}.md.txt"


def _architecture_path(architecture: str, role: str) -> Path:
    return roles_templates_root() / "architecture" / architecture / f"{role}.md.txt"


def _stack_path(stack: str, role: str) -> Path:
    return roles_templates_root() / "stack" / stack / f"{role}.md.txt"


def _read_fragment(path: Path) -> str:
    """Read an overlay fragment; return ``""`` when the fragment is absent.

    A missing per-role fragment for an overlay is legitimate (the overlay does
    not refine that role) and contributes nothing to the composition.
    """
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def compose_role(
    role: str,
    *,
    architecture: str,
    stack: tuple[str, ...] | list[str],
) -> str:
    """Compose one role file from CORE + architecture + stack overlays.

    The output is ``CORE`` then the single ``architecture`` overlay then each
    ``stack`` overlay in **sorted** order — deterministic for a given
    ``(role, architecture, stack)``. Raises :class:`FlowConfigError` for an
    unknown role / architecture / stack (so a bad compose request is loud, not
    a silently-empty file). The CORE fragment is required; overlay fragments
    are optional per role.
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

    core_path = _core_path(role)
    if not core_path.is_file():
        msg = f"compose_role: missing CORE fragment for role {role!r} at {core_path}"
        raise FlowConfigError(msg)

    parts = [core_path.read_text(encoding="utf-8")]
    parts.append(_read_fragment(_architecture_path(architecture, role)))
    for stack_name in sorted(stack):
        parts.append(_read_fragment(_stack_path(stack_name, role)))
    return "".join(parts)


def compose_all_roles(config: FlowConfig) -> dict[str, str]:
    """Compose every role for a :class:`FlowConfig`'s architecture + stack.

    Returns ``{role: composed_text}`` for all :data:`ROLE_NAMES`, ready to be
    written into each configured tool's adapter directory.
    """
    return {
        role: compose_role(
            role, architecture=config.architecture, stack=config.stack
        )
        for role in ROLE_NAMES
    }
