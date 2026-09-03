# BDL-068 S1.4. The sections a PLANNING document must carry, derived from the
# same composed templates the flow hands the author -- not from a list in code.
#
# One Feature per file, as everywhere in this suite: the Gherkin specification
# allows no more, and a file the runner refuses to parse would count as covering
# its node while nothing executed.

@bead:beadloom-0mdo.4 @node:doc-shape
Feature: a planning document is held to the sections its own template carries

  A BRIEF and an RFC are composed documents like any other, and until now
  nothing read one back to see whether it kept its shape. The requirement is
  DERIVED from the composed template's literal headings, so a project that adds
  a section to its own template layer makes it required by the same act.

  Scenario: A work item without an Axes section is reported before its first dev bead
    Given three briefs of which two carry an "Axes" section
    When the planning documents are checked against their templates
    Then the third brief is reported as missing "Axes"

  Scenario: An Axes section present with nothing under it is reported
    Given a brief whose "Axes" heading has nothing under it
    When the planning documents are checked against their templates
    Then that brief is reported as carrying an empty "Axes" section

  Scenario: A required section no majority of a kind carries is reported once against the kind
    Given three briefs of which one carries an "Axes" section
    When the planning documents are checked against their templates
    Then no document is reported for "Axes"
    And the kind is reported once with the ratio "1/3"

  Scenario: A document of a kind no template describes is not judged
    Given a document named "NOTES.md" carrying no section at all
    When the planning documents are checked against their templates
    Then no document is reported for "Axes"
    And the kinds judged do not include "NOTES"
