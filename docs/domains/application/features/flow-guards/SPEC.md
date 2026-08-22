# Flow Guards

The named-guard primitive the enforced agentic flow binds to.

**Source:** `src/beadloom/application/guards/`

---

## Specification

### Purpose

A guard answers one process question about one situation — "is this edit covered
by a claimed work item?", "is this happening off the protected trunk?" — and
returns a verdict a harness can act on without parsing anything. The primitive
exists so that the flow's rules stop being prose a model may ignore: the
condition is declared in `.beadloom/flow.yml`, evaluated by Beadloom, and bound
to a tool by an adapter that contains no logic of its own.

### Verdict

`evaluate_guard(name, *, project_root, context, probes, config)` returns a
`GuardVerdict`:

| Field | Meaning |
|---|---|
| `guard` | the registered guard name |
| `outcome` | `pass` / `warn` / `block` / `skip` |
| `why` | what was observed — never a restatement of the outcome |
| `not_covered` | what this evaluation did **not** verify |
| `remediation` | the command that resolves a `warn` / `block` |
| `context` | the evaluation context echoed back |

Exit codes carry the outcome, so a shell adapter needs no parsing: `0` for
`pass`/`skip`, `1` for `warn`, `2` for `block`. `3` is reserved for a usage or
configuration error — deliberately not `2`, which is Click's own usage code and
would otherwise be indistinguishable from a genuine block.

### Configuration

```yaml
guards:
  bead-claimed:
    on: [edit]
    strictness: { default: warn, epic: block, chore: off }
    exclusions:
      - path: "scripts/**"
        reason: "operational scripts are not bead-scoped"
        until: "BDL-0xx introduces a scripts node"
```

Strictness is resolved per work kind (`--context work_kind=epic`), falling back
to `default` and then to `warn`. Exclusion patterns follow POSIX glob semantics
where `**` crosses directories and `*` does not, so `src/*.py` cannot silently
exempt a subtree.

An absent `guards:` block is not an error: every registered guard runs at the
shipped default (`warn`), so upgrading Beadloom adds warnings that name what
they did not check — never a new red build.

### Shipped guards

| Guard | Guards that… | Skips when |
|---|---|---|
| `bead-claimed` | an edit happens under a claimed work item | the tracker is unavailable |
| `working-branch` | work happens off the protected trunk (`options.trunk`, default `main`) | no branch is checked out |

### Liveness

Every CLI evaluation appends one line to `.beadloom/guard-firings.jsonl`.
`beadloom guard --liveness` reports, per guard, its effective strictness, how
often it fired, its last outcome, and whether it is `never-fired` or
`excluded-everywhere` — a gate that cannot demonstrate it ran is treated as not
having run.

## Invariants

- **Read-only.** No guard writes to the index it inspects; the firing record is
  the only file guards write, and it is not the index.
- **`skip` always carries a reason.** A guard that silently does not apply is
  indistinguishable from one that passed.
- **A `warn` always names what it did not check** (`not_covered` is never empty).
- **An exclusion carries `reason` and `until`.** One without either is a
  configuration error, because an unnamed, undated exclusion disables a gate
  permanently by accident.
- **A guard name with no implementation is a configuration error**, not a no-op,
  so a typo in `flow.yml` cannot quietly switch a gate off.
- **Unavailable evidence skips, never passes.** A probe that cannot answer
  returns `None`, and the guard reports why.
- **One decision point.** The CLI, the hook adapter and (from S2) the Gate all
  call `evaluate_guard`, so their verdicts cannot diverge.

## Structure

| Module | Responsibility |
|---|---|
| `models.py` | the verdict and the exit-code contract |
| `contract.py` | what a check receives (request, probes) and returns (finding) |
| `config.py` | the `guards:` block of `flow.yml` — parsing and validation |
| `evaluation.py` | check outcome + strictness + exclusions → verdict |
| `firing.py` | the append-only firing record |
| `liveness.py` | which guards are actually protecting something |
| `hook_payload.py` | translating a harness hook event into guard context |
| `checks/` | the shipped guards, one module each |

Checks read the world exclusively through the ports in `contract.py`. The
concrete probes live in `services/guard_probes.py` because the `bd` seam is in
the services layer, which the application layer must not import.

## Related

- `docs/services/components/guard-probes/DOC.md` — the real `bd` / `git` probes
- `docs/domains/onboarding/components/guard-hooks/DOC.md` — the emitted adapter
- `docs/services/cli.md` — `beadloom guard`
