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
  `roles_templates_root()`, `roles_in()`, `fragment_role_name()`, `ROLE_NAMES`,
  and the re-exported `SHARED_ROLE_FRAGMENTS`.

### A role exists because a core fragment ships for it

`ROLE_NAMES` is **derived**, not declared (BDL-068 S1.5). It used to be a literal, and so
was `agentic_flow_setup.AGENT_FILES`, whose own comment said it mirrored this one — two homes
for one fact with eight readers between them, plus a third list spelled as prose inside the
Cursor orchestrator pointer. Adding a fifth role meant editing all three, and a fifth role
added to one of them is exactly the fifth thing that can drift (BDL-UX #191's shape).

`roles_in(core_dir)` reads the population out of `templates/roles/core/*.md.txt` over a SHAPE
rather than a spelling: a fragment is a role when it opens with YAML front matter whose `name:`
equals its own file name. That is already the stated difference between a role and the shared
`_writing` LAYER, which carries no front matter at all, so keying on the `_` prefix would have
been a convention a fragment can forget. A fragment naming a different role than its file is
skipped rather than guessed at: the two spellings are what every reader keys on, and one that
disagrees with itself would compose under one name and be written under another. That same rule
is what keeps a localisation from being a second role — `scout.ru.md.txt` declares `name:
scout`, which is not the name of its file. It was a separate guard until a mutant showed the
guard could not be made to fail, and it was deleted rather than kept. The result is sorted,
because a directory listing is not ordered and the adapters it generates must be byte-identical
between runs.

Dropping `explore.md.txt` into `roles/core/` therefore made `explore` a role in every reader
by the same act — the composer, the adapters, the vendored scaffold, the present/missing split
`config-check` reports and the Cursor pointer.

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
- `roles_in(core_dir)` → `tuple[str, ...]` — the roles a directory of CORE fragments ships,
  sorted
- `fragment_role_name(text)` → `str | None` — the role a fragment declares itself to be, or
  `None` for a layer
- `ROLE_NAMES` — derived from the shipped fragments; today
  `("dev", "explore", "review", "tech-writer", "test")`, and
  `agentic_flow_setup.AGENT_FILES` **is** this tuple rather than a copy of it
- `SHARED_ROLE_FRAGMENTS` — `("_writing",)`. A shared fragment is a **layer, not
  a role**: it carries no front matter, is never written as an adapter, and
  `compose_role("_writing", …)` raises `FlowConfigError`

## Testing

Tests: `tests/test_role_configurator.py`, `tests/test_flow_composition.py`,
`tests/test_shared_writing_standard.py`, `tests/test_role_bdd_mutation_duties.py`
