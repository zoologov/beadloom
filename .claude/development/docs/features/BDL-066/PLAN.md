# PLAN: BDL-066 — Agent behaviour observability

> **Status:** Draft
> **Created:** 2026-08-31

---

## Slices

Six slices, dependency-ordered. Each is its own PR and each leaves the Gate green.

| # | Slice | Depends on |
|---|---|---|
| S0 | Role separation, from the tracker alone — **no event store needed** | — |
| S1 | Store adapter, deterministic metrics, secrets and retention | — |
| S2 | Claim against trace | S1 |
| S3 | Brief delta — constraints added beyond the bead | S1 |
| S4 | The result side — Gate history, weakened checks, review outcomes | S1 |
| S5 | The retrospective role | S2, S3, S4 |
| S6 | Guards: scope drift and observability change | S1 |

S0 depends on nothing and needs nothing collected. It is first because it catches
the most expensive failure of all the ones examined, and because it works in a
repository that never enables the event store.

S6 is independent of S2–S5 and can run beside them. It is listed last because
the observability guard is the one piece that ships useful on its own even if the
rest slips.

## Beads per slice

Each slice carries the mandatory four roles: dev beads, then test, then review,
then tech-writer. Exact bead ids assigned at creation, after PLAN is approved.

## S0 — Role separation, from the tracker alone

**Case that produced this slice.** On another project a session read the harness
instruction *"Do not call the AgentTool unless the user requested it"* as a
prohibition. It is conditional, and the condition was met — the owner's first
message said to follow the agentic flow, whose §0.0 mandates launching roles via
the `Agent` tool. The whole wave then ran single-agent: the reviewer and the
author were the same entity, and the reports were green.

No brief exists to inspect, no subagent was launched, so every store-based check
in this feature is silent. But the tracker already records what is needed:

```
Comments on beadloom-viaj.6:
[agent-viaj-6] at 2026-08-26 12:05
  REVIEW ISSUES: 0 critical, 5 major

Owner: v.zoologov · Assignee: agent-viaj-6
```

**Checks:** distinct actors across an epic's dev / test / review / tech-writer
beads; the reviewer is not the author; comments on a role bead carry that role's
actor.

**The honest third state.** By default every agent resolves to `git user.name`
and they are indistinguishable. That is **not verified**, not pass — the check
cannot tell single-agent mode from multi-agent with undifferentiated identities.
This repository only has distinguishable actors because the coordinator began
setting `BEADS_ACTOR` per launch after BDL-UX #194.

**Consequence for the shipped flow:** the coordinator sets a distinct actor per
role launch, and `config-check` verifies it does. Without that the check is
permanently unverifiable, which makes it decoration.

**Acceptance:** a replayed single-agent run is named. BDL-062 replays as passing,
with its real per-role actors. A run whose actors are all one identity reports
not-verified and says why. TESTS MUST BITE: removing the actor distinction
reddens a test.

## S1 — Store adapter, metrics, secrets

The narrow interface (*events for this session, bead or time range*), one adapter
for the hook-event store, and the deterministic counters the rest consume.

**Secrets and retention ship here, not later.** Store path git-ignored by
default, redaction of known secret shapes on read, a retention window, and a
`doctor` check that the store is not tracked. A live Qwen key passed through tool
arguments in this repository on 2026-08-31; collection without redaction would
have written it to disk in plaintext.

**Acceptance:** with no store, every consumer reports *not verified* and names the
reason. With a store, the counters match a hand-verified sample. A planted secret
in a tool argument does not appear in any readable output.

## S2 — Claim against trace

Three states: *supported*, *contradicted*, *unsupported*. The third is the honest
default when the trace does not cover the action, and it must not read as either
of the others.

**Acceptance:** a deliberately false claim in a role report is caught. A true
claim the trace happens not to cover reports *unsupported*, not *contradicted* —
FAKES PROVE FAKES applies to the fixture that proves this.

## S3 — Brief delta

Constraints present in a subagent's `tool_input` and absent from the bead
description.

**Acceptance:** replaying the 2026-08-27 heading-lock brief against its bead
names the added constraint. A brief that adds nothing reports nothing.

## S4 — The result side

Gate verdicts across the epic's life, weakened checks, added suppressions,
lowered severities, review findings and whether they were addressed.

**Acceptance:** the BDL-062 epic replays with its real numbers — including the
suppressions retired by hand and the severity raised in `.9`.

## S5 — The retrospective role

Read-only. Runs at epic close. Consumes S2–S4 and may not assert beyond them.
Enforces **A LINK NEEDS A SHARED NAME**, and states events read out of events
available.

**Acceptance:** run over BDL-062 it produces the heading-lock observation from
S3 paired with the result metric it governed, and does not invent a causal claim
where the names do not match. Its report names its own denominator.

## S6 — Guards

**scope-drift** — files written against the bead's declared node scope. A bead
that declares no scope reports *not verified*, never clean. Blocked on bead-to-node
binding, which `flow.yml` already names as the reason `bead-claimed` cannot be
raised to `block`.

**observability-change** — a diff touching `.claude/**`, `.beadloom/flow*`, hooks,
CI, branch protection, `docs_audit.ignore`, rule severities or test thresholds.
Prints as its own block, not as one more warning among the fifty-nine this
repository already emits.

**Acceptance:** both ship `warn`. Reverting either check reddens a test. The
observability guard names every category above on a synthetic diff that touches
each.

## Not in this plan

The proxy adapter and the system prompt, per-agent scoring, and raising any guard
here to `error`. All three are recorded in CONTEXT.md with reasons.
