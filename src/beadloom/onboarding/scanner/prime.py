"""Compact project context for AI agent injection (`beadloom prime`)."""

# beadloom:domain=onboarding
# beadloom:feature=agent-prime

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from beadloom.onboarding.scanner.project_scan import _detect_project_name
from beadloom.onboarding.scanner.rules_gen import _read_rules_data

if TYPE_CHECKING:
    from pathlib import Path


def _get_lint_violations(project_root: Path) -> list[dict[str, str]]:
    """Get lint violations without reindexing (fast path)."""
    try:
        from beadloom.graph.linter import lint as run_lint

        result = run_lint(project_root)
        return [
            {
                "rule": v.rule_name,
                "node": v.from_ref_id or "",
                "message": v.message,
            }
            for v in result.violations
        ]
    except Exception:  # graceful degradation
        return []


def _format_prime_markdown(
    project_name: str,
    rules: list[dict[str, str]],
    dynamic: dict[str, Any],
) -> str:
    """Format prime context as compact Markdown."""
    lines: list[str] = [f"# Project: {project_name}", ""]

    if not dynamic:
        lines.append("Warning: Database not found. Run `beadloom reindex` for full context.")
        lines.append("")
    else:
        # Architecture summary
        kc: dict[str, int] = dynamic["kind_counts"]
        parts: list[str] = []
        for kind in ("domain", "service", "feature", "entity"):
            count = kc.get(kind, 0)
            if count:
                parts.append(f"{count} {kind}s")
        arch_str = ", ".join(parts) if parts else "no nodes"
        lines.append(f"Architecture: {arch_str} | {dynamic['symbols']} symbols")

        stale_count = len(dynamic.get("stale_docs", []))
        violations_count = len(dynamic.get("violations", []))
        last_reindex = dynamic.get("last_reindex", "never")
        lines.append(
            f"Health: {stale_count} stale docs,"
            f" {violations_count} lint violations"
            f" | Last reindex: {last_reindex}"
        )
        lines.append("")

    # Architecture Rules
    if rules:
        lines.append("## Architecture Rules")
        for rule in rules:
            desc = rule["description"]
            if desc:
                lines.append(f"- {rule['name']} ({rule['type']}): {desc}")
            else:
                lines.append(f"- {rule['name']} ({rule['type']})")
        lines.append("")

    # Key Commands
    lines.append("## Key Commands")
    lines.append("| Command | Description |")
    lines.append("|---------|-------------|")
    lines.append("| `beadloom ctx <ref_id>` | Full context bundle for a node |")
    lines.append('| `beadloom search "<query>"` | FTS5 search across nodes and docs |')
    lines.append("| `beadloom lint --strict` | Architecture boundary validation |")
    lines.append("| `beadloom sync-check` | Check doc-code freshness |")
    lines.append("")

    # Agent Instructions
    lines.append("## Agent Instructions")
    lines.append("- Before work: call `get_context(ref_id)` or `prime` MCP tool")
    lines.append("- After code changes: call `sync_check()`, update stale docs")
    lines.append("- New features: add `# beadloom:feature=REF_ID` annotations")
    lines.append("- Graph changes: run `beadloom reindex` after editing YAML")
    lines.append("")

    # Domains
    if dynamic and dynamic.get("domains"):
        lines.append("## Domains")
        for d in dynamic["domains"]:
            lines.append(f"- {d['ref_id']}: {d['summary']}")
        lines.append("")

    # Stale docs
    if dynamic:
        stale: list[dict[str, str]] = dynamic.get("stale_docs", [])
        lines.append("## Stale Docs")
        if stale:
            for s in stale:
                lines.append(f"- {s['doc_path']} ({s['ref_id']})")
        else:
            lines.append("(none)")
        lines.append("")

    # Lint violations
    if dynamic:
        violations: list[dict[str, str]] = dynamic.get("violations", [])
        lines.append("## Lint Violations")
        if violations:
            for v in violations:
                lines.append(f"- [{v['rule']}] {v['node']}: {v['message']}")
        else:
            lines.append("(none)")
        lines.append("")

    return "\n".join(lines)


