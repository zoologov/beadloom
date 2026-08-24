# The S6 review-independence suite (BDL-061). A reviewer is handed the CHANGE and
# the SPECIFICATION, and not the author's account of either.
#
# The reason is measured rather than argued. In hidden-profile tasks a group that
# hears one member's conclusion first scores 17-36% where a single holder of all
# the facts scores ~100% (BDL-UX #155 C), and this epic supplied six of its own
# occurrences: an honesty note that understated what the code did, caught every
# time by a reader who opened the code instead of the note.
#
# The split is BEFORE and AFTER, not summary against measurement. A bead's
# DESCRIPTION is the assignment and is handed over; its COMMENTS are the report
# and are withheld until a verdict is recorded. Classifying prose into "claim"
# and "measurement" would need a judgement no mechanism can make and an author
# could phrase around, whereas description-against-comment is structural.

@bead:beadloom-mr2l.79 @node:review-brief
Feature: the reviewer's input carries the change and the specification, never the author's account

  Scenario: A reviewer receives the diff and the spec without the author's summary
    Given a bead "alpha" declaring the node scope "billing"
    And the author recorded 3 comments on "alpha"
    And "src/billing/core.py" changed since the base ref
    When the reviewer's brief is assembled
    Then the brief carries the changed file "src/billing/core.py"
    And the brief carries the specification document of "billing"
    And the brief carries no author comment

  Scenario: A withheld comment is counted, never silently absent
    Given a bead "alpha" declaring the node scope "billing"
    And the author recorded 3 comments on "alpha"
    And "src/billing/core.py" changed since the base ref
    When the reviewer's brief is assembled
    Then the brief reports 3 author comments withheld
    And the brief names the condition that releases them

  Scenario: The author's account is released once a verdict is recorded
    Given a bead "alpha" declaring the node scope "billing"
    And the author recorded 3 comments on "alpha"
    And a verdict was recorded on "alpha"
    When the author's account is requested
    Then the author's account is released

  Scenario: The author's account stays withheld while no verdict is recorded
    Given a bead "alpha" declaring the node scope "billing"
    And the author recorded 3 comments on "alpha"
    When the author's account is requested
    Then the release is refused
    And the brief reports 3 author comments withheld

  Scenario: A change outside the bead's declared scope is named to the reviewer
    Given a bead "alpha" declaring the node scope "billing"
    And "src/shipping/core.py" changed since the base ref
    When the reviewer's brief is assembled
    Then the brief names "src/shipping/core.py" as outside the declared scope
    And the brief is not clean

  Scenario: A brief whose change inventory could not be measured is not reported clean
    Given a bead "alpha" declaring the node scope "billing"
    And the change inventory could not be measured
    When the reviewer's brief is assembled
    Then the brief reports the change as unmeasured
    And the brief is not clean

  Scenario: The scenarios bound to the bead are part of the specification handed over
    Given a bead "alpha" declaring the node scope "billing"
    And a scenario bound to "alpha"
    And "src/billing/core.py" changed since the base ref
    When the reviewer's brief is assembled
    Then the brief carries 1 bound scenario
    And the brief is clean

  # BDL-061.83. The gate read the verdict comment's author out of the tracker and
  # never compared it, so the author of a bead released the author's own account.
  # The comparison is made now. It reports rather than refuses, because the dev
  # agent and the review agent of this project write under one tracker identity
  # and a gate nobody can pass is bypassed rather than obeyed.

  @bead:beadloom-mr2l.83
  Scenario: A verdict recorded by the bead's own author releases with its independence unverified
    Given a bead "alpha" declaring the node scope "billing"
    And the author recorded 3 comments on "alpha"
    And the verdict on "alpha" was recorded by the bead's own author
    When the author's account is requested
    Then the author's account is released
    And the release says it cannot tell the verdict from the author's own
