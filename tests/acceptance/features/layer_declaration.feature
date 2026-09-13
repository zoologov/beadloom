# BDL-070 A7 (`beadloom-cfkk`), the scenarios PRD US-2 and US-4 reference by
# name.
#
# Before this epic three implementations answered "what layer is this node in":
# the rule engine's per-evaluator tag closures, `architecture_view`'s own
# `_LAYER_TAGS` / `_LAYER_RANK` table, and `liveness`. Two of them disagreed on
# verdict. The scenarios here hold the single answer: one lookup that reads the
# declaration, and a declaration `validate_rules` checks against the graph.
#
# The layering is `tier-web` / `tier-core` / `tier-store` on purpose. This
# repository declares four `layer-*` tags, and an implementation that hardcoded
# them would pass every scenario written in its own vocabulary.

@bead:beadloom-cfkk @node:rule-engine @node:application
Feature: one answer to what layer a node is in

  Scenario: the rule engine and the architecture view agree on every node's layer
    Given a project whose layering is declared as three tiers
    And a node carrying no tier of its own inside a container that carries one
    When each instrument is asked what layer every node is in
    Then the two answers agree node for node
    And the inherited node is placed in its container's tier by both

  Scenario: a layer declared only in rules.yml is honoured without being hardcoded
    Given a project whose layering is declared as three tiers
    When the layer rule is evaluated
    Then the bottom tier depending on the top one is reported as an error
    And no layer tag this project ships appears anywhere in that project

  Scenario: a layer tag matching no node is reported by validate_rules
    Given a project whose layering is declared as three tiers
    And the declaration names a fourth tier no node carries
    When the rules are validated against the graph
    Then the validation names the tier no node carries
    And it says nothing about the three tiers that hold a node
