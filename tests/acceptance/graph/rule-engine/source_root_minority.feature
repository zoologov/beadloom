# BDL-062 bead `.9`, closing BDL-UX #195.
#
# `doc-area-coherence` derived its source root as the longest prefix EVERY
# documented node's source shares. That is a unanimity rule, and unanimity hands
# every single source a veto over the whole derivation. On this repository one
# node whose source is `site/` — a VitePress theme beside the Python package —
# collapsed the root from `src/beadloom` to nothing for all 85 other pairs.
#
# The collapse has two faces, and which one an operator sees depends only on
# where the minority node's document happens to sit. Both were measured:
#
#   document names the minority area   -> a bogus convention is derived and
#                                         SEVEN correct nodes are reported wrong
#   document names no source area      -> nothing compares at all and the rule
#                                         reports that it checked nothing
#
# The second is the worse one. It reached `lint --strict` as a `warn`, so a rule
# this project had deliberately escalated to `error` stood down over its entire
# population while the Gate stayed green.

@bead:beadloom-viaj.9 @node:rule-engine
Feature: a minority source root does not veto the graph's convention

  Rule: one node outside the main source tree neither stops nor bends the derivation

    Scenario Outline: an outlier outside the source root invents no finding and blanks nothing
      Given a graph whose sources all sit under one root except a single outlier
      And the outlier is documented under a directory <where>
      When the doc-area-coherence rule is evaluated
      Then no node is reported
      And the rule does not report that it checked nothing

      Examples:
        | where                      |
        | named after the outlier    |
        | that names no source area  |

    Scenario: the pairs outside the source root are counted, not dropped in silence
      Given a graph whose sources all sit under one root except a single outlier
      And the outlier is documented under a directory named after the outlier
      When the doc-area-coherence rule is evaluated
      Then the population it states accounts for the outlier

  Rule: a rule that stands down says so at the severity the project gave it

    Scenario Outline: a rule that checked nothing reports it at the severity the project left it at
      Given a graph no convention can be read from
      And the project <declaration>
      When the doc-area-coherence rule is evaluated
      Then the rule reports that it checked nothing
      And that report carries the severity "<severity>"

      Examples:
        | declaration                                              | severity |
        | declared the doc-area-coherence rule blocking            | error    |
        | left the doc-area-coherence rule at its shipped severity | warn     |