def _format_prime_json(
    project_name: str,
    version: str,
    rules: list[dict[str, str]],
    dynamic: dict[str, Any],
) -> dict[str, Any]:
    """Format prime context as structured JSON dict."""
    result: dict[str, Any] = {
        "project": project_name,
        "version": version,
    }

    if dynamic:
        kc: dict[str, int] = dynamic["kind_counts"]
        result["architecture"] = {
            "domains": kc.get("domain", 0),
            "services": kc.get("service", 0),
            "features": kc.get("feature", 0),
            "symbols": dynamic["symbols"],
        }
        result["health"] = {
            "stale_docs": dynamic.get("stale_docs", []),
            "lint_violations": dynamic.get("violations", []),
            "last_reindex": dynamic.get("last_reindex", "never"),
        }
        result["domains"] = dynamic.get("domains", [])
    else:
        result["warning"] = "Database not found. Run `beadloom reindex` for full context."

    result["rules"] = rules
    result["instructions"] = (
        "Before work: call get_context(ref_id) or prime MCP tool. "
        "After code changes: call sync_check(), update stale docs. "
        "New features: add # beadloom:feature=REF_ID annotations. "
        "Graph changes: run beadloom reindex after editing YAML."
    )

    return result


def prime_context(
    project_root: Path,
    *,
    fmt: str = "markdown",
) -> str | dict[str, Any]:
    """Build compact project context for AI agent injection.

    Three layers:

    1. **Static** — ``AGENTS.md`` instructions, ``rules.yml``, ``config.yml``
    2. **Dynamic** — DB queries (nodes, stale docs, lint violations, symbols)
    3. **Format** — markdown or JSON output

    Works gracefully without DB (static-only mode).
    Target: <=2000 tokens output.

    Parameters
    ----------
    project_root:
        Root of the project (where ``.beadloom/`` lives).
    fmt:
        Output format — ``"markdown"`` (default) or ``"json"``.

    Returns
    -------
    str | dict[str, Any]
        Compact Markdown string or structured dict.
    """
    from beadloom import __version__

    # 1. Static layer
    project_name = _detect_project_name(project_root)
    rules = _read_rules_data(project_root)

    # 2. Dynamic layer (requires DB)
    db_path = project_root / ".beadloom" / "beadloom.db"
    dynamic: dict[str, Any] = {}

    if db_path.exists():
        from beadloom.infrastructure.db import connection, get_meta

        with connection(db_path) as conn:
            # Node counts by kind
            kind_rows = conn.execute(
                "SELECT kind, count(*) AS cnt FROM nodes GROUP BY kind"
            ).fetchall()
            kind_counts: dict[str, int] = {str(r["kind"]): int(r["cnt"]) for r in kind_rows}

            # Symbols count
            symbols: int = int(conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0])

            # Domain list
            domain_rows = conn.execute(
                "SELECT ref_id, summary FROM nodes WHERE kind = 'domain' ORDER BY ref_id"
            ).fetchall()
            domains: list[dict[str, str]] = [
                {"ref_id": str(r["ref_id"]), "summary": str(r["summary"] or "")}
                for r in domain_rows
            ]

            # Stale docs
            stale_rows = conn.execute(
                "SELECT doc_path, code_path, ref_id FROM sync_state WHERE status = 'stale'"
            ).fetchall()
            stale_docs: list[dict[str, str]] = [
                {
                    "doc_path": str(r["doc_path"]),
                    "code_path": str(r["code_path"]),
                    "ref_id": str(r["ref_id"]),
                }
                for r in stale_rows
            ]

            # Lint violations (fast, no reindex)
            violations = _get_lint_violations(project_root)

            # Last reindex
            last_reindex = get_meta(conn, "last_reindex_at", "never")

            dynamic = {
                "kind_counts": kind_counts,
                "symbols": symbols,
                "domains": domains,
                "stale_docs": stale_docs,
                "violations": violations,
                "last_reindex": last_reindex,
            }

    # 3. Format output
    if fmt == "json":
        return _format_prime_json(project_name, __version__, rules, dynamic)
    return _format_prime_markdown(project_name, rules, dynamic)
