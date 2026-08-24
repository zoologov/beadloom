# The document-shape half of S4 (BDL-061 S4b). One Feature per file — the
# Gherkin specification allows no more, and a file the runner refuses to parse
# would count as covering its nodes while nothing executed.
#
# These scenarios are the source of truth for what the document checks promise.
# They RUN: `beadloom lint` reads which node and which bead each one binds to,
# and `uv run pytest` executes them.

@bead:beadloom-b0xl @node:doc-shape
Feature: a document that loses its shape is reported, and a convention is reported once

  A generated document is born with the sections its template carries. Nothing
  used to notice when one lost them, because every other freshness reason
  compares content and a document losing a section IS a content change.

  Scenario: a document missing a section its peers carry is reported
    Given three domain documents of which two carry a "Features" section
    When the document shape is checked
    Then the third document is reported as missing "Features"

  Scenario: a section a minority carries is reported once against the kind
    Given three domain documents of which one carries a "Features" section
    When the document shape is checked
    Then no document is reported
    And the kind is reported once with the ratio "1/3"

  Scenario: a section stated under a wider heading is not missing
    Given three domain documents of which one states "Features and components"
    When the document shape is checked
    Then no document is reported
