# BDL-080 S3f (`beadloom-af99.14`), the S3 review's major (`beadloom-jtki`). Measured on
# 4b42e86f: a Python tree with src/app, src/entities and src/shared and no package.json was
# detected as `fsd`, given the frontend rules (`npm run lint:fsd` among them), and
# src/entities/order.py was left without a node. On main the same tree was a monolith.
# Folder names alone are not the layout: the frontend is evidence of its own.

@bead:beadloom-af99.14 @node:agent-prime
Feature: init reads layer-named folders as Feature-Sliced Design only on a frontend

  Scenario: a Python tree with app, entities and shared folders is not read as a frontend
    Given a Python project with the folders src/app, src/entities and src/shared and no package.json
    When beadloom init is run with --bootstrap
    Then init chose the "monolith" preset
    And the rules init wrote do not mention "lint:fsd"
    And a node owns "src/entities/order.py"

  Scenario: the same folders holding TypeScript are read as a frontend
    Given a project with the folders src/app, src/entities and src/shared holding TypeScript
    When beadloom init is run with --bootstrap
    Then init chose the "fsd" preset
