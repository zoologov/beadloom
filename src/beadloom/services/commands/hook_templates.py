"""The text of the git hooks ``install-hooks`` writes: pre-commit in two modes, and pre-push.

Lifted out of :mod:`beadloom.services.commands.docsync` in BDL-083 S1a (``beadloom-7i09``),
where about 400 of its 2020 lines were shell text beside four commands. The command that
writes the hooks stays there; this module holds what they say, and nothing else.
"""
# beadloom:component=cli-commands

from __future__ import annotations

from beadloom.doc_sync.engine import REASONS_ATTESTATION_CLEARS
from beadloom.graph.lint_scope import COMMIT_SCOPE_LEAD

#: The codec the installed git hooks are written in. UTF-8 is the hook's own
#: contract — the templates below carry an em dash, git executes the file as
#: bytes, and every reader of it (an editor, a diff, the shell's error message)
#: assumes UTF-8. Left to ``locale.getpreferredencoding(False)`` it was the
#: image's decision instead, which is a wrong answer in both directions
#: (BDL-061.42: 30 of the 108 measured ASCII-leg failures came from this one
#: call site).
HOOK_ENCODING = "utf-8"

#: The header both pre-commit templates open with, and the whole of the #118
#: repair in one place. The hook judges THE COMMIT: it reads what git says this
#: commit stages, and it states the tree it therefore did not judge. Serialising
#: *who* commits does not help — the merge slot orders the commits and leaves the
#: tree exactly as shared as it was — so the boundary has to be what each check
#: is asked about.
HOOK_SCOPE_MARKER = "# beadloom-hook-scope: commit"

HOOK_COMMIT_SCOPE = (
    HOOK_SCOPE_MARKER
    + """
# The line above is a MARKER, not a comment: an installed hook keeps its old
# behaviour until `beadloom install-hooks` is re-run, and nothing tells a
# repository to. `beadloom waves` reads this marker to decide whether the gate a
# concurrent wave is about to commit through judges the commit or the whole tree.
# Measured on this project's own S6 commit, which was judged by the whole-tree
# hook the change had just replaced.

# This hook judges THE COMMIT, not the working tree. In a tree shared by several
# agents -- the mode a multi-agent flow prescribes, not an exotic one -- a
# whole-tree check fails one agent's commit on a neighbour's half-written file,
# in a module the committer never opened (BDL-UX #118). The pre-push Beadloom
# Gate judges the whole tree, so nothing stops being enforced; what moves is WHEN
# a file is judged.
#
# Stated rather than assumed: the content read below is the WORKING-TREE content
# of the staged paths, not the staged blobs, so a partially staged file is judged
# including the part this commit leaves behind.
#
# `outside` reads `git status --porcelain` rather than `git diff --name-only`,
# because the second lists only TRACKED files with unstaged modifications: a
# neighbouring agent's brand-new module is untracked and was not counted, and a
# new module is the largest unjudged thing a neighbour can leave in a shared tree
# (BDL-061.22-4). The second status column is non-blank for a working-tree
# modification and is `?` for an untracked path, so one call answers both.
#
# `staged_py` states WHICH KIND of file this commit stages and never where code
# lives (BDL-UX #240). It selected `^(src|tests)/` until `beadloom-0mdo.42`, and
# that spelling was the gate in front of a derivation: `beadloom-gsal` had just
# replaced the hand-written typed surface with one read from the project's own
# `[tool.mypy]`, and the filter reaching it still named two directories. On the
# flat layout -- the package at the repository root, which is where a Python
# project sits unless someone chose otherwise -- the regex admits no package file
# at all, so with no `tests/` directory the typed leg printed NOTHING (no
# verdict, no NOTHING TO CHECK, no NOT CHECKED) and with one it printed a
# confident sentence about a population the package was not in. The ruff leg
# beside it is gated by the same variable and was equally blind. This repository
# is src-layout and could not observe either, which is why five waves did not.
#
# So each leg now narrows this population by its OWN declaration: the typed leg
# asks `beadloom typed-surface --filter`, and ruff applies the configuration it
# reads for itself. A path filter naming directories is a second list beside
# those declarations, and a second list is a second thing to forget.

staged_py=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '[.]py$')
outside=$(git status --porcelain | awk 'substr($0, 2, 1) != " "' | wc -l | tr -d ' ')
"""
)

