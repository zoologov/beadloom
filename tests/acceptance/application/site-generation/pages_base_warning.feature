# BDL-076 `beadloom-ujzb.13` (the owner's ruling after B2). A portal built for
# the wrong base loads none of its assets, and until now the first place that
# said so was the Pages workflow's check in CI.
#
# GitHub serves a project's Pages site under `/<repo>/`, and a portal generated
# with the default base `/` cannot work there. `docs site` reads the project's
# `origin` remote to notice that and warns on stderr, naming the setting that
# fixes it. The remote is read only to warn: the warning changes no exit code and
# nothing it reads is written anywhere. A user or organisation site
# (`<owner>.github.io`), a host that is not GitHub and a project with no remote
# get no warning, because nothing says their base is wrong.

@bead:beadloom-ujzb.13 @node:site-generation
Feature: docs site warns when the default base cannot match the project's GitHub Pages path

  Scenario: the default base on a GitHub project repository is warned about, with the fix
    Given a project that declares no site base
    And its origin remote is "git@github.com:acme/orders.git"
    When the site is generated
    Then the generation succeeds
    And the generation warns on stderr that the base should be "/orders/"
    And the warning is not in the standard output

  Scenario: a declared base gets no warning
    Given a project that declares the site base "/orders/"
    And its origin remote is "https://github.com/acme/orders.git"
    When the site is generated
    Then the generation succeeds
    And the generation gives no base warning

  Scenario: a user or organisation Pages repository gets no warning
    Given a project that declares no site base
    And its origin remote is "https://github.com/acme/acme.github.io"
    When the site is generated
    Then the generation succeeds
    And the generation gives no base warning

  Scenario: a repository on another host gets no warning
    Given a project that declares no site base
    And its origin remote is "git@gitlab.com:acme/orders.git"
    When the site is generated
    Then the generation succeeds
    And the generation gives no base warning

  Scenario: a project with no remote gets no warning
    Given a project that declares no site base
    And it is a git repository with no remote
    When the site is generated
    Then the generation succeeds
    And the generation gives no base warning
