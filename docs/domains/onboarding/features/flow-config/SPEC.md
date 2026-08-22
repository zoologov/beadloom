# Flow Config (`.beadloom/flow.yml`)

The role-configurator config + loader, in the onboarding domain (BDL-052 S3).

**Source:** `src/beadloom/onboarding/flow_config.py`

---

## Specification

### Purpose

The agentic flow is no longer hardcoded to Python + Claude Code. A repo declares
its **tools**, **architecture methodology**, **stack/frameworks**, and **quality
bars** in `.beadloom/flow.yml`; this module loads + validates that into an
immutable `FlowConfig` the composer turns into per-tool role adapters.

### Schema

```yaml
tools: [claude, cursor]        # which IDE adapter sets to generate
architecture: [ddd]            # exactly one methodology: ddd | fsd
stack: [python, fastapi]       # one+ stack/framework overlays
quality: [clean-code, tdd]     # quality bars (informational)
```

For Beadloom itself: `tools: [claude]`, `architecture: [ddd]`, `stack: [python]`.

### The `guards:` block is a second reader of the same file

`.beadloom/flow.yml` also carries the flow guards (BDL-061 S1):

```yaml
guards:
  bead-claimed:
    strictness: { default: warn, epic: block, chore: off }
    exclusions:
      - path: "scripts/**"
        reason: "operational scripts are not bead-scoped"
        until: "BDL-0xx introduces a scripts node"
```

`FlowConfig` neither validates nor carries it: `build_flow_config` reads the four
keys above and ignores every other top-level key, and
`application/guards/config.py:load_guards_config()` reads `guards:` on its own
and ignores the configurator's keys. The two readers share a file and a path
constant (`FLOW_CONFIG_RELPATH`) and nothing else, which is why an unparseable
`flow.yml` reaches an adopter twice — as `config-check` drift, and as a guard
that answers `error`. The block's schema, strictness resolution and exclusion
rules live in the
[flow-guards SPEC](../../../application/features/flow-guards/SPEC.md).

### Modules

- **flow_config.py** — `FlowConfig` (frozen dataclass), `build_flow_config()`
  (validate a parsed mapping), `load_flow_config()` / `load_flow_config_or_default()`,
  `resolve_flow_config()` (flag-over-config-over-default precedence), and
  `detect_stack()` (best-effort default from source file extensions).

### Invariants

- Validation is strict: an unknown tool / architecture / stack, an architecture
  that is not exactly one methodology, or an empty `tools`/`stack` raises
  `FlowConfigError` naming the offending value + the allowed set.
- `architecture` must name exactly one of `ddd` / `fsd` (peers).
- `tools`, `stack`, and `quality` are de-duplicated and sorted for deterministic
  composition.
- An absent `flow.yml` falls back to a default (resolve/or-default); a present
  but malformed one always raises (the `config-check` signal).
- Unknown **top-level** keys are ignored rather than rejected, which is what lets
  `guards:` live in the same file with its own reader and its own validation.
  Unknown values inside the four configurator keys are still errors.

## API

Module `src/beadloom/onboarding/flow_config.py`:
- `FlowConfig` — frozen config (`tools`, `architecture`, `stack`, `quality`).
- `FlowConfigError` — raised for malformed / unknown-value configs.
- `build_flow_config(data)` → `FlowConfig`
- `load_flow_config(project_root)` → `FlowConfig`
- `load_flow_config_or_default(project_root, *, default)` → `FlowConfig`
- `resolve_flow_config(project_root, *, tools, architecture, stack)` → `FlowConfig`
- `detect_stack(project_root)` → `tuple[str, ...]`
- `SUPPORTED_TOOLS` / `SUPPORTED_ARCHITECTURES` / `SUPPORTED_STACKS` / `SUPPORTED_QUALITY`

## Testing

Tests: `tests/test_role_configurator.py`
