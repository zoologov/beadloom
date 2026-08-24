# Console Streams (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/console_streams.py`

---

## Overview

`tolerate_unencodable_output()` relaxes the error handler on this process's own
`sys.stdout` / `sys.stderr` from `strict` to `backslashreplace`, so a character
the operator's terminal cannot represent is printed as its escape instead of
killing the command. It does **not** change the streams' codec.

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

The asymmetry that hid it for two slices: under the **C/POSIX** locale CPython
already gives `sys.stdout` the `backslashreplace` handler, so the same glyph
degrades quietly and the ASCII leg stayed green. A *named* 8-bit locale is a
real locale, gets `strict`, and raises. This is the defect that only the second
`tests-locale` row could find — "non-UTF-8" and "ASCII" are not the same
environment.

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
- **Never overrides an explicit choice.** A stream whose handler is already
  non-strict — `PYTHONIOENCODING=utf-8:replace`, or `stderr`, which CPython
  hands us as `backslashreplace` — is left alone.
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

**The codec is stated:** ruff's `PLW1514` is selected in `pyproject.toml`. It is a
preview rule in `ruff==0.16.3`, the release `uv.lock` pins, so `preview` and
`explicit-preview-rules` travel with the selection — selecting a preview rule without
them makes `ruff check` print a warning and exit 0, which is a gate that reads as
configured and checks nothing. Its reach was measured, not read off the rule description: it reports
`Path.read_text` only where it can infer a `Path` receiver, and it does not look
at `subprocess(text=True)` at all. The receiver-agnostic AST sweep in
`tests/test_locale_independent_io.py` therefore still covers `src/`, and
`PLW1514` adds `tests/`, which that sweep does not read.

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
