# BDL-076 K3, bead `beadloom-5o48`.
#
# `doc-area-coherence` derives a source root by descending while exactly one next
# segment is supported. A second source tree of two or more nodes beside the
# first (a frontend beside a backend) is a supported second way down, so the
# descent stops at the top with an empty root. The areas then became the tree
# names, no document names a tree, and the rule checked none of the pairs. On
# this repository 17 slice nodes under `site/` did that to all 126 pairs, and the
# rule was lowered from error to warn until this fix.
#
# A fork at the very top is read both ways: as the place the areas begin, and as
# the place the source trees begin. The documents decide which reading holds.

@bead:beadloom-5o48 @node:rule-engine
Feature: each source tree's documents are judged against the tree they belong to

  Rule: a second supported source tree does not blank the first

    Scenario Outline: a misplaced document in either tree is reported
      Given a backend tree and a frontend tree of several nodes each
      And the frontend's documents <frontend_docs>
      And one backend node is documented under another backend area
      And one frontend node is documented <frontend_stray>
      When the doc-area-coherence rule is evaluated
      Then exactly the two misplaced nodes are reported
      And the rule does not report that it checked nothing

      Examples:
        | frontend_docs                           | frontend_stray                        |
        | name the frontend's own areas           | under another frontend area           |
        | sit together under one shared directory | under a backend area                  |

    Scenario: the population names each source tree
      Given a backend tree and a frontend tree of several nodes each
      And the frontend's documents name the frontend's own areas
      When the doc-area-coherence rule is evaluated
      Then the population it states names both source trees and their counts

  Rule: a project with one source tree is read exactly as before

    Scenario: top-level packages that the documents name are still the areas
      Given a graph whose areas are top-level directories named by the documents
      And one node is documented under another area
      When the doc-area-coherence rule is evaluated
      Then only that node is reported
      And the population it states names no source tree
