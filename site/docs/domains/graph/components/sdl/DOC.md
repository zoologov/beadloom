<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T12:30:18.610981+00:00 · coverage 100% (`sdl`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# SDL (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/sdl.py`

---

## Overview

A minimal, dependency-free GraphQL SDL surface extractor. The cross-service
contract graph needs only the *names* a GraphQL producer exposes so a
consumer's declared `references` can be checked for presence. This module
implements a tiny line/brace scanner over the SDL text rather than pulling in a
full GraphQL parser (`graphql-core` is the documented upgrade path).

## Public surface

- `extract_surface(sdl_text)` — return the exposed surface as a `set[str]`: the
  top-level `Query` / `Mutation` / `Subscription` field names plus the
  `type` / `input` / `enum` / `interface` type names declared in the SDL.

## Collaborators

Called by the graph-loader (`_fold_graphql_surface`) at load time to fold a
GraphQL producer's `exposed: [...]` surface into the stored contract payload,
which `contracts.py` then reconciles against a consumer's declared `references`.
Pure, dependency-free, deterministic.

> Component doc (BDL-051). Public surface verified against `sdl.py`.
