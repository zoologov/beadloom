# Doc Templates

The shape of a generated document — its template, its values, and the sections it requires.

**Source:** `src/beadloom/onboarding/doc_templates.py`

---

## Specification

### Purpose

Until BDL-061 S4b every doc skeleton was an f-string inside `doc_generator.py`. Two consequences
followed, and both are why this module exists: an adopter had **nothing to adapt** — the shape of
their architecture documentation was a Python literal inside our package — and **nothing held the
shape after generation**, so a README could lose the sections it was born with and no check could
tell.

The templates ship as package data under `src/beadloom/onboarding/templates/docs/` and compose
through `compose(core, architecture, stack, project)`, the assembly S3 built for the role files.
Reusing that mechanism rather than inventing a second one is what makes a project layer work for
documents on the day it shipped for roles.

### Doc kinds

| Kind | Generated file | Node kind |
|------|----------------|-----------|
| `overview` | `docs/architecture.md` | — (the project) |
| `domain` | `docs/domains/<ref>/README.md` | `domain` |
| `service` | the service's page | `service` |
| `feature` | `docs/domains/<parent>/features/<ref>/SPEC.md` | `feature` |
| `beadloom-readme` | `.beadloom/README.md` | — (the project) |

A kind with no `node_kind` describes the project rather than a node, so it has no doc-code pair
and no sections to check it against.

### Rendering

Placeholders use a doubled brace, deliberately **not** `str.format`'s single brace:

```text
# {{ref_id}}

> {{summary}}
```

A generated document carries Mermaid, JSON and shell fragments, and a lone `{` in any of them
would either raise from the formatter or be eaten silently.

A placeholder with no value **raises** `DocTemplateError`. A silently-empty substitution is how a
document ships half-written, which is the class `unfilled-placeholder` exists to report. A value
the template does not use is allowed: an overlay is free to drop a fact it has no place for.

### Required sections are derived, never declared twice

`required_sections(kind)` reads the literal `## ` headings of the **composed** template, with
placeholders erased first. Two consequences follow from that one rule:

- A project fragment at `.beadloom/flow/docs/domain.md` that appends `## Runbook` makes `Runbook`
  a required section by the same act. That is PLAN's criterion "a project overlay can add
  required sections", met with one source of truth rather than two.
- A heading that reaches the document **through** a placeholder — `## Public API`, rendered only
  for a node with public symbols — is conditional by construction and cannot be required of a
  node that has none.

### A doc composition carries no suppression notice

`ArtifactKind.carries_suppressions` is `False` for `docs`. A declared suppression stands down a
rule addressed to an **agent**; a generated README has no rules to stand down, and appending the
notice would publish flow configuration as documentation.

## Public API

| Symbol | Kind |
|--------|------|
| `DOC_ARTIFACT_KIND` | constant |
| `DOC_KINDS` / `DOC_KIND_FOR_NODE_KIND` | constant |
| `DEFAULT_DOC_CONFIG` | constant |
| `DocKind` | dataclass |
| `DocTemplateError` | exception |
| `doc_template` | function |
| `doc_flow_config` | function |
| `render_doc` | function |
| `required_sections` | function |
| `required_sections_by_node_kind` | function |

## Dependencies

- Depends on: `flow-composer` (`compose`), `flow-config`
- Used by: `doc-generator`, `doc-shape-requirements`

## Parent

`onboarding`

## Testing

`tests/test_doc_templates.py` — composition of every kind, the project layer, the derived
sections, byte-identity of the extraction against the literals it replaced, and rendering for a
project that is not Beadloom.
