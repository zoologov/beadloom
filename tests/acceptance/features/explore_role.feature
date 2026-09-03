# BDL-068 S1.5. `Explore` is a role FILE, composed by the same composer as the
# other four, and the role population it joins is derived rather than declared
# twice. Measured at 2a5c0d1: the population lived in two hand-maintained
# literals -- `role_composer.ROLE_NAMES` and `agentic_flow_setup.AGENT_FILES` --
# with eight readers between them, so a fifth role added by editing both is
# exactly the fifth thing that can drift.

@bead:beadloom-0mdo.5 @node:role-composer
Feature: a role exists because a core fragment ships for it

  CONTEXT Q5 decides that `Explore` is a role file rather than a mode of an
  existing role, because a mode has no protocol file and that is why the one
  Explore run in BDL-067 returned an excellent trace of the defect and nothing
  about axes. A role file only stops the coordinator's prompt from mattering if
  every reader of the role population sees it, so the population is derived
  from the shipped fragments over a shape: a core fragment is a role when it
  opens with front matter naming it, which is already the stated difference
  between a role and the shared writing LAYER.

  Scenario: A shipped core fragment that names itself is a role
    Given the shipped role fragments
    When the role population is derived from them
    Then explore is one of the roles
    And the shared writing fragment is not one of the roles

  Scenario: A fragment carrying no front matter is a layer and not a role
    Given a role fragment directory holding one named fragment and one unnamed
    When the role population is derived from that directory
    Then only the named fragment is a role

  Scenario: The scaffold's role population is the composer's, not a second list
    Given the shipped role fragments
    When the role population is derived from them
    Then the vendored scaffold names exactly the same roles

  Scenario: The Explore role states the deliverable it must return
    Given the Explore role composed for a ddd python project
    Then it names the Axes section as its deliverable
    And it names the command the axes are derived by
    And it forbids returning a narrative instead

  Scenario: An Explore adapter that drifts from its composition is reported
    Given a project that adopted the flow and had its role adapters composed
    When the Explore adapter on disk is edited by hand
    Then config-check reports the Explore adapter
