# BDL-083 S1c, beadloom-b23f (BDL-UX #329; RFC D3). The commit-to-bead binding is the
# `Bead:` trailer since S1 fix 3, beadloom-7kas (RFC D10, the owner's ruling of 2026-10-19).
# The JSON and MCP `claims` entry names a misplaced line's commits since S1 fix 6,
# beadloom-g64s (D10's last paragraph, the owner's ruling of 2026-10-19). The placement
# in that entry is a token with the sentence beside it since S1 fix 7, beadloom-kdx7.
#
# Measured on 9.0.0 on 2026-10-16 on an outside monorepo. A wave of two beads: each was
# told it owned 9 findings, and all nine were of the first bead's work. A second work
# item's bead was told it owned 36 findings, every one on files of the first work item
# in the branch's diff against trunk, which it never touched. Its `refs:` named the
# node that covers the frontend's source whole, and the report attributed by that.

@bead:beadloom-b23f @node:gate-ownership
Feature: a gate finding is owned by the bead whose commits changed its files

  A report that tells an agent it owns findings it did not cause sends the fix to the
  wrong agent, and teaches the right one that its red is somebody else's. A node that
  covers a directory says what a bead may touch, not what it touched, so ownership is
  read from the commits: a commit is a bead's when its message carries the git trailer
  `Bead: <bead-id>`, and only then (RFC D10). A bead id mentioned anywhere else in a
  message — a landing-lock note, a test bead naming what it measured — binds nothing.
  A finding no claimed bead's commits explain is unattributed, and the report says by
  which rule it attributed what it did.

  Scenario: of two beads in flight, only the one whose commits changed the files owns the findings
    Given the monorepo fixture on a working branch cut from the trunk
    And bead A's commit makes a widget import the app layer
    And bead B, whose refs name the node that covers the whole frontend, is claimed beside A
    When the gate reports on the checkout
    Then the report names A as the owner of the layer finding
    And it says B owns no finding

  Scenario: a finding the claimed bead's commits did not cause is unattributed
    Given the monorepo fixture on a working branch cut from the trunk
    And an older commit of the branch makes a widget import the app layer
    And bead F2, whose refs name the node that covers the whole frontend, is claimed alone
    And F2's commit changes a file of the shared layer
    When the gate reports on the checkout
    Then the layer finding is unattributed
    And no finding about the widget is owned by F2

  Scenario: every surface that prints ownership prints the rule it attributed by
    Given the monorepo fixture on a working branch cut from the trunk
    And bead A's commit makes a widget import the app layer
    And bead B, whose refs name the node that covers the whole frontend, is claimed beside A
    When the gate reports on the checkout in every format
    Then the human report names the rule and the base it attributed by
    And the GitHub notices name the rule beside each owner
    And the JSON report carries the rule and the base

  @bead:beadloom-7kas
  Scenario: a commit that only mentions a bead's id is not that bead's
    Given the monorepo fixture on a working branch cut from the trunk
    And a commit that makes a widget import the app layer names bead M in its subject and carries no trailer
    And bead M is claimed alone
    When the gate reports on the checkout
    Then the layer finding is unattributed
    And it says M owns no finding because no commit carries its trailer

  @bead:beadloom-ba9w.18
  Scenario: a Bead line git reads no trailer from is named where it stands, not denied
    Given the monorepo fixture on a working branch cut from the trunk
    And a commit that makes a widget import the app layer carries bead P's trailer line above a separate attribution paragraph
    And bead P is claimed alone
    When the gate reports on the checkout
    Then the layer finding is unattributed
    And it says P's commit carries the line outside the message's final paragraph, where git reads no trailer

  @bead:beadloom-g64s
  Scenario: a machine reader is told which commits carry a Bead line git reads no trailer from
    Given the monorepo fixture on a working branch cut from the trunk
    And a commit that makes a widget import the app layer carries bead P's trailer line above a separate attribution paragraph
    And bead P is claimed alone
    When the gate reports on the checkout
    Then the JSON report's claim for P names that commit and where its line stands
    And the MCP verdict's owners carry the same claims as the JSON report

  @bead:beadloom-kdx7
  Scenario: a machine reader matches where a Bead line stands by a token, with the sentence beside it
    Given the monorepo fixture on a working branch cut from the trunk
    And a commit that makes a widget import the app layer carries bead P's trailer line above a separate attribution paragraph
    And a later commit carries bead P's line in a final paragraph git does not read as a trailer block
    And bead P is claimed alone
    When the gate reports on the checkout
    Then the JSON report's claim for P gives each placement as a token, outside_final before unread_final
    And each placement is stated in the words the human report prints
    And the MCP verdict's owners carry the same claims as the JSON report
