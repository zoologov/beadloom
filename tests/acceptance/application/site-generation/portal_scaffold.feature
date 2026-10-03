# BDL-076 B1 (`beadloom-dfwt`). The portal for a project that is not this one.
#
# Before this bead `beadloom docs site` wrote the content only: the theme, the
# viewer, `package.json` and the VitePress config existed in this repository
# alone. Explore built a TypeScript project's portal by copying them by hand,
# and the result carried Beadloom's title, the `/beadloom/` base and a link to
# Beadloom's repository.
#
# The scaffold now ships in the wheel and `docs site` writes it, with the
# identity the project declares under `site:` in `.beadloom/config.yml`. The
# output directory is the project's, so a file `docs site` did not write, or one
# somebody edited after it did, is never overwritten; `.beadloom/site/` is where
# a project's own change to the portal lives, and it is copied last.
#
# The project below is not this repository: its layers are `application`,
# `domain` and `infrastructure` over the tags `zone-app`, `zone-domain` and
# `zone-infra`, a vocabulary this repository does not ship.

@bead:beadloom-dfwt @node:site-generation
Feature: docs site writes a portal that carries the project's identity and keeps its edits

  Scenario: the portal carries the identity the project declares
    Given a project that declares the site "Acme Orders" at "/orders/" linking "https://gitlab.com/acme/orders"
    When the site is generated for the project
    Then the portal holds the scaffold: the VitePress config, the theme, package.json and the browser tests
    And the portal's identity is "Acme Orders" at "/orders/" linking "https://gitlab.com/acme/orders"
    And no file of the portal names this repository

  # beadloom-ujzb.18: the scaffold's source binds each theme file to a node of
  # this repository's graph with a `beadloom:component=` line. Those nodes are not
  # the project's, so the portal is written without the lines.
  @bead:beadloom-ujzb.18
  Scenario: the portal names none of the nodes this repository's graph binds to the scaffold
    Given a project that declares no site
    When the site is generated for the project
    Then no scaffold file of the portal carries a beadloom annotation
    And no file of the portal names a node this repository's graph binds to the scaffold

  Scenario: a project that declares nothing is named after its directory and links nowhere
    Given a project that declares no site
    When the site is generated for the project
    Then the portal's identity is named after the project directory at "/" with no repository link

  Scenario: a scaffold file edited by hand survives the next generation and is reported
    Given a project that declares no site
    And the site has been generated once
    And the portal's VitePress config has been edited by hand
    When the site is generated for the project
    Then the hand edit in the VitePress config is still on disk
    And the generation reports the VitePress config as kept, with ".beadloom/site/.vitepress/config.mjs" as where the edit belongs

  Scenario: the project's own portal files are copied last
    Given a project that declares no site
    And the project keeps its own "guide.md" and its own theme stylesheet under .beadloom/site/
    When the site is generated for the project
    Then the portal's "guide.md" is the project's own
    And the portal's theme stylesheet is the project's own

  Scenario: a site block with a key the portal does not read stops the generation
    Given a project whose site block misspells "base" as "bsae"
    When the site is generated for the project, expecting a refusal
    Then the refusal names "site.bsae"
    And nothing was written

  Scenario: the dashboard mounts the AI tech-writer panel only for a project that records its runs
    Given a project that declares no site
    When the site is generated for the project
    Then the dashboard page does not mount the AI tech-writer panel

  Scenario: a project that records AI tech-writer runs gets the panel
    Given a project that declares no site
    And the project records AI tech-writer runs
    When the site is generated for the project
    Then the dashboard page mounts the AI tech-writer panel
