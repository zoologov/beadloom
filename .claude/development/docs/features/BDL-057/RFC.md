# RFC: BDL-057 — Freshness for reference / overview documentation

> **Status:** Approved
> **Created:** 2026-06-15
> **PRD:** ./PRD.md
> **Type:** feature

---

## Summary

Two complementary mechanisms, plus a prose backfill:

- **Layer 1 — fact freshness (deterministic, blocking).** Promote `docs audit` from `[experimental]` to stable and add it as a `GateStep` in `run_ci_gate`. Default verdict: **block on `stale>0`** (owner-approved). It already detects stale numeric/version facts (version, node/edge counts, language count, MCP-tool count, CLI-command count) with false-positive masking + tolerances.
- **Layer 2 — surface drift (conceptual, advisory/warn).** A doc opts in with an annotation declaring a coarse `watches:` surface (`cli` / `graph` / `flow.yml`). `sync-check` computes an aggregate hash over the watched surface and, on drift, emits a **warning** (not a hard failure) so a human re-reads and clears it with `sync-update`.
- **Backfill (G4).** Fill the 11 skeleton SPECs with code-accurate prose (draft source: `archive/BDL-051-docs` tag) and declare `watches:` on the few key overviews (README, getting-started, architecture).

## Decisions on the PRD open questions

1. **Layer 1 Gate severity:** block on `stale>0` (owner-approved). Threshold/tolerances stay tunable via the existing `config.yml` audit section (extra facts + tolerances); a documented escape exists for intentional mentions. Prerequisite: Beadloom's own docs must be audit-clean first (done in G4), so turning it blocking doesn't immediately red the gate.
2. **Layer 2 declaration:** an in-doc annotation — an HTML comment `<!-- beadloom:watches=cli,graph,flow.yml -->` near the top of the markdown. Local to the doc, discoverable, no separate registry, mirrors the `# beadloom:` code-annotation idiom. (Rejected: graph-YAML node — heavier; config.yml list — non-local, easy to forget.)
3. **Watched-surface signatures (coarse, deterministic):**
   - `cli` — normalized Click command + option tree (command names + flag names, sorted), reusing the introspection `docs audit` already does.
   - `graph` — the node + edge identity set (sorted `ref_id`+`kind`, sorted edges), not full node content (too sensitive → noise).
   - `flow.yml` — normalized `.beadloom/flow.yml` content (parsed → re-serialized canonically).
   The aggregate hash = hash of the concatenation of the requested surfaces' signatures, in declared order.
4. **Baseline storage:** a NEW `reference_state` table (`doc_path`, `watches`, `aggregate_hash`, `status`), parallel to `sync_state`. Keeps the symbol-pair logic and the reason-masking invariant untouched; Layer 2 is additive.
5. **sync-check output:** reference drift surfaces as its own pair with `reason = surface_drift` and **severity = warning**; symbol-pair reasons are unchanged. The Gate's `sync-check` step fails only on symbol-pair `stale` (as today); `surface_drift` contributes a warning, never a block.
6. **Clearing:** `beadloom sync-update <doc>` (and `--yes`) recomputes + stores the new aggregate hash for a reference doc — same UX as re-attesting a symbol pair.

## Component / file impact

**Layer 1 (fact freshness):**
- `src/beadloom/services/cli.py` — drop `[experimental]` from `docs audit` (docstring + console banner); keep flags.
- `src/beadloom/application/gate.py` — new `_step_docs_audit(project_root)` `GateStep` (calls `doc_sync.audit.run_audit` with `stale>0`); add to `run_ci_gate` step list (after `sync-check`). Findings mapped to the shared finding shape.
- `src/beadloom/doc_sync/audit.py` — expose a gate-friendly entry returning findings (likely already present; thin adapter if not).

