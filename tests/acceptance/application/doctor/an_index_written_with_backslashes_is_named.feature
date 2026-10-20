# BDL-083 S2f (`beadloom-27br`), RFC D11, BDL-UX #353. The index is written with forward
# slashes on every platform from this version on. An index an older version built on a
# Windows checkout holds backslashes, which no `source:` matches, so every verdict read from it
# is a verdict over nothing. `doctor` names such an index as one to rebuild, with the command
# that rebuilds it, instead of leaving the reader to infer it from a surface that shrank.

@bead:beadloom-27br @node:doctor
Feature: doctor names an index written with backslashes as one to rebuild

  Background:
    Given the monorepo fixture indexed
    And its index rewritten with backslashes, as an older version wrote it on Windows

  Scenario: doctor names the index and the command that rebuilds it
    When doctor runs
    Then doctor warns that the index holds backslash paths and names "beadloom reindex --full"

  Scenario: a full reindex clears the warning
    When the index is rebuilt with a full reindex
    And doctor runs
    Then doctor says nothing about backslash paths
