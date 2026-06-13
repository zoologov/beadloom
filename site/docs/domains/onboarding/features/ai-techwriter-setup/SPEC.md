<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:42:55.793320+00:00 · coverage 100% (`ai-techwriter-setup`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# AI Tech-Writer Setup

The `setup-ai-techwriter` scaffolder, in the onboarding domain.

**Source:** `src/beadloom/onboarding/ai_techwriter_setup.py`

---

## Specification

### Purpose

Make adopting the AI tech-writer a one-command affair: `beadloom
setup-ai-techwriter --platform github|gitlab` emits the CI workflow, the recipe,
and the guide that wire the **packaged** harness
(`beadloom.ai_agents.ai_techwriter`) into a target repo. As of BDL-051 / S2 the
harness ships inside the installed `beadloom` package, so there is **no Python
vendoring** — adopters depend on `beadloom` and the scaffold only emits the
workflow that invokes the installed module.

### Contract

- **Input:** the target repo + chosen platform.
- **Output:** a CI workflow + recipe + guide referencing
  `python -m beadloom.ai_agents.ai_techwriter`.
- **Invariants:** idempotent; no harness source is copied into the target repo.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
