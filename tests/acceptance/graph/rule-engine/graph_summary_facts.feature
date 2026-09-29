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

  Rule: a number a summary states is compared with the number the project computes

    Scenario: a summary whose stated count differs from the computed fact is reported
      Given a project whose computed mcp_tool_count is 18
      And a node "gateway" whose summary reads "MCP stdio server with 14 tools for agents"
      When the graph-summary-facts rule is evaluated
      Then the node "gateway" is reported
      And the finding states both 14 and 18
      And the finding carries the severity the rule was configured with

    Scenario Outline: a summary that agrees with the project is not reported
      Given a project whose computed <fact> is <value>
      And a node "<node>" whose summary reads "<summary>"
      When the graph-summary-facts rule is evaluated
      Then no node is reported
      And the rule does not report that it checked nothing

      Examples:
        | fact           | value | node     | summary                                   |
        | version        | 4.2.0 | platform | The platform, release v4.2.0              |
        | mcp_tool_count | 18    | gateway  | MCP stdio server with 18 tools for agents |

  Rule: a claim nobody can check is reported as unverifiable, never as agreeing

    Scenario: a claim about a fact this project cannot compute is reported as unverifiable
      Given a project that declines to compute node_count because "the nodes table could not be read"
      And a node "atlas" whose summary reads "The atlas, indexing 42 nodes"
      When the graph-summary-facts rule is evaluated
      Then the node "atlas" is not reported as disagreeing
      And the rule reports that it could not verify a claim
      And the report repeats the project's own reason "the nodes table could not be read"

    Scenario Outline: a graph whose summaries state no checkable number is reported as unverifiable
      Given a project whose computed node_count is 30
      And a node "<node>" whose summary reads "<summary>"
      When the graph-summary-facts rule is evaluated
      Then no node is reported
      And the rule reports that it checked nothing

      Examples:
        | node    | summary                           |
        | widgets | Widgets, and the handling thereof |
        | router  | Routing across 3 kinds of node    |

  # BDL-062 `.14`. The scenarios below are about the SEVERITY the answers reach
  # the reader with, which is a different question from which answer is given. A
  # TOTAL STAND-DOWN IS NOT A PARTIAL GAP: the rule ships `error`, and a rule that
  # could check none of its population must not report that at `warn` — "the
  # numbers are fine" and "no number was read" would then be the same green. A
  # single unverifiable claim is the partial case and stays advisory.
  @bead:beadloom-viaj.14
  Rule: a total stand-down reaches the reader at the declared severity, a partial gap stays advisory

    Scenario Outline: a graph that checked nothing reports it at the severity the rule declares
      Given the graph-summary-facts rule is declared with severity "<severity>"
      And a project whose computed node_count is 30
      And a node "widgets" whose summary reads "Widgets, and the handling thereof"
      When the graph-summary-facts rule is evaluated
      Then the rule reports that it checked nothing
      And that report carries the severity "<severity>"

      Examples:
        | severity |
        | error    |
        | warn     |

    Scenario: a graph that checked nothing under the shipped severity reports it as an error
      Given a project whose computed node_count is 30
      And a node "widgets" whose summary reads "Widgets, and the handling thereof"
      When the graph-summary-facts rule is evaluated
      Then the rule reports that it checked nothing
      And that report carries the severity "error"

    Scenario: one claim the project cannot compute stays advisory though the rule blocks
      Given a project that declines to compute node_count because "the nodes table could not be read"
      And a node "atlas" whose summary reads "The atlas, indexing 42 nodes"
      And a node "ledger" whose summary reads "Double-entry ledger"
      When the graph-summary-facts rule is evaluated
      Then the rule reports that it could not verify a claim
      And that report carries the severity "warn"
