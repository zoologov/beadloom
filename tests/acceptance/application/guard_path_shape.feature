# The residue of `beadloom-mr2l.60`, whose measurement stands and is not redone
# here: `paths.py` carries no `sys.platform` and no `os.name`, and the refusal was
# reached before `os.fsencode` (monkeypatched to raise, and the verdict still came
# back). So the backslash refusal was ONE code path on every operating system, and
# on Windows — where a backslash is what `os.path.join` produces — every edit
# target was `MALFORMED` and every guarded edit an `error` at exit 2.
#
# The rule is over a SHAPE, not a spelling. What the guard is about is the
# separator: a spelling this platform does not read as one names a file whose
# reading the guard cannot settle, and a spelling it does read as one names
# exactly the file the writer will touch. The backslash was that shape written out
# for one family of platforms.
#
# What the shape gate then owes on Windows, and never checked: the Win32 name
# layer REWRITES what it is given — it strips a trailing dot or space and it
# redirects a reserved device name — which is the guard-and-writer divergence this
# module exists for, and a stronger argument for a refusal than the backslash ever
# was.
#
# There is no `tests-windows` leg and there will not be one (`beadloom-mr2l.64`,
# withdrawn on a measured ~16-28 runner-minutes per pull request for a platform
# outside this project's audience). So the platform is a SUBSTITUTABLE INPUT here:
# the scenarios below that name a platform run its rules on whatever machine
# collects them, and no scenario says "this platform" unless the sentence is true
# on every one of them. What no substitution can reach is written down as a
# residual in `flow-guards/SPEC.md` under "Windows: unverified by decision",
# never as a prediction and never as an xfail no runner can flip.

@bead:beadloom-0mdo.33 @node:flow-guards
Feature: the path guard refuses the names a platform would rewrite and accepts the ones it spells

  Scenario: The spelling this platform's own harness produces is judged, not refused
    Given a bead is claimed
    When the guard is asked about a target spelled with this platform's own separator
    Then the guard reaches a verdict about that file rather than refusing to read it

  Scenario: A separator spelling a platform does not use is refused there
    Given a platform that separates directories with a forward slash
    When the shape gate is asked about a target spelled with a backslash
    Then the target is refused, and the reason names both readings of the character

  Scenario: The same spelling is accepted on the platform that separates that way
    Given a platform that separates directories with a backslash
    When the shape gate is asked about a target spelled with a backslash
    Then the target is accepted, and it names the file that platform's writer would touch

  Scenario: A component ending in a dot is refused where the name layer strips it
    Given a platform that separates directories with a backslash
    When the shape gate is asked about a component ending in a dot
    Then the target is refused, and the reason says the platform would rewrite the name

  Scenario: A reserved device name is refused where the write would reach a device
    Given a platform that separates directories with a backslash
    When the shape gate is asked about a component that names a device
    Then the target is refused, and the reason says the write would reach a device

  Scenario: The same names are ordinary files where nothing rewrites them
    Given a platform that separates directories with a forward slash
    When the shape gate is asked about a component ending in a dot
    Then the target is accepted

  Scenario: The way out of a refusal is one this platform's harness can take
    Given a bead is claimed
    When the guard is asked about a target it refuses
    Then the remediation names the separator this platform uses rather than a platform's name