#: The coherence block, and the decision it no longer takes for the committer.
#:
#: `active-sync --stage` used to ADD paths to a commit already in flight, and the
#: block below used to announce the addition after the fact. BDL-UX #207 is what
#: that cost: an agent unstaged `.beads/issues.jsonl` deliberately, because it was
#: ANOTHER agent's tracker export, and this hook put it back. The project's own
#: instruction -- commit only your own files, by explicit path -- cannot survive a
#: tool that stages after the decision was taken, so the instruction was never the
#: thing to strengthen.
#:
#: Now `--stage` re-stages only the corrected content of paths the commit ALREADY
#: carries and names what it withheld, which is what this block prints. There is
#: no `git add` here and no addition to detect: the promise is asserted in the
#: suite, over the shipped hook text and over the staging decision itself, rather
#: than by a second check in the hook that would be a second thing to keep in step.
#:
#: The withheld lines are selected with `grep` and printed whole, deliberately not
#: with the `sed -n 's/^# //p'` shape the two porcelain legs above use. That shape
#: is this project's verdict/payload split and means something; borrowing its
#: spelling for an unrelated extraction is how one protocol acquires a second
#: meaning, and `test_the_two_halves_of_the_split_are_paired_in_every_template`
#: said so the first time this block was written.
_HOOK_COHERENCE = """\
# --- ACTIVE / tracker coherence ---
# Guarded no-op: only runs when BOTH `bd` and `beadloom` are installed. In any
# repo without `bd` (or without ACTIVE tables) this block does nothing and never
# blocks the commit. It reconciles the bead-status tables against the tracker and
# refreshes the tracked issues.jsonl, then re-stages ONLY those of them this
# commit already stages. A correction to a path you did not stage is named here
# and left in the working tree for you to decide about.
if command -v bd >/dev/null 2>&1 && command -v beadloom >/dev/null 2>&1; then
  withheld=$(beadloom active-sync --stage 2>/dev/null | grep '^  withheld: ')
  if [ -n "$withheld" ]; then
    echo "beadloom active-sync corrected path(s) this commit does not stage."
    echo "They were NOT added to it:"
    echo "$withheld"
  fi
fi
"""

#: The declared-axes block, written once and used by both templates -- the same
#: comparison in the warn hook and the blocking one, because a commit gate and a
#: push gate disagreeing about what left the approval would be a second home for
#: one answer.
#:
#: `beadloom-0mdo.32`, the residue of `beadloom-mr2l.81`. The call itself has
#: been here since S1; what it did with the answer had a hole. The command was
#: read as `2>/dev/null` and printed only when stdout came back non-empty, while
#: the reason for having compared nothing went to stderr -- so a run that found
#: nothing outside and a run that could attribute no work item were BOTH the
#: empty string here, and the gate printed the same nothing for both. A commit
#: nobody could attribute read as clean, which is the false green BDL-068 exists
#: to remove and the visible consequence of BDL-UX #230 (`beadloom-bdnv`), where
#: a branch named `features/BDL-068-S4` matches no work-item folder at all.
#:
#: Now the command leads its porcelain output with the verdict, marked so this
#: block splits it from the findings without parsing either, and the verdict is
#: printed whatever it says. The count it carries is a count of paths actually
#: COMPARED: the paths no node owns are stated beside it rather than folded in,
#: because a green count that reads as a checked count is the thing being fixed.
_HOOK_DECLARED_AXES = r"""
# --- Declared axes, over the paths this commit stages ---
# The work item is the one the BRANCH names: this hook runs before the commit
# message is finalised, so the `[KEY]` prefix is not readable here. A run that
# finds no branch, no work item, no index or no `## Axes` section reports its
# reason as the verdict and never blocks -- a check with nothing to compare
# against must not read as a clean sheet.
#
# WARNS in both hook modes, including the blocking one, and that is a decision
# rather than an omission. Measured over the eleven commits of `features/BDL-068`
# before this block was written -- 52 paths, 11 a node owns, 41 no node owns, 0
# findings -- the false-positive rate is zero, and that is still not enough to
# block on: only two of those commits touched an owned path at all, and one work
# item in this repository's sixty-four carries an `## Axes` section. A check that
# BLOCKED would meet a repository that cannot satisfy it and be answered with
# `--no-verify`, which is the failure BDL-UX #118 itself was. The branch-scoped
# run in `beadloom ci` reports the same comparison where a reviewer reads it.
axes_report=$(beadloom scope-check --porcelain 2>/dev/null)
axes_verdict=$(echo "$axes_report" | sed -n 's/^# //p')
axes_outside=$(echo "$axes_report" | grep -v '^# ')
if [ -n "$axes_outside" ]; then
  echo "Warning: this commit touches path(s) outside the axes its work item declared:"
  echo "$axes_outside" | sed 's/^/  /'
  echo ""
  echo "Run: beadloom scope-check   (for the axis each path fell outside)"
fi
# An empty verdict means the command produced none -- beadloom absent from PATH,
# or a failure that swallowed its own answer. That is a comparison that could not
# be made, and it prints a different word from one that passed.
if [ -z "$axes_verdict" ]; then
  axes_verdict="Declared axes: NOT CHECKED -- beadloom scope-check returned no verdict here"
fi
echo "$axes_verdict"
"""

