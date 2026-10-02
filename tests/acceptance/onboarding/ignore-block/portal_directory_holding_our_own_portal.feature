# BDL-076, the re-review's finding m4 (`beadloom-ujzb.22`), fixed by `beadloom-ujzb.24`.
# Since R2 finding 5 init writes no `/site/` line when `site/` already holds files,
# because such a folder is the project's own source. A `site/` holding the portal that
# `beadloom docs site` itself wrote was read the same way: `init --force` after `docs
# site` called it "the project's own" and left the generated portal unignored, so every
# file of it showed in `git status`.
#
# The same run read the generated portal as the project's code: `site` became a scan
# path, and its theme and browser tests became nodes.
#
# Whether a file is beadloom's is decided by the scaffold's own generated marker, the
# test `docs site` itself uses before it rewrites a file - not by a guess at file names.

@bead:beadloom-ujzb.24 @node:ignore-block
Feature: beadloom init ignores a site folder that holds the portal docs site wrote

  Scenario: init --force after docs site ignores the generated portal
    Given a git project whose site folder holds the portal beadloom docs site wrote, and no ignore line for it
    When beadloom init runs again with --force
    Then the portal line was added
    And git ignores a new file in the site folder
    And init says it ignored the portal
    And init makes no node and no scan path of the site folder
    And init says it did not scan the site folder

  Scenario: a site folder whose committed files carry no marker stays the project's
    Given a git project whose site folder holds a committed file and the portal beadloom docs site wrote
    When beadloom init runs again with --force
    Then the portal line was not added
    And init says the site folder holds files tracked by git
