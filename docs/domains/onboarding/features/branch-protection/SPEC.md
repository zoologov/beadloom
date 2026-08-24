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

## The default set, and what may change it

`DEFAULT_STATUS_CHECK_CONTEXTS` holds **nine** contexts — the check-runs of the
consolidated `ci.yml` (`gate`, the four `tests (3.x)` matrix legs, the two
`tests-locale (...)` environment-dimension legs, `site-build`, `ai-techwriter`).
It is the SCAFFOLDED DEFAULT that `setup-branch-protection` PUTs in any
repository, not a description of any repository's live protection.

The set has grown and shrunk, and the shrink is the instructive one. BDL-061.39
added a tenth context, `tests-windows`, for a platform dimension; the owner
withdrew it in `beadloom-mr2l.64` on a measured cost — ~16-28 runner-minutes per
pull request, and, unlike the locale legs, the pipeline's critical path, roughly
tripling PR-to-merge latency for a platform outside this project's audience. A
withdrawal moves the `ci.yml` job and this constant in ONE change, in either
direction: a job with no context is a check that gates nothing, and a context
with no job is a check-run that never reports.

## Invariants

- A required status-check context must match a real check-run name exactly and
  must not be produced by a path-filtered workflow (it would not run on every PR
  under `strict`, stalling PRs).
- Every declared context is produced by a job that exists, and every job that
  exists is a declared context. Both directions are enforced against the real
  `ci.yml` by `tests/test_ci_consolidated_structure.py::test_required_contexts_
  match_ci_yml_check_runs`; the second direction is what the withdrawal above
  exercised.
- `enforce_admins: true` with zero required reviews — strict trunk-based, but
  the owner can still self-merge.
- The operation is safe to re-run.

## API

Module `src/beadloom/onboarding/branch_protection.py`:

- The default runner states `encoding="utf-8"` in **both** directions, and the outbound one is the reason it is not cosmetic: the payload is PUT on `gh`'s stdin, so `text=True` would have encoded it with the image's locale — a check-run context with one non-ASCII character would raise on an ASCII image and be silently *altered* on an 8-bit one, i.e. the branch would be protected with a required check whose name nobody declared. JSON is UTF-8 by definition (RFC 8259 §8.1). `errors` stays strict: an outbound payload must never be made lossy to keep a call alive (BDL-061.42).
- `build_protection_payload(*, status_check_contexts=DEFAULT_STATUS_CHECK_CONTEXTS) -> dict`
  — the GitHub branch-protection request body.
- `BranchProtectionRequest` — `owner`, `repo`, `branch`, `status_check_contexts`,
  with `endpoint()`, `payload_json()`, and `gh_args()`.
- `apply_branch_protection(...)` — apply the protection via a `GhRunner`.
- `GhRunner` — the runner protocol (mockable in tests).

## Testing

Tests: `tests/test_branch_protection.py`
