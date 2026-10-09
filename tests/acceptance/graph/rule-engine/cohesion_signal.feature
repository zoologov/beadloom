# BDL-080 S2b (`beadloom-5wh2`), RFC D3. A Feature-Sliced frontend tags each slice
# with its layer, so a size signal per layer needed one `check` rule per tag: six
# rules for six layers, and a seventh the day a project adds a layer. A node
# matcher may now name `tag_prefix:`, and one rule judges every node carrying a
# tag that begins with it.
#
# The fixture's slices carry `ui-*` and its backend `tier-*`, a vocabulary this
# repository does not ship, so what passes passes because the rule was read.

@bead:beadloom-5wh2 @node:rule-engine
Feature: one size check covers every layer whose tag begins with a prefix

  Scenario: the one rule judges a slice of each layer and no node outside the prefix
    Given a frontend with slices tagged "ui-widgets" and "ui-features" beside a backend
    And one size check over the components whose tag begins with "ui-", at most 3 symbols
    When the project is linted
    Then "board" is reported by "ui-cohesion" as owning 5 symbols
    And "search" is reported by "ui-cohesion" as owning 4 symbols
    And no size finding names "badge"
    And no size finding names "ledger"

  Scenario: a prefix no tag begins with is reported as a rule that checks nothing
    Given a frontend with slices tagged "ui-widgets" and "ui-features" beside a backend
    And one size check over the components whose tag begins with "fsd-", at most 3 symbols
    When the project is linted
    Then "ui-cohesion" is reported as checking nothing because no node carries a tag beginning with "fsd-"

  # BDL-080 S2d: a matcher may set a tag and a prefix together, and the reason a rule
  # checks nothing names the field no node carries, not the first one written.
  @bead:beadloom-af99.10
  Scenario: a rule with a carried tag and an uncarried prefix names the prefix
    Given a frontend with slices tagged "ui-widgets" and "ui-features" beside a backend
    And one size check over the components tagged "ui-widgets" whose tag begins with "fsd-", at most 3 symbols
    When the project is linted
    Then "ui-cohesion" is reported as checking nothing because no node carries a tag beginning with "fsd-"
    And no finding of "ui-cohesion" says the tag "ui-widgets" is carried by no node
