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
    language: en                     # tag the flow's documents are written in
    overlays:
      suppress:                      # stand down a shipped core rule, declared
        - rule: "Anti-patterns / Shell"
          reason: "the team runs on Windows; the -f idiom does not apply"
          until: "a windows stack overlay ships"

For Beadloom itself: ``tools: [claude]``, ``architecture: [ddd]``,
``stack: [python]``.

Validation is strict and the errors are agent-actionable: an unknown tool,
architecture, or stack overlay raises :class:`FlowConfigError` naming the bad
value and the allowed set, so ``config-check`` can surface exactly what to fix.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from beadloom.onboarding.flow_suppression import (
    FlowSuppression,
    FlowSuppressionError,
    build_suppressions,
)

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

#: Language every shipped fragment is authored in; the composer falls back to
#: it and says so when a requested localisation is not shipped (BDL-UX #136).
DEFAULT_LANGUAGE = "en"

#: A language tag is validated for SHAPE, not against a closed list: the set of
#: languages a team writes in is not ours to enumerate, and rejecting an unlisted
#: one would push the project straight back to hand-editing.
_LANGUAGE_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")

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
    language:
        BCP-47-ish tag the flow's documents and role standards are written in
        (default :data:`DEFAULT_LANGUAGE`). A team writing in Russian is held to
        the standard in Russian, or told which fragment is missing.
    suppressions:
        Declared stand-downs of shipped core rules — each with a reason and an
        exit condition, appended to every composition as a visible notice.
    """

    tools: tuple[str, ...]
    architecture: str
    stack: tuple[str, ...]
    quality: tuple[str, ...] = ()
    language: str = DEFAULT_LANGUAGE
    suppressions: tuple[FlowSuppression, ...] = field(default_factory=tuple)


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


def _validate_language(value: object) -> str:
    """Validate the ``language`` tag's shape (absent → :data:`DEFAULT_LANGUAGE`)."""
    if value is None:
        return DEFAULT_LANGUAGE
    if not isinstance(value, str) or not _LANGUAGE_RE.match(value.strip()):
        msg = (
            f"flow.yml: 'language' must be a language tag like 'en', 'ru' or "
            f"'pt-BR', got {value!r}"
        )
        raise FlowConfigError(msg)
    return value.strip()


def _validate_suppressions(overlays: object) -> tuple[FlowSuppression, ...]:
    """Validate ``overlays.suppress`` (absent → empty).

    Re-raised as :class:`FlowConfigError` so ``config-check`` reports a bad
    suppression through the same channel as every other flow.yml defect.
    """
    if overlays is None:
        return ()
    if not isinstance(overlays, dict):
        msg = "flow.yml: 'overlays' must be a mapping"
        raise FlowConfigError(msg)
    unknown = sorted(str(k) for k in overlays if k != "suppress")
    if unknown:
        msg = (
            f"flow.yml: 'overlays' has unknown key(s) {unknown} — allowed: "
            "['suppress']. Project ADDITIONS are files under .beadloom/flow/, "
            "not keys here: overlays are append-only"
        )
        raise FlowConfigError(msg)
    try:
        return build_suppressions(overlays.get("suppress"))
    except FlowSuppressionError as exc:
        raise FlowConfigError(str(exc)) from exc


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
        language=_validate_language(data.get("language")),
        suppressions=_validate_suppressions(data.get("overlays")),
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


def persist_flow_config(project_root: Path, config: FlowConfig) -> Path | None:
    """Write ``config`` to ``.beadloom/flow.yml`` — only when there is none.

    A scaffold used to compose every artifact from a config it resolved in
    memory and never wrote down, so ``config-check`` took its no-``flow.yml``
    branch, expected the plain vendored role files, and reported four errors on
    an untouched repository (BDL-UX #187). The command's own closing advice
    pointed at that check, and the remediation it printed named the command the
    adopter had just run.

    Returns the path written, or ``None`` when a config already exists. An
    existing ``flow.yml`` is **never** rewritten: it is the adopter's policy
    file — ``language`` and ``overlays.suppress`` have no flag and live only
    there — and a scaffold that overwrote it would be the data loss BDL-UX #186
    ended for the role adapters.
    """
    path = project_root / FLOW_CONFIG_RELPATH
    if path.is_file():
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(
        {
            "tools": list(config.tools),
            "architecture": [config.architecture],
            "stack": list(config.stack),
            "quality": list(config.quality),
            "language": config.language,
        },
        sort_keys=False,
        allow_unicode=True,
    )
    header = (
        "# Beadloom agentic-flow configuration — the selection every composed\n"
        "# artifact is built from. Written once by `beadloom setup-agentic-flow`\n"
        "# from what it detected; yours to edit, never rewritten.\n"
    )
    path.write_text(header + body, encoding="utf-8")
    return path


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

    resolved = build_flow_config(
        {
            "tools": list(eff_tools),
            "architecture": [eff_arch],
            "stack": list(eff_stack),
            "quality": list(eff_quality),
        }
    )
    if on_disk is None:
        return resolved
    # `language` and `overlays.suppress` have no flag: they are project policy,
    # not a per-run choice, so they are carried through from flow.yml verbatim.
    return replace(
        resolved, language=on_disk.language, suppressions=on_disk.suppressions
    )
