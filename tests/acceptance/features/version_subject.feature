# BDL-068 S6, bead `beadloom-0mdo.63`, closing BDL-UX #253 and the foreign-subject
# face of #190.
#
# `_extract_versions` matched every `\bv?\d+\.\d+\.\d+\b` outside a pin and handed
# each one to an exact comparison against this project's own version. It had no
# notion of WHOSE product a version belongs to, so "Measured on bd 1.0.4" was a
# Gate finding and the only way to write it was a `docs_audit.ignore` triple. Ten
# version triples stood in this repository's config for one sentence shape, three
# of them in user-facing guides.
#
# The fix is the token beside the number, not a suppression per document: a
# version is attributed to the nearest SUBJECT NAME to its left inside its own
# clause, and only a version whose nearest name is this project's — or that has
# no name at all — is compared against this project's version.
#
# The subject vocabulary is DERIVED where it can be (every distribution the
# manifest declares, the interpreter families implied by `requires-python`, and
# `git` when the project is a git repository) and declared per NAME where it
# cannot (`docs_audit.subjects`). It is a vocabulary rather than a silencer: a
# name nobody declared keeps producing a finding, so the failure mode stays loud.

@bead:beadloom-0mdo.63 @node:docs-audit
Feature: a version token belongs to the subject named beside it

  Scenario: a measurement naming a dependency's release is not a claim about this project
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "Measured on bd 1.0.4 in an isolated rig."
    When the audit reads that project
    Then no finding reports a stale version
    And the audit attributes 1 version token to bd

  Scenario: a version with no named subject is still read as this project's claim
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "The current release is 3.1.0."
    When the audit reads that project
    Then a finding reports a stale version

  Scenario: the interpreter a measurement was taken under is derived from the manifest
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "Every verdict was taken on CPython 3.13.7."
    When the audit reads that project
    Then no finding reports a stale version

  Scenario: a dependency the manifest already declares needs no further declaration
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "The seam was measured against click 8.1.7."
    When the audit reads that project
    Then no finding reports a stale version

  Scenario: a subject the project never declared is reported rather than assumed
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "The rig ran on PostgreSQL 16.2.1."
    When the audit reads that project
    Then a finding reports a stale version

  Scenario: each version in a clause goes to the name beside it
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "beadloom 3.1.0 was measured on bd 1.0.4."
    When the audit reads that project
    Then a finding reports a stale version
    And the audit attributes 1 version token to bd

  # BDL-068 S6, bead `beadloom-0mdo.81`, closing BDL-UX #266.
  #
  # `git` entered the vocabulary from `(project_root / ".git").exists()`, and an
  # absent `.git` was read as the answer "this project has nothing to do with
  # git". A directory built by `git archive HEAD` — every clean room this
  # repository measures in — carries no `.git` by construction, so `git 2.49.0`
  # lost its subject and was compared against this project's own version. Every
  # clean-room Gate run on this repository was rc 1 for that one line.
  #
  # A source that cannot be consulted answers neither yes nor no. The name is
  # UNRESOLVED: the audit reports the token it declined to judge and names the
  # subject and the reason, rather than judging it against this project.

  @bead:beadloom-0mdo.81 @node:docs-audit
  Scenario: a subject the environment cannot confirm here leaves its version unjudged
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "Measured on git 2.49.0 in two isolated rigs."
    When the audit reads that project
    Then no finding reports a stale version
    And the audit reports 1 version token it could not judge, naming git

  @bead:beadloom-0mdo.81 @node:docs-audit
  Scenario: a subject the environment confirms is attributed, not left unjudged
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And the project is a git working tree
    And a document reading "Measured on git 2.49.0 in two isolated rigs."
    When the audit reads that project
    Then no finding reports a stale version
    And the audit attributes 1 version token to git
    And the audit reports no version token it could not judge

  @bead:beadloom-0mdo.81 @node:docs-audit
  Scenario: an unresolved subject silences nothing else in the same document
    Given a project at version "3.0.2" whose documentation declares bd a subject
    And a document reading "Measured on git 2.49.0; the current release is 3.1.0."
    When the audit reads that project
    Then a finding reports a stale version
    And the audit reports 1 version token it could not judge, naming git