**Layer 2 (surface drift):**
- `src/beadloom/doc_sync/` — new `surface.py`: compute `cli` / `graph` / `flow.yml` signatures + aggregate hash; parse the `<!-- beadloom:watches=... -->` annotation from a doc.
- `src/beadloom/infrastructure/db.py` — `reference_state` table (migration; created on reindex).
- `src/beadloom/doc_sync/engine.py` — during `build_sync_state`/`check_sync_state`: discover watched docs, compute/compare aggregate hash, emit `surface_drift` (warning) pairs; reset baseline on reindex like symbol pairs.
- `src/beadloom/application/` (sync-update path) + `cli.py` — `sync-update` recomputes the reference baseline.
- `sync-check` JSON/rich output — render the warning-severity `surface_drift` pairs without masking symbol-pair reasons.

**Backfill (G4):**
- `docs/**` — fill the 11 skeleton SPECs (prose from `archive/BDL-051-docs`, rewritten to 2.0.0); add `<!-- beadloom:watches=... -->` to README.md, README.ru.md, docs/getting-started.md, docs/architecture.md.
- Docs of the feature itself: `docs/services/cli.md` (`docs audit` stable + `sync-check` surface drift), `docs/getting-started.md`, the relevant guide.

## Algorithm (Layer 2, one reference doc)

```
on reindex:
  for each doc with `<!-- beadloom:watches=S1,S2,... -->`:
    sig = hash( signature(S1) || signature(S2) || ... )   # declared order
    upsert reference_state(doc_path, watches, aggregate_hash=sig, status='ok')

on sync-check:
  for each row in reference_state:
    now = hash(current signatures of its watches)
    status = 'ok' if now == stored aggregate_hash else 'surface_drift' (WARNING)
  report alongside symbol pairs; gate treats surface_drift as warn, not fail

on sync-update <doc>:
  recompute + store aggregate_hash; status -> ok
```

## Alternatives considered

- **Auto-rewrite reference docs on drift** (like the symbol-paired AI tech-writer). Rejected: overview prose is judgment-heavy; a `watches` drift means "a human should re-read," not "a machine should rewrite." Out of scope (PRD non-goal).
- **Per-symbol pairing of overviews.** Rejected: overviews legitimately span the whole CLI/graph; forcing symbol pairs would be noisy and false. Coarse surface hashing is the right granularity.
- **Hard-block on surface drift.** Rejected (PRD G3): would train people to bypass the Gate. Warn-only.
- **Declare `watches` in graph YAML / config.yml.** Rejected: less local/discoverable than an in-doc annotation.

## Risks & mitigations

- **Layer 1 false-positive hard-block.** `docs audit` masks dates/hex/issue-IDs/line-refs/version-pins and uses tolerances; before making it blocking we run it on Beadloom's docs and fix real findings (G4). Config escape (tolerances / extra facts) documented.
- **Layer 2 noise.** Default-off; opt-in per doc; only a few key overviews declared. Coarse signatures (identity sets, not content) avoid firing on cosmetic code edits.
- **Surface-signature instability** (e.g. graph hash changing on every node tweak → constant warnings). Mitigation: signatures are coarse identity sets; tune granularity if dogfooding shows churn; warn-only means churn is annoying, not blocking.
- **Reason-masking regression.** Layer 2 lives in a separate `reference_state` table and is additive in output — the symbol-pair `sync_state` transitions and the mark-synced→re-run-to-fixpoint invariant are untouched (verified concern from prior sync-check work).
- **Backward compatibility.** No `watches` annotations + audit-clean repo ⇒ both layers are safe no-ops.

## Rollout

One branch `features/BDL-057`, one PR to `main`. Build order: Layer 2 mechanism (dev) ∥ Layer 1 gate wiring (dev) → fill skeletons + declare watches + feature docs (tech-writer) → tests → review. Dogfooded: Beadloom's own README/getting-started/architecture declare `watches`; `docs audit` runs clean and blocking in `beadloom ci` before merge. After merge, the archive tag `archive/BDL-051-docs` can be deleted. Version bump handled in the subsequent release prep (likely 2.1.0 — additive feature).
