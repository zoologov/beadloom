# Role Composer

Composes role files from CORE + architecture + stack + **project** layers
(BDL-052 S3; the fourth layer and the shared implementation arrived in BDL-061 S3).

**Source:** `src/beadloom/onboarding/role_composer.py`

---

## Specification

### Purpose

A role file is assembled deterministically from a single CORE body plus the
selected overlays, so the same `(role, architecture, stack)` always yields
byte-identical output — the determinism the drift-guard relies on.

### Composition

`compose_role(...)` validates the role/architecture/stack and then delegates to
`composer.compose("roles", role, ...)` — the layering is shared with the slash
commands and `CLAUDE.md` rather than reimplemented per artifact. The order is:

1. **CORE** — the universal, stack/tool-neutral role protocol
   (`templates/roles/core/<role>.md.txt`), the single source of truth.
2. the **shared CORE fragments** (`SHARED_ROLE_FRAGMENTS`) — a text every role
   carries, composed straight after its own core. Today that is the **writing
   standard** (`templates/roles/core/_writing.md.txt`, BDL-061 S4): it used to
   live inside the `tech-writer` core, so the three roles that produce the TO-BE
   documents — PRD, RFC, CONTEXT, PLAN, review report — were held to no standard
   at all. It ships once and is language-selectable like any other layer, so a
   team writing in Russian is held to the standard in Russian (BDL-UX #136); the
   `ru` fragment ships.
3. one **ARCHITECTURE** overlay — `ddd` or `fsd` (peers)
   (`templates/roles/architecture/<arch>/<role>.md.txt`): the methodology's
   layer/boundary rules + the `# beadloom:` annotation vocabulary.
4. one+ **STACK** overlays in **sorted** order — `python` / `fastapi` /
   `javascript` / `typescript` / `vuejs`
   (`templates/roles/stack/<stack>/<role>.md.txt`): stack idioms + lint/type/test
   commands.

5. the **PROJECT** fragment — `.beadloom/flow/roles/<role>.md` in the adopting
   repo, when a `project_root` is given. This is the supported place for a
   team's standing practices; before it existed, any such addition was reported
   as drift and `--fix` deleted it (BDL-UX #139, #152).

A missing per-role overlay fragment contributes nothing (overlays are additive
and never break an unrelated role). Overlays are **append-only**: a core rule
can only be stood down by a declared suppression (see `flow-suppression`).

### Modules

- **role_composer.py** — `compose_role()`, `compose_all_roles(config)`,
  `roles_templates_root()`, `ROLE_NAMES`, and the re-exported
  `SHARED_ROLE_FRAGMENTS`.

### Invariants

- Deterministic: stack overlays are sorted, so listing order does not matter.
- An unknown role / architecture / stack raises `FlowConfigError` (loud, not a
  silently-empty file). The CORE fragment is required; overlay fragments are
  optional per role.
- FSD is at parity with DDD: every role has both architecture overlays.

## API

Module `src/beadloom/onboarding/role_composer.py`:
- `compose_role(role, *, architecture, stack, language=..., suppressions=(), project_root=None)` → `str`
- `compose_all_roles(config, project_root=None)` → `dict[str, str]` — omitting
  `project_root` yields the shipped-only composition, the drift baseline for a
  repo with no project layer
- `roles_templates_root()` → `Path`
- `ROLE_NAMES` — `("dev", "test", "review", "tech-writer")`
- `SHARED_ROLE_FRAGMENTS` — `("_writing",)`. A shared fragment is a **layer, not
  a role**: it carries no front matter, is never written as an adapter, and
  `compose_role("_writing", …)` raises `FlowConfigError`

## Testing

Tests: `tests/test_role_configurator.py`, `tests/test_flow_composition.py`,
`tests/test_shared_writing_standard.py`, `tests/test_role_bdd_mutation_duties.py`
