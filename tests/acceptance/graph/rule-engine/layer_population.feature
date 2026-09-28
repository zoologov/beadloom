# BDL-070 A7 (`beadloom-cfkk`), the scenarios PRD US-1 references by name.
#
# `architecture-layers` is this project's only machine check that dependencies
# run in the declared direction, and it is `severity: error` — what it evaluates
# decides whether `main`, ours and every adopter's, is mergeable. Measured at
# `aa4bfad4` it judged 16 of 362 live `depends_on` edges, because it reads a
# node's OWN tags and skips every edge with an untagged end. The green line said
# `0 violations, 16 rules evaluated` either way, so a reader could not tell
# 16 of 362 from 362 of 362.
#
# The graphs below declare `tier-web` / `tier-core` / `tier-store`, a vocabulary
# this repository does not ship, because a scenario written over `layer-domain`
# would pass against an implementation that hardcoded it.

@bead:beadloom-cfkk @node:rule-engine
Feature: a layer rule states how much of its edge set it judged

  Rule: an edge is judged only when both of its ends are in a declared layer

    Scenario Outline: the reach counts the edges with a tier at both ends
      Given a project whose layering is declared as three tiers
      And <tiered> dependency edges between tiered nodes and <untiered> with an untiered end
      When the project is linted
      Then the layer rule's reach is <tiered> of <total> dependency edges

      Examples:
        | tiered | untiered | total |
        | 3      | 2        | 5     |
        | 3      | 0        | 3     |
        | 2      | 1        | 3     |

  Rule: a partial reach is stated once, as a warning, wherever the result is read

    Scenario: the layer rule states how many edges it evaluated and how many it skipped
      Given a project whose layering is declared as three tiers
      And 3 dependency edges between tiered nodes and 2 with an untiered end
      When the project is linted
      Then the run states that it evaluated 3 of 5 dependency edges
      And it states that it skipped 2 for an end carrying no declared layer

    Scenario: a graph where every node is tagged reports no skipped edges
      Given a project whose layering is declared as three tiers
      And 3 dependency edges between tiered nodes and 0 with an untiered end
      When the project is linted
      Then the layer rule's reach is 3 of 3 dependency edges
      And the run makes no statement about its population

    Scenario: the population reaches a reader that calls the evaluators without lint
      Given a project whose layering is declared as three tiers
      And 3 dependency edges between tiered nodes and 2 with an untiered end
      When the evaluators are called the way a reader past lint calls them
      Then the run states that it evaluated 3 of 5 dependency edges
      And the statement is a warning even though the rule is declared an error

    # The A8 review measured this flag flipping 0 -> 1 on a partly tagged graph
    # nobody had changed. The finding cannot be acted on in the run that reddened:
    # tagging the ends is a change to the graph, not to the commit under test.
    @bead:beadloom-5tcc.1
    Scenario: a pipeline that fails on warnings does not redden for the population statement
      Given a project whose layering is declared as three tiers
      And 2 dependency edges between tiered nodes and 1 with an untiered end
      When the project is linted with the flag that fails on warnings
      Then the command exits 0
      And the run states that it evaluated 2 of 3 dependency edges
