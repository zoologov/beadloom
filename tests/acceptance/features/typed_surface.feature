# BDL-068 S4, `beadloom-gsal` (BDL-UX #231). The pre-commit hook type-checked
# every staged `.py` under `src/` or `tests/`, which is wider than the surface
# this project declares typed: `pyproject`'s `[tool.mypy]` sets
# `packages = ["beadloom"]` with `mypy_path = "src"`, and `ci.yml` runs
# `uv run mypy src/`. Measured on this repository: `uv run mypy tests/` reports
# 970 errors in 90 files, none of them a violation of anything the project
# claims.
#
# Measured over all 24 commits of `features/BDL-068` at `b7c9476..49c2ebe`,
# each against its own tree: 7 staged Python at all, and the hook warned on 4 of
# those 7. All 4 warnings were false. A surface-scoped check is clean on all 7.
#
# The three properties below are the ones the rest of this slice landed: a count
# that counts what was checked, an empty population that reads differently from a
# clean one, and the checker's own words rather than a sentence of ours.

@bead:beadloom-gsal @node:typed-surface
Feature: the commit gate type-checks the surface the project declares typed, and says which

  Scenario: The surface is the one the project declared, not the one the gate was handed
    Given a project whose mypy configuration declares one package typed
    When the staged paths are filtered against the declared typed surface
    Then only the paths inside the declared package are handed to the type checker
    And the verdict states how many staged files were checked out of how many staged

  Scenario: A commit staging nothing typed is unchecked, not clean
    Given a project whose mypy configuration declares one package typed
    When a commit staging only paths outside the declared surface is filtered
    Then no path is handed to the type checker
    And the verdict says none of the staged files is inside the declared surface

  Scenario: A project that declares no typed surface is unjudged, not clean
    Given a project whose configuration declares no typed surface
    When the staged paths are filtered against the declared typed surface
    Then the verdict says the surface could not be derived, with the reason
    And no path is handed to the type checker

  Scenario: A type error inside the declared surface reaches the committer in the checker's own words
    Given a pre-commit hook installed over a project with a declared typed surface
    When the hook runs on a commit whose typed file the checker rejects
    Then the checker's own diagnostic reaches the committer
    And the gate names how many files it type-checked

  # BDL-068 S4, `beadloom-0mdo.42` (BDL-UX #240). The scenarios above are all
  # taken on THIS repository's layout, and the defect below is invisible there:
  # the hook selected the Python it judged with a `^(src|tests)/` path regex, so
  # a project whose package sits at the repository root matched nothing and the
  # leg printed no line at all -- neither a verdict, nor NOTHING TO CHECK, nor
  # NOT CHECKED. The derivation `beadloom-gsal` landed was never asked.
  @bead:beadloom-0mdo.42
  Scenario: A project whose package sits at the repository root is judged, not passed over in silence
    Given a pre-commit hook installed over a project whose package sits at the repository root
    When the hook runs on a commit whose typed file the checker rejects
    Then the checker's own diagnostic reaches the committer
    And the gate names how many files it type-checked
