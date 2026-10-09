# BDL-080 S4d (`beadloom-af99.7`). The portal carries a logo, by the owner's rulings of
# 2026-10-09.
#
# The nav shows the ADOPTER's logo, declared as `site.logo` and copied into the portal;
# a project that declares none gets no nav logo. Beadloom's own icon appears in one
# place only, a footer that says "Powered by Beadloom" and that `site.powered_by: false`
# removes. The favicon is Beadloom's gradient icon. The icon beside the header's
# repository link is the adopter's forge, read from the host of `site.repo_url`, and
# `site.repo_icon` names it where the host says nothing.
#
# The project below is not this repository: its layers are `application`, `domain`
# and `infrastructure`, and it keeps its logo under `art/`.

@bead:beadloom-af99.7 @node:site-generation
Feature: the portal shows the project's logo, a footer that can be switched off and its forge's icon

  Scenario: a project that declares its logo finds it in the portal, named for the nav
    Given a project that holds the file "art/orders-logo.svg" and declares it as its logo
    When the site is generated for the project
    Then the portal holds the project's logo at "public/logo.svg", byte for byte
    And the portal's identity names the logo "/logo.svg"

  Scenario: a PNG logo keeps its kind
    Given a project that holds the file "art/orders-logo.png" and declares it as its logo
    When the site is generated for the project
    Then the portal holds the project's logo at "public/logo.png", byte for byte
    And the portal's identity names the logo "/logo.png"

  Scenario: a project that declares no logo gets no nav logo, and the footer is on
    Given a project that declares the site block "title: Acme Orders"
    When the site is generated for the project
    Then the portal's identity names no logo
    And the portal's identity switches the footer on

  Scenario: powered_by false switches the footer off
    Given a project that declares the site block "powered_by: false"
    When the site is generated for the project
    Then the portal's identity switches the footer off

  Scenario: the portal ships the favicon and the footer's icon as Beadloom's brand files
    Given a project that declares the site block "title: Acme Orders"
    When the site is generated for the project
    Then the portal holds the brand file "public/brand/beadloom-icon-gradient.svg"
    And the portal holds the brand file "public/brand/beadloom-icon.svg"
    And the portal's VitePress config names "brand/beadloom-icon-gradient.svg" as the favicon

  Scenario Outline: the header's repository icon follows the host of the repository
    Given a project that declares the site block "repo_url: <url>"
    When the site is generated for the project
    Then the portal's repository link carries the "<icon>" icon

    Examples:
      | url                                         | icon      |
      | https://github.com/acme/orders              | github    |
      | https://gitlab.com/acme/orders              | gitlab    |
      | https://gitlab.acme.example/sales/orders    | gitlab    |
      | https://bitbucket.org/acme/orders           | bitbucket |
      | https://codeberg.org/acme/orders            | codeberg  |
      | https://gitea.com/acme/orders               | gitea     |
      | https://gitea.acme.example/sales/orders     | gitea     |
      | https://git.acme.example/sales/orders       | git       |

  Scenario Outline: repo_icon names the icon where the host says nothing
    Given a project that declares the site block "repo_url: https://git.acme.example/sales/orders" and "repo_icon: <icon>"
    When the site is generated for the project
    Then the portal's repository link carries the "<icon>" icon

    Examples:
      | icon      |
      | github    |
      | gitlab    |
      | bitbucket |
      | codeberg  |
      | gitea     |
      | git       |

  Scenario: a project that declares no repository gets no header link, and config-check names it
    Given a project that declares the site block "title: Acme Orders"
    When the site is generated for the project
    Then the portal's repository link carries the "" icon
    And config-check passes the project naming "site.repo_url"

  Scenario Outline: a logo the portal cannot use is refused by name
    Given a project that holds the file "art/orders-logo.jpg" and declares the logo "<logo>"
    When the site is generated for the project, expecting a refusal
    Then the refusal names "site.logo" and "<word>"
    And config-check refuses the project naming "site.logo"

    Examples:
      | logo                 | word                |
      | art/missing.svg      | no file             |
      | art/orders-logo.jpg  | an SVG or a PNG     |
      | ../orders-logo.svg   | outside the project |
      | art                  | an SVG or a PNG     |

  Scenario Outline: a value the footer or the icon cannot use is refused by name
    Given a project that declares the site block "<line>"
    When the site is generated for the project, expecting a refusal
    Then the refusal names "<where>" and "<word>"
    And config-check refuses the project naming "<where>"

    Examples:
      | line                  | where           | word     |
      | powered_by: sometimes | site.powered_by | true     |
      | repo_icon: gitlabb    | site.repo_icon  | codeberg |
