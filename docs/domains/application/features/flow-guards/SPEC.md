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
| `outcome` | `pass` / `warn` / `block` / `skip` / `error` |
| `why` | what was observed — never a restatement of the outcome |
| `not_covered` | what this evaluation did **not** verify |
| `remediation` | the command that resolves a `warn` / `block` |
| `context` | the evaluation context echoed back |

Exit codes carry the outcome, so a shell adapter needs no parsing: `0` for
`pass`/`skip`, `1` for `warn`, `2` for `block`. `3` is reserved for a usage or
configuration error — deliberately not `2`, which is Click's own usage code and
would otherwise be indistinguishable from a genuine block.

`error` is the outcome for **the guard could not answer** — a refused path, a
`guards:` block that will not parse, or any failure inside the evaluation. It is
a verdict rather than an exception because a verdict is recorded, and an
evaluation missing from the firing record is invisible to `--liveness`. It exits
`2`: measured against the adapter this project ships, Claude Code blocks the tool
call on exit 2 and on nothing else, so an outcome that must stop work has exactly
one code available. `1` would be worse than useless here — it is the `warn` code,
which the harness reads as "carry on", and that is precisely how a crashing guard
let an edit through (BDL-061.27, F2). A configuration error additionally keeps
exit `3` at the CLI boundary, so a broken `flow.yml` is still not mistaken for a
guard that fired.

### Configuration

