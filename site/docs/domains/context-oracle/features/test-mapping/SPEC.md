<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`test-mapping`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Test Mapping

Test-to-source mapping for the context-oracle domain.

**Source:** `src/beadloom/context_oracle/test_mapper.py`

---

## Specification

### Purpose

Detect the test framework(s) in use and map test files to the source nodes they
exercise, so the graph and context bundles can report which nodes have test
coverage and surface the tests relevant to a given node.

### Contract

- **Input:** the indexed file set (test + source paths).
- **Output:** test-file → source-node associations.
- **Invariants:** mapping is heuristic (name/path proximity + framework
  conventions); it never fails the index when no tests are found.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