#: The type-check block, written once and rendered per mode -- the same surface
#: question in the warn hook and the blocking one.
#:
#: `beadloom-gsal` (BDL-UX #231), and the second attempt at it: `beadloom-mr2l.82`
#: scoped the same check by writing the surface INTO this template, the mypy
#: configuration then moved and the template did not. So the surface is asked for
#: at the moment the hook runs, from the declaration that decides it.
#:
#: What was here before ran `mypy` over every staged `.py` under `src/` or
#: `tests/`, which is wider than anything this project declares typed:
#: `pyproject` sets `packages = ["beadloom"]` and `uv run mypy tests/` reports
#: 970 errors in 90 files, not one of them a violation of a declared standard.
#: MEASURED over all 24 commits of `features/BDL-068` at `b7c9476..49c2ebe`,
#: each against its own tree: 7 staged Python, the old block warned on 4 of the
#: 7, and all 4 warnings were false. The same 4 would have been BLOCKED under
#: the blocking template, which is why block mode was unusable here.
#:
#: Three properties, and each replaces a way the old block carried no
#: information. The count is a count of files ACTUALLY handed to the checker,
#: not of files staged. A commit whose typed population is EMPTY says so in
#: different words from one that was checked and passed, because a check whose
#: population is empty reading as a check that passed is the phantom this epic
#: is named for. And a failure prints MYPY'S OWN OUTPUT: the old block kept
#: `2>/dev/null`, which does not hide mypy's findings -- those go to stdout --
#: but does hide the diagnostics of a mypy that could not START, so "found
#: errors" and "could not run" printed the identical sentence.
#:
#: NOT CHECKED never blocks, in either mode. A surface that could not be derived
#: is a check that did not happen, and turning a missing PATH entry into a
#: refused commit is how a gate gets answered with `--no-verify`.
def hook_type_check(*, blocking: bool) -> str:
    """The mypy block for one hook mode, scoped to the declared typed surface."""
    on_error = (
        '        echo "Error: mypy type errors in this commit \u2014 commit blocked"\n'
        "        failed=1\n"
        if blocking
        else '        echo "Warning: mypy type errors in this commit"\n'
    )
    return _HOOK_TYPE_CHECK_BODY.replace("__ON_ERROR__\n", on_error)


