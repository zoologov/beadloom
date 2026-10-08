# CONTEXT: BDL-079 — Release 8.0.0

> **Status:** Approved
> **Created:** 2026-10-08

---

## State

Branch `features/BDL-079` from `main` at `539ed4a3` (BDL-078 merged). PyPI latest 7.0.0. No
`[Unreleased]` section. No declared public API.

## Standards

Python >= 3.10; ruff, mypy --strict; pytest; the Gate (`beadloom ci`) rc 0 before every commit
that touches docs; commits `[BDL-079] <type>: <description>`; one PR; merge on green CI; publish
by a GitHub Release `v8.0.0`; verify on the downloaded wheel; documents in English, README
Russian first.

## Architectural Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-08 | The version follows SemVer 2.0.0; the number is derived from a declared public API and a measured diff, never from precedent | Owner: «Надо сделать согласно https://semver.org/lang/ru/ и следовать ему» |
| 2026-10-08 | Public API = commands, options, exit codes; `config.yml` keys; keys and value vocabularies of `--json` outputs (`ctx`, `status`, `export`, debt report); MCP tools; the portal data file schema; files generated for an adopter. Python import paths are not public | Owner: «Утверждаю» on the coordinator's composition |
| 2026-10-08 | 8.0.0 | The activity level vocabulary changed incompatibly (`cold` never emitted; `cool`, `quiet` new); the debt values move on an unedited tree; an unusable `site:` / `activity:` block is refused where it was ignored |
| 2026-10-08 | SemVer becomes a rule of the shipped flow in a later work item (`beadloom-tvjp`) | Owner: «можно в следующих задачах» |
| 2026-10-08 | Reference documents with surface drift are read, not re-baselined blind | BDL-UX #163; the drift accumulated through BDL-078 |

## Current Phase

- **Phase:** Planning
- **Current bead:** see ACTIVE.md
- **Blockers:** none
