# BDL-080 S1a (`beadloom-je0i`), RFC D1, PRD goal 1. A portal node declared
# `kind: site` landed under `other/` on the portal, was left out of its nav and
# was grouped with the kinds that have no directory. The graph loader now reads
# the kind as `service`, so the portal's readers see a service without a change
# of their own; this scenario holds them to it.
#
# The fixture is `atlas` with its portal `atlas-portal`, a project that is not
# this one: our own portal is declared `kind: service` in its graph file.

@bead:beadloom-je0i @node:site-generation
Feature: a node declared with the kind site is a service on the portal

  Scenario: the portal places a site node with the services
    Given a project whose portal node is declared with the kind "site" and consumes the data the product produces
    When the site is generated for the project
    Then the portal node's page is "services/atlas-portal.md" and there is none under "other/"
    And the nav links the portal node at "/services/atlas-portal"
    And the architecture data file groups the portal node with "services"
    And the landscape data file groups the portal node with "services"
