# Branch Protection

The `setup-branch-protection` helper, in the onboarding domain.

**Source:** `src/beadloom/onboarding/branch_protection.py`

---

## Specification

### Purpose

Configure `main` for strict trunk-based development idempotently: require a PR
(no direct push) and make the consolidated `ci.yml` check-runs **required status
checks**, so the pipeline becomes true enforcement rather than advisory CI.

### Contract

- **Input:** the repo + the set of required check-run contexts.
- **Output:** GitHub branch-protection applied to `main` (safe to re-run).
- **Invariants:** a required status-check context must match a real check-run
  name exactly and must not be produced by a path-filtered workflow.

> Skeleton (BDL-051 S3b / BEAD-14). The tech-writer pass (BEAD-13) fills prose.
