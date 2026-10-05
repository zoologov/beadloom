# BDL-078 F-activity (`beadloom-lw56`). Activity counted commits, with thresholds made
# for an un-squashed history: on a squash-merged history every change is one commit,
# so 85 of this repository's 130 nodes read "cold" with 1-4 commits, a box showed
# none of its parts' work, and a node with no change in 30 days was named like one
# with four commits. The owner's ruling 6: count changed lines over 30 days, rank
# nodes relative to the project, roll a box up from its parts, name zero as no change.
#
# `beadloom-btkd.1` refined the levels: a box is ranked among boxes and a leaf among
# leaves, so "parser" is hot and "core", the smaller of two boxes, is cool.
#
# The repository below reaches main only through squash merges: a ten-commit branch
# and a two-line change each land as one commit.

@bead:beadloom-lw56 @node:git-activity
Feature: activity separates busy nodes from quiet ones on a squash-merged history

  Scenario: changed lines rank the nodes where a commit count cannot
    Given a repository whose history reaches main only through squash merges
    When its activity is analysed
    Then the nodes "parser", "api" and "ui" each have 1 commit in 30 days
    And the node "parser" has 300 lines changed in 30 days
    And the node "api" has 10 lines changed in 30 days
    And the levels are "parser" hot, "api" warm, "ui" cool, "config" quiet and "legacy" dormant

  Scenario: a box rolls up the nodes it holds
    Given a repository whose history reaches main only through squash merges
    When its activity is analysed
    Then the node "core" has 300 lines changed in 30 days
    And the node "app" has 312 lines changed in 30 days
    And the node "core" is cool although none of its own files changed