#: The body both modes share. `__ON_ERROR__` is the one line they differ on.
_HOOK_TYPE_CHECK_BODY = r"""
# --- Type check (mypy), over the staged files INSIDE the declared typed surface ---
# The surface is DERIVED, never listed here: `beadloom typed-surface --filter`
# reads the staged paths and answers from the project's own `[tool.mypy]`
# declaration. A list in this template is a second thing to forget, and it was
# forgotten once already (BDL-UX #231).
#
# The verdict leads the command's output marked with `# `, the same marker
# `scope-check --porcelain` uses, so this splits verdict from payload on a shape
# rather than on an agreement between two spellings.
if [ -n "$staged_py" ]; then
  if ! command -v uv >/dev/null 2>&1 || ! command -v beadloom >/dev/null 2>&1; then
    echo "Typed surface: NOT CHECKED -- uv or beadloom is not on PATH here"
  else
    typed_report=$(echo "$staged_py" | beadloom typed-surface --filter 2>/dev/null)
    typed_verdict=$(echo "$typed_report" | sed -n 's/^# //p')
    typed_staged=$(echo "$typed_report" | grep -v '^# ')
    # An empty verdict means the command produced none. That is a comparison
    # that could not be made, and it prints a different word from one that passed.
    if [ -z "$typed_verdict" ]; then
      typed_verdict="Typed surface: NOT CHECKED -- beadloom typed-surface returned no verdict here"
    fi
    echo "$typed_verdict"
    if [ -n "$typed_staged" ]; then
      # `2>&1`, not `2>/dev/null`: a mypy that cannot start says why on stderr,
      # and losing that is what made "found errors" and "could not run" the same
      # sentence. The committer reads mypy's words, not ours.
      mypy_out=$(echo "$typed_staged" | xargs uv run mypy 2>&1)
      if [ $? -ne 0 ]; then
        echo "$mypy_out"
__ON_ERROR__
      fi
    fi
  fi
fi
"""


#: The re-attest instruction, scoped to the reasons re-attesting clears. One
#: wording for the hook and the markdown report, and the scope is read from the
#: engine's allow-list rather than from a list typed here.
REATTEST_INSTRUCTION = (
    "Run `beadloom sync-update {ref_id}` to review and re-attest a pair stale on "
    + ", ".join(sorted(REASONS_ATTESTATION_CLEARS))
)

#: The hook's closing instruction. It prints the porcelain rows and cannot choose
#: per row, so it states which reasons re-attesting clears and that the rest are
#: cleared by revising the document. It said "Run: beadloom sync-update <ref_id>
#: to update docs" for every reason until BDL-069, including the two it cannot
#: clear (BDL-UX #282). Backticks become quotes because the line is echoed inside
#: double quotes, where a backtick is command substitution.
_HOOK_REMEDIATION = (
    REATTEST_INSTRUCTION.format(ref_id="<ref_id>").replace("`", "'")
    + "; any other reason is cleared by revising the document, which re-attesting cannot do"
)


#: The ruff block, written once and rendered per mode, as the type-check block is.
#:
#: BDL-UX #327, measured on 9.0.0 on an adopter's monorepo with the Python backend
#: under `backend/` and nothing Python at the root: `uv run ruff` could not spawn ruff,
#: the leg hid stderr, and the hook printed "ruff lint violations in this commit" for a
#: ruff that never started. Over the same files ruff from `backend/.venv` was clean.
def _hook_ruff_check(*, blocking: bool) -> str:
    """The ruff block for one hook mode, run in the Python project that holds each file."""
    on_violations = (
        '        echo "Error: ruff lint violations in this commit — commit blocked"\n'
        '        echo "Run (in $ruff_where): uv run ruff check --fix <the file(s) named above>"\n'
        "        failed=1\n"
        if blocking
        else '        echo "Warning: ruff lint violations in this commit (in $ruff_where)"\n'
    )
    return _HOOK_RUFF_BODY.replace("__ON_VIOLATIONS__\n", on_violations)


