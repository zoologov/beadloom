# BDL-070 B4 (`beadloom-w34m`). The last of the three disagreeing answers. The
# architecture view drew a `depends_on` edge red whenever `dst_rank <= src_rank`,
# which is every edge pointing up AND every edge staying inside one layer — so a
# dependency between two parts of one domain was drawn as a layering violation
# while `beadloom lint` found nothing against it. Measured on this repository on
# 2026-09-13 over a warm full rebuild of the index: 130 such edges, against the
# rule's nought.
#
# The view now asks the rule. The graphs below declare `tier-web` / `tier-core` /
# `tier-store`, a vocabulary this repository does not ship, so a scenario cannot
# pass against an implementation that hardcoded our own layer tags.

@bead:beadloom-w34m @node:site-generation
Feature: the architecture view draws the verdict the layer rule reaches

  Scenario: a dependency between two parts of one container is not drawn as a violation
    Given a project whose layering is declared as two peer containers in one tier
    When the architecture view is built for the project
    Then the edge "ledger-api -> ledger-store" is drawn as healthy

  Scenario: a dependency between peers inside one layer is drawn as a violation
    Given a project whose layering is declared as two peer containers in one tier
    When the architecture view is built for the project
    Then the edge "ledger-api -> postings-api" is drawn as a violation

  Scenario: a crossing the rules file excuses by name is not drawn as a violation
    Given a project whose layering is declared as two peer containers in one tier
    And the rules file excuses the crossing "ledger-api -> postings-api"
    When the architecture view is built for the project
    Then the edge "ledger-api -> postings-api" is drawn as healthy
    And the edge "postings-api -> ledger-api" is drawn as a violation

  Scenario: the view and the linter name the same edges
    Given a project whose layering is declared as two peer containers in one tier
    When the architecture view is built for the project
    Then the edges drawn as violations are the ones the linter reports
