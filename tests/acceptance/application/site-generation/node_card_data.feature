# BDL-076 A1 (`beadloom-o2ua`). The viewer's node card and its impact mode read
# everything from `architecture.data.json`; the browser never queries the index.
# Schema version 1 carried a symbol count, one aggregate doc status and a lint
# boolean, and gave a `url` to three kinds of node out of five, so the card could
# not say which test files hold a node, which rule found against it and why, or
# link a component to the page `docs site` writes for it.
#
# The project below is not this repository: its layers are declared as
# `application` / `domain` / `infrastructure` over the tags `zone-app` /
# `zone-domain` / `zone-infra`, a vocabulary this repository does not ship, so a
# scenario cannot pass against an implementation that hardcoded our own layers.

@bead:beadloom-o2ua @node:site-generation
Feature: the architecture data file carries what a node card shows

  Scenario: a component carries its page, its bound tests and the findings against it
    Given a project whose storage pool imports the catalogue above it, with tests bound to the pool
    When the site is generated for the project
    Then the data file declares schema version 2
    And the node "storage-pool" links to its page "/other/storage-pool"
    And the node "storage-pool" is held by 2 test files with 3 tests, all placed "mirror"
    And the node "storage-pool" carries an "error" finding of the rule "tier-order" naming "infrastructure"
    And the node "storage-pool" is not lint clean

  Scenario: the layers are the ones the project declares
    Given a project whose storage pool imports the catalogue above it, with tests bound to the pool
    When the site is generated for the project
    Then the data file declares the layers "application, domain, infrastructure" in that order
    And the declared layers carry the tags "zone-app, zone-domain, zone-infra"

  # BDL-076 K4 (`beadloom-ujzb.3`). Listing every test file at its node and again
  # at each container made the test lists the largest field of the file. A file is
  # listed once, where it is bound; a container keeps the counts it showed before.
  @bead:beadloom-ujzb.3
  Scenario: a test file is listed at its own node, and its container only counts it
    Given a project whose storage pool imports the catalogue above it, with tests bound to the pool
    When the site is generated for the project
    Then the node "storage" lists no test file and counts 2 test files with 3 tests
    And every test file of the project is listed at exactly one node

  # BDL-076 R1 finding M1 (`beadloom-ujzb.7`). The card built a source link from
  # GitHub's route whatever the remote was, so an adopter on Bitbucket, Gitea or
  # Azure DevOps got a dead link. The generator knows the remote and decides the
  # link; a host it does not recognise gets no link rather than a guessed one.
  @bead:beadloom-ujzb.7
  Scenario Outline: a node's source links to the page its forge serves for the commit
    Given a project whose storage pool imports the catalogue above it, with tests bound to the pool
    And the project is a git repository whose origin is "<remote>"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "<link>"

    Examples:
      | remote                                           | link                                                                                  |
      | git@github.com:team/shop.git                     | https://github.com/team/shop/tree/{ref}/src/storage/pool.py                           |
      | https://gitlab.com/team/shop.git                 | https://gitlab.com/team/shop/-/tree/{ref}/src/storage/pool.py                         |
      | git@bitbucket.org:team/shop.git                  | https://bitbucket.org/team/shop/src/{ref}/src/storage/pool.py                         |
      | https://codeberg.org/team/shop.git               | https://codeberg.org/team/shop/src/commit/{ref}/src/storage/pool.py                   |
      | git@ssh.dev.azure.com:v3/team/sales/shop         | https://dev.azure.com/team/sales/_git/shop?path=/src/storage/pool.py&version=GC{ref}  |

  @bead:beadloom-ujzb.7
  Scenario: a forge the generator does not recognise gets no source link
    Given a project whose storage pool imports the catalogue above it, with tests bound to the pool
    And the project is a git repository whose origin is "git@git.example:team/shop.git"
    When the site is generated for the project
    Then the node "storage-pool" has no source link

  # BDL-076 R1 finding M2 (`beadloom-ujzb.7`). The reindex records the names of a
  # node's most frequent committers; the card never shows them, and the data file
  # is published, often for a private service's portal.
  @bead:beadloom-ujzb.7
  Scenario: the published data file names no commit author
    Given a project whose storage pool imports the catalogue above it, with tests bound to the pool
    And the project is a git repository whose origin is "git@github.com:team/shop.git"
    When the site is generated for the project
    Then the data file does not contain the name of the project's commit author
    And the node "storage-pool" carries only the activity the card shows
