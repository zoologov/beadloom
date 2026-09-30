# BDL-076 `beadloom-ujzb.13` (the owner's ruling after B2). The portal
# `beadloom docs site` writes is output, rebuilt from the project on every run,
# and it must not land in an adopter's repository by accident.
#
# `beadloom init` names the portal's default directory in the project's
# `.gitignore`: it creates the file when there is none, appends one line when no
# line already covers the directory, and leaves every other line, and the file's
# line endings, as they were. Outside a git working tree it writes nothing,
# because which version control the project uses is not beadloom's to guess.

@bead:beadloom-ujzb.13 @node:ignore-block
Feature: beadloom init keeps the generated portal out of the project's repository

  Scenario: init on a project with no ignore file ignores the portal directory
    Given a git project with source code and no .gitignore
    When beadloom init runs
    Then git ignores a file the portal would write
    And the .gitignore names the portal directory on one line

  Scenario: init keeps every line of an existing ignore file and its line endings
    Given a git project with source code whose .gitignore has Windows line endings
    When beadloom init runs
    Then every line the .gitignore held before is still in it, in order
    And every line of the .gitignore ends with a Windows line ending
    And git ignores a file the portal would write

  Scenario: an ignore file that already covers the portal directory gets no second line for it
    Given a git project with source code whose .gitignore already ignores "site/"
    When beadloom init runs
    Then the portal line was not added
    And git ignores a file the portal would write

  Scenario: a second init leaves the ignore file as the first one left it
    Given a git project with source code and no .gitignore
    And beadloom init has run once
    When beadloom init runs again over the first
    Then the .gitignore is byte for byte the one the first init left

  Scenario: outside a git working tree init writes no ignore file
    Given a project with source code that is not in a git working tree
    When beadloom init runs
    Then no .gitignore was written
