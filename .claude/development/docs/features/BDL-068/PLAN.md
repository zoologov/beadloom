# PLAN: BDL-068 — The flow's rules are advice; make them instruments

> **Status:** Approved
> **Created:** 2026-09-02

---

## Epic Description

Six ordered slices. S1 builds the instrument; S2–S6 are the first five things measured by it,
and each is independently shippable. The epic's DAG is the six slices. **A slice's beads are
created when the preceding slice's review closes** — the architectural decision in CONTEXT,
and the re-plan rule expressed as structure rather than as discipline.

## Dependency DAG

```mermaid
graph TD
    S1[S1 impact + Axes + Explore P0] --> S2[S2 review independence P0]
    S1 --> S3[S3 what we measure with P0]
    S2 --> S4[S4 the guards' surface P1]
    S3 --> S4
    S4 --> S5[S5 tracker adapters P1]
    S5 --> S6[S6 documents and roles P2]
```

**Critical path:** S1 → S2 → S4 → S5 → S6. S3 runs after S1 and may run beside S2.

## Beads

Only S1's beads are created now. S2–S6 are carried as slice-level placeholders so the DAG is
visible and the ordering is enforced by dependency rather than by memory.

| ID | Name | Priority | Depends On | Status |
|----|------|----------|------------|--------|
| S1.1 | Lift the three AST derivations out of `tests/` into a production package | P0 | - | Pending |
| S1.2 | `beadloom impact <path\|symbol>` over the lifted derivations, with the unresolved population in the answer | P0 | S1.1 | Pending |
| S1.3 | Validate the derivations retroactively against BDL-067's first dev bead | P0 | S1.1 | Pending |
| S1.4 | `## Axes` in the BRIEF and RFC core templates; `doc-quality` reports its absence | P0 | S1.2 | Pending |
| S1.5 | `Explore` role file, composed by `role-composer`, positioned in `/task-init` step 0.5 | P0 | S1.2 | Pending |
| S1.6 | The commit-scope check: a change outside the work item's declared axes is a finding | P0 | S1.4 | Pending |
| S1.7 | test — the derivations as shapes, the unresolved population, and the two new checks | P0 | S1.3, S1.5, S1.6 | Pending |
| S1.8 | review | P0 | S1.7 | Pending |
| S1.9 | tech-writer | P0 | S1.8 | Pending |
| S2 | slice: the review's independence, reported rather than asserted (#204, #212, #219) | P0 | S1.8 | Pending |
| S3 | slice: what we measure with — mutation runner, the platform axis, the clean-room limit | P0 | S1.8 | Pending |
| S4 | slice: the guards' enforcement surface (#170, `mr2l.81`, `mr2l.60`, `mr2l.82`, `mr2l.92`) | P1 | S2, S3 | Pending |
| S5 | slice: the tracker adapters (#187, #194, #171, #165, #164, #97, #207, #210) | P1 | S4 | Pending |
| S6 | slice: the flow's documents and roles (`mr2l.72`, `mr2l.91`, #191, #213, `iur5`, `ec1a`) | P2 | S5 | Pending |

## Bead Details

### S1.1: Lift the three AST derivations out of `tests/` into a production package

**Priority:** P0 · **Depends on:** — · **Blocks:** S1.2, S1.3

**What to do.** `tests/test_init_branches_that_reach_the_bootstrap.py` (30 cases) derives a
command's writing branches from its own source; `tests/test_one_parent_post_condition_over_every_writer.py`
(25) derives the graph writers by shape; `tests/test_graph_files_are_read_under_one_policy.py`
(15) derives the readers as *lists a directory and parses YAML* over six listing verbs and six
loaders. Move the derivations into a production package under `application/`; the tests keep
their assertions and import the lifted code.

**Done when:**
- [ ] No derivation logic remains in `tests/`, and each test still fails on the shape it was
      written to catch — verified by re-running the mutants those modules already carry.
- [ ] A derivation with no test that fails on a fifth body is NOT lifted; it is reported.
- [ ] `beadloom lint --strict` rc 0 with the new package placed inside the layer rules.

### S1.2: `beadloom impact <path|symbol>`

**Priority:** P0 · **Depends on:** S1.1 · **Blocks:** S1.4, S1.5

**What to do.** Four questions answered from the source — who else writes these files, who
else calls these symbols, how many branches the enclosing command has and how many ways it
terminates — plus the boundary from the graph: which domain each found site belongs to, and
therefore when a change leaves one. Human and `--json` output.

**Done when** — rewritten by S1.3's measurement, which found the answer to both of the
criteria below is a property of the seed and not of the tree:

- [ ] The answer names the population it could not resolve — unparseable module, dynamic
      dispatch, call through a variable — as a field, not an omission.
- [ ] **`impact` derives its seed from the target and names it in the answer.** No invocation
      takes the commit point as an argument and no literal names it. Measured at `af26750d`:
      seeded with `write_yaml_atomic` the lifted derivations list 2 writers and 4 branches of
      `init`; seeded with `bootstrap_project`, the function that bead was changing, they list
      0 writers and 3 branches. Three is the number BDL-067 carried for the whole epic. The
      criteria below are satisfied by a tool that hardcodes `write_yaml_atomic`, which is the
      authored list this epic exists to remove, so they are worth nothing without this one.
- [ ] The answer names the RULE the seed came from, and a target the rule finds no seed for
      puts that in the unresolved population rather than answering over an empty set. A clean
      list is trusted and stopped at.
- [ ] Run against `onboarding/scanner/bootstrap.py` **at `af26750d`**, with no argument naming
      a commit point, it lists both writers of graph nodes.
- [ ] Run against `services/commands/setup.py` at the same commit, on the same terms, it lists
      four entry points of `init` and the exit forms including `sys.exit`. Measured there: the
      commit point is two hops from that file, so a seed rule that stops at the target's own
      callees returns eight first-hop names and not the sink.
- [ ] The seed rule is not stated over `PUTS_BYTES_ON_DISK`. Measured at `af26750d`:
      `write_yaml_atomic` is not among the 268 names that reach a body in that set, because it
      puts its bytes down through `os.fdopen(...).write` and `Path.replace` and the set spells
      `write_text`, `write_bytes` and `open`. Over `SERIALISES_YAML` it is one of two
      candidates from `bootstrap.py`.
- [ ] It is NOT a graph walk: a node whose axes live entirely inside it still produces an answer.

### S1.3: Validate the derivations against BDL-067 retroactively

**Priority:** P0 · **Depends on:** S1.1 · **Blocks:** S1.7

**What to do.** Run the lifted derivations against the tree as it stood at BDL-067's first dev
bead (2026-08-31, before `acf4066`) and answer one question: would they have listed **both**
writers of graph nodes and **four** entry points of `init`?

**Done when:**
- [x] The answer is recorded with the commit it was measured at, whichever way it comes out.
- [x] If it is no, S1.2's acceptance is rewritten against what the derivation actually finds
      before any further slice consumes it. A feature justified by an argument where a
      measurement was available is the defect this epic exists to remove.

**The answer: PARTIAL, and the partial half is the seed.** Measured at `af26750d` — the parent
of `acf4066`, 2026-08-31 22:29 +0300, reached through a detached worktree — on macOS
(Darwin 25.6.0, CPython 3.13.7), in the foreground, with the lifted package imported from
`430d9ae`:

| seeded with | writers of graph nodes | direct callers of the seed | branches of `init` |
|-------------|------------------------|----------------------------|--------------------|
| `write_yaml_atomic`, the commit point | 2 — `bootstrap_project`, `import_docs` | 6 | 4 — `non_interactive`, `bootstrap`, `import_path`, the fallthrough |
| `bootstrap_project`, the function under change | 0 | 3, and `import_docs` is not among them | 3 |

Both facts were inside the derivations' reach on the day, before either was known: the second
writer was first answered in BDL-067's fourth fix cycle and the fourth entry point by its ninth
review. Neither is reached from the function the first dev bead was changing. BDL-067's own
instrument was seeded narrowly until its fifteenth bead, so the seed that gives the right
answer is not the seed that day had. The premise therefore survives as a conditional, and the
condition is now S1.2's hardest criterion rather than an assumption.

The measurement is kept as a check rather than as this paragraph, so the command that re-runs
it is:

```
uv run pytest tests/test_the_seed_decides_what_impact_reports.py
```

Eight cases in three classes. `TestTheSeedDecidesTheAnswer` builds a tree with the shape
`af26750d` had and runs everywhere; `TestTheMeasurementAtTheBdl067Tree` re-runs the original
measurement against the real commit through `git archive`, and skips where the commit is not in
the checkout — which is CI's `tests` job, at `actions/checkout@v5`'s default depth of one. Each
case was demonstrated red: the reachability fixpoint frozen at the seed turns five red, the
writer's payload half removed turns four red, and widening `PUTS_BYTES_ON_DISK` with `write`
and `fdopen` turns the two gap-recording cases red.

Run against the current tree as a control the derivations reproduce the same structure — 2
writers, 6 callers, 4 guards wide and 3 narrow — so the difference between the two rows is the
seed and not the two months between the trees.

### S1.4: `## Axes` as a required section

**Priority:** P0 · **Depends on:** S1.2 · **Blocks:** S1.6

**What to do.** Add the heading to the BRIEF and RFC core templates.
`doc_templates.required_sections` already derives required sections from the composed
template's literal `## ` headings, so the heading makes the section required by the same act
and `doc-quality` reports its absence as `missing_sections` does for any other.

**Done when:**
- [ ] A BRIEF without `## Axes` is a `doc-quality` finding, verified on a document that lacks it.
- [ ] An `## Axes` section that is present and empty is also a finding.
- [ ] The section records the derivation's output AND the human's scope decision, and the
      bead's `refs:` is generated from it (CONTEXT Q1).

### S1.5: The `Explore` role

**Priority:** P0 · **Depends on:** S1.2 · **Blocks:** S1.7

**What to do.** A role file composed by `role-composer` like the other four, whose deliverable
is fixed: the `## Axes` section, paths and lines, no narrative. Positioned inside `/task-init`
before the type is chosen, because the axis count is what says whether a work item is a bug.

**Done when:**
- [ ] `config-check` sees it as a composed artifact, so `setup-agentic-flow` cannot drift it
      independently (#191's shape).
- [ ] `/task-init` cannot reach the type decision without it having run.

### S1.6: The commit-scope check

**Priority:** P0 · **Depends on:** S1.4 · **Blocks:** S1.7

**What to do.** A change touching a call site outside the work item's declared axes is a
finding. `sync-check --staged` and the commit-scoped hook already judge a commit by its paths;
this compares those paths against the axes the work item declared.

**Done when:**
- [ ] A commit touching a path outside the declared axes is reported, verified on a commit
      that does.
- [ ] A commit inside them is silent, verified on one that is — an always-red check is an
      ignored check.
- [ ] The finding names which axis the path fell outside, not merely that it did.

### S1.7: test

**Priority:** P0 · **Depends on:** S1.3, S1.5, S1.6 · **Blocks:** S1.8

Every derivation is asserted as a SHAPE with at least three evasion spellings measured, the
way `.25` did for the readers. Every new check is verified red on a named tree. Any assertion
that cannot fail is declared with its reason.

### S1.8: review · S1.9: tech-writer

**Priority:** P0

The review's assignment is fixed in advance: say whether `impact` under-reports, and on what
tree. A second ISSUES verdict on this slice re-plans it rather than opening a tenth cycle.
