# The acceptance suite for `doc-area-coherence` (BDL-062 `.2`).
#
# The rule holds a graph to its OWN convention: a node should document itself
# where its own graph says nodes like it are documented. No layout is written
# down anywhere — every scenario below builds a different tree, and the rule has
# to learn the convention from the tree it is handed or say it learned none.

@bead:beadloom-viaj.2 @node:rule-engine
Feature: a node documented outside its graph's own convention is reported

  A team places its documentation somewhere. The question the rule answers is
  which node contradicts the placement the rest of the graph agrees on, and it
  answers "I could not tell" out loud when the graph agrees on nothing.

  Rule: a node that contradicts the placement the rest of the graph agrees on is reported

    Scenario: a node documented outside the dominant area is reported
      Given a graph where 4 nodes under source area "billing" are documented under "billing"
      And a graph where 3 nodes under source area "shipping" are documented under "shipping"
      And 1 stray node under source area "billing" is documented under "shipping"
      When the doc-area-coherence rule is evaluated
      Then the stray node is reported
      And the finding states the sample size and the threshold
      And the rule does not report that it checked nothing

  Rule: a graph that agrees on nothing is reported as unverifiable, not as clean

    Scenario Outline: a graph with no convention to read is reported as unverifiable
      Given the documentation is laid out <layout>
      When the doc-area-coherence rule is evaluated
      Then the rule reports that it checked nothing
      And no node is reported as misplaced

      Examples:
        | layout                               |
        | flat at the root of the docs tree    |
        | as one documented node per source area |
