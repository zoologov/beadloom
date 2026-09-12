# BDL-070 B2 (`beadloom-xmfs`). RFC Q1 decided that an edge inside one layer is
# legal when both ends share a tagged ancestor and a finding when they do not.
# On this repository that predicate reports sixteen crossings, and the bead's
# done-when says each is FIXED or EXEMPTED WITH A STATED REASON — a bare allow
# is not an outcome. `exempt:` on a layer rule is where a stated reason goes,
# and these scenarios are what stops it from becoming a silent one.
#
# The graphs below declare `tier-web` / `tier-core` / `tier-store`, a vocabulary
# this repository does not ship, because a scenario written over `layer-domain`
# would pass against an implementation that hardcoded it.

@bead:beadloom-xmfs @node:rule-engine
Feature: a same-layer crossing is excused by name, with a reason and an exit condition

  Scenario: an entry that excuses nothing is reported as excusing nothing
    Given a project whose layering is declared as two peer containers in one tier
    And the rule excuses "ledger-store -> postings-api" until "2030-01-01"
    When the project is linted
    Then the run reports that the exemption for "ledger-store" excuses nothing

  Scenario: an entry that excuses a real crossing is not reported
    Given a project whose layering is declared as two peer containers in one tier
    And the rule excuses "ledger-api -> postings-api" until "2030-01-01"
    When the project is linted
    Then the run makes no finding about an exemption that excuses nothing

  Scenario: excusing one direction does not excuse the other
    Given a project whose layering is declared as two peer containers in one tier
    And the rule excuses "ledger-api -> postings-api" until "2030-01-01"
    When the same-layer crossings are read off the graph
    Then "postings-api -> ledger-api" is still a crossing no entry excuses

  Scenario: an entry past its own deadline is reported while it goes on excusing
    Given a project whose layering is declared as two peer containers in one tier
    And the rule excuses "ledger-api -> postings-api" until "2020-01-01"
    When the project is linted
    Then the run reports that the exemption for "ledger-api" expired

  Scenario: an entry that excuses without saying why is refused when the rules are read
    Given a project whose layering is declared as two peer containers in one tier
    And the rule excuses "ledger-api -> postings-api" with no reason
    When the project is linted
    Then the lint fails, naming the entry that carries no reason

  Scenario: a part of a container does not cross with the container it is inside
    Given a project whose layering is declared as two peer containers in one tier
    When the same-layer crossings are read off the graph
    Then "ledger-api -> ledger-store" is not among them
