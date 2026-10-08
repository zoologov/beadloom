# ACTIVE: BDL-079 — Release 8.0.0

> **Created:** 2026-10-08

---

## Current Bead

**Bead:** R1 `beadloom-91iv` (the bump, the declaration, the change log); then D1 ∥ V1, R, P.

## Progress

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-91iv` | R1 | ✓ done | 8.0.0 in every place; public API in CONTRIBUTING.md + docs/guides/public-api.md; CHANGELOG [8.0.0]; `beadloom ci` rc 0 |
| `beadloom-ghu3` | D1 | ✓ done | README pair: a portal and viewer section (125 blocks, 0 findings); 8 surface-drift docs read, corrected and attested one by one; vitepress-site TODO filled (318 cases); `beadloom ci` rc 0 |
| `beadloom-jxp4` | V1 | ✓ done | `tests/release/verify_the_release.py` on a wheel path or `beadloom==X.Y.Z`: the built wheel 12 of 12 (exit 0); `beadloom==7.0.0` red, first: `--version` (with `--release 7.0.0`: the activity levels); `beadloom ci` rc 0 |
| `beadloom-urgi` | R | ready | review, bead id only |
| `beadloom-fymn` | P | blocked | PR, merge, Release, downloaded wheel, portal |

## Results

(filled per wave)

## Notes

- **D1 closed (2026-10-08):** `9d18e000` — README pair gains «Портал и просмотрщик архитектуры» / «The portal and the architecture viewer» (RU first; readme-pair 125 blocks); the eight surface-drift docs read and corrected (architecture.md's Gate order, schema, `site` kind; counts in bdd-scenarios/document-kinds; parallel-waves' graph-files medium and `--pair`; project-overlays' closed issues; testing.md's `tests:` block and `flat_tests`); the TODO filled: PR #94's site-e2e ran 318 cases, 318 passed; `beadloom ci` rc 0, drift 8 -> 0. V1 launched.

- **R1 closed (2026-10-08):** `be97f6f5` — 8.0.0 in the nine checked places and the unchecked ones (CLAUDE.md through `setup-agentic-flow`); `CONTRIBUTING.md` Public API section, `docs/guides/public-api.md`, CHANGELOG `[8.0.0]`; `beadloom ci` rc 0. The scaffold's package.json stays 1.0.0 (a private npm package). Two RFC rows corrected: `export` carries no activity; `reindex` names only a shallow history. For the owner: public-api.md says adding a value to a vocabulary is MINOR (R1's own rule). D1 ∥ V1 launched.

- Epic `beadloom-1l8d`; branch `features/BDL-079` from `main` at `539ed4a3`; the close-out commit of BDL-078 is the branch's first.
