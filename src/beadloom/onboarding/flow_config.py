# beadloom:domain=onboarding
# beadloom:feature=flow-config
"""``.beadloom/flow.yml`` — the role-configurator config + loader (BDL-052 S3).

The agentic flow is no longer hardcoded to Python + Claude Code. A repo
declares its **tools**, **architecture methodology**, **stack/frameworks**, and
**quality bars** in ``.beadloom/flow.yml``; :func:`load_flow_config` reads +
validates it into an immutable :class:`FlowConfig`, and the composer
(:mod:`beadloom.onboarding.role_composer`) turns that into per-tool role
adapters (CORE + the selected architecture overlay + the selected stack
overlays).

Schema
------
.. code-block:: yaml

    tools: [claude, cursor]          # which IDE adapter sets to generate
    architecture: [ddd]              # exactly one methodology: ddd | fsd
    stack: [python, fastapi]         # one+ stack/framework overlays
    quality: [clean-code, tdd]       # quality bars (informational)

For Beadloom itself: ``tools: [claude]``, ``architecture: [ddd]``,
``stack: [python]``.

Validation is strict and the errors are agent-actionable: an unknown tool,
architecture, or stack overlay raises :class:`FlowConfigError` naming the bad
value and the allowed set, so ``config-check`` can surface exactly what to fix.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

#: Tool adapters Beadloom can generate (each writes a per-tool role-file set).
SUPPORTED_TOOLS: tuple[str, ...] = ("claude", "cursor")

#: Architecture methodologies available as role overlays (peers — pick one).
SUPPORTED_ARCHITECTURES: tuple[str, ...] = ("ddd", "fsd")

#: Stack/framework overlays available (a subset is selected per repo).
SUPPORTED_STACKS: tuple[str, ...] = (
    "python",
    "fastapi",
    "javascript",
    "typescript",
    "vuejs",
)

#: Quality bars (informational — recorded, not yet overlay-bearing).
SUPPORTED_QUALITY: tuple[str, ...] = ("clean-code", "tdd")

#: Config path relative to the project root.
FLOW_CONFIG_RELPATH = Path(".beadloom") / "flow.yml"


class FlowConfigError(ValueError):
    """A ``.beadloom/flow.yml`` that is malformed or names an unknown value.

    The message always names the offending value and the allowed set so the
    fix is mechanical (surfaced by ``config-check``).
    """


@dataclass(frozen=True)
class FlowConfig:
    """A validated ``.beadloom/flow.yml`` — the role-configurator inputs.

    Attributes
    ----------
    tools:
        Tool adapter sets to generate (subset of :data:`SUPPORTED_TOOLS`).
    architecture:
        Exactly one methodology from :data:`SUPPORTED_ARCHITECTURES`.
    stack:
        One+ overlays from :data:`SUPPORTED_STACKS`, deterministically ordered.
    quality:
        Quality bars from :data:`SUPPORTED_QUALITY` (informational).
    """

    tools: tuple[str, ...]
    architecture: str
    stack: tuple[str, ...]
    quality: tuple[str, ...] = ()


def _as_str_list(value: object, *, key: str) -> list[str]:
    """Coerce a YAML scalar/sequence into a list of strings (or raise)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return list(value)
    msg = f"flow.yml: '{key}' must be a string or a list of strings"
    raise FlowConfigError(msg)


def _validate_subset(
    values: list[str], *, allowed: tuple[str, ...], key: str
) -> tuple[str, ...]:
    """Validate every value is in ``allowed``; return them de-duped + sorted.

    Order is normalized (sorted) so the composition is deterministic regardless
    of the order the user listed the overlays.
    """
    unknown = [v for v in values if v not in allowed]
    if unknown:
        msg = (
            f"flow.yml: unknown {key} {unknown} — "
            f"allowed: {list(allowed)}"
        )
        raise FlowConfigError(msg)
    return tuple(sorted(set(values)))


def _validate_architecture(values: list[str]) -> str:
    """Architecture must be exactly one known methodology (ddd or fsd)."""
    if len(values) != 1:
        msg = (
            "flow.yml: 'architecture' must name exactly one methodology "
            f"(one of {list(SUPPORTED_ARCHITECTURES)}), got {values}"
        )
        raise FlowConfigError(msg)
    arch = values[0]
    if arch not in SUPPORTED_ARCHITECTURES:
        msg = (
            f"flow.yml: unknown architecture {arch!r} — "
            f"allowed: {list(SUPPORTED_ARCHITECTURES)}"
        )
        raise FlowConfigError(msg)
    return arch


