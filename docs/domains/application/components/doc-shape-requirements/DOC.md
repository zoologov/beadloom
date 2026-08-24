# Doc Shape Requirements (component)

The shape a project's documents are held to.

**Source:** `src/beadloom/application/doc_shape.py`

---

## Overview

The shape a generated document must keep is derived from the composed doc templates, which live
in the **onboarding** domain. The check that reads a document back lives in **doc-sync**. The two
are peers and neither may import the other, so the join happens here, in the layer whose job is
that kind of orchestration.

The same module resolves the other input the document checks need from outside their domain: the
placeholder vocabulary, derived from the shipped `/templates` command.

## Public surface

- `section_requirements(project_root)` — required sections per **graph node kind**, or `None`
  when the flow config is malformed. `None` is returned rather than raised because a bad
  `flow.yml` is `config-check`'s finding by name, and raising here would turn one configuration
  error into a failing freshness gate that names the wrong file.
- `planning_document_globs(project_root)` / `planning_documents(project_root)` — where the
  writing-standard checks read from. Defaults to
  `.claude/development/docs/features/*/*.md`, the convention `/task-init` scaffolds into;
  overridable by `doc_quality.paths` in `.beadloom/config.yml`, because the flow ships to
  projects with their own layout and a hardcoded path would make the check true only here.
- `shipped_placeholders(project_root)` — the placeholder tokens the composed templates leave for
  an author, read from **fenced blocks only** and excluding anything wholly inside an inline code
  span.

## Where it is called

`section_requirements` is passed into `check_sync` by the four surfaces that REPORT freshness:
the CI gate, `beadloom sync-check`, the MCP `sync_check` tool and the TUI dashboard. Three call
sites deliberately do not pass it — `sync-update` (twice), where re-baselining cannot fix a
missing section, and `site_published`, where publishing does not judge one.

`planning_documents` and `shipped_placeholders` are called by `beadloom docs quality` and by the
`docs-quality` gate step.

## Configuration

```yaml
# .beadloom/config.yml
doc_quality:
  paths:
    - docs/rfcs/*.md
```

```yaml
# .beadloom/flow/docs/domain.md — the project layer, appended to the template
## Runbook
Who to page.
```

A section appended by the project layer becomes a required section of that doc kind. There is one
source of truth: the composed template.