#: The body both modes share. `__ON_VIOLATIONS__` is the one line they differ on.
_HOOK_RUFF_BODY = r"""
# --- Lint check (ruff), over the staged files, in the Python project that holds them ---
# ruff runs from the OUTERMOST directory holding a `pyproject.toml` between the
# repository root and the file -- the root itself when it holds one -- so `uv run`
# finds the environment that project's ruff lives in. ruff then reads the nearest
# configuration above each file by itself (measured: ruff 0.17.1, run from the root,
# applies `backend/pyproject.toml` to `backend/src/a.py`). Outermost rather than
# nearest, because a project can hold whole projects as test data -- this one does,
# under `tests/fixtures/` -- where `uv run` would build an environment inside one.
#
# The files are handed to ruff as arguments, never through `xargs`: BSD xargs reports
# a failing command as 1 and GNU xargs as 123, so ruff's own 1 could not be read on
# either. 0 is clean and 1 is violations. Anything else is a ruff that did not run --
# uv's 2 for a command it could not spawn, the shell's 127 for one that is not there,
# ruff's own 2 for a configuration it could not read -- and it is NOT CHECKED, which
# never blocks, as the typed leg's is not. stderr is shown: hiding it is what made
# "not installed" print as "violations".
ruff_root_of() {
  ruff_found=.
  ruff_dir=$(dirname "$1")
  while [ "$ruff_dir" != "." ] && [ "$ruff_dir" != "/" ]; do
    if [ -f "$ruff_dir/pyproject.toml" ]; then ruff_found=$ruff_dir; fi
    ruff_dir=$(dirname "$ruff_dir")
  done
  if [ -f pyproject.toml ]; then ruff_found=.; fi
  echo "$ruff_found"
}
ruff_check_in() {
  (
    cd "$1" || exit 2
    ruff_prefix="$1/"
    set --
    while IFS= read -r ruff_file; do
      [ "$ruff_prefix" = "./" ] || ruff_file=${ruff_file#"$ruff_prefix"}
      set -- "$@" "$ruff_file"
    done
    uv run ruff check "$@" 2>&1
  )
}
if [ -n "$staged_py" ]; then
  if ! command -v uv >/dev/null 2>&1; then
    echo "Ruff: NOT CHECKED -- uv is not on PATH here"
  else
    echo "Running ruff check on the staged Python file(s)..."
    ruff_roots=$(printf '%s\n' "$staged_py" | while IFS= read -r f; do
      ruff_root_of "$f"
    done | sort -u)
    while IFS= read -r ruff_root; do
      ruff_files=$(printf '%s\n' "$staged_py" | while IFS= read -r f; do
        if [ "$(ruff_root_of "$f")" = "$ruff_root" ]; then echo "$f"; fi
      done)
      ruff_count=$(printf '%s\n' "$ruff_files" | wc -l | tr -d ' ')
      ruff_where="$ruff_root/"
      if [ "$ruff_root" = "." ]; then ruff_where="the repository root"; fi
      ruff_out=$(printf '%s\n' "$ruff_files" | ruff_check_in "$ruff_root")
      ruff_rc=$?
      # ruff's own words first, whatever it said: the committer reads ruff, not us.
      if [ -n "$ruff_out" ]; then echo "$ruff_out"; fi
      if [ $ruff_rc -eq 0 ]; then
        echo "Ruff: $ruff_count staged file(s) checked in $ruff_where -- clean"
      elif [ $ruff_rc -eq 1 ]; then
__ON_VIOLATIONS__
      else
        echo "Ruff: NOT CHECKED in $ruff_where -- ruff did not run (exit $ruff_rc);" \
          "its own words are above"
      fi
    done <<RUFF_ROOTS
$ruff_roots
RUFF_ROOTS
  fi
fi
"""


#: The architecture-lint block, written once and rendered per mode.
#:
#: BDL-UX #326, measured on 9.0.0: the pre-commit hook ran ruff, the typed surface,
#: `sync-check --staged`, `scope-check` and `active-sync`, and no `beadloom lint`. The
#: word "lint" in its description meant ruff, so a graph-boundary violation was not
#: judged at commit time: on the monorepo fixture, with a widget's spec importing the
#: app layer staged, `lint --strict` on the tree exited 1 and the warn-mode hook exited
#: 0 without a line about it.
def _hook_architecture_lint(*, blocking: bool) -> str:
    """The `beadloom lint --staged` block for one hook mode."""
    on_errors = (
        '    echo "Error: architecture lint errors on the node(s) this commit touches'
        ' — commit blocked"\n'
        "    failed=1\n"
        if blocking
        else '    echo "Warning: architecture lint errors on the node(s) this commit touches"\n'
    )
    return _HOOK_LINT_BODY.replace("__ON_ERRORS__\n", on_errors).replace(
        "__LEAD__", COMMIT_SCOPE_LEAD
    )


