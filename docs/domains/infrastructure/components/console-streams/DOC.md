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
