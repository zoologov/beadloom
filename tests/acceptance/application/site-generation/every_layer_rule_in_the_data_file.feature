# BDL-080 S1b (`beadloom-kgh6`), RFC D2, PRD goal 2. The architecture view read
# the FIRST layer rule by name and nothing else, so a repository with a backend
# and a frontend drew its frontend grey: this repository's twenty site slices had
# no lane, no Layer-filter value and never a red edge while `lint` judged them.
#
# The data file now carries every layer rule, the container each one stratifies,
# and per node the rule it is placed by. The original keys keep their meaning —
# the first rule by name — so a viewer that reads schema 2 sees what it saw.
#
# The graph declares `tier-*` for the backend and `ui-*` for the portal's slices,
# a vocabulary this repository does not ship.

@bead:beadloom-kgh6 @node:site-generation
Feature: the architecture data file carries every layer rule the project declares

  Scenario: the data file names every layer rule with the container it stratifies
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    When the site is generated for the project
    Then the data file's layer rules are "tier-order" over "shop" and "ui-slices" over "shop-portal"
    And the layers of "ui-slices" carry their names as tokens: "pages, widgets, shared"

  Scenario: a slice carrying its own layer tag is placed by the rule that tag belongs to
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    When the site is generated for the project
    Then the node "portal-widgets" is placed by "ui-slices" at rank 1
    And the node "shop-portal" is placed by "tier-order" at rank 0
    And the node "loose" is placed by no layer rule
    And the node "portal-widgets" keeps the layer rank 0 the first rule by name gives it

  Scenario: an edge either rule finds against is drawn as a violation
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    When the site is generated for the project
    Then the edge "portal-shared -> portal-widgets" is drawn as a violation
    And the edge "shop-core -> shop-api" is drawn as a violation
    And the edge "portal-widgets -> portal-shared" is drawn as healthy
    And the edges drawn as violations are the ones the linter reports

  Scenario: a declared scope is the container the data file names
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    And two slices outside the portal carry the frontend's tags
    And the frontend's layer rule declares the scope "shop-portal"
    When the site is generated for the project
    Then the data file's layer rules are "tier-order" over "shop" and "ui-slices" over "shop-portal"
    And the node "stray-pages" is placed by no layer rule

  # BDL-080 S1e: a rule's name is its identifier, written for lint and the URL;
  # the portal shows a reader the rule's title where the rule declares one.
  @bead:beadloom-af99.2
  Scenario: a layer rule's declared title is carried beside its name
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    And the frontend's layer rule declares the title "Storefront FSD"
    When the site is generated for the project
    Then the data file's layer rule "ui-slices" is titled "Storefront FSD"
    And the data file's layer rule "tier-order" carries no title
