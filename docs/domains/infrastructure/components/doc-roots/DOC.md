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

**When kind and root disagree, kind wins and the disagreement is reported.** A
document whose kind places it in a space whose own roots exclude it is counted in
that space, and `beadloom docs spaces` reports
`document_outside_declared_root` naming the kind, the space, the count and up to
five paths. Before BDL-061 S5's `.77` such a document was in *no* population at
all: found by one glob, rejected by one classifier, and looked for by nobody —
so a project whose planning directories hold a `README.md` lost every one of its
epics and their documents while the gate printed a plausible number. A space
that declares **no** root has said nothing about where its documents live and
contradicts nothing, which is why the shipped `ACTIVE.md` layout is silent.

**One scan places every document.** `DocSpaces.classify(project_root)` globs
every declared root once and classifies each file once, so
`sum(len(bucket) for bucket in by_space.values())` equals the number of files the
roots matched, on any tree. `documents_in` and `working_documents` read off that
classification rather than assembling a population from a space's own glob.

**Among kinds, WORKING is consulted first** (`_KIND_PRECEDENCE`, separate from
`SPACES`, which is the order a report reads best). A kind a project declares for
WORKING is the one declaration that changes what a check *does* rather than where
it looks, so a shipped default shadowing it switches nothing on and says nothing.
The three shipped kind lists are disjoint, so no shipped classification depends
on this order.

**Among roots, WORKING is consulted first.** Its shipped root list is empty, so
the only way a document reaches WORKING by root is a project declaring it, while
the AS-IS default is the catch-all `docs/**/*.md`. If the catch-all won, a
declaration written in the file adopters are told to edit would be silently
inert. The declaration wins, and the win is visible: a document excused this way
that the graph also declares as a node's documentation is reported as
`working_declaration_contradicted` by `beadloom docs spaces`.

## One spelling of a document path

A `sync_state` row names its document **relative to the docs directory**
(`guides/ci.md`) because that is what the indexer writes, while every root glob
is written **relative to the project** (`docs/guides/ci.md`). Those were two
different questions asked of one declaration: kind agreed on both spellings (a
stem carries no prefix), roots did not, and a root-declared WORKING exemption
therefore reached freshness without reaching the report that exists to object to
it. `DocSpaces.project_path(doc_path)` is the one translation, and every caller
holding a docs-dir-relative path passes it through before asking `space_of`.

The docs directory itself is read by `resolve_docs_dir(project_root)` — the
single reader of the `docs_dir` config key, which three readers held before
(the reindexer's, the reference-document scan's, and a hardcoded `docs` inside
`check_sync`).

## Configuration

`.beadloom/config.yml`, key `doc_roots`. Every part is optional; what a project
does not declare keeps the shipped default.

```yaml
doc_roots:
  to_be:
    roots: [".claude/development/docs/features/*/*.md"]
    kinds: [PRD, RFC, BRIEF, CONTEXT, PLAN]
    intent_documents: [CONTEXT.md, BRIEF.md]
  as_is:
    roots: ["docs/**/*.md", "*.md"]
    kinds: [SPEC, DOC, README]
  working:
    kinds: [ACTIVE]
    roots: []
    exempt_from_freshness: true
    reason: "an ACTIVE document records progress, not what the code is"
```

Each half a project **declares** answers for itself. `beadloom docs spaces`
prints how many documents every declared kind and every declared root excused,
and reports `working_exemption_inert` for each one that excused nothing. A
declaration covering 39 documents therefore has to print the number 39, and a
`kinds: [ACTIVE, SPEC]` line whose `SPEC` half reaches nothing says so instead of
being silenced by its live sibling. A project that declares the exemption without
a list of its own is asked the same question about the WORKING space as a whole.

`intent_documents` names the files an epic declares its related nodes in, most
specific first. It is configuration for the reason every root beside it is: with
the pair hardcoded, an adopter whose planning document is named otherwise lost
100% of its epics and the gate printed a plausible `0 of 0 epic(s) with closed
beads`. A declared list REPLACES the shipped pair rather than joining it — a
project's convention is a statement, not an addition to ours.

`reason` is mandatory whenever `exempt_from_freshness` is true — an exemption
without a stated reason is reported as a configuration error by
`beadloom docs spaces`. There is deliberately no `until` field: `until` is an
exit condition for a debt, and a document's being ephemeral is not one.

Configuration errors are carried rather than raised, so one malformed line
cannot turn into a crashing gate that names the wrong file.

## Public surface

- `SPACE_TO_BE`, `SPACE_AS_IS`, `SPACE_WORKING`, `SPACES` — the vocabulary.
- `DEFAULT_ROOTS`, `DEFAULT_KINDS`, `DEFAULT_WORKING_REASON`,
  `DEFAULT_DOCS_DIR`, `DOCS_DIR_KEY`, `DEFAULT_INTENT_DOCUMENTS` — the shipped
  defaults and the config key naming the documentation directory.
- `document_kind(path)` — the kind a path names (`PRD.md` is a `PRD`).
- `WorkingExemption` — `exempt_from_freshness` plus its declared `reason`,
  `declared`, and `kinds_declared` / `roots_declared` saying which halves the
  project wrote rather than inherited.
- `Classification` — `by_space` (a bucket per space) and
  `outside_declared_root` (the documents whose kind overruled their space's
  roots).
- `DocSpaces` — `space_of(rel_path)`, `space_of_kind(kind)`,
  `project_path(doc_path)`, `classify(project_root)`,
  `documents_in(project_root, space)`, `working_documents(project_root)`, the
  `docs_dir` and `intent_documents` it was resolved with, and the
  `config_errors` found while reading the block.
- `resolve_doc_spaces(project_root)` / `default_doc_spaces(docs_dir)`.
- `resolve_docs_dir(project_root)` — the documentation directory, project
  relative.

## Collaborators

- `doc_sync/engine.py` reads the WORKING exemption in `check_sync`, where an
  exempt pair is reported with status `exempt` and the declared reason. The
  exemption covers freshness and nothing else: a pair whose document or code file
  is gone is reported `missing` before any exemption applies, so deleting a file
  cannot be quieter than leaving it.
- `application/doc_spaces.py` classifies populations and evaluates the
  TO-BE → AS-IS relation.
- `application/reindex/indexing.py` indexes the TO-BE space in place.
- `doc_sync/doc_quality.py` re-exports `document_kind`, so the kind vocabulary
  has one definition rather than two.

> Component doc (BDL-061 S5). Public surface verified against `doc_roots.py`.
