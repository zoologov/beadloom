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

  Rule: an entry that no longer earns its place is reported, on every run

    Scenario Outline: an entry that excuses nothing, or outlived its deadline, is reported
      Given a project with two peer containers in one tier
      And the rule excuses "<source> -> <target>" until "<until>"
      When the project is linted
      Then the run reports that the exemption for "<source>" <state>

      Examples:
        | source       | target       | until      | state           |
        | ledger-store | postings-api | 2030-01-01 | excuses nothing |
        | ledger-api   | postings-api | 2020-01-01 | expired         |

    Scenario: an entry that excuses a real crossing is not reported
      Given a project with two peer containers in one tier
      And the rule excuses "ledger-api -> postings-api" until "2030-01-01"
      When the project is linted
      Then the run makes no finding about an exemption that excuses nothing

  Rule: an entry excuses the one pair it names, in the direction it names

    Scenario: excusing one direction does not excuse the other
      Given a project with two peer containers in one tier
      And the rule excuses "ledger-api -> postings-api" until "2030-01-01"
      When the same-layer crossings are read off the graph
      Then "postings-api -> ledger-api" is still a crossing no entry excuses

    Scenario: a part of a container does not cross with the container it is inside
      Given a project with two peer containers in one tier
      When the same-layer crossings are read off the graph
      Then "ledger-api -> ledger-store" is not among them

  Rule: an entry must say why it excuses, or the rules are not read at all

    Scenario: an entry that excuses without saying why is refused when the rules are read
      Given a project with two peer containers in one tier
      And the rule excuses "ledger-api -> postings-api" with no reason
      When the project is linted
      Then the lint fails, naming the entry that carries no reason
