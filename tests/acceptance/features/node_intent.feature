# `beadloom ctx` is step 4 of BEFORE ANY WORK, so it is the one moment an agent
# is guaranteed to ask about a node. Until now it answered with reality alone —
# what the code IS, never what it is FOR. These scenarios are about the answer
# arriving, and about the two absences that read alike unless they are kept
# apart: no epic declared this node, and nobody read the intent space.

@bead:beadloom-mr2l.87 @node:node-intent @node:intent-reader
Feature: a node's context carries the intent recorded about it

  Scenario: A node an epic declared carries that epic's intent into its context
    Given an epic whose CONTEXT declares the node "checkout"
    When a context bundle is built for "checkout"
    Then the bundle names the epic that declared it
    And the bundle points at the intent document that declares it

  Scenario: A node no epic declares says how much intent was read
    Given an epic whose CONTEXT declares the node "checkout"
    When a context bundle is built for "shipping"
    Then the bundle reports that no epic declares it
    And the bundle states how many epics were read

  Scenario: A bundle built without reading the intent space says so rather than reporting none
    Given an epic whose CONTEXT declares the node "checkout"
    When a context bundle is built for "checkout" without reading the intent space
    Then the bundle reports that intent was not checked
    And the bundle does not claim that no epic declares it
