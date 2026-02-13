"""Graph domain — YAML loader, diff, rule engine, import resolver, linter."""

# beadloom:domain=graph

from beadloom.graph.diff import (
    EdgeChange,
    GraphDiff,
    NodeChange,
    compute_diff,
    diff_to_dict,
    render_diff,
)
from beadloom.graph.import_resolver import (
    ImportInfo,
    create_import_edges,
    extract_imports,
    index_imports,
    resolve_import_to_node,
)
from beadloom.graph.linter import (
    LintError,
    LintResult,
    format_json,
    format_porcelain,
    format_rich,
    lint,
)
from beadloom.graph.loader import (
    GraphLoadResult,
    ParsedFile,
    load_graph,
    parse_graph_file,
    update_node_in_yaml,
)
from beadloom.graph.rule_engine import (
    DenyRule,
    NodeMatcher,
    RequireRule,
    Rule,
    Violation,
    evaluate_all,
    evaluate_deny_rules,
    evaluate_require_rules,
    load_rules,
    validate_rules,
)

__all__ = [
    "DenyRule",
    "EdgeChange",
    "GraphDiff",
    "GraphLoadResult",
    "ImportInfo",
    "LintError",
    "LintResult",
    "NodeChange",
    "NodeMatcher",
    "ParsedFile",
    "RequireRule",
    "Rule",
    "Violation",
    "compute_diff",
    "create_import_edges",
    "diff_to_dict",
    "evaluate_all",
    "evaluate_deny_rules",
    "evaluate_require_rules",
    "extract_imports",
    "format_json",
    "format_porcelain",
    "format_rich",
    "index_imports",
    "lint",
    "load_graph",
    "load_rules",
    "parse_graph_file",
    "render_diff",
    "resolve_import_to_node",
    "update_node_in_yaml",
    "validate_rules",
]
