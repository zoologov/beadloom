# BDL-083 S2F1 (`beadloom-ba9w.22`), RFC D6 as amended on 2026-10-19 by the owner's ruling.
# S2a read `.github/workflows` first and set `.gitlab-ci.yml` aside whenever both were in the
# tree: a choice of forge made by the census, on the project's behalf, and right only for a
# project whose GitLab file is a mirror. Which pipeline files the census reads is now declared
# in `.beadloom/config.yml` under `rooms.pipelines`; with no key it reads every file present.

@bead:beadloom-ba9w.22 @node:verdict-room
Feature: the pipeline files the room census reads are declared by the project, never guessed

  Background:
    Given the monorepo fixture checked out
    And the checkout holds a GitHub workflow beside its GitLab pipeline

  Scenario: with no declaration every pipeline file present is read
    When the rooms are reported as JSON
    Then a declared room comes from ".gitlab-ci.yml: backend-tests"
    And a declared room comes from ".github/workflows/ci.yml: tests"

  Scenario: a pipeline file the declaration leaves out is set aside with the key named
    Given the checkout declares the pipelines "[github]"
    When the rooms are reported as JSON
    Then no declared room comes from ".gitlab-ci.yml"
    And an unresolved entry for ".gitlab-ci.yml" names "rooms.pipelines"

  Scenario: a declared pipeline with no file in the tree is a named line
    Given the checkout declares the pipelines "[gitlab]"
    And the checkout's GitLab pipeline removed
    When the rooms are reported as text
    Then the command exits 0
    And the room block says "`rooms.pipelines` names `gitlab`"
