# Every role this flow composes is named in the document that enumerates roles
# (BDL-068 S6, BDL-UX #252). One Feature per file.

@bead:beadloom-0mdo.59 @node:role-map
Feature: a role this flow composes is named in the map that enumerates roles

  `Explore` shipped as a composed role, was invoked by two slash skills, and was
  absent from `CLAUDE.md` -- the file that calls itself the entry point, whose
  section 0.0 draws the role map and whose section 4 is the Agent Roles table.
  Both listed four roles while five were composed. An agent reading the entry
  point, as that document instructs, learned that the fifth did not exist.

  It is the third direction of the graph `role-duties` checks two directions of.
  BDL-UX #228 was a duty declared for a role that does not reach that role's core.
  This is a role that exists and does not reach the document that lists roles. The
  edge was never built because nobody had added a role since the map was written,
  and `Explore` is the first new role in this flow's life.

  The role population is DERIVED from what `role-composer` composes, never from a
  directory listing: `templates/roles/core/` also holds `_landing`, `_rooms`,
  `_tracker` and `_writing` and their localisations, which are fragments rather
  than roles.

  A name is read as a role only inside a construct that designates one. A bare
  word search would read "test" in "Committing with failing tests" as the role,
  which is the keyword-proximity class this project has filed three times.

  Scenario: a composed role the map names nowhere is a finding
    Given a project running the flow exactly as this repository ships it
    And the flow composes a role named "scout"
    When the role map is checked
    Then "scout" is reported as a role the map names nowhere

  Scenario: a roster that names some roles and omits another is a finding
    Given a project running the flow exactly as this repository ships it
    And the flow composes a role named "scout"
    And the project layer names "scout" in a role designation
    When the role map is checked
    Then "scout" is reported as omitted from a roster that names other roles
    And "scout" is not reported as a role the map names nowhere

  Scenario: a name the map designates as a role and no core fragment backs is a finding
    Given a project running the flow exactly as this repository ships it
    And the project layer names "scout" in a role designation
    When the role map is checked
    Then "scout" is reported as a name no composed role backs

  Scenario: a name outside a role designation is not read as a role
    Given a project running the flow exactly as this repository ships it
    And the project layer says "the scout walked past" in ordinary prose
    When the role map is checked
    Then "scout" is not reported as a name no composed role backs

  Scenario: the report names the shapes it could not judge
    Given a project running the flow exactly as this repository ships it
    When the role map is checked
    Then the report names every line that lists two or more roles in a shape it does not read
    And it states how many role designations it did read

  Scenario: a role designation no composed role backs blocks the agent-config check
    Given a project running the flow exactly as this repository ships it
    And the project layer names "scout" in a role designation
    When the agent-config check runs
    Then the check reports the unbacked name and blocks

  Scenario: a roster this derivation inferred warns where a designation blocks
    Given a project running the flow exactly as this repository ships it
    And the project layer lists "dev" and "test" as a punctuated roster
    When the role map is checked
    Then the finding about that roster carries the `warn` severity
    And a finding about a role designation carries the `error` severity

  # The scenarios above run against a synthetic role in a temporary project. The
  # one below runs against the flow this repository ships, which is where the
  # class was measured: `Explore` was composed, invoked by two skills, and named
  # zero times in the map.

  Scenario: the shipped map names every role the shipped flow composes
    Given a project running the flow exactly as this repository ships it
    When the role map is checked
    Then every composed role is named in the map
    And every roster in the map names every composed role
    And no role map finding is reported

  # BDL-068 `.84`, the S6 review's Major 1. Until it, `role_map_report` composed
  # Claude's map for every project and never read `tools:`, so a cursor-only
  # adopter's verdict was about a document their agent does not read while the
  # one it does read -- `.cursor/rules/beadloom-flow.md`, whose body enumerates
  # the roles -- was asked nothing. The map artifact is now derived per declared
  # tool, and a tool this release names no map artifact for is an unreached
  # population rather than a substitution.

  @bead:beadloom-0mdo.84
  Scenario: a cursor-only project is checked against the map a Cursor adopter reads
    Given a project whose flow declares "cursor" alone
    When the role map is checked
    Then the map artifact read for "cursor" is ".cursor/rules/beadloom-flow.md"
    And no map artifact is read for "claude"

  @bead:beadloom-0mdo.84
  Scenario: a role missing from one tool's map is a finding against that tool's artifact
    Given a project whose flow declares "cursor" alone
    And the flow composes a role named "scout"
    When the role map is checked
    Then "scout" is reported as a role the map names nowhere
    And that finding names the tool "cursor" and the artifact ".cursor/rules/beadloom-flow.md"

  @bead:beadloom-0mdo.84
  Scenario: a declared tool with no map artifact is an unreached population, not another tool's map
    Given the flow declares a tool this release ships no map artifact for
    When the role map is checked
    Then that tool is reported as unreached and its reason names it
    And no map artifact is read for "claude"
    And no role map finding is reported

  @bead:beadloom-0mdo.84
  Scenario: the report states its tool population on a clean run
    Given a project running the flow exactly as this repository ships it
    When the role map is checked
    Then it states how many declared tools a map artifact was read for and how many were not

  @bead:beadloom-0mdo.84
  Scenario: the agent-config check names the tool axis of the role map
    Given a project running the flow exactly as this repository ships it
    When the agent-config check runs
    Then its role-map block names each declared tool beside the artifact read for it
