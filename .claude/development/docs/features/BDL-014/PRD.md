# PRD: BDL-014 — Agent Prime (Cross-IDE Context Injection)

> **Status:** Approved
> **Author:** Claude
> **Date:** 2026-02-14

---

## Problem

AI agents in IDEs lose project context at session start, after compaction, and when switching contexts. Each time the agent starts from scratch — doesn't know the architecture, Beadloom commands, or project rules.

Current state:
- `.beadloom/AGENTS.md` — static file created at `beadloom init`, goes stale quickly
- `.beadloom/README.md` — human-facing description, not optimized for agent context injection
- MCP `get_status` — too brief (counters only)
- MCP `get_context` — too detailed (for a specific ref_id, not a project overview)

No single command to say "give me everything I need to work on this project."

---

## Goal

Create **Agent Prime** — a single command / single MCP call that delivers compact project context to the agent, working **identically across all IDEs** (Claude Code, Cursor, Windsurf, Cline).

---

## User Stories

### US-1: Developer starts a session in any IDE
> As a developer using Beadloom in Cursor/Windsurf/Claude Code,
> I want the AI agent to automatically receive project context at session start,
> so it immediately knows the architecture, commands, and rules.

### US-2: Agent recovers after context loss
> As an AI agent that lost context (compaction, new session),
> I want to call a single command/tool and get everything I need,
> so I can continue working without quality loss.

### US-3: Developer avoids config duplication
> As a developer configuring Beadloom,
> I want to maintain agent instructions in one place,
> so I don't have to edit .cursorrules, .windsurfrules, and .claude/CLAUDE.md separately.

---

## Solution Overview

### Three-layer architecture

```
Layer 1: .beadloom/AGENTS.md          ← Single source of truth
         (instructions + rules + MCP commands)

Layer 2: IDE adapters                 ← Thin pointers
         .cursorrules
         .windsurfrules
         .clinerules
         → "Read .beadloom/AGENTS.md"

Layer 3: beadloom prime (CLI + MCP)   ← Dynamic context
         (architecture + status + violations + stale docs)
```

### Components

| # | Component | Type | Description |
|---|-----------|------|-------------|
| 1 | `beadloom prime` CLI | New command | Outputs compact project context |
| 2 | MCP tool `prime` | New tool (#10) | Same via MCP for any IDE |
| 3 | `AGENTS.md` v2 | Enhancement | Dynamic generation with current state |
| 4 | `beadloom setup-rules` | New command | Generates IDE adapters (.cursorrules etc.) |
| 5 | Integration into `beadloom init` | Enhancement | setup-rules called during bootstrap |

---

## Functional Requirements

### FR-1: `beadloom prime` CLI
- Outputs compact Markdown with project context to stdout
- Contains: architecture overview, key commands, current status, violations/stale
- Format optimized for LLM context injection (~500-1500 tokens)
- `--json` flag for machine-readable output
- Works without DB (graceful degradation — static-only from AGENTS.md)

### FR-2: MCP tool `prime`
- No parameters (or `format: "markdown" | "json"`)
- Returns the same content as CLI
- Works through the existing MCP server

### FR-3: `AGENTS.md` v2
- Generated/updated via `beadloom prime --update` or `beadloom reindex`
- Contains: agent instructions, MCP tools reference, architecture rules from rules.yml
- Does not overwrite user edits (`## Custom` section is preserved)

### FR-4: `beadloom setup-rules`
- Detects installed IDEs (by marker files/directories)
- Generates adapters for detected IDEs
- Adapter = 3-5 lines: "Read .beadloom/AGENTS.md before starting work"
- Does not overwrite existing files (skip with warning)
- Supported IDEs: Cursor, Windsurf, Cline

### FR-5: Integration into init
- `beadloom init --bootstrap` calls `setup-rules` automatically
- Output: "Created .cursorrules, .windsurfrules" (similar to MCP setup)

---

## Non-Functional Requirements

- **Speed:** `beadloom prime` < 500ms (hot cache)
- **Size:** prime output ≤ 2000 tokens (to avoid context pollution)
- **Compatibility:** Python 3.10+, works without installed IDEs
- **Security:** does not output sensitive data (paths to .env, keys)
- **Idempotency:** repeated setup-rules calls are safe

---

## Success Metrics

- Agent gets project context in 1 call (instead of 3-5 currently)
- Single point of instruction maintenance (AGENTS.md vs 4 separate files)
- Works in ≥3 IDEs without manual setup

---

## Out of Scope

- Claude Code hooks (configured by user manually, but we document how to set them up)
- Auto-updating AGENTS.md on every commit
- IDE-specific logic (all adapters have identical structure)
- TUI integration
