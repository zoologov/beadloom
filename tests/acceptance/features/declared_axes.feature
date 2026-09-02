# BDL-068 S1.6. `sync-check --staged` and the commit-scoped pre-commit hook
# already judge a commit by the paths it stages, and until now nothing compared
# those paths against the scope a human approved. Measured on this epic's own
# RFC before the rule was chosen: comparing a staged path's owning NODE against
# the nodes the kept axis rows name is red on all three of this branch's code
# commits (c7591a8 11 paths, 3f68442 5, 2f9e343 6), because the table records
# what a change ranges over and the surfaces it changes live in the `Derived by`
# field. Judged at the bounded context those axes reach, the same three commits
# are silent, and 115 of the 155 commits before this branch that touch an owned
# path -- 74 per cent -- fall outside it.

@bead:beadloom-0mdo.6 @node:scope-check
Feature: a commit outside the work item's declared axes is a finding

  The unit is the WORK ITEM's axes and not the bead's, because the work item's
  axes are what a human approved and a bead may narrow freely inside them. A
  commit leaving the work item's axes means the approval no longer covers the
  change, which is the re-plan trigger. An always-red check is an ignored
  check, and this repository has the receipt: `docs_audit.ignore` exists
  because a check that fired on everything was suppressed instead of fixed.

  Scenario: A commit touching a call site outside the declared axes is reported
    Given a work item whose declared axes reach one bounded context
    When a commit staging a path in another bounded context is judged
    Then the path is reported as outside the declared axes
    And the finding names every axis the work item declared

  Scenario: A staged path an axis rules out of scope is reported by that axis
    Given a work item whose axes name a node and rule it out of scope
    When a commit staging a path that node owns is judged
    Then the path is reported as outside the declared axes
    And the finding names the axis that ruled it out

  Scenario: A staged path inside the declared axes is silent
    Given a work item whose declared axes reach one bounded context
    When a commit staging a path a kept axis names is judged
    Then nothing is reported

  Scenario: A staged path in a declared context that no row names is silent
    Given a work item whose declared axes reach one bounded context
    When a commit staging a path in that context which no row names is judged
    Then nothing is reported

  Scenario: A path no node owns is counted rather than reported
    Given a work item whose declared axes reach one bounded context
    When a commit staging a path no node owns is judged
    Then nothing is reported
    And the verdict states how many staged paths no node owns

  Scenario: The surfaces the derivation ran over are inside the approval
    Given a work item whose Axes section names the target it was derived over
    When a commit staging that target is judged
    Then nothing is reported

  Scenario: An undecided row neither widens the scope nor narrows it
    Given a work item whose axes carry a row nobody decided
    When a commit staging a path that row names is judged
    Then the path is reported as outside the declared axes
    And the verdict states how many rows nobody decided

  Scenario: A branch naming no work item is not checked rather than passed
    Given a branch that names no work item
    When the branch is asked which work item's axes to judge against
    Then the run reports that it checked nothing, with the reason

  Scenario: A work item carrying no Axes section is not checked rather than passed
    Given a work item carrying no Axes section
    When the branch is asked which work item's axes to judge against
    Then the run reports that it checked nothing, with the reason
