# Doc templates as composed package data (BDL-061 S4b). One Feature per file.

@bead:beadloom-b0xl @node:doc-templates
Feature: a project adapts the shape of its generated documents without forking the generator

  The shape of every generated document used to be an f-string inside the
  generator. An adopter had nothing to adapt, and the required sections could
  only ever be ours.

  Scenario: a project layer adds a section to a generated document
    Given a project whose layer appends a "Runbook" section to the domain template
    When a domain document is generated for the node "billing"
    Then the document carries a "Runbook" section

  Scenario: a section the project added becomes a required section
    Given a project whose layer appends a "Runbook" section to the domain template
    When the required sections of a domain document are resolved
    Then "Runbook" is required
