---
title: application
kind: domain
---

# application

**Kind:** domain

Use-case orchestration: reindex, doctor, debt report, file watcher

**Source:** `src/beadloom/application/`

## Public symbols

- `CategoryScore`
- `Check`
- `DebtData`
- `DebtReport`
- `DebtTrend`
- `DebtWeights`
- `GateResult`
- `GateStep`
- `MermaidIssue`
- `MermaidValidationError`
- `NodeDebt`
- `NodePage`
- `NodeRow`
- `PublishedDoc`
- `ReindexResult`
- `Severity`
- `SiteResult`
- `WatchEvent`
- `build_dashboard_data`
- `build_landscape_data`
- `build_published_docs`
- `collect_debt_data`
- `compute_debt_score`
- `compute_debt_trend`
- `compute_top_offenders`
- `format_debt_json`
- `format_debt_report`
- `format_top_offenders_json`
- `format_trend_section`
- `generate_site`
- `incremental_reindex`
- `inject_badge`
- `load_debt_weights`
- `load_nodes`
- `publish_docs`
- `reindex`
- `render_all_pages`
- `render_dashboard_md`
- `render_landscape_md`
- `render_node_page`
- `render_published_doc`
- `resolve_scan_paths`
- `run_checks`
- `run_ci_gate`
- `serialize_dashboard_data`
- `validate_mermaid`
- `watch`

## Relationships

- **part_of**: [beadloom](../services/beadloom.md)
- **depends_on**: [context-oracle](../domains/context-oracle.md), [doc-sync](../domains/doc-sync.md), [graph](../domains/graph.md), [infrastructure](../domains/infrastructure.md)
- **uses**: [context-oracle](../domains/context-oracle.md), [doc-sync](../domains/doc-sync.md), [graph](../domains/graph.md), [infrastructure](../domains/infrastructure.md), [onboarding](../domains/onboarding.md)

## Documentation

- [domains/application/README.md](/docs/domains/application/README.md)

## Diagram

```mermaid
C4Container
    System_Boundary(application_boundary, "application") {
        Component(debt_report, "Debt Report", "", "Architecture debt aggregation, scoring, trend tracking, and CI gating")
        Component(doctor, "Doctor", "", "Validation checks for graph and data integrity")
        Component(reindex, "Reindex", "", "Full reindex pipeline — drop, recreate, reload graph/docs/code/sync")
        Component(watcher, "Watcher", "", "File watcher for auto-reindex on changes")
    }
```

