# BDL-080 S4c (`beadloom-e1xo`), BDL-UX #307. The node card's Source link is a permalink
# to the commit the portal was built from. A portal built locally from a commit that no
# remote branch holds linked every node to a 404: the forge has never seen the commit.
#
# When no branch of origin holds the built commit, the links name a branch origin does
# hold instead: the branch's upstream when it is a branch of origin, else origin's branch
# of the same name, else origin's default branch (`origin/HEAD`). With none of them the
# links keep the commit, because nothing better is known. The links name origin's
# address, so a branch only another remote holds, a fork's, is not one of them
# (`beadloom-af99.16`, the S4 review's M1). The data file says which, under
# `source_ref`, the card says so beside the link, and `docs site` warns on stderr.
#
# A forge serves a branch under the route it serves a commit under, except Gitea, which
# names the kind of revision in the path, and Azure DevOps, which names it in the query.
#
# The project below is not this repository. Its remote is never contacted: the steps write
# the remote-tracking refs a fetch would have written.

@bead:beadloom-e1xo @node:site-generation
Feature: the Source link of a portal built from an unpublished commit names a branch the remote holds

  Scenario: a commit a remote branch holds is linked by itself
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the remote's branch "work" holds the last commit
    When the site is generated for the project
    Then the node "storage-pool" links its source to "https://github.com/team/shop/tree/{commit}/src/storage/pool.py"
    And the data file's source ref is the last commit, linked at "{commit}", pushed

  Scenario: an unpublished commit links the upstream of its branch
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the branch "work" tracks the remote's branch "release/2.0", which holds the first commit
    And the remote's branch "main" holds the first commit
    And the remote's default branch is "main"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "https://github.com/team/shop/tree/release%2F2.0/src/storage/pool.py"
    And the data file's source ref is the last commit, linked at "release/2.0", not pushed

  @bead:beadloom-af99.16
  Scenario: an unpublished commit whose branch tracks another remote links origin's default branch
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the branch "work" tracks the branch "topic" of the remote "fork", which holds the first commit
    And the remote's branch "main" holds the first commit
    And the remote's default branch is "main"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "https://github.com/team/shop/tree/main/src/storage/pool.py"
    And the data file's source ref is the last commit, linked at "main", not pushed

  @bead:beadloom-af99.16
  Scenario: a commit only another remote holds is not published where the links point
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the branch "work" of the remote "fork" holds the last commit
    And the remote's branch "main" holds the first commit
    And the remote's default branch is "main"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "https://github.com/team/shop/tree/main/src/storage/pool.py"
    And the data file's source ref is the last commit, linked at "main", not pushed

  Scenario: an unpublished commit links the remote's branch of the same name when it tracks none
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the remote's branch "work" holds the first commit
    And the remote's branch "main" holds the first commit
    And the remote's default branch is "main"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "https://github.com/team/shop/tree/work/src/storage/pool.py"
    And the data file's source ref is the last commit, linked at "work", not pushed

  Scenario: an unpublished commit on a branch the remote does not have links the default branch
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the remote's branch "main" holds the first commit
    And the remote's default branch is "main"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "https://github.com/team/shop/tree/main/src/storage/pool.py"
    And the data file's source ref is the last commit, linked at "main", not pushed

  Scenario: an unpublished commit with no branch to stand in for it keeps the commit
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "https://github.com/team/shop/tree/{commit}/src/storage/pool.py"
    And the data file's source ref is the last commit, linked at "{commit}", not pushed

  Scenario Outline: a branch is linked by the route its forge serves a branch under
    Given a project committed twice on the branch "work" whose origin is "<remote>"
    And the remote's branch "main" holds the first commit
    And the remote's default branch is "main"
    When the site is generated for the project
    Then the node "storage-pool" links its source to "<link>"

    Examples:
      | remote                                   | link                                                                            |
      | https://gitlab.com/team/shop.git         | https://gitlab.com/team/shop/-/tree/main/src/storage/pool.py                    |
      | git@bitbucket.org:team/shop.git          | https://bitbucket.org/team/shop/src/main/src/storage/pool.py                    |
      | https://codeberg.org/team/shop.git       | https://codeberg.org/team/shop/src/branch/main/src/storage/pool.py              |
      | git@ssh.dev.azure.com:v3/team/sales/shop | https://dev.azure.com/team/sales/_git/shop?path=/src/storage/pool.py&version=GBmain |

  Scenario: a project without a repository address carries no source ref
    Given a project committed twice on the branch "work" with no remote
    When the site is generated for the project
    Then the node "storage-pool" has no source link
    And the data file carries no source ref

  Scenario: docs site warns on stderr that the portal was built from an unpublished commit
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the remote's branch "main" holds the first commit
    And the remote's default branch is "main"
    When docs site generates the portal
    Then docs site succeeds
    And docs site warns on stderr that the links point at "main" instead of the last commit
    And the warning is not in docs site's standard output

  Scenario: docs site says how to name a stand-in when there is none
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    When docs site generates the portal
    Then docs site succeeds
    And docs site warns on stderr that the links point at the last commit and names "git remote set-head origin --auto"

  Scenario: docs site gives no such warning for a commit a remote branch holds
    Given a project committed twice on the branch "work" whose origin is "git@github.com:team/shop.git"
    And the remote's branch "work" holds the last commit
    When docs site generates the portal
    Then docs site succeeds
    And docs site gives no unpublished-commit warning
