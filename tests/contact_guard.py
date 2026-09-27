"""Fail the test that reaches this repository's live state: its index, tracker or history.

Why this exists (BDL-074 A1)
----------------------------
The product defaults a missing root to ``Path.cwd()`` in 52 places, and that is
correct CLI behaviour. A test that relied on that default measured this
repository's working tree, which is also the tree the suite runs in: the live
``.beadloom/beadloom.db``, the tracker under ``.beads/`` and the git history.
Such a test depends on the machine and on the order the suite ran in, and
``beadloom-qq6m`` was one such flake. The suite now moves every test into an
empty directory (``tests/conftest.py``). This guard catches the contacts that
still arrive by an explicit path, a ``cwd=`` or a ``-C``.

It is the sibling of :mod:`tests.tracked_write_guard`: that guard is about
WRITES to tracked files, this one about CONTACT with state git does not track.
Both deliver their verdict from the same conftest hook, in the call phase.

What counts as a contact, stated as a list somebody can check
-------------------------------------------------------------
* ``live index`` — ``sqlite3.connect`` or ``open`` of ``<root>/.beadloom/beadloom.db``
  (and its ``-wal`` / ``-shm`` / ``-journal`` sidecars); a ``beadloom`` process
  (the executable, or ``python -m beadloom…``) whose ``--project`` or, without
  one, whose working directory is inside the root;
* ``tracker`` — ``open`` of a file under ``<root>/.beads/``; a ``bd`` process whose
  working directory, ``--db`` or ``BEADS_DIR`` / ``BEADS_DB`` is inside the root,
  or that is handed an absolute path inside it;
* ``git history`` — ``open`` of a file under ``<root>/.git/``; a ``git`` process
  whose working directory after every ``-C``, or whose ``GIT_DIR`` / ``--git-dir``,
  is inside the root, or that is handed an absolute path inside it (a clone).

Honest limits, because a guard that overstates its reach is what it guards against
----------------------------------------------------------------------------------
* It observes the interpreter's audit events (``open``, ``sqlite3.connect``,
  ``subprocess.Popen``, ``os.system``). What a CHILD process does is not visible,
  so a tool is classified by what it is asked to do: ``sh -c "git …"``,
  ``uv run beadloom …`` and a nested ``python -m pytest`` are not classified.
* A RELATIVE path opened by a low-level ``os.open`` (the audit event's mode is
  ``None``) is not classified: it may be relative to a ``dir_fd`` the event does
  not carry, and resolving it against the cwd names a different file (measured:
  pytest's temp-dir cleanup opens ``.git`` of a temp repo that way). The same
  limit, for the same reason, as the tracked-write guard's.
* Paths are compared as strings after normalisation, like the tracked-write
  guard: a symlinked spelling of the root, or a different letter case on a
  case-insensitive disk, is not recognised.
* Code that runs at COLLECTION time, before any test and before the empty
  directory is entered, is recorded as "outside any test" and reported in the
  terminal summary rather than failing a test that did not make it.
"""

from __future__ import annotations

import os
import shlex
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import unquote

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence
    from pathlib import Path

LIVE_INDEX = "live index"
TRACKER = "tracker"
GIT_HISTORY = "git history"

#: Where a contact made outside any test (collection, session teardown) is filed.
OUTSIDE_ANY_TEST = "outside any test"

_INDEX_FILE = ".beadloom/beadloom.db"
_INDEX_SIDECARS = ("", "-wal", "-shm", "-journal")
_TRACKER_DIR = ".beads"
_GIT_DIR = ".git"

_PROCESS_EVENTS = frozenset({"subprocess.Popen", "os.system"})
_OBSERVED_EVENTS = frozenset({"open", "sqlite3.connect", *_PROCESS_EVENTS})


@dataclass(frozen=True)
class Contact:
    """One contact: what was reached, how, and in which test and phase."""

    kind: str
    detail: str
    during: str

    @property
    def nodeid(self) -> str:
        """The test the contact was made in, without its phase suffix."""
        return self.during.rsplit(" (", 1)[0]


