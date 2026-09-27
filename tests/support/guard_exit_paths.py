"""Every exit path of one guard invocation, and the failures injected into its recording step."""

from __future__ import annotations

#: A guard declared blocking, with one ordinary exclusion over ``src/``.
BLOCKING_WITH_EXCLUSION = (
    "guards:\n"
    "  bead-claimed:\n"
    "    strictness: { default: block }\n"
    "    exclusions:\n"
    "      - path: 'src/*.py'\n"
    "        reason: 'generated sources'\n"
    "        until: 'BDL-999'\n"
)


#: Stands in, inside a row's argv, for a directory that exists and is not a project.
NOT_A_PROJECT = "{not_a_project}"


#: (label, argv-after-the-name, stdin, flow.yml, guard name, exit code).
#: Whether the row records is NOT a column — see :func:`_should_record`.
EXIT_PATHS: tuple[tuple[str, str | None, list[str], str, str, int], ...] = (
    ("a guard that passes", "working-branch", [], BLOCKING_WITH_EXCLUSION, "", 0),
    (
        "a guard that blocks",
        "bead-claimed",
        ["--context", "path=app.py"],
        BLOCKING_WITH_EXCLUSION,
        "",
        2,
    ),
    (
        "an excluded path",
        "bead-claimed",
        ["--context", "path=src/a.py"],
        BLOCKING_WITH_EXCLUSION,
        "",
        0,
    ),
    (
        "a refused path",
        "bead-claimed",
        ["--context", "path=src\\app.py"],
        BLOCKING_WITH_EXCLUSION,
        "",
        2,
    ),
    ("an unreadable flow.yml", "bead-claimed", [], "guards: [1, 2\n", "", 3),
    (
        "an exclusion with no reason",
        "bead-claimed",
        [],
        "guards:\n  bead-claimed:\n    exclusions:\n      - path: 'x/**'\n",
        "",
        3,
    ),
    ("a guard name nobody registered", "no-such-guard", [], BLOCKING_WITH_EXCLUSION, "", 3),
    ("no guard name at all", None, [], BLOCKING_WITH_EXCLUSION, "", 3),
    (
        "a malformed --context pair",
        "bead-claimed",
        ["--context", "nonsense"],
        BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        "a --context pair with an empty key",
        "bead-claimed",
        ["--context", "=value"],
        BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        # Exit 1 since BDL-UX #254, having been 3 until BDL-061.33 and 2 between
        # them. Every other row that answers 3 is reachable from a shell, where 3
        # keeps a declared-configuration defect distinct from a guard that fired;
        # this one names a harness, and a harness reads only the code. It is an
        # `unresolved` verdict — the guard could not evaluate itself, because it
        # cannot translate the payload this binding sends — and the repair is an
        # edit to the binding, which the blocking code forbade. The hooked twin
        # of each 3-row is derived from this table in
        # ``tests/test_guards_unresolved.py`` rather than written out again.
        "a harness nobody supports",
        "bead-claimed",
        ["--hook", "no-such-harness"],
        BLOCKING_WITH_EXCLUSION,
        "",
        1,
    ),
    (
        "a hook payload that is not JSON",
        "bead-claimed",
        ["--hook", "claude-code"],
        BLOCKING_WITH_EXCLUSION,
        "{not json",
        2,
    ),
    (
        "a hook payload that is not an object",
        "bead-claimed",
        ["--hook", "claude-code"],
        BLOCKING_WITH_EXCLUSION,
        "[1, 2]",
        2,
    ),
    ("the liveness report", None, ["--liveness"], BLOCKING_WITH_EXCLUSION, "", 0),
    (
        "the liveness report with a guard named",
        "bead-claimed",
        ["--liveness"],
        BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        "the liveness report over an unreadable flow.yml",
        None,
        ["--liveness"],
        "guards: [1\n",
        "",
        3,
    ),
    # Rows BDL-061.30 derived from the code and the CLI surface, which this
    # table did not carry. Four are argv-reachable and live here; the fifth (an
    # interrupt during the evaluation) is injected, and is a row of
    # :data:`INJECTED_FAILURES` instead.
    ("an empty guard name", "", [], BLOCKING_WITH_EXCLUSION, "", 3),
    (
        # Exit 3 since BDL-UX #254: an unlocatable project is an inability the
        # guard has about ITSELF, and this row is a shell caller. Nothing is
        # manufactured either way — the "creates nothing" half of BDL-061.32 is
        # asserted on this same row below and did not move.
        "a --project that is not a project",
        "bead-claimed",
        ["--project", NOT_A_PROJECT, "--context", "path=app.py"],
        BLOCKING_WITH_EXCLUSION,
        "",
        3,
    ),
    (
        "a hook payload of zero bytes",
        "bead-claimed",
        ["--hook", "claude-code"],
        BLOCKING_WITH_EXCLUSION,
        "",
        2,
    ),
    (
        "a --context key supplied twice",
        "bead-claimed",
        ["--context", "path=src/a.py", "--context", "path=app.py"],
        BLOCKING_WITH_EXCLUSION,
        "",
        2,
    ),
)


#: Failures injected at the evaluation seam, and the fragment each must explain.
#: The third row is BDL-061.30's finding A: ``KeyboardInterrupt`` is neither an
#: ``Exception`` nor a ``SystemExit``, so it escaped the boundary and Click
#: turned it into exit 1 — the WARN code the shipped adapter carries on past —
#: with no verdict and no record.
INJECTED_FAILURES = (
    (
        "an exception during the evaluation",
        lambda: RuntimeError("the tracker probe blew up"),
        "the tracker probe blew up",
    ),
    ("a process exit during the evaluation", lambda: SystemExit(7), "exit 7"),
    ("an interrupt during the evaluation", KeyboardInterrupt, "interrupted"),
)
