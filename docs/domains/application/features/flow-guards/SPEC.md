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

**Which failures earn `3` rather than `2`** is one line, not a list of cases: `3`
is for a defect in the project's *declared configuration* (a `guards:` block that
will not parse, an exclusion with no reason, a guard name nobody registered) and
for a command line that could not be used at all (no guard named, `--liveness`
with a name, a malformed `--context` pair, an unsupported `--hook` harness). Both
are stable defects that fail identically on every invocation until a human edits
a file, and neither is about a particular edit. Everything that goes wrong while
trying to answer about *this* edit — a hook payload that cannot be decoded or
parsed, a project that cannot be located, an exception anywhere — is an `error`
verdict at exit `2`. That is a change of position for the payload cases, and its
reason is that the payload comes from the harness at edit time: a truncated pipe
or a schema change used to exit `3`, which the harness treats as non-blocking, so
the gate switched itself off loudly while failing open.

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

### The project a guard answers about

With no `--project`, the project root is the **nearest directory at or above the
working directory that contains `.beadloom/`**. With `--project`, that directory
is the root and no search happens — and it must carry the marker itself.

This is a decision with a live alternative, so both sides are stated. Until
BDL-061.29 the root was `Path.cwd()`, and the shipped adapter passes no
`--project`, so the root was wherever the harness happened to have chdir'd.
Measured from `<root>/src/beadloom` in a project whose `flow.yml` declares
`block`: the declared strictness was gone (`block`, exit 2 → the shipped default
`warn`, exit 1, non-blocking), every declared exclusion was gone with it, and the
firing was written to a new `src/beadloom/.beadloom/` that `--liveness` at the
real root never reads — the report showed the guard as never having fired *after
a real evaluation had happened*. It also manufactured a second project root
inside the first, so the next invocation from that directory would find the stray
marker and keep using it: self-entrenching, not one-shot.

**Walking up** was chosen over **refusing to run outside a project root**, which
would have been the consistent extension of "narrow the input" one section below.
The trade-off is what each failure costs. Refusing turns an agent that merely
changed directory into an agent that cannot edit anything, for a reason it cannot
fix from inside the harness; and it does not remove the "cannot locate the
project" path, it only makes it the common case. Walking up is also not the kind
of guess this feature removed elsewhere: that was about repairing a
*model-supplied string*, where every normalisation is a bet on what the harness
will write. A directory tree is not model-supplied, `.beadloom/` is evidence
rather than an inference, and there is exactly one nearest ancestor carrying it.

The marker is `.beadloom/` and not `.git/`, because it is the directory the
guard's own configuration and its own record live in — so the directory that
answers "where does this firing belong" is the one that answers "which `flow.yml`
governs this edit". `.git/` nests (submodules, worktrees) and would name a root
Beadloom knows nothing about.

**A guard that cannot locate a project answers `error`, which blocks, and writes
nothing.** It does not create `.beadloom/` where it stands, and it does not
create one where it was pointed: a silent `skip` at exit 0 was the shape of this
defect, and manufacturing the directory was its self-entrenching half.

**`--project` must name a directory that carries the marker** (BDL-061.31).
Until then any `is_dir()` was honoured, and that made the flag a second route to
the failure this section exists to close: measured through the real binary,
`--project <an ordinary directory>` found no `flow.yml`, silently traded the
project's declared `block` for the shipped default `warn` — a non-blocking exit
1 — and then created `.beadloom/` there when the firing was written, while the
real project's record stayed empty. A missing path, a file, and a directory
with no `.beadloom/` are now one refusal — "the project could not be located" —
which is also the refusal the discovery path gives, not a separate spelling of
it. This removes the case where Click's own validation exited on the block code
with no verdict at all.

A directory the process **may not read** is that same refusal (BDL-061.32).
`click.Path` defaults `readable=True`, and that check runs in Click, so
`--project <an unreadable directory>` was a usage error at exit 2 with no
verdict, no record, and nothing on stdout for `--json` to parse. The option now
declares `readable=False`, which is not a relaxation: the directory is refused
by the boundary, as a verdict a reader and a harness can both act on, instead of
by the argument parser.

The cost, stated because it is real: `--project` can no longer point at a
directory before `beadloom init` has run there. That is the intended reading —
there is no `flow.yml` in such a directory to answer from, so any verdict it
produced would be about the shipped defaults rather than about that project.

This sentence — "the guard manufactures no root" — has now been an understated
honesty note three times in this slice, true of the walk and false through the
flag on each of them. It is therefore quantified rather than asserted: the
claim is checked over **every** way a root can be named (discovery from inside a
project, discovery from outside one, and `--project` naming the project, an
ordinary directory, a subdirectory of the project, a missing path, or a file),
and no row may leave a `.beadloom/` behind that did not already exist.

