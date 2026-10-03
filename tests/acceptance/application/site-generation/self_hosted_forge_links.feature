# BDL-076 B4 (`beadloom-ujzb.8`). The owner's team keeps its repositories on its
# own GitLab. The generator recognises a forge by its public host only, because a
# guessed route is a 404 that looks like a link, so a self-hosted host got no
# source link at all; and the links from the README went to GitHub's route on a
# branch assumed to be `main`, an image included, which a forge serves as a page.
#
# The project names the forge that serves its host in the `site:` block of
# `.beadloom/config.yml`, and every repository link is that forge's route at the
# commit the site was generated from: a node's source, a file the README links
# to, and an image the README draws, from the file itself.
#
# The project below is not this repository: a JavaScript service on a GitLab
# served from its own host, three groups deep, reached over SSH on its own port.

@bead:beadloom-ujzb.8 @node:site-generation
Feature: a self-hosted forge links sources, files and images by the kind the project declares

  Scenario Outline: a project that declares its GitLab host links through GitLab's routes
    Given a JavaScript service whose README links its licence and draws its flow diagram
    And the project is committed to git with the origin "<remote>"
    And the project declares its repository "https://git.acme.example/platform/team/orders" on the forge "gitlab"
    When the project is initialised and its site is generated
    Then every node's source links to "https://git.acme.example/platform/team/orders/-/tree/{commit}/<source>"
    And the About page links "license" to "https://git.acme.example/platform/team/orders/-/blob/{commit}/LICENSE"
    And the About page draws "the flow" from "https://git.acme.example/platform/team/orders/-/raw/{commit}/art/flow.png"
    And the portal's repository link carries the "gitlab" icon

    Examples:
      | remote                                                     |
      | ssh://git@git.acme.example:2222/platform/team/orders.git   |
      | https://git.acme.example/platform/team/orders.git          |
      | git@git.acme.example:platform/team/orders.git              |

  Scenario: without the setting the self-hosted host gets no link, as before
    Given a JavaScript service whose README links its licence and draws its flow diagram
    And the project is committed to git with the origin "ssh://git@git.acme.example:2222/platform/team/orders.git"
    And the project declares its repository "https://git.acme.example/platform/team/orders" and no forge
    When the project is initialised and its site is generated
    Then no node's source has a link
    And the About page reads "license" as plain text
    And the About page reads "the flow" in place of the image

  # The owner's ruling (BDL-076 CONTEXT): nothing from the git remote is
  # published except each node's source link. The README's links go only to a
  # repository the project declared, whatever the remote says.
  Scenario: a project that declares no repository links its sources and nothing from its README
    Given a JavaScript service whose README links its licence and draws its flow diagram
    And the project is committed to git with the origin "git@git.acme.example:platform/team/orders.git"
    And the project declares the forge "gitlab" for "git.acme.example" and no repository
    When the project is initialised and its site is generated
    Then every node's source links to "https://git.acme.example/platform/team/orders/-/tree/{commit}/<source>"
    And the About page reads "license" as plain text
    And the About page reads "the flow" in place of the image

  Scenario: a forge kind the generator does not know stops the site and names the host
    Given a JavaScript service whose README links its licence and draws its flow diagram
    And the project declares its repository "https://git.acme.example/platform/team/orders" on the forge "gitlab-ce"
    When the project is initialised and its site is generated
    Then the site is refused naming "site.forges[git.acme.example]" and "gitlab-ce"
    And config-check refuses the project naming "site.forges[git.acme.example]"

  # beadloom-ujzb.20 (R2 finding F9). The declared address was used as written,
  # so one copied from the address bar built `orders//-/tree/...` and the clone
  # address built `orders.git/-/tree/...`. Both name the same repository and are
  # read as the address without them; the host is read in lower case.
  @bead:beadloom-ujzb.20
  Scenario Outline: an address copied with a trailing slash or .git links like the address itself
    Given a JavaScript service whose README links its licence and draws its flow diagram
    And the project is committed to git with the origin "ssh://git@git.acme.example:2222/platform/team/orders.git"
    And the project declares its repository "<written>" on the forge "gitlab"
    When the project is initialised and its site is generated
    Then every node's source links to "https://git.acme.example/platform/team/orders/-/tree/{commit}/<source>"
    And the About page links "license" to "https://git.acme.example/platform/team/orders/-/blob/{commit}/LICENSE"

    Examples:
      | written                                                  |
      | https://git.acme.example/platform/team/orders/           |
      | https://git.acme.example/platform/team/orders.git        |
      | https://Git.Acme.Example/platform/team/orders.git/       |

  # A page inside the repository is no spelling of it: every link would be
  # appended to that page, and no reading recovers the repository on every forge.
  @bead:beadloom-ujzb.20
  Scenario: an address that runs past the repository into a page of it is refused by name
    Given a JavaScript service whose README links its licence and draws its flow diagram
    And the project declares its repository "https://git.acme.example/platform/team/orders/-/tree/main" on the forge "gitlab"
    When the project is initialised and its site is generated
    Then the site is refused naming "site.repo_url" and "past the repository"
    And config-check refuses the project naming "site.repo_url"