@dataclass(frozen=True)
class AllowedContact:
    """A test permitted to reach the live state, and why. ``target`` is a node-id prefix."""

    target: str
    reason: str

    def covers(self, nodeid: str) -> bool:
        return (
            nodeid == self.target
            or nodeid.startswith(self.target + "::")
            or nodeid.startswith(self.target + "[")
        )


#: Why each entry below may reach the live state, and what retires it. Every
#: reason names what the test asserts on THIS repository; every exit names the
#: bead that removes the entry, so the list only ever shrinks. A1 printed 44
#: entries; A2 (beadloom-kixx) moved the 24 it was the exit of — 20 on this
#: repository's graph, 4 on its tracker export — onto the self-check snapshot
#: (``self_check_snapshot`` in tests/conftest.py), leaving 20.
_OWN_COMMITS = (
    "judges this repository's own commits, so it reads its git history (its index "
    "is the self-check snapshot's since A2, and that snapshot carries the history "
    "too); exit: A3 (beadloom-2esy) triage"
)
_OWN_BD_CALL_SITES = (
    "derives this repository's own bd call sites, and the derivation also reads the "
    "git hooks installed in this checkout; exit: A3 (beadloom-2esy) triage"
)
_GATE_DUPLICATE_LINT = (
    "lints this repository, which repeats the Gate's required `lint` leg; exit: "
    "A3 (beadloom-2esy) removes it and names the leg"
)
_REAL_PROBES = (
    "measures the real index and the real bd/git probes by design, and its tmp_path "
    "twin is the test above it; exit: A3 (beadloom-2esy) decides whether it stays"
)

_BD_CALL_SITES = "tests/test_bd_call_sites.py"

#: The tests allowed to reach this repository's live state. Printed at the top of
#: every run. Nothing is added to it without a reason that says what the test
#: asserts on this repository and which bead retires the entry.
ALLOWED_CONTACTS: tuple[AllowedContact, ...] = (
    # -- this repository's own commits ---------------------------------------
    AllowedContact(
        "tests/test_a_commit_is_judged_against_the_declared_axes.py"
        "::TestTheCheckOnThisRepositorysOwnCommits",
        _OWN_COMMITS,
    ),
    AllowedContact(
        "tests/test_a_commit_is_judged_against_the_declared_axes.py"
        "::TestTheRowsTheseCasesDependOn",
        _OWN_COMMITS,
    ),
    AllowedContact(
        "tests/test_the_commit_gate_states_what_it_compared.py"
        "::TestTheExemptSetOnThisRepositorysOwnCommits",
        _OWN_COMMITS,
    ),
    AllowedContact(
        "tests/test_the_gate_checks_the_surface_the_project_declared.py"
        "::TestThePopulationTheDecisionWasTakenOver",
        _OWN_COMMITS,
    ),
    AllowedContact(
        "tests/test_impact_derives_the_seed_it_answers_from.py"
        "::TestTheAcceptanceTargetsAtTheBdl067Tree",
        _OWN_COMMITS,
    ),
    AllowedContact(
        "tests/test_the_seed_decides_what_impact_reports.py::TestTheMeasurementAtTheBdl067Tree",
        _OWN_COMMITS,
    ),
    # -- this repository's own bd call sites, hooks included -----------------
    AllowedContact(
        f"{_BD_CALL_SITES}::test_no_python_call_site_of_ours_is_left_unsettled",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        f"{_BD_CALL_SITES}::test_every_python_list_call_names_the_population_it_asked_for",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        f"{_BD_CALL_SITES}::test_the_hook_channel_reaches_the_file_no_python_sweep_can_see",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        f"{_BD_CALL_SITES}"
        "::test_the_most_relied_upon_assumption_in_this_flow_is_named_at_its_sites",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        f"{_BD_CALL_SITES}::test_the_derivation_names_what_it_did_not_reach",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        "tests/test_bd_answers.py"
        "::test_no_artifact_of_ours_instructs_the_suggestion_without_its_confirmation",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        "tests/test_bd_answers.py"
        "::test_the_project_asks_bd_ready_for_its_whole_answer_wherever_it_asks_at_all",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        "tests/test_bead_creation.py::TestTheAnswerIsReadFromBdRatherThanScraped"
        "::test_the_creation_site_is_visible_to_the_derivation_that_judges_it",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        "tests/test_bead_creation.py::TestThisProjectSOwnPopulation"
        "::test_no_python_call_site_of_ours_authors_a_bead_id",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        "tests/test_s5_the_instruments_agree.py"
        "::test_the_two_command_families_the_coordinator_runs_are_still_unjudged",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        "tests/test_s5_the_instruments_agree.py"
        "::test_no_instruction_of_ours_leaves_a_creation_or_wiring_assumption_unsettled",
        _OWN_BD_CALL_SITES,
    ),
    AllowedContact(
        "tests/test_s5_the_instruments_agree.py"
        "::test_every_call_to_the_seam_in_this_package_is_visible_to_the_derivation",
        _OWN_BD_CALL_SITES,
    ),
    # -- a Gate duplicate, and a probe of the real thing ---------------------
    AllowedContact("tests/test_integration_v1.py::TestSelfLint", _GATE_DUPLICATE_LINT),
    AllowedContact(
        "tests/test_guards_parity.py::TestGuardsAreReadOnly"
        "::test_the_live_repo_index_is_byte_identical_after_a_real_evaluation",
        _REAL_PROBES,
    ),
)


