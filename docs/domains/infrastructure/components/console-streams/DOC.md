# Console Streams (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/console_streams.py`

---

## Overview

`tolerate_unencodable_output()` relaxes the error handler on this process's own
`sys.stdout` / `sys.stderr` to `backslashreplace`, so a character the operator's
terminal cannot represent is printed as its escape instead of killing the
command. It does **not** change the streams' codec.

It relaxes the two handlers a console stream carries when nobody chose one —
`strict` under a named locale and `surrogateescape` under C/POSIX — and leaves
alone any handler the operator named through `PYTHONIOENCODING`. The handler's
name cannot answer which of the two it is, which is what the second measurement
below cost.

That distinction is the whole decision. Every other byte stream Beadloom writes
is a **contract** — an installed git hook, `AGENTS.md`, a rules adapter, graph
YAML, a `--json` payload — read back by us or by another program, and therefore
UTF-8 by definition, stated at each call site. A **terminal** is the one stream
whose codec genuinely belongs to the operator's locale: writing UTF-8 into a
latin-1 terminal would put mojibake on their screen. So the codec stays theirs
and only the failure mode changes.

## Why it exists (measured, BDL-061.42)

On `LC_ALL=en_US.ISO-8859-1` (`PYTHONUTF8=0`, `PYTHONCOERCECLOCALE=0`) on a real
Linux image, before this component:

| Invocation | Behaviour |
|------------|-----------|
| `python -m beadloom.ai_agents.ai_techwriter --help` | exit **1**, `UnicodeEncodeError: 'latin-1' codec can't encode character '→'` from inside `click.echo` — the help text carries an arrow |
| `beadloom guard working-branch` on a passing project | **nothing** on stdout: the verdict line carries an em dash, the write died, and a guard whose PASS is silent cannot be told from one that never ran |

A *named* 8-bit locale is a real locale, gets `strict`, and raises, so only the
second `tests-locale` row could find this — "non-UTF-8" and "ASCII" are not the
same environment.

## Why the C room stayed broken afterwards (measured, BDL-068 `beadloom-0mdo.65`)

The paragraph that stood here said the ASCII leg was green because under the
C/POSIX locale CPython already gives `sys.stdout` the `backslashreplace`
handler. That is false, and it is why the fix above stepped aside in the one
room it was most needed in for two further slices.

MEASURED in this room, to a pipe and to a tty alike, `sys.stdout` is `ascii`
with **`surrogateescape`**:

```
Darwin arm64 · CPython 3.13.7 · LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0
```

The room is stated in a code block rather than in the sentence because
`docs audit` reads every semantic-version token in scanned prose as a claim
about *this project's* version, so a measurement naming its interpreter cannot
be written as prose in a scanned document.

That handler re-encodes lone surrogates and nothing else, so an ordinary
non-ASCII character raises exactly as it does under `strict` — and the rule
"a non-strict handler is the operator's decision" read CPython's own default as
a choice and left it in place.

| Invocation, same room | Before | After |
|---|---|---|
| `beadloom docs audit` | exit **1** after 1321 bytes of a partial report, `UnicodeEncodeError: 'ascii' codec can't encode character '\xb1' in position 111` at `rich/console.py` in `self.file.write(text)` — the `±` of the tolerance label | exit **0**, 2277 bytes, the label reading `\xb110%` |
| `beadloom docs audit`, default locale | exit 0, 2275 bytes | unchanged |

Rich is the reachable half and Click is not, which is why the `--help` rows of
the 8-bit measurement above do not cover this: MEASURED in the same room, Click
replaces an ASCII stdout with a UTF-8 writer of its own and emits the raw
`e2 80 94` of an em dash, while a direct `sys.stdout.write` degrades it. Anything
Rich-printing a non-ASCII glyph was in the same position as `docs audit`; the
neighbours swept in that room — `status`, `prime`, `doctor`, `sync-check`,
`lint --strict`, `bd-calls` and `rooms` — all exited 0, so `docs audit` is the
one found rather than the only one possible.

**No CI leg observes this and none will.** The `tests-locale` legs run `pytest`,
and `beadloom ci` runs under the default UTF-8 locale, so the room that reaches
it is an adopter's C-locale container. It was found while confirming the product
was *not* at fault for a red locale leg (`beadloom-0mdo.64`), which is the only
reason it was found at all.

**This is an encode site and not the mirror of the decode sites.** Where
Beadloom reads bytes it does not own — `bd`'s JSON, a git ref name, a filesystem
path — `surrogateescape` is chosen deliberately and argued at each call site,
because it is the only handler of the three that is injective and so no
comparison can be given a wrong answer by a byte. Nothing here compares
anything: the consumer is a terminal, the requirement is that the process
finishes, and `backslashreplace` is total where `surrogateescape` is partial.
Making the two directions agree would answer the encode question with the decode
question's reason.

## Where it is applied

At the **Click entry object** of each of the two console entry points, not in a
group callback:

- `beadloom.services.commands._root.TolerantOutputGroup` (the `beadloom` script);
- `beadloom.ai_agents.ai_techwriter.cli._TolerantOutputCommand`
  (`python -m beadloom.ai_agents.ai_techwriter` and the
  `beadloom-ai-techwriter` script).

