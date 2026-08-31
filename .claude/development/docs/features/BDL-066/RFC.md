# RFC: BDL-066 — Agent behaviour observability, trace and result

> **Status:** Draft
> **Created:** 2026-08-31

---

## Summary

An optional event store, read through a narrow adapter. A deterministic layer
that computes numbers from it. Guards that use those numbers per bead. A
read-only retrospective role that interprets them per epic and may not assert
more than they show.

## What Beadloom can and cannot see

Beadloom is not part of the harness and must not become part of it. It cannot
intercept a tool call, read the model's reasoning, or stop an action. It can only
read the traces an agent leaves.

The design therefore does not supervise the agent. It **forces traces to exist
and makes their absence a state rather than a silence** — the same move this
project made for documentation freshness in BDL-061.

Three collection layers exist, with different fidelity:

| Layer | Gives | Cost |
|---|---|---|
| Claude Code native OpenTelemetry | metrics, tokens, cost | none, but **no prompt content** — built for administration |
| Hook events | `PreToolUse`, `PostToolUse`, `SubagentStart/Stop`, `UserPromptSubmit`, with `tool_name`, `tool_input`, `tool_use_id` | a settings change; SQLite store |
| Local proxy | full request and response bodies including the system prompt | routes all traffic locally; **captures every secret in a prompt** |

**The first release targets the hook layer.** It carries the subagent launch and
its `tool_input`, which is the brief — so the brief becomes an artifact with no
cooperation from the coordinator, which is the point. The proxy is a later
adapter behind the same interface.

## The adapter boundary

Stores differ per project and will keep differing. Beadloom declares one narrow
interface — *give me the events for this session, bead or time range* — and
ships adapters for the known shapes. This is the same seam as the contract
adapters in federation, and it is what keeps the feature tool-agnostic.

An absent or unreadable store is not an error. It yields **not verified**, with
the reason, in every consumer.

## The deterministic layer

Everything a retrospective needs that can be counted is counted without a model:

- subagents launched per bead, their briefs, restarts
- constraints present in a brief and absent from the bead description
- files written (`PostToolUse` on `Edit`/`Write`) against the bead's node scope
  from the graph
- test, CI, hook, severity and suppression edits, attributed to the agent that
  made them
- elapsed time between checkpoints, and the length of the longest autonomous span
- fix cycles: how many times a role returned ISSUES and how many rounds followed

If the model narrates first, the result is a plausible story instead of a
measurement. Beadloom counts; the role interprets.

## Claim against trace

Role reports carry claims that are checkable and are currently accepted on
trust. The check pairs a claim pattern with the trace evidence that would
support it:

| Claim in a report | Evidence sought |
|---|---|
| "ran the full suite" | a `pytest` invocation in the trace for that bead |
| "green in a clean room over N files" | `git archive` plus a run inside the extracted tree |
| "reverted to a clean diff" | the edit and its inverse, or a `git checkout` of the same path |
| "N neuterings, each reverted" | N edit/revert pairs |

A claim with no supporting evidence is reported as **unsupported**, which is a
third state beside *supported* and *contradicted*. The check never asserts the
agent lied — the trace may simply not cover the action.

## Correlating trace with result

The result side is already available to Beadloom: the diff, the Gate history
over the epic, weakened checks, added suppressions, lowered severities, review
findings and whether they were addressed.

Correlation is where the value is, and where invention starts. One rule governs
it:

> A link between a trace observation and a result may be asserted **only when
> both sides name the same thing.**

"The brief constrained headings" plus "14 of 14 headings unchanged" is
assertable — mechanical, same named object. "The brief said to be careful" plus
"the text is weak" is not. Everything below that bar is reported as two
observations side by side, unlinked.

## The retrospective role

A fifth role beside dev, test, review and tech-writer. **Read-only**, like
review: the thing that audits the process must not be able to change it.

It runs at epic close, not per bead. Its report is bounded — measurements, then
a small number of process changes, each tied to a named observation. If it
produces more than a handful of recommendations it is retelling rather than
thinking, and the 2026-08-28 retrospective is the cautionary example.

It states how many events it read out of how many exist. A retrospective that
read a third of the trace and does not say so is the same false green this
project spent August removing.

## Secrets and retention

Not an appendix. The store holds tool arguments, and this repository has already
passed a live API key through them: on 2026-08-31 the coordinator read a Qwen key
from a `.env` and passed it as an argument. With collection enabled that key
would sit in a local SQLite in plaintext.

So the shipped mechanism includes, as mechanism rather than advice: the store
path git-ignored by default, redaction of known secret shapes on read, a
retention window, and a `doctor` check that the store is not tracked.

## Where the checks run

Guards run locally in a pre-push hook and in CI. Locally the guard runs inside
the process that could have violated it, which is a conflict of interest this
project has already stated as principle 5: CI is the only true enforcement point.
CI has the branch, the diff and the tracker export, which is enough for scope and
observability checks. Claim-against-trace needs the event store, which is local
by nature — so that check is advisory in CI unless the store is exported.

## Risks

**The retrospective becomes a new unverifiable green.** An agent summarising
agents. Mitigated by the denominator requirement and by the deterministic layer
producing the numbers it may not exceed.

**Alert fatigue.** The observability guard fires on every hook and CI edit. It
must print as its own block rather than as one more warning among the fifty-nine
this repository already emits.

**Tamper.** Hooks run inside the harness; a proxy address is an environment
variable. Neither is tamper-proof. What the design buys is that disabling
collection edits `.claude/**`, which the observability guard names. Not
prevention — a louder exit.

## Alternatives rejected

- **Beadloom collects events itself.** Makes it part of the harness and
  duplicates good third-party tools.
- **Require the coordinator to write briefs to files.** Depends on the
  cooperation of the component being audited. The hook layer gets the brief
  regardless.
- **Start with the proxy for the system prompt.** More data than the failure
  classes need, and every secret with it.
