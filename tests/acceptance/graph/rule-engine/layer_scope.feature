# BDL-080 S1b (`beadloom-kgh6`), RFC D2. A layer rule reached the whole graph: a
# frontend's layering, declared beside a backend's, judged any node anywhere that
# carried one of its tags. A `layers` rule may now name the container it judges
# inside with `scope: <ref_id>`, and an edge with an end outside that subtree is
# not the rule's to judge — it is neither found against nor counted in the
# population the rule states.
#
# The graph declares `tier-*` for the backend and `ui-*` for the portal's slices,
# a vocabulary this repository does not ship.

@bead:beadloom-kgh6 @node:rule-engine
Feature: a layer rule declared with a scope judges only the subtree it names

  Scenario: without a scope, the rule judges a tagged node anywhere in the graph
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    And two slices outside the portal carry the frontend's tags
    When the project is linted
    Then "stray-shared -> stray-pages" is reported by "ui-slices"
    And "ui-slices" judged 4 of 6 live depends_on edges

  Scenario: with a scope, an edge outside the subtree is not judged
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    And two slices outside the portal carry the frontend's tags
    And the frontend's layer rule declares the scope "shop-portal"
    When the project is linted
    Then no finding names "stray-shared -> stray-pages"
    And "portal-shared -> portal-widgets" is reported by "ui-slices"
    And "ui-slices" judged 3 of 3 live depends_on edges

  Scenario: a scope that names no node is reported as a rule that checks nothing
    Given a project with a backend layer rule and a frontend layer rule inside its portal
    And the frontend's layer rule declares the scope "no-such-node"
    When the project is linted
    Then "ui-slices" is reported as checking nothing because its scope "no-such-node" names no node
