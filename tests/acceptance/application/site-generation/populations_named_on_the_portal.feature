# BDL-080 S4a (`beadloom-5pxv`), RFC D8, PRD goal 5 (BDL-UX #305, #306). The
# portal's numbers did not name what they were counted over. A card's
# `Rule findings: none` read the same whether lint found nothing on the node or
# never ran; the findings lint binds to no node appeared nowhere on the portal;
# a box's `Debt` was its own score while its activity rolled up from its parts.
#
# The data file now carries lint's totals for the project and the findings bound
# to no node, a box's debt carries what its parts hold, and the dashboard's data
# file names the pages the run wrote. The graph declares `tier-*` tags this
# repository does not ship.

@bead:beadloom-5pxv @node:site-generation
Feature: every number on the portal names the population it was counted over

  Scenario: the data file carries lint's totals for the whole project
    Given a project whose layering lint finds against and one rule that cannot fire
    When the site is generated for the project
    Then the data file's lint totals are the ones the linter reports
    And the lint totals name 2 nodes with findings

  Scenario: a finding bound to no node is listed among the node-less findings
    Given a project whose layering lint finds against and one rule that cannot fire
    When the site is generated for the project
    Then the node-less findings of the data file are the rule "nobody-reaches-core"
    And the dashboard's data file lists the same node-less findings

  Scenario: a box's debt carries the debt of the nodes inside it, by reason
    Given a project whose layering lint finds against and one rule that cannot fire
    When the site is generated for the project
    Then the debt inside the box "shop" is the sum of its parts' own debt
    And the debt inside the box "shop" counts its parts by each reason they carry
    And the leaf "store" carries no debt inside

  Scenario: the dashboard's data file names the pages the site run wrote
    Given a project whose layering lint finds against and one rule that cannot fire
    When the site is generated for the project
    Then the page map counts every page the run wrote under its section
    And the page map's node pages are one per node
    And the page map names the language of each About page
