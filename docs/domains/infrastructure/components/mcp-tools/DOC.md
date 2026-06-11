# MCP Tools (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/mcp_tools.py`

---

## Overview

The canonical, single-source-of-truth catalog of MCP tool names. The MCP server
builds full `mcp.Tool` objects (with input schemas) from this catalog, and the
agent-facing docs generator enumerates the same list — so the documented tool
count can never drift from the registered count. Lives in `infrastructure` (the
lowest layer) so both `services` and `onboarding` may depend on it without
violating the layering rules.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.
