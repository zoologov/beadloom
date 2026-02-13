# ACTIVE: BDL-011 — Plug & Play Onboarding

> **Current wave:** 1 (Foundation)
> **In progress:** —
> **Blocked:** —

---

## Wave 1 — Foundation

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-01: Root node + project name detection | `beadloom-dj9.1` | ready | P0, blocks 02/04/08 |
| BEAD-02: Auto-rules generation | `beadloom-dj9.2` | blocked by 01 | |
| BEAD-03: Auto MCP config | `beadloom-dj9.3` | ready | P0, independent |

**Plan:** Start BEAD-01 + BEAD-03 in parallel. After BEAD-01 done → BEAD-02.

## Wave 2 — Doc generation

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-04: Doc skeleton generation | `beadloom-dj9.4` | blocked by 01 | new file: doc_generator.py |
| BEAD-05: Polish data generation | `beadloom-dj9.5` | blocked by 04 | |

## Wave 3 — CLI + MCP

| Bead | ID | Status | Notes |
|------|----|--------|-------|
| BEAD-06: CLI docs generate + polish | `beadloom-dj9.6` | blocked by 04,05 | |
| BEAD-07: MCP tool generate_docs | `beadloom-dj9.7` | blocked by 05 | |
| BEAD-08: Enhanced init output | `beadloom-dj9.8` | blocked by 01-04 | |

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

Claim BEAD-01 (`beadloom-dj9.1`) + BEAD-03 (`beadloom-dj9.3`), start Wave 1.
