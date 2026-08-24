# The second half of the S4 acceptance suite (BDL-061). One Feature per file:
# the Gherkin specification allows no more, and a file the runner refuses to
# parse would be counted as covering its nodes while nothing executed — a false
# green of exactly the shape this slice exists to remove.

@bead:beadloom-mr2l.13 @node:scenario-binding
Feature: a scenario says which node and which bead it belongs to

  Scenario: a tag on the feature binds every scenario beneath it
    Given a feature file tagged "@node:billing @bead:proj-7" with two scenarios
    When the suite is read
    Then both scenarios are bound to the node "billing"
    And both scenarios are bound to the bead "proj-7"

  Scenario: a dialect the parser cannot read is reported rather than counted as empty
    Given a feature file that declares the language "ja"
    When the suite is read
    Then the file is reported as unreadable
    And the suite contains no scenario from it
