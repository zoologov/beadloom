# BDL-076 R2 finding 5 (`beadloom-fht7`), fixed by `beadloom-ujzb.19`. init appended
# `/site/` to the project's .gitignore whenever no line named `site/`, without asking
# whether `site/` already held the project's own files - a website, an app, a folder
# of that common name. Tracked files stayed tracked, but every NEW file there was
# silently ignored: it never showed in `git status` and was never committed.
#
# A `site/` that already holds files is the project's, not the portal's: init writes
# nothing for it, says so, and names what to do instead.

@bead:beadloom-ujzb.19 @node:ignore-block
Feature: beadloom init leaves a site folder that holds the project's own files visible to git

  Scenario: a site folder with tracked files is not ignored, and init says why
    Given a git project whose site folder holds a committed file
    When beadloom init runs
    Then the portal line was not added
    And git does not ignore a new file in the site folder
    And init says the site folder holds a file tracked by git and names --out

  Scenario: a site folder holding files not yet committed is not ignored either
    Given a git project whose site folder holds a file that is not committed yet
    When beadloom init runs
    Then the portal line was not added
    And git does not ignore a new file in the site folder
    And init names --out