#: The body both modes share. `__ON_ERRORS__` is the one line they differ on, and
#: `__LEAD__` is the lead `lint --staged` prints its verdict with, spelled once.
_HOOK_LINT_BODY = r"""
# --- Architecture lint (beadloom lint --strict), over the nodes this commit touches ---
# `--staged` narrows the run to the nodes that own a staged path and the findings in a
# staged file, and counts what it left to the push gate, so a neighbour's work in a
# shared tree does not fail this commit (BDL-UX #118). The lint reindexes incrementally
# first. The verdict is the line `lint --staged` leads with; no such line is a lint that
# did not run -- a missing index, a configuration error, a crash -- and is NOT CHECKED,
# which never blocks.
if ! command -v beadloom >/dev/null 2>&1; then
  echo "Architecture lint: NOT CHECKED -- beadloom is not on PATH here"
else
  lint_out=$(beadloom lint --staged --strict --format rich 2>&1)
  lint_rc=$?
  lint_verdict=$(printf '%s\n' "$lint_out" | grep '^__LEAD__')
  if [ -z "$lint_verdict" ]; then
    printf '%s\n' "$lint_out"
    lint_verdict="Architecture lint: NOT CHECKED -- beadloom lint gave no verdict (exit $lint_rc)"
    echo "$lint_verdict; its own words are above"
  elif [ $lint_rc -ne 0 ]; then
    printf '%s\n' "$lint_out"
__ON_ERRORS__
  else
    echo "$lint_verdict"
  fi
fi
"""


HOOK_TEMPLATE_WARN = """\
#!/bin/sh
# pre-commit hook managed by beadloom
""" + HOOK_COMMIT_SCOPE + _hook_ruff_check(blocking=False) + hook_type_check(
    blocking=False
) + _hook_architecture_lint(blocking=False) + """
# --- Doc sync check, over the pairs this commit stages ---
stale=$(beadloom sync-check --staged --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Warning: stale documentation in this commit"
  echo "$stale"
  echo ""
  echo \"""" + _HOOK_REMEDIATION + """\"
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi
""" + _HOOK_DECLARED_AXES + """
# --- What this commit did NOT judge ---
echo "$outside modified or untracked file(s) outside this commit were not judged here;"
echo "the pre-push Gate (beadloom ci) judges the whole tree."

""" + _HOOK_COHERENCE


HOOK_TEMPLATE_BLOCK = """\
#!/bin/sh
# pre-commit hook managed by beadloom
failed=0
""" + HOOK_COMMIT_SCOPE + _hook_ruff_check(blocking=True) + hook_type_check(
    blocking=True
) + _hook_architecture_lint(blocking=True) + """
# --- Doc sync check, over the pairs this commit stages ---
stale=$(beadloom sync-check --staged --porcelain 2>/dev/null)
exit_code=$?

if [ $exit_code -eq 2 ]; then
  echo "Error: stale documentation in this commit — commit blocked"
  echo "$stale"
  echo ""
  echo \"""" + _HOOK_REMEDIATION + """\"
  failed=1
fi

if [ $exit_code -eq 1 ]; then
  echo "Warning: beadloom sync-check failed (index may be stale)"
fi
""" + _HOOK_DECLARED_AXES + """
# --- What this commit did NOT judge ---
echo "$outside modified or untracked file(s) outside this commit were not judged here;"
echo "the pre-push Gate (beadloom ci) judges the whole tree."

""" + _HOOK_COHERENCE + """
if [ $failed -ne 0 ]; then
  exit 1
fi
"""


#: The line `beadloom ci --format rich` states its verdict on, as an extended regular
#: expression the pre-push hook greps for and a test holds against the renderer.
GATE_VERDICT_PATTERN = "^(PASS|FAIL) .*gate (clean|blocked)$"

