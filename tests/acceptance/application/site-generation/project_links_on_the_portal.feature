# BDL-076 (`beadloom-ujzb.11`). A link the project wrote, on the portal the project gets.
#
# `beadloom init` takes the root service's summary from the README's first
# paragraph, and `docs site` wrote that summary onto the service's page as it
# was. A README that opens with `See [license](LICENSE).` therefore gave the page
# a link to `./LICENSE`, a file the portal does not publish, and `vitepress build`
# failed on the dead link. The link was correct where its author wrote it: the
# generator moved the text and broke it.
#
# Every page that carries text from the project's own files now treats a link
# the same way. A link to a file the portal publishes goes to that page; a link
# to any other file in the repository goes to the declared repository, or
# becomes its own text when no repository is declared; an absolute address and
# an anchor stay as they were.
#
# BDL-076 B4 (`beadloom-ujzb.8`): the repository's copy is its forge's page for
# the file at the commit the site was generated from, so the project is
# committed, and GitLab's route is `/-/blob/`, not GitHub's `/blob/main/`.

@bead:beadloom-ujzb.11 @node:site-generation
Feature: a link in a project's own text is a working link or plain text on its portal

  Scenario: a README that opens with a relative link gives the root service a page with no dead link
    Given a project whose README opens with "See [license](LICENSE)."
    When the project is initialised and its site is generated
    Then the root service's page reads "See license."
    And no page of the portal holds a dead link

  Scenario: with a repository declared, the link goes to the file in that repository
    Given a project whose README opens with "See [license](LICENSE)."
    And the project declares the repository "https://gitlab.com/acme/orders"
    And the project is committed to git
    When the project is initialised and its site is generated
    Then the root service's page links "license" to "https://gitlab.com/acme/orders/-/blob/{commit}/LICENSE"
    And no page of the portal holds a dead link

  Scenario: a published document that links out of the documentation tree
    Given a project whose README opens with "Takes orders."
    And the project's document "docs/guide.md" links "[the readme](../README.md)" and "[the handler](../src/api/handler.js)"
    When the project is initialised and its site is generated
    Then the published guide links "the readme" to "/"
    And the published guide reads "the handler" as plain text
    And no page of the portal holds a dead link