```yaml
guards:
  bead-claimed:
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

**There is no `on:` key, and event routing is not Beadloom's today.** Which tool
invocations count as an edit is decided entirely by the harness adapter — in
Claude Code, the `Edit|Write|MultiEdit|NotebookEdit` matcher in
`.claude/settings.json` —
and which guards run is one settings entry per guard name. Beadloom is told
"evaluate this guard for this context"; it is not told, and does not decide, what
happened. An `on:` key was shipped in the S1 schema and read by no code path, so
it was deleted rather than quoted: a documented key with no consumer teaches an
incantation that has never done anything. It returns, wired to a selector, in S3
when composition and adapters are reworked.

### The path a guard is asked about

The evaluation context carries `path` from the harness (`tool_input.file_path`),
which means it is model-supplied. It is **resolved** — `..` collapsed and
symlinks followed — against the project root before any exclusion is matched
against it. Unresolved, every exclusion was a skeleton key: with `scripts/**`
declared, `scripts/../src/app.py` matched the pattern and skipped, while the
write landed on `src/app.py` and the printed reason was true about the string and
false about the file.

#### The accepted shape, and what happens outside it

**A well-formed edit target is a non-empty string that contains no C0 control
character and no `DEL` (`U+0000`–`U+001F`, `U+007F`), contains no backslash, does
not begin with `~`, and can be encoded for this filesystem (`os.fsencode`);
whitespace at either end is stripped as a transport artifact before it is
judged.** Anything else is refused, unresolved, with a stated reason. Each rule
removes a spelling that means one file to this guard and a different one to
whoever performs the write: a NUL ends the name in the C layer beneath the
writer, a backslash separates directories on the harness's platform and is an
ordinary character on this one, `~` is expanded by a shell and not here, and a
string the filesystem cannot encode names nothing at all. Deliberately not part
of the shape: a length limit (a long path resolves to exactly what it says, and
the OS enforces its own maximum) and percent-encoding (nothing here decodes it,
so `%2e%2e` names a directory called `%2e%2e`).

The shape is narrow because normalising was tried twice and failed twice, in the
same place both times: the first fix taught the resolver about `..` and opened a
NUL crash, and each new normalisation is another guess about what the harness
will write. Refusing is cheaper to reason about than guessing, and it is the
version that stops generating cases.

A refused path produces an **`error` verdict**, which blocks — never a `skip`
("not applicable", and the edit proceeds), never a `warn` (exit 1, which the
harness reads as non-blocking), and never a traceback. It is decided *after*
`strictness: off`, because an opt-out is a deliberate human decision recorded in
`flow.yml` and an inactive guard never looks at the path, and *before* exclusions,
because matching a pattern against a string the guard has refused to interpret is
the bypass this order removes. The verdict names the offending rule, echoes the
target (escaped and bounded at 120 characters), and states the way out: spell the
path POSIX-style, or set the guard's strictness to `off` if such a name is
legitimate in this project.

What remains outside the shape check, named rather than implied: a file whose
name genuinely ends in whitespace is guarded as though it did not; a bare drive
letter (`C:/Users/...`) is well-formed POSIX and is read as a relative directory
called `C:`, because this build of Beadloom resolves paths with POSIX semantics;
and a homoglyph or a Unicode look-alike names a *different* file, which the guard
then reports accurately — the over-guarding direction, and not a bypass.

A path that resolves **outside the project root** is matched against no
exclusion, and the verdict says so in `not_covered`, naming the resolved target.
The guard still runs on its other evidence. An exclusion is written about this
project's tree and cannot speak for anything else, and inheriting a pattern would
give an out-of-project write the same reassuring `skip` as an in-project one.
What is deliberately **not** claimed: no shipped guard decides whether editing
outside the project is acceptable at all.

### Shipped guards

| Guard | Guards that… | Skips when |
|---|---|---|
| `bead-claimed` | an edit happens under a claimed work item | the tracker is unavailable |
| `working-branch` | work happens off the protected trunk (`options.trunk`, default `main`) | no branch is checked out |

### Liveness

Every CLI evaluation appends one line to `.beadloom/guard-firings.jsonl`.
`beadloom guard --liveness` reports, per guard, its effective strictness, how
often it fired, its last outcome, and three ways a gate stops protecting
anything — a gate that cannot demonstrate it ran is treated as not having run.

| Flag | Means | Computed from |
|---|---|---|
| `never-fired` | no firing that reached a verdict (an `error` record does not count) | the firing record |
| `excluded-everywhere` | every strictness is `off`, or nothing escapes the exclusions | the configuration alone |
| `matches no file in the project: '<pattern>'` | a declared exclusion matches nothing that exists right now | the project's files |

The two exclusion flags answer different questions and neither pretends to
answer the other. `excluded-everywhere` asks whether the **exclusion list**
covers everything, by matching it against a fixed representative set of paths
rather than comparing spellings to a list of known catch-alls — the spelling
comparison was wrong in both directions, missing `**/**` and calling `*` a
catch-all though `*` does not cross directories. It is asked of the list and not
of one pattern at a time because `*` and `*/**` are each narrow and together
exempt every path there is. Because it reads the patterns only, it does **not**
report `src/**` in a project whose code is entirely under `src/`; the report
could walk the tree to answer that, and does not, for a measured reason —
declaring an exclusion requires a `.beadloom/flow.yml`, which no realistic
exclusion covers, so a whole-tree flag computed from real files would be `False`
in every project that has one.

`never-fired` counts only firings that reached a verdict. An `error` is recorded
and shown as the last outcome, so a broken guard is visible, but it does not
clear the flag: a gate that has run three times and answered none of them is not
a live gate.

`matches no file in the project` is the project-dependent half: a typo'd
`scrpits/**` exempts nothing, which is the safe direction but was silent until
someone reread `flow.yml`. It is a statement about the tree **right now**, not a
claim that the pattern can never match; a directory added tomorrow revives it.
Vendor and build trees (`.git`, `.venv`, `node_modules`, `build`, `dist`, …) are
not walked, and the walk stops at 20 000 files — both make the report quieter,
never louder.

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
- **A probe reads all of its evidence.** `bd list` paginates at 50 rows by
  default; the tracker probe lifts the limit and asks bd for the claimed beads
  rather than filtering its first page, because a guard reporting a violation of
  a condition that holds is the failure this primitive exists to remove.
- **An exclusion is matched against a resolved path** that is inside the
  accepted shape and inside the project root — never against a refused string
  and never against a target elsewhere on the machine.
- **No invocation that names a registered guard ends without a firing record.**
  A failure that leaves no record is invisible to the one report whose whole
  product is honesty about dead gates. The single exception is a name that is not
  a registered guard: there is nothing to record it against, and the caller's
  shell already carries the error.
- **A guard that cannot answer says so and blocks.** "I could not tell" is a
  verdict (`error`), not an exception, and it never borrows the `warn` code.
- **One decision point.** The CLI, the hook adapter and (from S2) the Gate all
  call `evaluate_guard`, so their verdicts cannot diverge.

## Structure

| Module | Responsibility |
|---|---|
| `models.py` | the verdict and the exit-code contract |
| `contract.py` | what a check receives (request, probes) and returns (finding) |
| `config.py` | the `guards:` block of `flow.yml` — parsing and validation |
| `evaluation.py` | check outcome + strictness + exclusions → verdict |
| `paths.py` | the accepted shape of an edit path, and resolving it against the project root |
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