def _normalise(raw: str, base: str | None = None) -> str:
    """``raw`` as a normalised absolute path string, without touching the disk."""
    if not os.path.isabs(raw):  # noqa: PTH117 - string arithmetic on every open(), on purpose
        raw = os.path.join(base or os.getcwd(), raw)  # noqa: PTH109,PTH118 - same reason
    return os.path.normpath(raw)


def _as_text(value: object) -> str | None:
    """A path-like or string ``value`` as text; ``None`` for a descriptor or anything else."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "surrogateescape")
    if isinstance(value, str):
        return value
    if hasattr(value, "__fspath__"):
        return _as_text(os.fspath(value))  # type: ignore[arg-type]  # guarded by hasattr
    return None


def _argv(args: object) -> list[str]:
    """A process's argument vector as text, whether it was a list or a shell string."""
    text = _as_text(args)
    if text is not None:
        try:
            return shlex.split(text)
        except ValueError:
            return text.split()
    if isinstance(args, (list, tuple)):
        return [t for t in (_as_text(a) for a in args) if t is not None]
    return []


def _tool(argv: Sequence[str]) -> str:
    """The tool a process runs: ``git``, ``bd``, ``beadloom`` or the executable's name."""
    if not argv:
        return ""
    name = os.path.basename(argv[0]).lower().removesuffix(".exe")  # noqa: PTH119 - string-level
    if name.startswith("python") and "-m" in argv:
        index = argv.index("-m")
        if index + 1 < len(argv) and argv[index + 1].split(".", 1)[0] == "beadloom":
            return "beadloom"
    return name


def _option(argv: Sequence[str], flag: str) -> list[str]:
    """Every value given to ``flag``, in either ``--flag value`` or ``--flag=value`` form."""
    values: list[str] = []
    for index, token in enumerate(argv):
        if token == flag and index + 1 < len(argv):
            values.append(argv[index + 1])
        elif token.startswith(flag + "="):
            values.append(token[len(flag) + 1 :])
    return values


