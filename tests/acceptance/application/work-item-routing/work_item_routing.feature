# BDL-068 S6 / BDL-UX #259. The `/task-init` routing table is the THIRD reader of
# one boundary. BDL-UX #213 (`doc-quality`) and #244 (`axes-section`) were one
# sentence found in two places hours apart: a section holding two tables was read
# as one, so a second table's rows were judged against the first table's column
# index and its header row came back as data. `beadloom-0mdo.46` lifted the rule
# into `doc_sync/tables.py`, and filed this reader rather than fixing it there.
#
# No instance fired, and that was the finding rather than a reason to defer: the
# reader survived only because it discarded a row whose second cell named neither
# `simplified` nor `full`. Measured over this repository's 456 markdown documents
# and 5 122 table data rows, that guard admits 27 rows, of which 10 are the
# routing table itself and 17 are rows of other tables in 15 other documents --
# `D4`, `BEAD-05`, `Q1`, `12.8.3` and `Local proxy` among the types it would
# report. A guard that rejects 99.5% of a corpus is a sparse filter, not a
# boundary, and #213's measured cause was precisely that vocabulary cannot decide
# this.

@bead:beadloom-0mdo.77 @node:work-item-routing
Feature: the routing /task-init declares is read from one table

  A work item's type decides which documents get written and which approval
  gates it passes, so a phantom route invents a document set and a dropped route
  removes one. `/task-init` composes a project layer under the core, which is
  how a second table arrives under the same heading without anyone intending one.

  Scenario: A second table below the routing table contributes no route
    Given a task-init command whose project layer adds a second table describing the two flows
    When the routing is read from it
    Then the routes read are the ones the routing table states
    And no row of the second table is read as a route

  Scenario: A table stated before the routing table does not become the routing table
    Given a task-init command in which an earlier table quotes a routing row as an example
    When the routing is read from it
    Then the routes read are the ones the routing table states
    And the type decision is located at the routing table
    And the document every route writes is still named

  Scenario: A row of the routing table naming no declared flow is reported rather than dropped
    Given a task-init command whose routing table adds a type routed through a third flow
    When the routing is read from it
    Then the routing names that row as one it could not read
    And the routes read are the ones the routing table states
