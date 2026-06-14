"""Onboarding domain — project bootstrap, doc import, and presets."""

from beadloom.onboarding.config_sync import ConfigDrift, check_config_drift
from beadloom.onboarding.doc_generator import generate_polish_data, generate_skeletons
from beadloom.onboarding.flow_config import (
    FlowConfig,
    FlowConfigError,
    build_flow_config,
    detect_stack,
    load_flow_config,
    load_flow_config_or_default,
    resolve_flow_config,
)
from beadloom.onboarding.presets import (
    MICROSERVICES,
    MONOLITH,
    MONOREPO,
    PRESETS,
    Preset,
    PresetRule,
    detect_preset,
)
from beadloom.onboarding.role_adapters import (
    AdapterResult,
    generate_adapters,
)
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    compose_all_roles,
    compose_role,
)
from beadloom.onboarding.scanner import (
    auto_link_docs,
    bootstrap_project,
    classify_doc,
    generate_agents_md,
    generate_rules,
    import_docs,
    interactive_init,
    non_interactive_init,
    prime_context,
    refresh_claude_md,
    scan_project,
    setup_mcp_auto,
    setup_rules_auto,
)

__all__ = [
    "MICROSERVICES",
    "MONOLITH",
    "MONOREPO",
    "PRESETS",
    "ROLE_NAMES",
    "AdapterResult",
    "ConfigDrift",
    "FlowConfig",
    "FlowConfigError",
    "Preset",
    "PresetRule",
    "auto_link_docs",
    "bootstrap_project",
    "build_flow_config",
    "check_config_drift",
    "classify_doc",
    "compose_all_roles",
    "compose_role",
    "detect_preset",
    "detect_stack",
    "generate_adapters",
    "generate_agents_md",
    "generate_polish_data",
    "generate_rules",
    "generate_skeletons",
    "import_docs",
    "interactive_init",
    "load_flow_config",
    "load_flow_config_or_default",
    "non_interactive_init",
    "prime_context",
    "refresh_claude_md",
    "resolve_flow_config",
    "scan_project",
    "setup_mcp_auto",
    "setup_rules_auto",
]