class ContactGuard:
    """Records every contact a test makes with ``root``'s live index, tracker or history."""

    def __init__(self, root: Path | str, allowed: Iterable[AllowedContact] = ()) -> None:
        self.root = os.path.realpath(os.fspath(root))
        self._prefix = self.root + os.sep
        self.allowed: tuple[AllowedContact, ...] = tuple(allowed)
        self._contacts: list[Contact] = []
        #: Classification failures, reported rather than raised (see :meth:`observe`).
        self.errors: list[str] = []
        self._observing = False
        self._suspended = False

    # -- classification -----------------------------------------------------

    def _inside(self, path: str) -> bool:
        return path == self.root or path.startswith(self._prefix)

    def _relative(self, path: str) -> str | None:
        """``path`` relative to the root, ``None`` when it is outside."""
        if path == self.root:
            return "."
        if not path.startswith(self._prefix):
            return None
        return path[len(self._prefix) :].replace(os.sep, "/")

    def _file_kind(self, raw: object) -> tuple[str, str] | None:
        """``(kind, relative path)`` when an opened file is part of the live state."""
        text = _as_text(raw)
        if text is None:
            return None
        rel = self._relative(_normalise(text))
        if rel is None:
            return None
        if any(rel == _INDEX_FILE + sidecar for sidecar in _INDEX_SIDECARS):
            return LIVE_INDEX, rel
        top = rel.split("/", 1)[0]
        if top == _TRACKER_DIR:
            return TRACKER, rel
        if top == _GIT_DIR:
            return GIT_HISTORY, rel
        return None

    def _database_kind(self, database: object) -> tuple[str, str] | None:
        text = _as_text(database)
        if text is None:
            return None
        if text.startswith("file:"):
            text = unquote(text[len("file:") :].split("?", 1)[0])
            if text.startswith("//"):
                text = text[2:]
        return self._file_kind(text)

    def _process_kind(self, argv: list[str], cwd: str, env: Mapping[str, str]) -> str | None:
        """The kind of contact a process makes, or ``None`` when it is not rooted here."""
        tool = _tool(argv)
        if tool == "beadloom":
            projects = _option(argv, "--project")
            where = _normalise(projects[-1], cwd) if projects else cwd
            return LIVE_INDEX if self._inside(where) else None
        if tool == "git":
            return GIT_HISTORY if self._git_rooted_here(argv, cwd, env) else None
        if tool == "bd":
            return TRACKER if self._bd_rooted_here(argv, cwd, env) else None
        return None

    def _names_a_path_here(self, argv: Sequence[str]) -> bool:
        return any(os.path.isabs(t) and self._inside(os.path.normpath(t)) for t in argv[1:])  # noqa: PTH117

    def _git_rooted_here(self, argv: list[str], cwd: str, env: Mapping[str, str]) -> bool:
        where = cwd
        for value in _option(argv, "-C"):
            where = _normalise(value, where)
        git_dirs = [*_option(argv, "--git-dir"), *([env["GIT_DIR"]] if "GIT_DIR" in env else [])]
        if git_dirs:
            where = _normalise(git_dirs[0], where)
        return self._inside(where) or self._names_a_path_here(argv)

    def _bd_rooted_here(self, argv: list[str], cwd: str, env: Mapping[str, str]) -> bool:
        declared = [*_option(argv, "--db"), env.get("BEADS_DIR", ""), env.get("BEADS_DB", "")]
        if any(value and self._inside(_normalise(value, cwd)) for value in declared):
            return True
        return self._inside(cwd) or self._names_a_path_here(argv)

    # -- recording ----------------------------------------------------------

    def observe(self, event: str, args: tuple[object, ...]) -> None:
        """The audit hook's body: record a contact the event makes, if it makes one."""
        if event not in _OBSERVED_EVENTS or self._observing or self._suspended:
            return
        self._observing = True
        try:
            self._record(self._classify(event, args))
        except Exception as exc:  # an audit hook that raises breaks the open() it saw
            # The guard must never change what the observed operation does, so a
            # classification bug is kept and reported in the terminal summary instead.
            self.errors.append(f"{event}: {exc!r}")
        finally:
            self._observing = False

    def _classify(self, event: str, args: tuple[object, ...]) -> tuple[str, str] | None:
        if event == "open":
            if args[1] is None and not os.path.isabs(_as_text(args[0]) or "/"):  # noqa: PTH117
                # A low-level `os.open` may carry a `dir_fd` the event does not
                # report, so a relative name cannot be resolved (see module notes).
                return None
            found = self._file_kind(args[0])
            return None if found is None else (found[0], f"open({found[1]})")
        if event == "sqlite3.connect":
            found = self._database_kind(args[0])
            return None if found is None else (found[0], f"sqlite3.connect({found[1]})")
        if event == "os.system":
            argv, cwd, env = _argv(args[0]), os.getcwd(), os.environ  # noqa: PTH109
        else:
            _executable, raw_args, raw_cwd, raw_env = args
            argv = _argv(raw_args)
            cwd = _normalise(_as_text(raw_cwd) or os.getcwd())  # noqa: PTH109
            env = raw_env if isinstance(raw_env, dict) else os.environ
        kind = self._process_kind(argv, cwd, env)
        if kind is None:
            return None
        return kind, f"{shlex.join(argv)}  (cwd {cwd})"

    def _record(self, found: tuple[str, str] | None) -> None:
        if found is None:
            return
        during = os.environ.get("PYTEST_CURRENT_TEST", OUTSIDE_ANY_TEST)
        contact = Contact(kind=found[0], detail=found[1], during=during)
        if contact not in self._contacts:
            self._contacts.append(contact)

    @contextmanager
    def suspended(self) -> Iterator[None]:
        """Record nothing for the duration — for the one sanctioned reader of the live tree.

        The self-check snapshot (tests/self_check_snapshot.py) copies the working
        tree, the tracker export among it, and clones the git history: reading the
        live tree is its whole job, done once per session, and it touches no index.
        Nothing else suspends the guard; the conftest's terminal summary states
        what the snapshot read.
        """
        previous, self._suspended = self._suspended, True
        try:
            yield
        finally:
            self._suspended = previous

    def take(self) -> list[Contact]:
        """Return and clear what has been recorded."""
        recorded, self._contacts = self._contacts, []
        return recorded

    def allows(self, nodeid: str) -> bool:
        return any(entry.covers(nodeid) for entry in self.allowed)

    # -- reporting ----------------------------------------------------------

    def describe(self, contacts: Sequence[Contact]) -> str:
        """The failure message: what was reached, how, and the way out."""
        lines = [
            "this test reached this repository's LIVE state (BDL-074 contact guard):",
            *(f"  - {c.kind}: {c.detail}   [{c.during}]" for c in contacts),
            "",
            f"root: {self.root}",
            "A test that reads the live index, tracker or git history measures whatever "
            "state the working tree is in, so its result depends on the machine and the "
            "order the suite ran in. Give it an explicit root instead: build the project "
            "in `tmp_path` (or an adopter fixture) and pass it as `--project`, `cwd=` or "
            "`-C`. Only a test that genuinely asserts on this repository belongs in "
            "ALLOWED_CONTACTS (tests/contact_guard.py), with its reason.",
        ]
        return "\n".join(lines)

    def listing(self) -> list[str]:
        """The allowed list as printed at the top of every run."""
        lines = [
            f"contact guard: {len(self.allowed)} test node(s) allowed to reach the live "
            f"state of {self.root}, each with its reason and the bead that retires it:"
        ]
        lines.extend(f"  {entry.target}  -- {entry.reason}" for entry in self.allowed)
        return lines

    # -- installation -------------------------------------------------------

    def install(self) -> ContactGuard | None:
        """Make this guard the one the audit hook reports to; return the one it replaced.

        An audit hook cannot be removed once added, so ONE hook is added per process
        and dispatches to whichever guard is installed; :meth:`uninstall` hands the
        hook back to the guard this one replaced.
        """
        global _INSTALLED
        if not _HOOK_ADDED:
            _add_hook()
        previous, _INSTALLED = _INSTALLED, self
        return previous

    def uninstall(self, previous: ContactGuard | None = None) -> None:
        global _INSTALLED
        if _INSTALLED is self:
            _INSTALLED = previous


_INSTALLED: ContactGuard | None = None
_HOOK_ADDED = False


def _dispatch(event: str, args: tuple[object, ...]) -> None:
    guard = _INSTALLED
    if guard is not None and event in _OBSERVED_EVENTS:
        guard.observe(event, args)


def _add_hook() -> None:
    global _HOOK_ADDED
    sys.addaudithook(_dispatch)
    _HOOK_ADDED = True
