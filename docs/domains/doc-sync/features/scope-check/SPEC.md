# Scope Check

The paths a commit stages, judged against the axes its work item declared: a node an axis
rules out of scope, or a bounded context no declared axis reaches.

**Source:** `src/beadloom/doc_sync/scope_check.py`

---

## Specification

### Purpose

`sync-check --staged` and the commit-scoped pre-commit hook already judge a commit by the
paths it stages. Neither compares those paths against the scope a human approved. This is
that comparison.

The unit is the WORK ITEM's axes and never the claimed bead's (CONTEXT Q2). The work item's
axes are what the human approved, and a bead may narrow freely inside them. A commit that
LEAVES the work item's axes means the approval no longer covers the change, which is exactly
the re-plan trigger. Comparing against the bead would fire on every legitimate cross-bead
commit inside one approved scope.

| Check | Fires when |
|-------|-----------|
| `outside-the-declared-axes` | a staged path's owning node is ruled out of scope by an axis, or sits in a bounded context no declared axis reaches |

### The rule was measured before it was chosen

An always-red check is an ignored check, and this repository holds the receipt:
`docs_audit.ignore` exists because a check that fired on everything was suppressed instead of
repaired. Two candidate rules were run against BDL-068's own `## Axes` table before either
was written.

| Rule | On this branch's three code commits | On the 155 commits before it that touch an owned path |
|------|-------------------------------------|--------------------------------------------------------|
| the path's node must be a node a kept row names | red on all three — 11, 5 and 6 paths | — |
| the bounded context the declared axes reach | silent on all three | 115 outside (74%) |

The first rule is red on commits the approval does cover, and the reason is a fact about the
section rather than about the rule: the table records what a change RANGES OVER, and the
surfaces the change IS are named in the `Derived by` field instead. The second is specific to
the work item's own work and still fires on three quarters of unrelated work, which is the
profile a signal has.

### The rule

A staged path is INSIDE the approval when either holds:

1. its owning node is named by a row kept in scope, or is a node the derivation ran over —
   the surfaces an answer was derived from are the surfaces the work item changes;
2. no row names its node, and its bounded context is one the declared axes reach — a sibling
   module in a context the work item already works in is inside the approval, and a context
   it never named is not.

It is OUTSIDE when a row names its node and every such row rules it OUT of scope, which is
the sharpest half because the person wrote "not this one", or when no declared axis reaches
its bounded context.

A node kept by one row and ruled out by another is KEPT: the person took it somewhere, and a
ruling elsewhere narrows that row's axis rather than refusing the node.

### The finding names which axis

A node an axis rules out is reported by that axis's name. A node no row names is reported
against every axis the work item declared, each with the bounded contexts its kept rows
reach — `` outside every axis the work item declared — `callers` (application, cli, doc-sync,
onboarding) ``. Naming only that a path fell outside would leave the reader to re-derive the
table by eye.

### What is deliberately not reported

A path no node owns — a document, a test, a graph YAML — is not a call site and has no axis
to be outside of. It is counted in `ScopeVerdict.unowned` and stated beside the verdict,
never reported. A count that reads as a checked count is the false green this epic exists to
remove, and `CommitScope` already states the pairs it leaves to the push gate the same way.

### An undecided row neither widens nor narrows

A row carrying the derivation's half and no decision is not kept, so it cannot authorise a
commit, and it is not a ruling, so it does not condemn one. Its node falls to the
bounded-context clause like any other. The count travels on the verdict and is printed,
because `axis-without-a-scope-decision` already owns that fault and a second reporter of one
fault is a second thing to keep in step.

### What decides ownership

Nothing here. Path ownership and node contexts arrive as mappings, resolved by
`beadloom.application.declared_scope` from the graph index, because this domain has no index
to ask — the same split `work-item-type` and `work-item-routing` already use.

## Interfaces

| Name | Purpose |
|------|---------|
| `declared_scope(section, *, document, target_nodes, node_contexts)` | What a `## Axes` section puts inside the approval |
| `check_commit_scope(paths, scope, *, ownership)` | The paths the scope does not cover |
| `DeclaredScope` | Kept nodes, derivation targets, rulings, contexts and the undecided count |
| `ScopeVerdict` | The findings, the paths judged, the paths no node owns and the undecided rows |
| `OUTSIDE_THE_DECLARED_AXES` | The check's name |

## Tests

- `tests/acceptance/features/declared_axes.feature` — the scenarios.
- `tests/test_a_commit_is_judged_against_the_declared_axes.py` — the cases.
