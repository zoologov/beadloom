# BDL-068 S1.2. The command answers four questions about a change from the
# source: who else commits through the same sink, who else calls the target,
# how many branches the enclosing command has and how many ways it ends.
#
# The scenarios below are ordered by what BDL-068 S1.3 MEASURED at af26750d,
# and the first one is the one that decides whether this command helps or
# harms. Both facts BDL-067 paid nine review cycles for were inside the lifted
# derivations' reach on the day -- under a seed nobody had. Seeded with the
# commit point they report two writers and four branches; seeded with the
# function the first dev bead was changing they report none and three, cleanly,
# with nothing to suggest a fourth branch and a second writer exist. A wrong
# seed produces a clean, confident, wrong answer, and a list is trusted and
# stopped at where wide reading was not. So the seed is DERIVED from the target
# and NAMED in the answer, and a target no rule finds a sink for is unresolved
# rather than answered over an empty set.

@bead:beadloom-0mdo.2 @node:impact
Feature: impact answers from the source, and names the seed it answered from

  Scenario: The answer names the seed and the rule that derived it
    Given a project whose command commits through a helper two hops away
    When impact runs against the file holding that command
    Then the answer names the derived seed
    And the answer names the rule the seed came from
    And no argument of the run named the seed

  Scenario: The seed is the sink, not the first name the target calls
    Given a project whose command commits through a helper two hops away
    When impact runs against the file holding that command
    Then the derived seed is the helper that performs the effect itself
    And the first-hop name it goes through is not reported as a seed

  Scenario: A second writer the target never calls is reported
    Given a project whose command commits through a helper two hops away
    When impact runs against the file the change was being made in
    Then the co-writers include the writer that file never calls

  Scenario: A target no rule finds a sink for is unresolved, not empty
    Given a project whose module reaches no declared effect sink
    When impact runs against that module
    Then the co-writers axis reads unresolved rather than empty
    And the unresolved population says no seed rule found a sink

  Scenario: A target whose axes live entirely inside it still gets an answer
    Given a project whose module reaches no declared effect sink
    When impact runs against that module
    Then the answer still reports that module's branches and exit forms

  Scenario: The exit forms include the one that is not a return
    Given a project whose command commits through a helper two hops away
    When impact runs against the file holding that command
    Then the exit forms of that command include the call that never returns

  Scenario: The graph supplies the boundary and says when a change leaves it
    Given a project whose command commits through a helper two hops away
    And the project is indexed
    When impact runs against the file holding that command
    Then each found site names the graph node that owns it
    And the answer says the change leaves the target's own node

  Scenario: The boundary is unresolved rather than absent when there is no index
    Given a project whose command commits through a helper two hops away
    When impact runs against the file holding that command
    Then the unresolved population says the boundary had no index to read

  Scenario: The same answer is available as JSON
    Given a project whose command commits through a helper two hops away
    When impact runs against the file holding that command with --json
    Then the JSON carries the seed, the rule and the unresolved population
