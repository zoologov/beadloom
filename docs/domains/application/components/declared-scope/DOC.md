# Declared Scope

The work item a branch names, and the scope its `## Axes` section declares — resolved through
the graph index, git and the planning corpus.

**Source:** `src/beadloom/application/declared_scope.py`

---

## Purpose

The join `scope-check` cannot make for itself. The check is a domain question — do these
paths fall outside these axes — and answering it needs three things from outside that domain:
the graph index that says which node owns a path, git for the paths and for the branch, and
the planning corpus that says which folders are work items. This module composes them and
hands the check pure data, the way `work-item-routing` does for `work-item-type`.

## The work item is found by the branch

The pre-commit hook runs BEFORE the commit message is finalised, so the `[BDL-068]` prefix is
not readable at the moment the commit is judged. The branch is, and this project's own
convention (`git switch -c features/<ISSUE-KEY>`) puts the key in it.

The key is not parsed out of a prefix. It is matched against the work items that actually
exist: a folder is the work item when its name is one of the branch's `/`-separated segments.
The population comes from `planning_documents()`, so a project that configures its own
`doc_quality.paths` is judged over its own corpus rather than over this repository's
convention. A branch naming none is NOT CHECKED with a reason.

## Five reasons to have checked nothing

No branch, no work item, no index, no `## Axes` section and no answer from git are different
facts, and each is reported as itself. `ScopeRun.reason` is present exactly when nothing was
checked, so a run that reports no findings and states no reason really did compare the paths.

## Two scopes, one comparison

Without `since` the staged index is judged, which is the commit gate's question. With `since`
the branch is judged against a ref, which is the push gate's: `ref...HEAD` is what a pull
request contains and what the approval was spent on. A commit gate and a push gate
disagreeing about what left the approval would be the second home this epic removes.

## Which ref, and why it matters

`trunk_ref()` prefers `origin/<trunk>` over the local `<trunk>`, and the trunk's name comes
from the `options.trunk` the `working-branch` guard already reads rather than from a second
declaration. This is a measurement, not a preference: on this repository with a local `main`
two commits behind the remote, `--since main` reported another work item's LANDED change as
this branch's and `--since origin/main` did not. `paths_changed_since` uses the three-dot
form for the same reason.

## Which paths a derivation target resolves

`derived_targets()` returns the words a `Derived by` field names; this module resolves each
against the project root and then against the single source package, because the field is
written by a human as often as it is rendered and a human writes `doc_sync/axes_section.py`.
Only an existing FILE is resolved: the rendered field names the sweep root beside the target,
and resolving a directory would put its whole domain inside the approval by accident.

## The same read, rendered for the wave planner

`work_item_axes()` returns what `scope_of_branch()` already read, in the vocabulary
`beadloom waves` compares a bead's declared `refs:` against. A second RENDERING and never a
second read: the commit gate and the wave plan judging one approval differently is the
two-sources-of-truth class this epic exists to remove, and BDL-UX #232 is that class inside
the planner itself.

Two things are added that the commit gate has no use for. The rows the derivation attributed
to **no node** — no declaration can name them, so no comparison can reach them — and the
section's own `Unresolved` field, because a plan compared against an incomplete derivation
has to say so and `beadloom impact` is measurably incomplete on this layout (BDL-UX #225).
The undecided rows are also NAMED here rather than counted: `DeclaredScope` carries a count,
which is all a commit gate needs, while a wave plan compares a named declaration against them.

An unreadable work item comes back as a `WorkItemAxes` carrying the reason rather than as
`None`, so the reason travels with the plan instead of being dropped at the edge.

## Interfaces

| Name | Purpose |
|------|---------|
| `scope_check(project_root, *, branch, since)` | One run: the verdict, the work item and the reason for neither |
| `scope_of_branch(project_root, *, branch)` | The declared scope, or the reason there is none |
| `work_item_axes(project_root, *, branch)` | The same read in the wave planner's vocabulary, carrying its reason when there is nothing to read |
| `work_item_of_branch(project_root, branch)` | The work-item folder a branch names |
| `trunk_ref(project_root)` | The ref a branch's whole work is compared against |
| `ScopeRun` | The verdict, the work item, the document, the scope and the reason |
| `VERDICT_MARKER` | What marks `ScopeRun.describe()` in porcelain output, so a shell gate splits it from the findings |

`VERDICT_MARKER` is `"# "`, and it is declared beside the line it marks rather than at either
end of the pipe. The producer is `beadloom scope-check --porcelain` and the consumer is the
pre-commit hook `install-hooks` writes; a marker each of them spelled for itself would be two
things that can disagree. The split works on a shape rather than an agreement: a finding line
opens with a project-relative path, and no path opens with `# `.

## Tests

- `tests/acceptance/features/declared_axes.feature` — the scenarios.
- `tests/acceptance/features/commit_gate_verdict.feature` — what the gate says it compared.
- `tests/test_a_commit_is_judged_against_the_declared_axes.py` — the cases.
- `tests/test_the_commit_gate_states_what_it_compared.py` — the verdict's stream, and the
  exempt set measured over this branch's own commits.
