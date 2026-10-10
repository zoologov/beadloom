# BDL-081 R2 (`beadloom-ehts`), RFC D4, the owner's ruling 6. A node declared
# `kind: site` has its page under `services/` since BDL-080 S1a; 8.0.0 wrote it
# under `other/`. Measured on this repository's portal written by the released
# 8.0.0 and rewritten by the tree: the new page was written and the old one stayed
# beside it, so the portal carried the node twice. `docs site` now removes a node
# page it wrote under a section the node's page has left, and only such a page.
#
# The fixture is `atlas` with its portal `atlas-portal`, a project that is not
# this one, and its portal as 8.0.0 left it: the page under `other/` with
# `kind: site` in its front matter.

@bead:beadloom-ehts @node:site-generation
Feature: a node page that moved to another section is retired from the old one

  Scenario: an upgrade removes the page 8.0.0 wrote under other
    Given a project whose portal node is declared with the kind "site"
    And a portal 8.0.0 wrote for it, with the portal node's page under "other/"
    When docs site rewrites the portal
    Then the portal node's page is "services/atlas-portal.md" and there is none under "other/"
    And the scaffold line counts 1 moved pages retired

  Scenario: a page the project provides under its override directory stays
    Given a project whose portal node is declared with the kind "site"
    And a portal 8.0.0 wrote for it, with the portal node's page under "other/"
    And the project provides its own "other/atlas-portal.md" under .beadloom/site/
    When docs site rewrites the portal
    Then the portal node's page is "services/atlas-portal.md" and the project's own page stays under "other/"
    And the scaffold line counts 0 moved pages retired

  # The release review (`beadloom-g0a0`, major 1): a node id may hold a slash and
  # its page is then nested. The run read the id from the file name, so the page
  # of `x/b` looked like a page `b` had left, and `services/b.md` was removed.
  Scenario: a fresh portal keeps the page of every node, a node id holding a slash included
    Given a project with the service nodes "b" and "x/b"
    When docs site rewrites the portal
    Then the portal has the pages "services/b.md" and "services/x/b.md"
    And the scaffold line counts 0 moved pages retired
