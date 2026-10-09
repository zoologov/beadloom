# BDL-080 S1a (`beadloom-je0i`), RFC D1. A portal node was declared `kind: site`,
# a kind no rule can match (`VALID_NODE_KINDS` lacks it), that got no document
# skeleton, landed under `other/` on the portal and was left out of its nav.
# The product keeps accepting the kind, because removing a kind from the graph
# schema would be a major change, and reads it as `service` at the one place
# every reader of a node's kind takes it from: the graph loader.
#
# The fixture is a project that is not this one: `atlas` and its portal
# `atlas-portal`. This repository declares its own portal `kind: service`, so
# a scenario passing here cannot be an implementation that recognised our tree.

@bead:beadloom-je0i @node:graph-loader
Feature: a node declared with the kind site is a service

  Scenario: the loader reads the kind site as service and says so
    Given a graph whose portal node is declared with the kind "site"
    When the graph is loaded
    Then the portal node's kind in the graph is "service"
    And the load reports one info line naming the portal node, "site" and "service"
    And the load reports no error and no warning about the portal node

  Scenario: reindex prints the alias on an info line
    Given a project whose portal node is declared with the kind "site"
    When the project is reindexed from the command line
    Then the output carries an info line naming the portal node, "site" and "service"

  Scenario: a rule written for services judges the portal
    Given a project whose portal node is declared with the kind "site" and has no parent
    When the project is linted
    Then the rule that requires every service to have a parent names the portal node
