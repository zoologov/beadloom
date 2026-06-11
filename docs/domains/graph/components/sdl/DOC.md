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

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.
