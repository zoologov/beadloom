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

  # BDL-068 `.15`, from the epic's first CRITICAL verdict. Both findings below
  # are false negatives in a NARROWING tool, and both fire on adopter trees
  # rather than on this one: every package in this repository carries an
  # `__init__.py`, so the suite, the Gate and the author's own dogfooding all
  # read green over the defect. The scenarios therefore BUILD the layout instead
  # of assuming the one this repository happens to have.

  @bead:beadloom-0mdo.15
  Scenario: A caller across a namespace package is found rather than reported as none
    Given a project whose package carries no __init__.py file
    When impact runs against the file in one of its subpackages
    Then the callers include the function in the neighbouring subpackage
    And the swept root is the namespace package rather than the subpackage

  @bead:beadloom-0mdo.15
  Scenario: One target spelled two ways gives one answer
    Given a project whose package carries no __init__.py file
    When impact runs against that file and again against the symbol it defines
    Then both runs name the same callers

  @bead:beadloom-0mdo.15
  Scenario: A sweep pointed away from the target refuses the caller axis
    Given a project whose package carries no __init__.py file
    When impact runs against that file over a root that does not hold it
    Then the callers axis reads unresolved rather than empty
    And the unresolved population names the target that fell outside the sweep
    And the unresolved population says the sweep is narrower than the project

  @bead:beadloom-0mdo.15
  Scenario: The branch axis is read from the caller's seat as well as the target's
    Given a project whose command commits through a helper two hops away
    When impact runs against the file the change was being made in
    Then the branches of the command that calls the target are reported too
    And every branch count says which seat it was taken from

  # BDL-UX #255, found by `beadloom-0mdo.72` while deriving S6's axes -- by using
  # this instrument for the job that slice exists to do. A target that EXISTS and
  # is not Python reached `ast.parse` and ended the command in a traceback, while
  # an ABSENT target was reported in one sentence: the worse failure belonged to
  # the more plausible request. A file this derivation cannot read is a verdict
  # like every other gap in this population.

  @bead:beadloom-0mdo.73
  Scenario: A target that exists and is not Python is a verdict rather than a traceback
    Given a project whose module reaches no declared effect sink
    When impact runs against a document in that project
    Then the run ends with an answer rather than a traceback
    And the unresolved population names the target it could not read
    And the callers axis reads unresolved rather than empty
    And the co-writers axis reads unresolved rather than empty

  @bead:beadloom-0mdo.73
  Scenario: A Python target that does not parse is a verdict rather than a traceback
    Given a project holding a Python file that does not parse
    When impact runs against that file
    Then the run ends with an answer rather than a traceback
    And the unresolved population names the target it could not read

  @bead:beadloom-0mdo.73
  Scenario: One unreadable file among many does not cost the answer the rest
    Given a project holding a Python file that does not parse
    When impact runs against the package holding it
    Then the answer still reports the branches of the files that did parse
    And the unresolved population names the target it could not read

  # BDL-UX #284. Three nodes were ruled out of an epic's scope as blast radius and
  # turned out to be the sites the fix had to reach. One of them was not misread:
  # it was invisible. The fix reached `.md.txt` templates that node owned, this
  # derivation reads Python, and the one place an answer names what it could not
  # read -- the section's `Unresolved` line -- said nothing about them. Nothing
  # pointed from the unread population to the node that owns it, so a person
  # ruling the node's `callers` row had no row that said so.

  @bead:beadloom-rqma.2
  Scenario: A row names the files its node owns that the derivation could not read
    Given a project whose caller renders a template its own node owns
    And the project is indexed
    When impact renders the Axes section for the target that caller calls
    Then the caller's row names the template its node owns
    And the target's row states that its node owns no file the derivation could not read
    And the unresolved population names the node that owns the unread template
