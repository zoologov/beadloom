# Branch Protection

The `setup-branch-protection` helper, in the onboarding domain.

**Source:** `src/beadloom/onboarding/branch_protection.py`

---

## Specification

### Purpose

Configure `main` for strict trunk-based development idempotently: require a PR
(no direct push) and make the consolidated `ci.yml` check-runs **required status
checks**, so the pipeline becomes true enforcement rather than advisory CI.

### Protection contract

`build_protection_payload` produces the GitHub request body: required status
checks in `strict` mode over the supplied contexts, `enforce_admins: true` (even
admins integrate through PRs — no bypass), zero required reviews, and
`restrictions: null` so the owner is not locked out and can still self-merge a
green PR. `BranchProtectionRequest` captures the exact `gh api` call — endpoint,
deterministic JSON payload, and arguments — so it is inspectable and mockable;
`apply_branch_protection` sends it through a `GhRunner`.

## Invariants

- A required status-check context must match a real check-run name exactly and
  must not be produced by a path-filtered workflow (it would not run on every PR
  under `strict`, stalling PRs).
- `enforce_admins: true` with zero required reviews — strict trunk-based, but
  the owner can still self-merge.
- The operation is safe to re-run.

## API

Module `src/beadloom/onboarding/branch_protection.py`:

- `build_protection_payload(*, status_check_contexts=DEFAULT_STATUS_CHECK_CONTEXTS) -> dict`
  — the GitHub branch-protection request body.
- `BranchProtectionRequest` — `owner`, `repo`, `branch`, `status_check_contexts`,
  with `endpoint()`, `payload_json()`, and `gh_args()`.
- `apply_branch_protection(...)` — apply the protection via a `GhRunner`.
- `GhRunner` — the runner protocol (mockable in tests).

## Testing

Tests: `tests/test_branch_protection.py`
