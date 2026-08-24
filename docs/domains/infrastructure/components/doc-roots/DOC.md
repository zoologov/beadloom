# Doc Roots (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/doc_roots.py`

---

## Overview

Resolves the three documentation spaces a project keeps, and answers which space
a given document belongs to.

- **TO-BE** — `PRD`, `RFC`, `BRIEF`, `CONTEXT`, `PLAN`. What the system is to
  become.
- **AS-IS** — `SPEC`, `DOC`, `README`. What it is; the space `sync-check` holds
  against the code.
- **WORKING** — `ACTIVE`. Ephemeral progress state, exempt from freshness by
  declaration.

The names are deliberately not TODO/DONE. Nothing changes status: a PRD stays
the record of what was intended, and a *different* artifact — the AS-IS document
— is what gets updated when reality moves. That makes the checkable claim a
relation between two artifacts, which `application/doc_spaces.py` evaluates.

It lives in `infrastructure` (the lowest layer), beside `scan_paths`, so that
`doc-sync` can resolve doc roots for the WORKING freshness exemption without a
domain reaching UP into `application`.

**Kind wins over root**, and the ordering carries weight: `ACTIVE.md` lives
inside the TO-BE tree, so a root-first answer would classify every WORKING
document as intent and the exemption would apply to nothing.

## Configuration

`.beadloom/config.yml`, key `doc_roots`. Every part is optional; what a project
does not declare keeps the shipped default.

```yaml
doc_roots:
  to_be:
    roots: [".claude/development/docs/features/*/*.md"]
    kinds: [PRD, RFC, BRIEF, CONTEXT, PLAN]
  as_is:
    roots: ["docs/**/*.md", "*.md"]
    kinds: [SPEC, DOC, README]
  working:
    kinds: [ACTIVE]
    exempt_from_freshness: true
    reason: "an ACTIVE document records progress, not what the code is"
```

`reason` is mandatory whenever `exempt_from_freshness` is true — an exemption
without a stated reason is reported as a configuration error by
`beadloom docs spaces`. There is deliberately no `until` field: `until` is an
exit condition for a debt, and a document's being ephemeral is not one.

Configuration errors are carried rather than raised, so one malformed line
cannot turn into a crashing gate that names the wrong file.

## Public surface

- `SPACE_TO_BE`, `SPACE_AS_IS`, `SPACE_WORKING`, `SPACES` — the vocabulary.
- `DEFAULT_ROOTS`, `DEFAULT_KINDS`, `DEFAULT_WORKING_REASON` — the shipped
  defaults.
- `document_kind(path)` — the kind a path names (`PRD.md` is a `PRD`).
- `WorkingExemption` — `exempt_from_freshness` plus its declared `reason`.
- `DocSpaces` — `space_of(rel_path)`, `space_of_kind(kind)`,
  `documents_in(project_root, space)`, `working_documents(project_root)`, and
  the `config_errors` found while reading the block.
- `resolve_doc_spaces(project_root)` / `default_doc_spaces()`.

## Collaborators

- `doc_sync/engine.py` reads the WORKING exemption in `check_sync`, where an
  exempt pair is reported with status `exempt` and the declared reason.
- `application/doc_spaces.py` classifies populations and evaluates the
  TO-BE → AS-IS relation.
- `application/reindex/indexing.py` indexes the TO-BE space in place.
- `doc_sync/doc_quality.py` re-exports `document_kind`, so the kind vocabulary
  has one definition rather than two.

> Component doc (BDL-061 S5). Public surface verified against `doc_roots.py`.
