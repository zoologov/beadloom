# BDL-083 S1d, beadloom-fgu8 (BDL-UX #330, #344, #300; RFC D4; PRD ruling 4).
#
# Measured on 9.0.0 on 2026-10-17 on an outside monorepo. A work item cut from a feature
# branch not yet merged was judged against the trunk: `beadloom ci` reported 304
# `outside-the-declared-axes` warnings about the parent branch's files, and the base it
# judged against was printed nowhere. In CI the same step skipped on every pull request,
# because the checkout is a detached HEAD and no branch named the work item.

@bead:beadloom-fgu8 @node:declared-scope
Feature: a branch is judged against the branch it was cut from, and the base is printed

  The base is the merge-base with the branch the work was cut from; `--base` names it
  by hand; the trunk is the fallback. Whichever it is, the header says which base was
  used and how many files of the trunk's diff were attributed to the parent branch, so
  a reader can tell a finding about this work from a finding about its parent's.

  Scenario: a branch cut from an unmerged branch judges only its own files
    Given the monorepo fixture with a work item on a branch cut from an unmerged branch
    When the gate judges the branch against its declared axes
    Then no path of the parent branch is reported outside the axes
    And the scope-check line names the merge-base with the parent branch
    And it says 2 files were attributed to the parent branch

  Scenario: the ownership report holds the commits against the same base
    Given the monorepo fixture with a work item on a branch cut from an unmerged branch
    And the work item's bead is claimed
    When the gate judges the branch against its declared axes
    Then the ownership report's base is the base the scope-check line names

  Scenario: a base named by hand judges the parent's files again
    Given the monorepo fixture with a work item on a branch cut from an unmerged branch
    When scope-check is asked to judge the branch against the trunk named by hand
    Then the parent branch's 2 files are reported outside the axes
    And the header says the base was named by hand

  Scenario: in a pull request's CI job the work item comes from the pull request
    Given the monorepo fixture with a work item on a branch cut from an unmerged branch
    And the checkout is a detached HEAD, as a pull request's CI job has it
    When the gate judges the checkout with the pull request's head branch in its environment
    Then the scope-check step judged the work item's paths rather than skipping

  Scenario: in a merge request's CI job the work item comes from the merge request
    Given the monorepo fixture with a work item on a branch cut from an unmerged branch
    And the checkout is a detached HEAD, as a pull request's CI job has it
    When scope-check judges the checkout with the merge request's source branch in its environment
    Then the header names the work item the merge request's branch names