def build_flow_config(data: object) -> FlowConfig:
    """Validate a parsed YAML mapping into a :class:`FlowConfig`.

    Raises :class:`FlowConfigError` on anything malformed (non-mapping, unknown
    tool/architecture/stack, empty required field).
    """
    if not isinstance(data, dict):
        msg = "flow.yml: top-level content must be a mapping"
        raise FlowConfigError(msg)

    tools = _validate_subset(
        _as_str_list(data.get("tools"), key="tools"),
        allowed=SUPPORTED_TOOLS,
        key="tool(s)",
    )
    if not tools:
        msg = (
            "flow.yml: 'tools' is required and must name at least one of "
            f"{list(SUPPORTED_TOOLS)}"
        )
        raise FlowConfigError(msg)

    architecture = _validate_architecture(
        _as_str_list(data.get("architecture"), key="architecture")
    )

    stack = _validate_subset(
        _as_str_list(data.get("stack"), key="stack"),
        allowed=SUPPORTED_STACKS,
        key="stack overlay(s)",
    )
    if not stack:
        msg = (
            "flow.yml: 'stack' is required and must name at least one of "
            f"{list(SUPPORTED_STACKS)}"
        )
        raise FlowConfigError(msg)

    quality = _validate_subset(
        _as_str_list(data.get("quality"), key="quality"),
        allowed=SUPPORTED_QUALITY,
        key="quality bar(s)",
    )

    return FlowConfig(
        tools=tools,
        architecture=architecture,
        stack=stack,
        quality=quality,
    )


def load_flow_config(project_root: Path) -> FlowConfig:
    """Load + validate ``<project_root>/.beadloom/flow.yml``.

    Raises :class:`FileNotFoundError` if the config is absent and
    :class:`FlowConfigError` if it is malformed. Callers that want a default
    when the file is absent should use :func:`load_flow_config_or_default`.
    """
    path = project_root / FLOW_CONFIG_RELPATH
    if not path.is_file():
        msg = f"flow.yml not found at {path}"
        raise FileNotFoundError(msg)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        msg = f"flow.yml: invalid YAML — {exc}"
        raise FlowConfigError(msg) from exc
    return build_flow_config(data)


def load_flow_config_or_default(
    project_root: Path, *, default: FlowConfig
) -> FlowConfig:
    """Load ``flow.yml`` if present, else return ``default``.

    A malformed present config still raises :class:`FlowConfigError` (the
    config-check signal) — only an *absent* config falls back to the default.
    """
    path = project_root / FLOW_CONFIG_RELPATH
    if not path.is_file():
        return default
    return load_flow_config(project_root)


#: File extension → stack overlay, for auto-detecting the default stack.
_EXTENSION_STACK: tuple[tuple[str, str], ...] = (
    (".py", "python"),
    (".ts", "typescript"),
    (".vue", "vuejs"),
    (".js", "javascript"),
)


def detect_stack(project_root: Path) -> tuple[str, ...]:
    """Best-effort default stack from source file extensions under the root.

    Walks ``src``/``app``/the root for known extensions and maps them to stack
    overlays (deterministically ordered). Falls back to ``("python",)`` when
    nothing recognizable is found — a safe, non-empty default the composer
    accepts. This is only the *default* when neither ``flow.yml`` nor explicit
    flags name a stack.
    """
    found: set[str] = set()
    search_dirs = [project_root / "src", project_root / "app", project_root]
    for base in search_dirs:
        if not base.is_dir():
            continue
        for ext, stack in _EXTENSION_STACK:
            if any(base.rglob(f"*{ext}")):
                found.add(stack)
    if not found:
        return ("python",)
    return tuple(sorted(found))


def resolve_flow_config(
    project_root: Path,
    *,
    tools: tuple[str, ...] = (),
    architecture: str | None = None,
    stack: tuple[str, ...] = (),
) -> FlowConfig:
    """Resolve the effective :class:`FlowConfig` for a setup/compose run.

    Precedence: an explicit flag overrides the corresponding ``flow.yml`` field;
    fields neither flagged nor present in ``flow.yml`` fall back to the defaults
    (``tools=[claude]``, ``architecture=ddd``, ``stack=`` auto-detected). A
    present-but-malformed ``flow.yml`` still raises :class:`FlowConfigError`.
    Returns a fully validated config (built via :func:`build_flow_config`).
    """
    on_disk: FlowConfig | None = None
    if (project_root / FLOW_CONFIG_RELPATH).is_file():
        on_disk = load_flow_config(project_root)

    eff_tools = tools or (on_disk.tools if on_disk else ("claude",))
    eff_arch = architecture or (on_disk.architecture if on_disk else "ddd")
    eff_stack = stack or (on_disk.stack if on_disk else detect_stack(project_root))
    eff_quality = on_disk.quality if on_disk else ()

    return build_flow_config(
        {
            "tools": list(eff_tools),
            "architecture": [eff_arch],
            "stack": list(eff_stack),
            "quality": list(eff_quality),
        }
    )
