"""Onboarding domain — project bootstrap, doc import, and presets."""

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
    import_docs,
    interactive_init,
    scan_project,
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
    "import_docs",
    "interactive_init",
    "scan_project",
]
