# BDL-076 J2. Measured by A0 (`beadloom-kcwz`) on 2026-09-30, in a copy of this
# repository with `site/.vitepress/theme` added to the scan paths: 1,318 Python
# imports that name no project module (`typing`, `pathlib`, ...) resolved to
# `vitepress-site`, and 103 false `depends_on` edges joined the graph. The resolver
# prefixed every scan path to an import it could not place and walked up to `site/`,
# the node's source. The layer rule did not judge those edges, so the Gate stayed
# green.
#
# The fixture is a project that is not this one: a Python service beside a JS theme,
# where the node that owns the theme's folder has its source ABOVE the theme's scan
# path, which is the shape A0 measured.

@bead:beadloom-g9fb @node:import-resolver
Feature: a scan path of another language adds no false depends_on edge

  Scenario: a Python import that names no project module stays unresolved
    Given a Python service beside a JavaScript theme that is its own scan path
    When the project is indexed
    Then no depends_on edge points at "site"
    And the import "typing" of "src/api/handlers.py" is recorded with no node

  Scenario: a Python import is not read through a JavaScript scan path
    Given a Python service beside a JavaScript theme that is its own scan path
    When the project is indexed
    Then the import "widgets.card" of "src/api/handlers.py" is recorded with no node

  Scenario: the mixed project's edges are exactly the edges its imports name
    Given a Python service beside a JavaScript theme that is its own scan path
    When the project is indexed
    Then the depends_on edges are exactly "api -> store", "pages -> widgets"
