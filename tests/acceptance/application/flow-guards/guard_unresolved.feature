# BDL-UX #254, the entry `beadloom-0mdo.60` is named after. Hit live in BDL-068
# S5: `beadloom-0mdo.51` ran `git mv` to split `services/bd_seam.py` into a
# package, and the next call -- creating `__init__.py` -- was refused. Between
# the two moments the package does not import, `guard_probes.py:79` imports it to
# reach the tracker, so the guard could not answer, and a guard that could not
# answer BLOCKED. Its own remediation read "fix the reported error, then re-run",
# asking for the write it had just disabled. Measured from two sessions: `Bash`,
# `Write` and `Edit` all returned the same ImportError and only `Read` did not.
# The owner cleared it by typing a heredoc in their own shell.
#
# The coverage is not the defect. `beadloom-0mdo.31` widened the matcher to
# include `Bash` in S4, which is the whole of BDL-UX #170 and is correct; before
# it, a shell write slipped past the guard and could have repaired the tree.
# Closing a real hole removed the last exit. So the fix is the verdict on
# inability and never the surface: a guard that cannot evaluate ITSELF is
# unresolved, and an unresolved guard warns and permits while saying that it
# checked nothing. A gate that blocks on its own inability is not strict, it is
# unavailable.
#
# The line the scenarios below hold is between two failures that read alike and
# are not alike. A guard that cannot RUN has no answer about anything, and the
# repair for it is a write it is refusing. A guard that ran and refuses to
# interpret the target it was HANDED has an answer about this edit, and the next
# edit is not affected -- that one still stops.

@bead:beadloom-0mdo.60 @node:flow-guards
Feature: a guard that cannot evaluate itself permits, and says it checked nothing

  Scenario: The guard's own machinery cannot run, so the edit it would repair proceeds
    Given a project whose guard cannot import the probe it reaches the tracker through
    When the harness asks that guard about a write to that project
    Then the verdict is unresolved
    And the edit is permitted
    And the verdict states that nothing was checked

  Scenario: An unresolved guard is not readable as a guard that passed
    Given a project whose guard cannot import the probe it reaches the tracker through
    When the harness asks that guard about a write to that project
    Then the verdict is not a pass
    And the exit code is not the one a passing guard returns

  Scenario: The repair an unresolved guard names does not need the write it disabled
    Given a project whose guard cannot import the probe it reaches the tracker through
    When the harness asks that guard about a write to that project
    Then the remediation does not claim the edit is blocked

  Scenario: A configuration the guard cannot read leaves the file that holds it writable
    Given a project whose flow.yml will not parse
    When the harness asks that guard about a write to that project
    Then the verdict is unresolved
    And the edit is permitted

  Scenario: A target the guard refuses to interpret still stops that edit
    Given a bead is claimed
    When the guard is asked about an edit target it refuses to interpret
    Then the verdict is an error about the edit
    And the edit is blocked

  Scenario: An unresolved firing is not counted as a guard that answered
    Given a project whose guard cannot import the probe it reaches the tracker through
    When the harness asks that guard about a write to that project
    Then the liveness report still calls that guard never-fired
