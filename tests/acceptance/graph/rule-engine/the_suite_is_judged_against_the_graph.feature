# BDL-074 C3. The test suite is bound to the graph: a test file to the node whose
# code its path mirrors, an acceptance scenario to the node its folder names. Lint
# judges that binding the way it judges code — three rules, each of which states
# how much of the suite it judged, so a green run is readable as a measurement.

@bead:beadloom-kag9 @node:rule-engine
Feature: lint judges the test suite against the graph

  Rule: every test file binds to a node, or is excused by an entry that still excuses it

    Scenario: a test file that binds to no node is reported by its path
      Given a graph with a feature node and a test file placed where its path mirrors no code
      When the test-binding rule is evaluated
      Then that test file is reported as bound to no node
      And the rule states how many test files it judged

    Scenario: an exemption excuses what it lists and reports an entry that excuses nothing
      Given a graph with a feature node and a test file placed where its path mirrors no code
      And the test-binding rule exempts that file and a file that no longer exists
      When the test-binding rule is evaluated
      Then no test file is reported as bound to no node
      And the entry for the file that no longer exists is reported

  Rule: a unit test of a domain node does not reach into the infrastructure

    Scenario: a unit test of a domain node that imports the infrastructure is reported
      Given a graph with a domain node and an infrastructure node
      And a unit test of the domain node that imports the infrastructure
      When the test-import-boundary rule is evaluated
      Then the import is reported at its line in the unit test
      And the rule states how many test files it judged

  Rule: a scenario is written in the folder of the node it names

    Scenario: a scenario whose tag names another node than its folder is reported
      Given a graph with two feature nodes of one domain
      And a scenario in the folder of the first node tagged with the second
      When the scenario-binding rule is evaluated
      Then the scenario is reported where it is written
      And the rule states that it does not judge what the steps execute
