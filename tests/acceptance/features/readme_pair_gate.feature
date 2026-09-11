# BDL-069 S4, beadloom-dibq. The comparison built by beadloom-19m6 answers
# whether two declared documents have the same shape. This is the leg that runs
# it on every `beadloom ci`, and the binding constraint of the epic is what the
# first scenario states: an adopter who declares no pair is not judged, so the
# upgrade that ships the leg cannot change anyone's verdict.
#
# The second scenario is the other half. A check that cannot go red is not a
# check, and a green that says only `0 finding(s)` cannot be told apart from a
# declaration that left nothing to compare -- so the line names the pairs it
# held and the blocks it compared, on the red run as well as the green one.

@bead:beadloom-dibq @node:ci-gate
Feature: the Gate holds a project's declared document pairs against each other

  Scenario: A project that declares no document pair is skipped by name, not passed in silence
    Given a project that declares no document pair
    When the gate runs
    Then the readme-pair step is a skip that names the config block to add
    And the gate verdict is green

  Scenario: A declared pair whose shapes diverge reddens the gate and names the population held
    Given a project whose declared follower is missing a paragraph its source has
    When the gate runs
    Then the readme-pair step fails and the gate verdict is red
    And the readme-pair line names the pair it held and the blocks it compared
