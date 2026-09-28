# BDL-074 G5, `beadloom-2mj3.15` (review `beadloom-b9ll` M-new-1).
#
# The retired mapper read every JS/TS file under a Jest `__tests__/` folder. The
# binding read only `*.test.*` and `*.spec.*` names, so on a two-node TypeScript
# project `ctx orders` said "jest, 0 tests in 0 files" and the debt report said
# "untested: 1 ... all 1 test file(s) placed" — while one test file was not read at
# all. A pattern that names a folder is matched against the end of the path, Jest's
# own folder convention is a default, and ctx and the debt report say which files
# count as tests every time, not only when there are none.

@bead:beadloom-2mj3.15 @node:test-mapping
Feature: Every test-file convention the retired mapper read is read

  Scenario: a Jest test in a __tests__ folder is shown as the test of the node its folder sits in
    Given a TypeScript project with one test beside its code and one in a __tests__ folder
    When the index is rebuilt and the context of the orders node is read
    Then the context names the orders __tests__ file as a jest file holding 2 tests

  Scenario: the debt report counts no node of that project untested and says what a test file is
    Given a TypeScript project with one test beside its code and one in a __tests__ folder
    When the index is rebuilt and the debt report is read
    Then the debt report counts 0 untested nodes
    And its test population names the jest folder pattern it read the tests by

  Scenario: ctx says which files count as tests when every file is placed
    Given a TypeScript project with one test beside its code and one in a __tests__ folder
    When the index is rebuilt and the context of the orders node is printed
    Then the printed context says a test file is read when its path matches a pattern

  Scenario: a folder pattern the project declares reads every file under that folder
    Given a TypeScript project whose tests sit in an e2e folder beside its code
    And the project declares the jest pattern e2e/**
    When the index is rebuilt and the context of the orders node is read
    Then the context names the orders e2e file as a jest file holding 2 tests
