# The S5 acceptance suite (BDL-061). Three named documentation spaces, and the
# one claim that is a RELATION between two artifacts rather than a flag on one:
# intent recorded in TO-BE is reflected in AS-IS. Nothing here changes status —
# a PRD stays the record of what was intended, and a different document is what
# gets updated.

@bead:beadloom-mr2l.17 @node:doc-roots @node:doc-spaces
Feature: documentation is named by space, and intent is held against reality

  Scenario: The TO-BE space is indexed and searchable
    Given a project whose planning documents live under the TO-BE root
    When the project is reindexed
    Then the planning document is in the index in the "to_be" space
    And a search for a phrase only that document contains finds it

  Scenario: An epic whose beads are closed but whose criteria never reached AS-IS is reported
    Given an epic whose CONTEXT names the node "billing" and whose beads are closed
    And the node "billing" has no AS-IS document
    When the documentation spaces are checked
    Then the epic is reported as intent that never reached AS-IS
    And the report names the node "billing"

  Scenario: An epic that names no node is counted as unresolved rather than passed
    Given an epic whose CONTEXT names no node and whose beads are closed
    When the documentation spaces are checked
    Then the epic is counted as stating no AS-IS relation
    And the epic is not reported as a finding

  @bead:beadloom-mr2l.73
  Scenario: A planning directory with no intent document is counted with its reason
    Given a planning directory whose only document is a summary
    When the documentation spaces are checked
    Then the directory is counted as an epic that carries no intent document
    And it is not reported as a finding

  @bead:beadloom-mr2l.74
  Scenario: An epic the tracker does not name is reported rather than skipped
    Given an epic whose CONTEXT names the node "dispatch" and whose beads the tracker never mentions
    When the documentation spaces are checked
    Then the epic is counted as one whose beads could not be resolved
    And the finding names the tracker that has no record of it

  Scenario: A WORKING document is exempt from freshness checks
    Given a graph node whose documentation is an ACTIVE document and whose code changed
    When freshness is checked
    Then the ACTIVE document is exempt rather than stale
    And the exemption states the reason it was declared with

  @bead:beadloom-mr2l.76
  Scenario: A pair the exemption excused is counted where the other verdicts are
    Given a graph node whose documentation is an ACTIVE document and whose code changed
    When freshness is checked
    Then the gate line states how many pairs it excused and the declared reason

  Scenario: A WORKING exemption that matches no document reports itself
    Given a project that declares a WORKING kind no document uses
    When the documentation spaces are checked
    Then the WORKING exemption is reported as matching no document

  Scenario: A WORKING declaration contradicted by the graph is reported
    Given a graph node whose documentation is an ACTIVE document
    When the documentation spaces are checked
    Then the contradicted WORKING declaration is reported

  @bead:beadloom-mr2l.75
  Scenario: A WORKING root that switches freshness off is a root the report names
    Given a project that declares its whole documentation tree exempt from freshness
    When freshness is checked
    And the documentation spaces are checked
    Then the paired document is exempt rather than stale
    And the contradicted WORKING declaration is reported

  Scenario: A project that keeps its documents elsewhere is read from its configured roots
    Given a project whose doc roots are configured away from the shipped defaults
    When the documentation spaces are checked
    Then the documents under the configured roots are the ones classified
