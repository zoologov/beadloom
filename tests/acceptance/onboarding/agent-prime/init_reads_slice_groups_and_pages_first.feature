# BDL-082 S2a (`beadloom-6e2o`), RFC D2 and D3. Measured before this bead with `init --yes`
# and `lint --strict` on the specification's own examples (the axes' probes p2-groups and
# p3-pagesfirst): the group `features/auth` became ONE node, so `register` importing
# `login` was no edge, and the page's two imports were two false "no index" errors; a page
# of 90 symbols was a `fsd-cohesion-pages` finding the specification's pages-first denies.

@bead:beadloom-6e2o @node:agent-prime
Feature: init reads a slice group as its slices and writes no size limit for pages

  Scenario: a group of two slices is two nodes, and the sharing inside it is a finding
    Given the specification's slice group "features/auth" holding "login" and "register"
    When beadloom init is run with --yes
    And beadloom lint --strict is run
    Then the graph holds the node "features-auth-login" tagged "fsd-features"
    And the graph holds the node "features-auth-register" tagged "fsd-features"
    And the graph holds no node for the folder "src/features/auth"
    And lint reports "fsd-layers" for the edge "features-auth-register" -> "features-auth-login"
    And lint reports no "fsd-public-api" finding

  Scenario: a page of 90 symbols is no finding, and a feature of 90 symbols still is
    Given a pages-first frontend whose page and feature each own 90 symbols
    When beadloom init is run with --yes
    And beadloom lint --strict is run
    Then lint reports no "fsd-cohesion-pages" finding
    And lint reports "fsd-cohesion-features" for "features-compose"

  Scenario: a rules file an adopter already has is not rewritten
    Given a pages-first frontend whose page and feature each own 90 symbols
    And a rules file written by an earlier init that limits the pages layer
    When beadloom init is run with --bootstrap
    And beadloom lint --strict is run
    Then the rules file is byte for byte the one the adopter had
    And lint reports "fsd-cohesion-pages" for "pages-feed"
