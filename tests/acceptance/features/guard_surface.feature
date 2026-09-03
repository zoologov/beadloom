# BDL-UX #170, the entry BDL-068 S4 is named after. The shipped hook bound
# `PreToolUse` with `matcher: "Edit|Write|MultiEdit|NotebookEdit"`, so a file
# written through `python3 - <<EOF`, `sed -i` or a heredoc went through `Bash`
# and fired no guard at all — while `--liveness` reported the guards healthy.
#
# The failure is shaped like success: `bead-claimed` cannot warn about an edit it
# was never told about, so a session that edits exclusively through `Bash`
# produces a clean liveness report and zero warnings, byte-identical to the
# output of a session that complied perfectly.
#
# Three pieces, and the third is the one that closes the class. Widening the
# matcher alone would make the false green WIDER: more events would report `pass`
# on a target nobody resolved. So the verdict states that a shell command's write
# set was not determined, and the report answers what fraction of the write paths
# the binding could have seen at all.

@bead:beadloom-0mdo.31 @node:flow-guards
Feature: the guard binding sees every write path, and reports the ones it does not

  Scenario: A file written through the shell reaches the guard
    Given the harness binding this project emits
    Then the shell tool is one of the tools the binding fires on

  Scenario: A pass on a shell command does not read as coverage
    Given a bead is claimed
    When the guard is asked about a shell command whose writes cannot be determined
    Then the verdict states that the command's write set was not determined

  Scenario: A write target the command line names is reported
    Given a bead is claimed
    When the guard is asked about a shell command that redirects into a file
    Then the verdict names that file as a write target it could see

  Scenario: A derived target does not grant an exclusion
    Given a bead is claimed and every path under docs is excluded
    When the guard is asked about a shell command that redirects into a file under docs
    Then the guard is not skipped as excluded

  Scenario: The report names a write path the binding cannot see
    Given a project whose roles are granted the shell tool and whose matcher omits it
    When the binding surface is reported
    Then the shell tool is reported as a write path the binding cannot see

  Scenario: A tool nothing classifies is reported, never counted as harmless
    Given a project whose roles are granted a tool this report cannot classify
    When the binding surface is reported
    Then that tool is reported as unclassified rather than as a non-writer

  Scenario: A binding that cannot be read is unresolved, not empty
    Given a project with no emitted harness settings
    When the binding surface is reported
    Then the report states why the binding could not be read
    And it claims no coverage fraction