Click resolves `--help` while *parsing*, so a group/command callback never runs
for it — and `--help` is one of the two measured failures. Overriding `main()`
keeps `beadloom.services.cli:main` as the console-script target, so no import
path an adopter or a test uses moves. The four-line dispatch is repeated in the
two entry points because they are separate Click objects and a domain may not
import a service; the decision and its reasons live only here.

## What it deliberately does not do

- **Never changes the codec.** The terminal's encoding is the operator's.
- **Never overrides an explicit choice**, and the channel is named rather than
  guessed from the handler. `PYTHONIOENCODING=utf-8:replace` states a handler
  and is left alone; `PYTHONIOENCODING=utf-8` states only a codec and leaves the
  handler to CPython, so it is not a choice of handler. An operator who wants
  byte-exact piping can still ask for `:surrogateescape` and keep it, which the
  handler name alone could not have granted.
- **Never touches a stream it does not understand.** Click's test runner, a
  captured pipe or a redirected buffer has no `reconfigure`; those keep their
  own policy and the command still runs.
- **`replace` was rejected in favour of `backslashreplace`:** U+FFFD tells a
  reader that a character was there and nothing about which one, while `\uXXXX`
  names it and can be searched for in a log.

The function returns the names of the streams it actually reconfigured, so
"nothing needed changing" is distinguishable from "nothing was done" — a silent
no-op is how a policy stops being applied without anyone noticing.

## The read side: a handler as wide as what the read can raise (BDL-061.68)

The section above settles the **codec**. It does not settle what happens when
the bytes do not match it, and that is a separate defect with its own history:
`read_text(encoding="utf-8")` states the codec and still raises
`UnicodeDecodeError` on a byte that is not UTF-8, so `except OSError` around it
catches the file being *absent* and not the file being *unreadable*.

That exact shape was repaired five times in one epic — `beadloom-mr2l.36` (two
instances), `.37` (the tracker probes), `.40` (four call sites), `.42` (a sweep
of about forty) — and then `doc_sync/doc_quality.py`, written after all four,
took the `docs quality` gate down the same way. Five repairs did not reach the
sixth author, so the rule is now enforced by two mechanisms rather than
remembered.

**The codec is stated:** ruff reports text I/O that names no codec. That takes
**three** settings in `pyproject.toml`, and they travel together — any one of them
alone is inert:

| Setting | What it does | What its absence costs |
|---|---|---|
| `select = [..., "PLW1514"]` | asks for `unspecified-encoding` | without it, nothing is reported |
| `preview = true` | `PLW1514` is a preview rule in `ruff==0.16.3`, the release `uv.lock` pins | **selecting a preview rule without it is not an error**: ruff prints `Selection PLW1514 has no effect because preview is not enabled` and exits 0 |
| `explicit-preview-rules = true` | keeps every *other* preview rule out of the selection | without it, enabling preview opts the project into the whole preview rule set at once |

The middle row is the reason all three are named here rather than one. A
config line that reads as a gate, warns, and exits 0 is a gate that checks
nothing — the same class as BDL-UX #172 and #173, measured with `--isolated`
rather than read off the documentation.

`explicit-preview-rules` bounds the rule set; it does **not** stop preview from
changing a STABLE rule's behaviour, and that cost was measured rather than
argued: exactly one new finding on this tree, `RUF002` on the deliberate
latin-1 mojibake docstring in `tests/test_decoding_symmetry.py`, answered with a
line `noqa` carrying its reason rather than by editing the measurement that row
records. Further preview drift arrives with a reviewed lockfile bump, because
ruff is pinned by `uv.lock`. **When the rule graduates:** delete the two knobs,
keep the `select` line — the `noqa` then becomes unused, which `RUF100` says out
loud rather than leaving behind.

Its reach was measured, not read off the rule description: it reports
`Path.read_text` only where it can infer a `Path` receiver — an unannotated
parameter hides the call from it — and it does not look at
`subprocess(text=True)` at all. Over `src/` the reach is broad because
`mypy --strict` makes annotations mandatory there; over `tests/`, type-checked
by nothing, it is partial. The receiver-agnostic AST sweep in
`tests/test_locale_independent_io.py` therefore still covers `src/`, and
`PLW1514` adds `tests/`, which that sweep does not read. Neither instrument
contains the other.

**The handler is wide enough:** `tests/test_decode_handlers.py` holds an AST
ledger of every `try` or `contextlib.suppress` block in `src/beadloom` whose body
decodes text. Measured on this tree: `203` modules parsed, 55 such blocks, 28 of
them narrow — no handler catching `UnicodeDecodeError`, `UnicodeError`,
`ValueError` or a blanket clause. Each of the 28 is listed with the stream it
reads, the answer its handler gives today and what happens instead when the
bytes will not decode. A new narrow block fails the suite; so does a listed one
that is repaired without deleting its row.

The 28 are **not** 28 defects. Each needs the per-site judgement `.42` used — is
this stream a UTF-8 contract we wrote, or somebody else's document in their
codec — and that judgement is `beadloom-mr2l.67`'s, one site at a time. What the
ledger buys before then is that every one of them is a decision on the record
instead of an accident, and that the twenty-ninth cannot be added silently.
