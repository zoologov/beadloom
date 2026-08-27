# BDL-062 bead `.4`, closing BDL-UX #193.
#
# `framework_count` counted nodes whose `extra.tests.framework` is non-empty —
# 84 on this repository, exactly `node_count` — while its name and its scanner
# keywords ("framework", "supported framework") promise how many DISTINCT
# frameworks exist. Two unrelated meanings of the word collided under one fact
# name: the web frameworks a parser supports, and the nodes that declare a test
# framework.
#
# The collision reached the graph before it reached prose. `route-extraction`'s
# summary — "tree-sitter AST + regex fallback across 12 web frameworks" — is
# factually correct (the extractor carries exactly 12 framework literals) and
# was reported as disagreeing with 84.
#
# The fix is the fact's name and its keywords, not a suppression: silencing a
# correct sentence to protect a misnamed fact leaves the misnaming in place.
# Counting DISTINCT frameworks was measured worse — the value is 1 here, and
# `unreadable_reason` declares 0 and 1 structurally unverifiable, so that
# candidate buys correct semantics at the price of never being checkable.

@bead:beadloom-viaj.4 @node:docs-audit
Feature: a fact's name and its keywords describe what the fact counts

  Scenario: a sentence about the frameworks a parser supports states no fact about nodes
    Given a line of prose reading "route extraction across 12 web frameworks"
    When the scanner reads that line for fact mentions
    Then no mention claims how many nodes declare a framework

  Scenario: a sentence about nodes declaring a framework states that fact
    Given a line of prose reading "84 nodes declare a test framework"
    When the scanner reads that line for fact mentions
    Then a mention claims that 84 nodes declare a framework

  Scenario: the fact the project computes carries the name of what it counts
    Given a project whose graph records a test framework on 3 of its nodes
    When the audit collects that project's facts
    Then the fact named nodes_with_framework has the value 3
    And no fact is named framework_count
