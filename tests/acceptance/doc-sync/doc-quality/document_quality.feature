# The writing standard, read back (BDL-061 S4b). One Feature per file.

@bead:beadloom-b0xl @node:doc-quality
Feature: a planning document is held to the writing standard it was written under

  The conventions these documents follow are stated in every role's writing
  standard and were checked by nobody. A practice that is not a mechanism does
  not survive the session.

  Scenario: a goal with no measurable clause is reported
    Given a document whose only goal is "Make the tool better"
    When the writing standard is checked
    Then "measurable-goal" is reported

  Scenario: a risk whose mitigation names no action is reported
    Given a document with a risk mitigated by "Monitor it"
    When the writing standard is checked
    Then "risk-mitigation" is reported

  Scenario: an approved document with a Pending question is reported
    Given an Approved document with an open question answered "Pending"
    When the writing standard is checked
    Then "pending-in-approved" is reported

  Scenario: a draft is allowed its open questions
    Given a Draft document with an open question answered "Pending"
    When the writing standard is checked
    Then nothing is reported

  # BDL-UX #213: the coordinator's verification of a subagent's report is a
  # two-column table, and it sat in the same section as the decision table.
  Scenario: a table of claims and measurements below a decision table is not read as decision rows
    Given a section holding a decision table and, below it, a table of claims and measurements
    When the writing standard is checked
    Then nothing is reported

  Scenario: a table with a reason column the document never declares as decisions is not classified
    Given a table with an empty reason cell in a section the document never declares as decisions
    When the writing standard is checked
    Then nothing is reported
    And the table is reported as not classified
