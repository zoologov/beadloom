# PRD: BDL-079 — Release 8.0.0: the viewer ships, and the public API is declared

> **Status:** Approved
> **Created:** 2026-10-08

---

## Problem

PyPI's latest is 7.0.0 (2026-09-29). `main` at `539ed4a3` carries BDL-076, BDL-077 and BDL-078
— the architecture viewer, the portal for adopters, the edges drawn like a classic diagram, the
finished look, the activity metric by changed lines, five defects fixed — and none of it is
published. `CHANGELOG.md` has no `[Unreleased]` section.

**The version number must follow Semantic Versioning 2.0.0** (owner, 2026-10-08: «Надо сделать
согласно https://semver.org/lang/ru/ и следовать ему»). SemVer's first rule is that the software
declares a public API, and no document of this project declares one: `CONTRIBUTING.md:254` names
SemVer in one line, `CHANGELOG.md:6` says the project adheres to it, and 7.0.0's entry treated the
values of `ctx` and the debt count as public without saying so anywhere else.

Measured on 2026-10-08 (`v7.0.0` against `main`, two versions of the code over one tree; the
table is in RFC.md): no command added, removed or renamed; options and `config.yml` keys only
added; the activity level vocabulary changed incompatibly — `cold` is never emitted any more, the
set is `hot / warm / cool / quiet / dormant` ranked by changed lines; `ctx --json`, `export` and
`docs polish` gain `lines_30d` / `lines_90d`; the debt report's values move on an unedited tree;
the portal data file is schema 2, a superset of 1; 40 Python import paths moved, none documented
as public.

Loose ends the release must not ship with: an HTML `TODO` marker in
`docs/services/vitepress-site.md` asking for the site-e2e case count of the PR run; eight
reference documents (the README pair, `docs/architecture.md`, guides) carrying a surface-drift
warning that nobody has read since the viewer landed; the version places that no instrument
checks (`ROADMAP.md:3`, `CHANGELOG.md`, `tests/test_integration_v1.py:17`, the docs-audit SPEC).

## Goals

1. **8.0.0 on PyPI, verified on the wheel downloaded from PyPI** — not on the local build — on a
   project that is not this repository: `beadloom --version`, `__version__` and the distribution
   metadata read 8.0.0; `docs site` writes the scaffold and the portal builds; `reindex` prints the
   activity line with the five levels; the same harness fails on 7.0.0.
2. **The public API is declared** in `CONTRIBUTING.md` and one document under `docs/`, in the
   owner's composition (2026-10-08, «Утверждаю»): the commands, their options and exit codes; the
   keys of `.beadloom/config.yml`; the keys **and the value vocabularies** of the `--json` outputs
   (`ctx`, `status`, `export`, the debt report); the MCP tools; the portal data file's schema;
   the files generated for an adopter. Python import paths are **not** public API, stated.
3. **The CHANGELOG names the release by the declaration:** `[8.0.0]` with *Breaking* (the activity
   vocabulary; the debt values that move; the new refusal of an unusable `site:` / `activity:`
   block), *Added*, *Changed*, *Fixed*, each line traceable to a PR; the version is major because
   of the first *Breaking* line and for no other reason.
4. **Every version place reads 8.0.0**, checked and unchecked alike, and the loose ends above are
   closed: the `TODO` marker filled with the measured count, the eight reference documents read
   and either corrected or attested by a person who read them.
5. **The README pair tells an adopter the viewer exists** — Russian first, English follows — if it
   does not already.

## Non-goals

- No product code changes beyond the version bump and what a documentation fix strictly needs.
- SemVer as a rule of the shipped flow — the release role, the roles' duties, the public-API
  template, the CHANGELOG check — is `beadloom-tvjp`, after this release.
- The follow-ups of BDL-078 (`beadloom-be6e`, `beadloom-j4gi`, `beadloom-pre3`).

## User stories

- **US-1** As an adopter, `pip install beadloom` gives me the viewer and the portal, and the
  CHANGELOG tells me in one place what changed and what I must regenerate.
- **US-2** As an adopter with a script on `ctx --json`, the CHANGELOG's *Breaking* section names
  the value set that changed before my script breaks.
- **US-3** As a contributor, I can read what the public API is and decide a version number
  without a precedent hunt.

## Success criteria

- `pip download beadloom==8.0.0` from PyPI, installed in a fresh environment on another project:
  version 8.0.0 everywhere; `docs site` + `npm run docs:build` green; `reindex` names the activity
  levels; the harness red on 7.0.0.
- `beadloom ci` rc 0 on `main` after the merge; `beadloom lint --strict` 0 errors (the root
  node's summary is a checked version claim).
- `grep -rn 7\.0\.0` over the tracked tree finds only history (archive, BDL-075/076/077/078
  documents, the CHANGELOG's older sections).
- The published portal (deploy-site from `main`) shows five activity levels, not "1 commit"
  everywhere — the proof that the full-history checkout works where readers look.

## Rulings

- 2026-10-08, owner: the version follows SemVer 2.0.0; the public API composition above;
  8.0.0; SemVer recorded in roles and release rules later (`beadloom-tvjp`).