The residual, named: a **nested** `.beadloom/` — a fixture project checked into a
tree — makes the inner directory the root for every invocation beneath it. That
is what a nested project is, and the verdict names the root it used.

### One boundary per invocation

Every invocation of `beadloom guard` — however it arrives, however it fails —
returns through one function, which produces a verdict and, where there is one to
write, a firing record. A failure anywhere inside it, including in argument
parsing and in the stdin read (i.e. before a guard name is even known), becomes a
recorded verdict of "I could not tell" rather than a traceback. New failure modes
will still appear; the requirement is that they appear in `--liveness` instead of
in a traceback.

The boundary exists because the invariant below was, for three fix cycles,
honoured case by case: each entry path decided for itself whether to record, and
each new one was a fresh place to forget — one of the holes was introduced by the
fix that closed the previous one. The CLI now terminates the process in exactly
one place, and the boundary returns in exactly one statement, which is the step
that records.

**Nothing raised inside the boundary leaves it — the last-resort handler is
`BaseException`, and that has a price** (BDL-061.31). `SystemExit` was caught
from the first version, because a lower layer that terminates the process
without a verdict is the shape of every hole this feature closed.
`KeyboardInterrupt` is the other `BaseException` a running guard actually meets,
and it was not caught: measured, an interrupt during an evaluation escaped to
Click, which turned it into exit **1** — the *warn* code the shipped adapter
reads as "carry on" — with no verdict and no record. That is the one combination
this slice exists to prevent, in a different exception class.

Both sides, because the fix is not free. Catching it means **Ctrl-C during a
guarded edit now BLOCKS that edit**: the interrupt becomes a recorded `error` at
exit 2, not a silent pass at exit 1. Against catching it: an interrupt is the
operator's escape hatch, and turning it into a blocking verdict takes an escape
hatch away and writes a firing the operator did not ask for. For catching it,
which is the decision: SIGINT is delivered to the whole foreground process
group, so the harness's own tool call is interrupted along with the guard and
there is usually no edit left to let through; the verdict is the *honest* one,
because an interrupted guard genuinely did not check anything; and the
alternative makes an interrupt indistinguishable from a passing `warn`, which is
the failure mode every fix cycle in this slice has been about. `_record`'s
handler is as wide, for the same reason: an interrupt landing on the write is a
missing record either way, and the difference is only whether the reader is told.

**The render step cannot choose the exit code.** Printing the verdict happens
after the boundary has decided and recorded, so it is wrapped: a failure there
is reported on stderr and the process still exits on the verdict's code. This
was previously a claim resting on one round's failure to break it — attacked
with a non-UTF-8 stream, a lone surrogate, a closed `fd 1` and a truncated pipe,
none of which reached a raising case — and a claim nobody could break is not a
guarantee.

**The structural pin is as wide as the invariant it is about.** "An exit added
without a record is a diff that reddens" was pinned as calls *named* `exit` in
*one* module, and that is not the same sentence: measured, `sys.exit(0)` placed
inside the boundary function shipped the entire guard suite and all four pins
green while `beadloom guard ""` exited 0, printed nothing and recorded nothing.
The pin now (a) derives its scope from the package rather than listing modules,
so a new module is covered on the day it is added, (b) recognises terminators by
measured effect — every construct it flags is run in a real subprocess and shown
to end one — rather than by name, and (c) asserts, over a generated matrix run
in a subprocess, that every result carries the witness that the recording step
ran: exactly one of `recorded` / `not_recorded_because` is set on every result
the boundary returns.


**A firing is written when the invocation produced a verdict, a project was
located, and the verdict names a registered guard.** The three exceptions are
intrinsic rather than convenient, and each is *reported* on the result (and shown
as `not recorded: <reason>` on stderr, or as `recorded` / `not_recorded_because`
under `--json`) instead of being left to be inferred from a missing line:

| Exception | Why it cannot be otherwise |
|---|---|
| a successful `--liveness` report | it evaluates nothing, so there is no verdict to record, and recording one would inflate the count it prints |
| no project could be located | there is nowhere to write it, and creating a project root is the failure this rule exists to prevent |
| the name is not a registered guard (including no name at all) | there is nothing to attribute the row to, and an invented row is a lie in the one report whose product is honesty |

A fourth case is a failure rather than an exception: if the record cannot be
written (a read-only filesystem, say), the verdict still reaches the reader and
carries the reason the record is missing.

