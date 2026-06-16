"""Onboarding scanner — project bootstrap, doc import, and initialization.

Cohesion-driven package (BDL-059 S4): the former 2.7k-LOC ``scanner.py`` split
by responsibility into focused submodules. This ``__init__`` re-exports the full
public surface so existing ``from beadloom.onboarding.scanner import X`` imports
keep working unchanged.
"""

# beadloom:domain=onboarding

from beadloom.onboarding.scanner.agents_md import (
    _BEADLOOM_ADAPTER_MARKERS,
    _RULES_ADAPTER_TEMPLATE,
    _RULES_CONFIGS,
    _build_mcp_tools_section,
    _build_rules_section,
    _extract_agents_custom_content,
    _is_beadloom_adapter,
    build_agents_md_content,
    generate_agents_md,
    setup_mcp_auto,
    setup_rules_auto,
)
from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.onboarding.scanner.claude_md import (
    _auto_insert_markers,
    _parse_markers,
    _render_project_info_section,
    refresh_claude_md,
)
from beadloom.onboarding.scanner.constants import (
    _CODE_EXTENSIONS,
    _MANIFESTS,
    _SOURCE_DIRS,
    _is_in_skip_dir,
    _sanitize_ref_id,
)
from beadloom.onboarding.scanner.doc_classify import (
    auto_link_docs,
    classify_doc,
    import_docs,
)
from beadloom.onboarding.scanner.entry_points import _discover_entry_points
from beadloom.onboarding.scanner.import_scan import _MAX_IMPORT_EDGES, _quick_import_scan
from beadloom.onboarding.scanner.init_flow import (
    _format_review_table,
    interactive_init,
    non_interactive_init,
)
from beadloom.onboarding.scanner.prime import prime_context
from beadloom.onboarding.scanner.project_scan import (
    _cluster_by_dirs,
    _cluster_with_children,
    _detect_project_name,
    _read_manifest_deps,
    scan_project,
)
from beadloom.onboarding.scanner.readme import (
    _detect_tech_stack,
    _extract_first_paragraph,
    _extract_non_heading_content,
    _ingest_readme,
)
from beadloom.onboarding.scanner.rules_gen import (
    _detect_rule_type,
    _read_rules_data,
    generate_rules,
)
from beadloom.onboarding.scanner.summary import (
    _build_contextual_summary,
    _detect_framework_summary,
)

# The public surface is the un-underscored names. The underscore-prefixed
# entries are internal helpers re-exported only to preserve the historical
# ``from beadloom.onboarding.scanner import _helper`` import paths used by the
# test suite and a few in-package callers (behavior-preserving split, BDL-059).
__all__ = [
    "_BEADLOOM_ADAPTER_MARKERS",
    "_CODE_EXTENSIONS",
    "_MANIFESTS",
    "_MAX_IMPORT_EDGES",
    "_RULES_ADAPTER_TEMPLATE",
    "_RULES_CONFIGS",
    "_SOURCE_DIRS",
    "_auto_insert_markers",
    "_build_contextual_summary",
    "_build_mcp_tools_section",
    "_build_rules_section",
    "_cluster_by_dirs",
    "_cluster_with_children",
    "_detect_framework_summary",
    "_detect_project_name",
    "_detect_rule_type",
    "_detect_tech_stack",
    "_discover_entry_points",
    "_extract_agents_custom_content",
    "_extract_first_paragraph",
    "_extract_non_heading_content",
    "_format_review_table",
    "_ingest_readme",
    "_is_beadloom_adapter",
    "_is_in_skip_dir",
    "_parse_markers",
    "_quick_import_scan",
    "_read_manifest_deps",
    "_read_rules_data",
    "_render_project_info_section",
    "_sanitize_ref_id",
    "auto_link_docs",
    "bootstrap_project",
    "build_agents_md_content",
    "classify_doc",
    "generate_agents_md",
    "generate_rules",
    "import_docs",
    "interactive_init",
    "non_interactive_init",
    "prime_context",
    "refresh_claude_md",
    "scan_project",
    "setup_mcp_auto",
    "setup_rules_auto",
]
