# PRD: BDL-057 — Freshness for reference / overview documentation

> **Status:** Approved
> **Created:** 2026-06-15
> **Type:** feature
> **Roadmap:** the last feature before the next release; closes the freshness gap left open since BDL-051.

---

## Problem

Beadloom's freshness guarantee only covers **symbol-paired** docs. `sync-check` watches a doc against the code symbols it documents (a `feature` SPEC, a `component` DOC). But the highest-traffic, most public documents are **not** paired with a code symbol:

- `README.md` / `README.ru.md`, `docs/getting-started.md`, `docs/architecture.md`, the guides (`docs/guides/*`), `docs/vision`-style overviews.
- The site generator even badges these "📘 **reference** — overview/guide, not tied to a code symbol" — an honest admission that **nothing checks their freshness**.

So these docs rot silently: a CLI flag is renamed, a command is added, the graph node set changes, `flow.yml` gains a stack — and the overview prose drifts with zero signal. This directly contradicts the thesis we just shipped in BDL-056 ("nothing stale reaches `main`"): the most-read docs are exactly the ones the Gate ignores.

Two foundations already exist but are inert:
1. **`docs audit`** detects stale *numeric/version facts* in prose (version, node/edge counts, language count, MCP-tool count, CLI-command count) via a fact-registry + keyword-proximity scanner with tolerances. But it is marked **`[experimental]`** and is **NOT wired into `beadloom ci`** — so it enforces nothing.
2. **`reference`** exists only as a *display badge* for an unpaired doc, not as a declared, watchable doc kind.

Separately, **11 feature SPECs in `docs/` are still skeletons** (footer "Skeleton (BDL-051 … tech-writer pass fills prose)") — the BDL-051 prose pass never merged. They are reference docs with no real content, and a freshness mechanism is only meaningful once they hold prose.

## Impact

- **Public credibility:** stale README/portal guides ship silently on a tool whose whole pitch is "source of truth that doesn't drift."
- **Dogfooding integrity:** Beadloom governs its own code (BDL-051) and its own symbol-paired docs, but not its own overview docs — a visible gap in "Beadloom governs itself."
- **Leverage:** the freshness mechanism watches the **interface surface** (CLI, graph, `flow.yml`) — the same stable surface that is the product's moat. A drift signal there is high-value.

## Goals

- **G1 — Layer 1 (deterministic facts):** promote `docs audit` out of `[experimental]` to a stable, supported command, and **wire it into the Gate** (`beadloom ci`) with a sensible default verdict (severity + threshold decided in the RFC).
- **G2 — Layer 2 (conceptual drift, new):** introduce a declared **`reference`** doc kind that names a coarse **`watches:`** surface (e.g. `cli`, `graph`, `flow.yml`). `sync-check` computes an aggregate hash over the watched surface; when it drifts, the reference doc is flagged so a human re-reads and clears it (via review + `sync-update`).
- **G3 — Severity is honest:** Layer 2 conceptual drift is **advisory (warn)**, not a hard block — overview freshness is judgment-heavy, and false hard-blocks would train people to bypass the Gate. Layer 1 fact-staleness can be stricter (RFC decides).
- **G4 — Fill the 11 skeleton SPECs** with real prose (rewritten against current 2.0.0 code; the abandoned `archive/BDL-051-docs` tag is a draft source), so the reference mechanism has real content to guard and the portal stops shipping empty skeletons.
- **G5 — No noise:** Layer 2 applies only to a few hand-declared key overview docs, not every markdown file. Default-off; opt-in per doc.

## Non-goals (out of scope)

- **Prose quality / semantic correctness.** Whether the wording is good or the explanation is right stays a human-review concern (and the tech-writer writing standard from BDL-056). BDL-057 only signals *possible staleness*, it does not judge text.
- **Auto-rewriting reference docs.** No agent auto-edits overviews on a `watches:` drift; the signal prompts a human/tech-writer pass.
- **New fact types beyond what `docs audit` already extracts** (unless trivial). REST/OpenAPI/gRPC contract surfaces are not watched.
- **Turning symbol-paired docs into `reference`.** The two mechanisms are complementary, not a replacement.

## Open architecture questions (→ resolved in the RFC)

- Layer 1 Gate severity: does stale-fact `docs audit` **block** (`stale>0`) or **warn** in `beadloom ci`? Default threshold?
- Layer 2 `watches:` surface definition: what exactly hashes for `cli` (Click command/flag tree?), `graph` (node/edge set? rules?), `flow.yml` (the file content/normalized config?). Where is the aggregate-hash baseline stored (alongside sync_state?) and how is it cleared (`sync-update`)?
- Where is `reference` + `watches:` declared — in the graph YAML, a doc front-matter, or `config.yml`? How does it relate to the existing display-only `reference` badge?
- How does Layer 2 surface in `sync-check` output / the Gate without masking the existing symbol-pair reasons (cf. the sync-check reason-masking invariant)?
- Does filling the 11 skeleton SPECs (G4) belong in this feature's beads or split out? (Proposed: in-scope, as a dedicated tech-writer bead.)

## User stories

### US-1: Overview docs can't rot silently
As a maintainer, when I rename a CLI flag or change the graph, I get a signal that `getting-started.md` / `README` may now be stale — instead of finding out from a confused user.

### US-2: The signal is trustworthy, not noisy
As a maintainer, the conceptual-drift signal is a **warning** I can clear with a review, scoped to a few key docs — so I never learn to ignore or bypass the Gate.

### US-3: Stale facts are caught deterministically
As a contributor, if I bump a count or version in code but a doc still cites the old number, `beadloom ci` tells me before merge.

### US-4: The portal stops shipping empty skeletons
As a reader, the feature SPECs on the portal contain real prose, not "Skeleton — tech-writer pass fills prose."

## Acceptance criteria

- `docs audit` is no longer `[experimental]`; it is documented, stable, and runs inside `beadloom ci` with a defined verdict.
- A `reference` doc kind with a `watches:` declaration exists; a watched-surface change produces a **warning** in `sync-check` / the Gate for the declared reference docs, cleared via `sync-update`.
- Layer 2 is opt-in and applied only to a small set of key overview docs (README/getting-started/architecture at minimum); no false signal on unrelated markdown.
- The 11 skeleton SPECs hold real, code-accurate prose; the "Skeleton (BDL-051…)" footer is gone; `sync-check` clean.
- `beadloom ci` green on Beadloom itself with the new checks active (dogfooded); no regression to existing symbol-pair sync-check behavior.
- Backward-compatible: repos without `reference`/`watches` declarations and without `docs audit` findings are unaffected (Layer 2 default-off, safe no-op).