#: The pre-push hook: the AUTHORITATIVE blocking Beadloom Gate. It runs the full
#: `beadloom ci` and exits non-zero to block the push on red. Idempotent: re-running
#: `install-hooks` overwrites it. `--no-verify` is the documented escape hatch. The
#: pre-commit hook judges the commit; the whole tree is judged here, once per push.
HOOK_TEMPLATE_PRE_PUSH = r"""#!/bin/sh
# pre-push hook managed by beadloom -- the blocking Beadloom Gate.

# Without `beadloom` on the PATH git runs this hook with, the Gate cannot run, and a
# push nobody judged is refused rather than let through (BDL-UX #326, BDL-083 ruling 3).
# The hook is installed per clone by `beadloom install-hooks`, so a missing binary is a
# setup error the person pushing must see. Through 9.0.0 this branch passed in silence.
if ! command -v beadloom >/dev/null 2>&1; then
  echo "Beadloom Gate did not run: 'beadloom' is not on the PATH this hook runs with," \
    "so this push was not judged and is refused." >&2
  echo "Put beadloom on that PATH (activate the project's environment, or install it" \
    "as a tool), or remove the hook: beadloom install-hooks --remove --pre-push" >&2
  echo "To push without the Gate (discouraged): git push --no-verify" >&2
  exit 1
fi

# The Gate's own verdict line decides what this hook says. `--format rich` because it
# is the format that prints one: the default follows git's stdout, and the github
# format prints none. The Gate writes its report to this hook's output itself and a copy
# to a temporary file, and the verdict is read from the copy (BDL-UX #226). Measured at
# 12c35cf3: a hook that captured the report and printed it with the shell's printf lost
# it on a non-blocking pipe whose reader was slow -- under dash the reader got 65575 bytes,
# no verdict line and no sentence from this hook. printf gives up on EAGAIN; the Gate's
# writer waits for the reader. An exit code with no verdict line in the copy is a Gate
# that did not run -- a crash, a missing index -- and is said in those words, never as
# stale documentation.
#
# `say` is this hook's own sentence, retried while the pipe is full. Each sentence is
# shorter than PIPE_BUF (512 bytes on Darwin, the smallest of the supported platforms),
# and a pipe write that short lands whole or not at all, so a retry repeats nothing.
say() {
  say_tries=0
  until printf '%s\n' "$*" 2>/dev/null; do
    say_tries=$((say_tries + 1))
    if [ "$say_tries" -ge 30 ]; then
      return 1
    fi
    sleep 1
  done
}

gate_copy=$(mktemp "${TMPDIR:-/tmp}/beadloom-gate.XXXXXX") || {
  say "Beadloom Gate did not run: no temporary file for its verdict, so this push was" \
    "not judged and is refused."
  exit 1
}
trap 'rm -f "$gate_copy"' EXIT
say "Running Beadloom Gate (beadloom ci)..."
beadloom ci --format rich --tee "$gate_copy"
gate_rc=$?
gate_verdict=$(grep -E '__VERDICT__' "$gate_copy" | tail -n 1)
if [ -z "$gate_verdict" ]; then
  gate_verdict="NOT CHECKED -- the Gate did not run: beadloom ci exited $gate_rc without a verdict"
  say ""
  say "Beadloom Gate: $gate_verdict; its own words are above."
  say "To push without the Gate (discouraged): git push --no-verify"
  exit 1
fi
if [ $gate_rc -ne 0 ]; then
  say ""
  say "Beadloom Gate blocked this push: $gate_verdict"
  case "$gate_verdict" in
    *"step(s) crashed"*)
      say "A step that crashed checked nothing: what it checks was not checked in this" \
        "run. Its exception is listed above under Crashed; any finding above names its" \
        "own fix."
      ;;
    *)
      say "The findings above name their fixes; fix them and push again."
      ;;
  esac
  say "To override (discouraged): git push --no-verify"
  exit 1
fi
""".replace("__VERDICT__", GATE_VERDICT_PATTERN)


def pre_commit_hook_body(*, blocking: bool) -> str:
    """The pre-commit hook text this project installs, in one of its two modes.

    Public because the promise the hook makes is asserted over the text that is
    actually written, not over a copy of it: a test that reads a duplicate of the
    template is a test of the duplicate (BDL-UX #207).
    """
    return HOOK_TEMPLATE_BLOCK if blocking else HOOK_TEMPLATE_WARN
