# ACTIVE: BDL-011 — Plug & Play Onboarding

> **Current wave:** 1→2 (Foundation done, Doc generation next)
> **In progress:** —
> **Blocked:** —

---

## Wave 1 — Foundation (DONE)

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-01: Root node + project name detection | `beadloom-dj9.1` | **done** | _detect_project_name + root node + part_of edges |
| BEAD-02: Auto-rules generation | `beadloom-dj9.2` | ready | P0, unblocked |
| BEAD-03: Auto MCP config | `beadloom-dj9.3` | **done** | setup_mcp_auto + editor detection |

## Wave 2 — Doc generation

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-04: Doc skeleton generation | `beadloom-dj9.4` | ready | new file: doc_generator.py, unblocked |
| BEAD-05: Polish data generation | `beadloom-dj9.5` | blocked by 04 | |

## Wave 3 — CLI + MCP

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-06: CLI docs generate + polish | `beadloom-dj9.6` | blocked by 04,05 | |
| BEAD-07: MCP tool generate_docs | `beadloom-dj9.7` | blocked by 05 | |
| BEAD-08: Enhanced init output | `beadloom-dj9.8` | blocked by 02,04 | |

## Wave 4 — Tests

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-09: Integration tests | `beadloom-dj9.9` | blocked by 06-08 | |

## Wave 5 — Dogfooding

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-10: Self-apply on Beadloom | `beadloom-dj9.10` | blocked by 09 | UX validation |
| BEAD-11: Graph + CHANGELOG + docs | `beadloom-dj9.11` | blocked by 10 | |

---

## Next Action

Claim BEAD-02 (`beadloom-dj9.2`) + BEAD-04 (`beadloom-dj9.4`) in parallel.
