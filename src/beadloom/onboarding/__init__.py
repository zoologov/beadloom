"""Onboarding domain — project bootstrap, doc import, and presets."""

from beadloom.onboarding.doc_generator import generate_polish_data, generate_skeletons
from beadloom.onboarding.presets import (
    MICROSERVICES,
    MONOLITH,
    MONOREPO,
    PRESETS,
    Preset,
    PresetRule,
    detect_preset,
)
from beadloom.onboarding.scanner import (
    bootstrap_project,
    classify_doc,
    generate_agents_md,
    generate_rules,
    import_docs,
    interactive_init,
    non_interactive_init,
    prime_context,
    scan_project,
    setup_mcp_auto,
    setup_rules_auto,
)

__all__ = [
    "MICROSERVICES",
    "MONOLITH",
    "MONOREPO",
    "PRESETS",
    "Preset",
    "PresetRule",
    "bootstrap_project",
    "classify_doc",
    "detect_preset",
    "generate_agents_md",
    "generate_polish_data",
    "generate_rules",
    "generate_skeletons",
    "import_docs",
    "interactive_init",
    "non_interactive_init",
    "prime_context",
    "scan_project",
    "setup_mcp_auto",
    "setup_rules_auto",
]
