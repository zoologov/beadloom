# BDL-076 B2 (`beadloom-qki6`). Publishing a portal is a workflow, and the
# workflow is the project's.
#
# `beadloom docs site` writes an adopter's portal. Before this bead publishing it
# meant copying this repository's own `deploy-site.yml`, which names this
# repository's base path and installs beadloom from this repository's source.
# `--pages-workflow` writes a GitHub Pages workflow from the project's own
# declarations: the base under `site:`, the Node major the scaffold's
# `package.json` declares, and the beadloom that wrote it.
#
# The workflow carries the scaffold's generated marker, so a second run changes
# nothing and a hand edit is never written over.

@bead:beadloom-qki6 @node:site-generation
Feature: docs site --pages-workflow writes a Pages workflow for the project's portal

  Scenario: the workflow deploys the portal under the base the project declares
    Given a project that declares the site base "/orders/"
    When the site is generated with the Pages workflow
    Then the Pages workflow parses as YAML
    And the Pages workflow builds the portal for "/orders/"
    And the Pages workflow sets up the Node major the portal's package.json declares
    And the generation names the Pages workflow as written

  Scenario: a second generation leaves the workflow as it is
    Given a project that declares the site base "/orders/"
    And the site has been generated with the Pages workflow once
    When the site is generated with the Pages workflow
    Then the Pages workflow is byte for byte the one written before
    And the generation names the Pages workflow as unchanged

  Scenario: a hand-edited workflow is not written over and is reported
    Given a project that declares the site base "/orders/"
    And the site has been generated with the Pages workflow once
    And the Pages workflow has been edited by hand
    When the site is generated with the Pages workflow
    Then the hand edit in the Pages workflow is still on disk
    And the generation reports the Pages workflow as kept, edited by hand

  Scenario: a generation without the flag writes no workflow
    Given a project that declares the site base "/orders/"
    When the site is generated
    Then no Pages workflow was written

  Scenario: a portal written outside the project gets no workflow, and nothing is written
    Given a project that declares the site base "/orders/"
    When the site is generated outside the project with the Pages workflow
    Then the generation is refused, naming --out
    And no Pages workflow was written
    And no portal was written outside the project

  # beadloom-ujzb.20 (R2 finding F10): the build job runs install scripts, so it
  # only reads; a push to another branch starts no run, and a tag named like the
  # default branch deploys nothing; every action is pinned by a commit.
  @bead:beadloom-ujzb.20
  Scenario: the workflow runs on the branch the project's git records as its default
    Given a project that declares the site base "/orders/"
    And the project's git records "trunk" as its remote's default branch
    When the site is generated with the Pages workflow
    Then a push starts the Pages workflow only on "trunk"
    And the Pages workflow builds only from a branch that is the default, never a tag
    And only the deploy job of the Pages workflow may write Pages or mint a token
    And every action the Pages workflow uses is pinned by a full commit
    And the generation names "trunk" as the branch the Pages workflow runs on

  @bead:beadloom-ujzb.20
  Scenario: with no default branch recorded, no branch is named and the generation says so
    Given a project that declares the site base "/orders/"
    When the site is generated with the Pages workflow
    Then the Pages workflow names no branch
    And the Pages workflow builds only from a branch that is the default, never a tag
    And the generation says the Pages workflow names no branch, and how to give it one

  @bead:beadloom-ujzb.20
  Scenario: a base holding an Actions expression is refused before anything is written
    Given a project that declares the site base "/${{ github.token }}/"
    When the site is generated with the Pages workflow, expecting a refusal
    Then the generation is refused, naming site.base
    And no Pages workflow was written
