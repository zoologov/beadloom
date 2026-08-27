# The acceptance suite for `graph-summary-facts` (BDL-062 `.1`).
#
# A node summary is prose that states numbers, and nothing has ever checked
# those numbers against the project they describe. The rule below checks them,
# and — the point of the whole feature — keeps four answers apart instead of
# three: a fact it could not compute must not be reported in the same word as a
# fact that checked out.
#
# Every graph in these scenarios is deliberately NOT this repository's.

@bead:beadloom-viaj.1 @node:rule-engine
Feature: a number stated in a node summary is checked against the project

  Scenario: a summary whose stated count differs from the computed fact is reported
    Given a project whose computed mcp_tool_count is 18
    And a node "gateway" whose summary reads "MCP stdio server with 14 tools for agents"
    When the graph-summary-facts rule is evaluated
    Then the node "gateway" is reported
    And the finding states both 14 and 18
    And the finding carries the severity the rule was configured with

  Scenario: a summary whose stated version matches the computed version is not reported
    Given a project whose computed version is 4.2.0
    And a node "platform" whose summary reads "The platform, release v4.2.0"
    When the graph-summary-facts rule is evaluated
    Then no node is reported
    And the rule does not report that it checked nothing

  Scenario: a claim about a fact this project cannot compute is reported as unverifiable
    Given a project that declines to compute node_count because "the nodes table could not be read"
    And a node "atlas" whose summary reads "The atlas, indexing 42 nodes"
    When the graph-summary-facts rule is evaluated
    Then the node "atlas" is not reported as disagreeing
    And the rule reports that it could not verify a claim
    And the report repeats the project's own reason "the nodes table could not be read"

  Scenario: a graph whose summaries state no checkable fact is reported as unverifiable
    Given a project whose computed node_count is 30
    And a node "widgets" whose summary reads "Widgets, and the handling thereof"
    When the graph-summary-facts rule is evaluated
    Then no node is reported
    And the rule reports that it checked nothing

  Scenario: a number that is prose rather than a project count is not reported
    Given a project whose computed node_count is 30
    And a node "router" whose summary reads "Routing across 3 kinds of node"
    When the graph-summary-facts rule is evaluated
    Then no node is reported
    And the rule reports that it checked nothing

  # BDL-062 `.14`. The three scenarios below are about the SEVERITY the four
  # answers reach the reader with, which is a different question from which
  # answer is given. A TOTAL STAND-DOWN IS NOT A PARTIAL GAP: the rule ships
  # `error`, and a rule that could check none of its population must not report
  # that at `warn` — "the numbers are fine" and "no number was read" would then
  # be the same green. A single unverifiable claim is the partial case and stays
  # advisory, which is why the third scenario is here beside the first two.

  @bead:beadloom-viaj.14
  Scenario: a graph that checked nothing reports it at the severity the rule declares
    Given a project whose computed node_count is 30
    And a node "widgets" whose summary reads "Widgets, and the handling thereof"
    When the graph-summary-facts rule is evaluated
    Then the rule reports that it checked nothing
    And that report carries the severity "error"

  @bead:beadloom-viaj.14
  Scenario: an adopter who declared the rule advisory gets an advisory stand-down
    Given the graph-summary-facts rule is declared with severity "warn"
    And a project whose computed node_count is 30
    And a node "widgets" whose summary reads "Widgets, and the handling thereof"
    When the graph-summary-facts rule is evaluated
    Then the rule reports that it checked nothing
    And that report carries the severity "warn"

  @bead:beadloom-viaj.14
  Scenario: one claim the project cannot compute stays advisory though the rule blocks
    Given a project that declines to compute node_count because "the nodes table could not be read"
    And a node "atlas" whose summary reads "The atlas, indexing 42 nodes"
    And a node "ledger" whose summary reads "Double-entry ledger"
    When the graph-summary-facts rule is evaluated
    Then the rule reports that it could not verify a claim
    And that report carries the severity "warn"
