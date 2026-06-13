<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`contracts`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Contracts (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/contracts.py`

---

## Overview

The first-class cross-service contract model and its protocol-agnostic
reconciliation. Owns the `Contract` model, the language-neutral `contract_key`
derivation, the `ContractVerdict` enum, and `reconcile_contracts` (which
`federation.py` delegates to). Promotes the contract out of the edge-buried
`extra.contract` blob into a first-class object computed at the federation hub.

> Component doc skeleton (BDL-051 S3b / BEAD-14). Tech-writer (BEAD-13) fills prose.
