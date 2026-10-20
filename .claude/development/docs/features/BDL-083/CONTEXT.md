# CONTEXT: BDL-083 — Debt to zero

> **Status:** Approved
> **Created:** 2026-10-18

---

## Goal

Every recorded issue re-measured and closed or owned; the gates that lie fixed first; a monorepo
on GitLab supported or refused by name; the original debt A–D and the tooling baseline E–I at
their measured zero; the count kept at zero by construction. The owner's P0 of 2026-10-18:
development continues only after this.

## State

Branch `features/BDL-083` from `main` at `0f1cb9a3` (9.0.0 released; BDL-UX #326–#350 filed
by PR #105). The parent bead is `beadloom-ba9w` (P0 since 2026-10-18), with 16 children and the
slices A–I of 2026-10-08 to 2026-10-11 already on it. The owner's eight rulings are in PRD.md;
the decisions D1–D9 in RFC.md; the undecided axes in `axes.md`, ruled in the RFC.

## Key Constraints

- Seven slices in the PRD's order; one PR per slice, never a bag. S1 and S2 are designed to the
  bead here; S3's result designs S4–S7, each as a PLAN section approved on its own (ruling 6),
  so the DAG never holds the whole epic at once.
- The version is MAJOR by three measured exit-code or finding-set moves (D8); each is a test
  that is red first and the CHANGELOG names it with its measurement.
- No new feature: a slice that finds a feature behind a bug files the feature as a bead outside
  this epic (the PRD's non-goal). The adopter's `guard architecture` is the first such bead.
- The adopter's layout is a fixture under `tests/fixtures/`, anonymised; no owner or colleague
  project name in any artifact, the issue log and the archive included.
- `beadloom waves` decides the waves; two-level verification (green in a clean room over N
  files is a different claim from green on the tree); one bead per agent; commits by path under
  the landing lock; documents in English; a user-visible behaviour rule is agreed with the owner
  before code (D1, D4, D5 and D9 are those rules, agreed on 2026-10-18).
- The re-measurement protocol (D9) is the only way an entry leaves the open index: evidence,
  a bead, or the owner's `Won't fix` ruling — never a silent deletion.
- Existing beads are reused where an entry already has one (`beadloom-jwfc`, `beadloom-ba9w.13`,
  `beadloom-tsqz`, `beadloom-ba9w.1`, `beadloom-7pd6`); a duplicate bead is a finding.

## Code Standards

Python >= 3.10 — click, rich, pyyaml, tree-sitter, mcp; ruff (lint + format); mypy --strict;
pytest + pytest-cov; no `Any` or `# type: ignore` without a stated reason, no `print()`, no bare
`except:`, `pathlib` over `os.path`, parameters in SQL, `yaml.safe_load`; documents in English;
commits `[BDL-083] <type>: <description>`; one PR per slice; merge on green CI.

## Architectural Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-18 | The order S1 gates → S2 monorepo and GitLab → S3 re-measurement → S4 false-stale → S5 A–D → S6 E–I → S7 the rest and the recurrence; S1 and S2 before the team model's measurements | Owner's ruling 1 |
| 2026-10-18 | Zero means an empty open index, where a close is dated evidence or a `Won't fix` ruling with a reason, both archived; an unmeasured entry is not closed | Owner's ruling 2 |
| 2026-10-18 | The pre-push hook without `beadloom` on PATH fails with a sentence; pre-commit runs `lint --strict` over the nodes of staged paths; the Gate has a per-step `ERROR` status and a pipe-safe writer | Owner's ruling 3; D1 |
| 2026-10-18 | Liveness tells an unmatchable glob from a live rule with nothing to ban, by the matcher on a synthetic path | D2 |
| 2026-10-18 | Ownership by the files a bead's commits changed, the rule printed | D3 |
| 2026-10-18 | The base is the merge-base with the parent branch, then `--base`, then trunk, printed always; CI resolves the branch from the pull or merge request | Owner's ruling 4; D4 |
| 2026-10-18 | The version is MAJOR | Owner's ruling 5; D8 |
| 2026-10-18 | `beadloom-ba9w` stays the feature bead; children per slice as each PLAN section is approved | Owner's ruling 6 |
| 2026-10-18 | Re-measurement after S1 and S2, feeding S4–S7; `measured_on` and an age rule in the issue-log leg ship in this epic | Owner's rulings 7, 8; D9 |
| 2026-10-19 | D3 amended: ownership by the files a bead's commits changed only; `refs:` attributes nothing. D10: a commit is a bead's by its `Bead: <id>` trailer, the composed commit format carries it | Owner's rulings on S1R Minors 1 and 3 |
| 2026-10-19 | D10 clarified: the trailer sits in the message's final paragraph beside the other trailers; the ownership report names a `Bead:` line outside it instead of denying it; git >= 2.22 | S1R second pass, Major 1 |
| 2026-10-19 | The JSON and MCP `claims` entry carries the count and hashes of the commits whose `Bead:` line git reads no trailer from, the same fact the text surfaces print (one shape, as S1c ruled for `ownership`/`owners`); done in S1, folded into the next fix bead or as a bead of its own after S1R pass 3 | Owner's ruling on the fix-5 question |
| 2026-10-19 | #353 taken into this epic as S2f: indexed paths are POSIX on every platform, `source:` normalised before it is matched, the surface ledger names its pairs; the Windows CI leg stays withdrawn, two tests are the measurement | Owner's decision 2026-10-19; D11 |
| 2026-10-19 | #354 taken into this epic as S2g: the lock's release is exported and landed before the push; the pre-push hook refuses a tree whose export holds the slot for the pushed bead; `waves` names the remedy for a closed holder | Owner's decision 2026-10-19; D12 |
| 2026-10-19 | The pipeline files the room census reads are declared in `config.yml` under `rooms.pipelines` (`github`, `gitlab`); unset reads every file present; S2a's GitHub-first ordering withdrawn; this repository declares `[github]` | Owner's ruling 2026-10-19 on S2a; D6 amended |
| 2026-10-19 | #356 measured on this repository (all six claims hold) and taken into this epic: (a), (e), (g) as S2h — Cursor reads the composed core, project layer, overlay and commands; `config-check` names a missing layer; portable MCP command; absolute plan path — (b) kept for S3's placement as a rule to agree first; (c), (d), (f) filed outside as features | Owner's decision 2026-10-19; D13; the PRD's non-goal |
| 2026-10-20 | `doctor` exits 1 on any `ERROR` row (S2e's generalisation accepted); D13 amended: `.beadloom/flow/claude/CLAUDE.md` is the one project layer reaching both tools' composed core, `.beadloom/flow/cursor/` Cursor alone; S2c's `project_name:` calls accepted (key, manifest second, undeclared name kept as not compared, directory for a first composition only) and `init`/`prime` writing and reading the key filed outside the epic | Owner's rulings 2026-10-20 on S2R Minor 2, S2h and S2c |
| 2026-10-18 | Rooms from `.github/workflows` and `.gitlab-ci.yml`; distributions by `**/pyproject.toml` under `scan_paths`; the room's environment and hint from the found distribution; `config-check` by the declared project name | D6, D7 |

## Related Files

`src/beadloom/services/commands/{docsync.py,issue_number.py,federation.py,clean_room.py}`,
`src/beadloom/graph/rules/{liveness.py,types.py}`, `src/beadloom/application/{gate.py,gate_ownership.py,gate_coverage.py,declared_scope.py,rooms.py}`,
`src/beadloom/application/waves/clean_room.py`, `src/beadloom/onboarding/flow_config.py` (the
composition `config-check` compares), `tests/fixtures/<the adopter's layout>`,
`tests/test_ci_consolidated_structure.py` (the structural-test shape), `.claude/development/BDL-UX-Issues.md`
and `archive/BDL-UX-Issues-closed.md`, `.claude/development/BDL-UX-Issues/` (the ledger),
`docs/guides/public-api.md`, the ci-gate, rule-engine, verdict-room and wave-plan SPECs.

## Current Phase

- **Phase:** Development — S1 merged into `main` as `ab174d34` on 2026-10-19 (PR #106); S2 merged as `41245dc7` on 2026-10-20 (PR #107); S3 running on `features/BDL-083` — the six measure beads and S3z landed, S3R in progress
- **Current bead:** see ACTIVE.md
- **Blockers:** none