What remains outside the boundary, named rather than implied: an argv **Click
itself** cannot parse — an unknown option — never reaches the callback, so it
exits 2 with Click's usage message and no record. It is fail-closed (the harness
blocks), it fails identically on every invocation, and the reachable cases that
used to hide there (`--project` pointing at a missing directory, and at one this
process may not read) have been moved inside.

**No parameter of the command declares a conversion that can refuse an argv
string** (BDL-061.32) — that is what keeps the paragraph above true as options
are added. A conversion Click can fail is applied *before* the callback, so an
option typed `click.Choice([...])` (the shape `--work-kind` would plausibly
take) would answer a typo with a usage message rather than a verdict. The rule
is therefore quantified over every parameter Click converts on the way in, the
group's options as well as the command's, and is measured through Click's own
parse rather than matched by constructor name — the narrower form of this pin
was blind to `click.Choice`, to `int`, and to the `readable=True` default it
never had to type.

### The path a guard is asked about

`--context KEY=VALUE` is repeatable, and where the same key is supplied more
than once **the last occurrence wins** — the ordinary shell reading of a
repeated scalar flag. It is stated rather than left to be discovered because
"which `path` was the guard actually asked about" is the question every verdict
in this feature is an answer to.

The evaluation context carries `path` from the harness (`tool_input.file_path`),
which means it is model-supplied. It is **resolved** — `..` collapsed and
symlinks followed — against the project root before any exclusion is matched
against it. Unresolved, every exclusion was a skeleton key: with `scripts/**`
declared, `scripts/../src/app.py` matched the pattern and skipped, while the
write landed on `src/app.py` and the printed reason was true about the string and
false about the file.

#### The accepted shape, and what happens outside it

**A well-formed edit target is a string that contains no C0 control character
and no `DEL` (`U+0000`–`U+001F`, `U+007F`), contains no backslash, does not begin
with `~`, and can be encoded for this filesystem (`os.fsencode`); it is judged
exactly as supplied, with nothing removed first.** Anything else is refused,
unresolved, with a stated reason. (An absent or empty target is not a refusal at
all: it is "the harness supplied no path", which the guard states in
`not_covered` — "no path supplied" and "a malformed path" are different facts and
the verdict says which one it saw.) Each rule removes a spelling that means one
file to this guard and a different one to
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

**Nothing is stripped before the judgement, and that is a correction.** An
earlier version removed surrounding whitespace as "a transport artifact", and
`str.strip()` removes every character Python calls whitespace — which includes
nine code points (`\t \n \v \f \r` and `U+001C`–`U+001F`) inside the C0 range
this same paragraph refuses. Two sentences of this document disagreed and the
code resolved the disagreement in the accepting direction: measured with
`src/*.py` excluded and strictness `block`, `'src/app.py\n'` reached `skip`,
quoting an exclusion that does not cover the file the writer would create. Every
character the strip removed is a legal file-name character on this platform, so
removing any of them was the same guess the shape exists to stop making. The
cost, named: a target that arrives with a stray trailing newline is refused
rather than evaluated — the over-guarding direction, with a stated reason and a
way out.

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

What remains outside the shape check, named rather than implied: a bare drive
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

- **Read-only with respect to the index.** No guard writes to the index it
  inspects. The firing record is the one deliberate write, it is not the index,
  and it goes to the project's own `.beadloom/` — a guard never creates a project
  root as a side effect of recording.
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
- **No invocation ends without a verdict, and none that names a registered guard
  in a located project ends without a firing record.** A failure that leaves no
  record is invisible to the one report whose whole product is honesty about dead
  gates. Held by one boundary rather than case by case — see *One boundary per
  invocation* for the three exceptions, each reported on the result rather than
  inferred from its absence.
- **The record is the project's.** The root is discovered by walking up for
  `.beadloom/`, never taken from the working directory and never created: a
  firing written somewhere `--liveness` does not read is indistinguishable from
  no firing at all. `--project` states the root instead of searching for it, and
  must name a directory that carries the marker — a guard manufactures no root
  by any route.
- **Every result carries the witness that the recording step ran.** Exactly one
  of `recorded` / `not_recorded_because` is set on every result the boundary
  returns, so "did this path record?" is a fact about the returned object rather
  than an inference from a line that is not there.
- **Nothing raised inside the boundary leaves it, and nothing after it chooses
  the exit code.** The last-resort handler is `BaseException`, so an interrupt
  is a recorded `error` that blocks rather than an escape at the `warn` code;
  and the render step is wrapped, so a failure while printing cannot move the
  code the harness reads.
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
| `invocation.py` | one invocation end to end: decide, then record or say why not |
| `project_root.py` | locating the project a guard answers about and records into |
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
