<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:53:18.143877+00:00 · coverage 100% (`route-extraction`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Route Extraction

API route extraction across web frameworks for the context-oracle domain.

**Source:** `src/beadloom/context_oracle/route_extractor.py`

---

## Specification

### Purpose

Discover the HTTP API routes a codebase exposes by combining tree-sitter AST
analysis with a regex fallback, covering ~12 web frameworks (Flask, FastAPI,
Express, Spring, …). Extracted routes enrich the graph so the context bundle
and landscape can describe a service's external surface.

### Contract

- **Input:** source files for a supported framework.
- **Output:** structured route records (method, path, handler) per file.
- **Invariants:** AST extraction is preferred; the regex fallback applies only
  when no parser is available for the language.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
