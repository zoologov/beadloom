<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T12:30:18.610981+00:00 · coverage 100% (`role-composer`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Role Composer

Composes role files from CORE + architecture + stack overlays (BDL-052 S3).

**Source:** `src/beadloom/onboarding/role_composer.py`

---

## Specification

### Purpose

A role file is assembled deterministically from a single CORE body plus the
selected overlays, so the same `(role, architecture, stack)` always yields
byte-identical output — the determinism the drift-guard relies on.

### Composition

`compose_role(role, *, architecture, stack)` concatenates, in order:

1. **CORE** — the universal, stack/tool-neutral role protocol
   (`templates/roles/core/<role>.md.txt`), the single source of truth.
2. one **ARCHITECTURE** overlay — `ddd` or `fsd` (peers)
   (`templates/roles/architecture/<arch>/<role>.md.txt`): the methodology's
   layer/boundary rules + the `# beadloom:` annotation vocabulary.
3. one+ **STACK** overlays in **sorted** order — `python` / `fastapi` /
   `javascript` / `typescript` / `vuejs`
   (`templates/roles/stack/<stack>/<role>.md.txt`): stack idioms + lint/type/test
   commands.

A missing per-role overlay fragment contributes nothing (overlays are additive
and never break an unrelated role).

### Modules

- **role_composer.py** — `compose_role()`, `compose_all_roles(config)`,
  `roles_templates_root()`, `ROLE_NAMES`.

### Invariants

- Deterministic: stack overlays are sorted, so listing order does not matter.
- An unknown role / architecture / stack raises `FlowConfigError` (loud, not a
  silently-empty file). The CORE fragment is required; overlay fragments are
  optional per role.
- FSD is at parity with DDD: every role has both architecture overlays.

## API

Module `src/beadloom/onboarding/role_composer.py`:
- `compose_role(role, *, architecture, stack)` → `str`
- `compose_all_roles(config)` → `dict[str, str]`
- `roles_templates_root()` → `Path`
- `ROLE_NAMES` — `("dev", "test", "review", "tech-writer")`

## Testing

Tests: `tests/test_role_configurator.py`
