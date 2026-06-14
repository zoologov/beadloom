<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T18:52:29.106245+00:00 · coverage 100% (`flow-config`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

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
