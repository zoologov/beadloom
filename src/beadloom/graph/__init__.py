"""Graph domain — YAML loader, diff, rule engine, import resolver, linter, snapshots."""

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
    get_node_tags,
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
    load_rules_with_tags,
    validate_rules,
)
from beadloom.graph.snapshot import (
    SnapshotDiff,
    SnapshotInfo,
    compare_snapshots,
    list_snapshots,
    save_snapshot,
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
    "SnapshotDiff",
    "SnapshotInfo",
    "Violation",
    "compare_snapshots",
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
    "get_node_tags",
    "index_imports",
    "lint",
    "list_snapshots",
    "load_graph",
    "load_rules",
    "load_rules_with_tags",
    "parse_graph_file",
    "render_diff",
    "resolve_import_to_node",
    "save_snapshot",
    "update_node_in_yaml",
    "validate_rules",
]
