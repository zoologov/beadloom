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

  # BDL-082 S2 fix (`beadloom-us5r.2`), review S2R minor 3: a group holding only another
  # group was read as ONE slice, `features-account`, measured with `init --yes`.
  @bead:beadloom-us5r.2
  Scenario: a group inside a group is read as its slices too
    Given a slice group "features/account" holding only the group "settings" of "profile" and "billing"
    When beadloom init is run with --yes
    And beadloom lint --strict is run
    Then the graph holds the node "features-account-settings-profile" tagged "fsd-features"
    And the graph holds the node "features-account-settings-billing" tagged "fsd-features"
    And the graph holds no node for the folder "src/features/account"
    And the graph holds no node for the folder "src/features/account/settings"
    And lint reports "fsd-layers" for the edge "features-account-settings-billing" -> "features-account-settings-profile"
    And lint reports no "fsd-public-api" finding

  # BDL-082 S2 fix 2 (`beadloom-us5r.3`), the re-review of S2R, Major A: reading groups at
  # any depth split this slice into one node for `Summary` and left four files in no node.
  @bead:beadloom-us5r.3
  Scenario: a slice not yet split into segments is one node holding all its files
    Given a slice "features/checkout" with code at its top and a component "components/Summary" holding an index
    When beadloom init is run with --yes
    And beadloom lint --strict is run
    Then the graph holds the node "features-checkout" tagged "fsd-features"
    And the graph holds no node for the folder "src/features/checkout/components/Summary"
    And lint reports no finding of code at a group's top

  # BDL-082 S2 fix 4 (`beadloom-us5r.5`), the owner's ruling of 2026-10-13 on Major B of the
  # third review pass: a folder holding code at its top is still a group when a child holds
  # a standard segment. 7be98929 read this group as one slice and the crossing vanished.
  @bead:beadloom-us5r.5
  Scenario: a group with a shared file at its top is still two slices, and both findings are reported
    Given the specification's slice group "features/auth" with a shared file "helpers.ts" at its top
    When beadloom init is run with --yes
    And beadloom lint --strict is run
    Then the graph holds the node "features-auth-login" tagged "fsd-features"
    And the graph holds the node "features-auth-register" tagged "fsd-features"
    And lint reports "fsd-layers" for the edge "features-auth-register" -> "features-auth-login"
    And lint reports code at a group's top in "src/features/auth/helpers.ts"

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
