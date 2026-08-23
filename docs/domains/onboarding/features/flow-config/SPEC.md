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
language: en                   # tag the flow's documents are written in
overlays:
  suppress:                    # stand down a shipped core rule, declared
    - rule: "Anti-patterns / Shell"
      reason: "the team runs on Windows; the -f idiom does not apply"
      until: "a windows stack overlay ships"
```

For Beadloom itself: `tools: [claude]`, `architecture: [ddd]`, `stack: [python]`.

### `language` (BDL-061 S3, BDL-UX #136)

A BCP-47-ish tag, default `en`. It is validated for **shape**, not against a
closed list: the set of languages a team writes in is not ours to enumerate, and
rejecting an unlisted one would push the project straight back to hand-editing a
drift-guarded file. It does two things:

- every composition layer prefers a `<name>.<lang>.md.txt` fragment, and a
  missing localisation falls back to the default **with a note** — the
  composition says which fragment it could not find, so a Russian-speaking team
  is never silently handed English;
- the `doc-language` auto-region in `CLAUDE.md` renders from it, replacing the
  unconditional "ALL documents MUST be written in English" the scaffolded flow
  used to state as a core rule.

### `overlays.suppress` (BDL-061 S3)

Overlays are append-only, so nothing in the project layer can delete core text.
A core rule can only be stood down by declaration, and `rule`, `reason` and
`until` are all mandatory — the same bar `guards.<name>.exclusions` holds.
Validation runs through `flow_suppression`; an unknown key under `overlays` is
rejected with the reminder that project *additions* are files under
`.beadloom/flow/`, not keys here. See the
[Flow Suppression SPEC](../flow-suppression/SPEC.md).

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
- `FlowConfig` — frozen config (`tools`, `architecture`, `stack`, `quality`,
  `language`, `suppressions`).
- `FlowConfigError` — raised for malformed / unknown-value configs.
- `build_flow_config(data)` → `FlowConfig`
- `load_flow_config(project_root)` → `FlowConfig`
- `load_flow_config_or_default(project_root, *, default)` → `FlowConfig`
- `resolve_flow_config(project_root, *, tools, architecture, stack)` → `FlowConfig`
- `detect_stack(project_root)` → `tuple[str, ...]`
- `persist_flow_config(project_root, config)` → `Path | None`
- `SUPPORTED_TOOLS` / `SUPPORTED_ARCHITECTURES` / `SUPPORTED_STACKS` /
  `SUPPORTED_QUALITY` / `DEFAULT_LANGUAGE`

`resolve_flow_config()` carries `language` and `suppressions` through from
`flow.yml` verbatim: they are project policy, not a per-run choice, so they have
no overriding flag.

### The resolved selection is written down (BDL-UX #187)

`persist_flow_config()` writes the resolved config to `.beadloom/flow.yml` on a
first scaffold, and **never** over an existing one — that file is the adopter's
policy, and `language` / `overlays.suppress` have no flag and live only there.

Before this, `setup-agentic-flow` composed every artifact from a selection it
resolved in memory and never recorded. Measured on a fresh TypeScript project:
`init` → `setup-agentic-flow` → `config-check` exited **1** with four errors,
one per role adapter, because the no-`flow.yml` branch expects the plain
vendored role files and the composed ones are not that. The command's own
closing advice points at `config-check`, and following it produced four errors
on an untouched repository — with a remediation that read *"Add a flow.yml
(`beadloom setup-agentic-flow`)"*, the command the reader had just run.

Persisting the selection also closed a divergence found while fixing it:
`scaffold()` re-resolved the config from disk **without the CLI flags**, so
`setup-agentic-flow --architecture fsd` composed the role adapters as `fsd` and
the slash commands and `CLAUDE.md` as `ddd`. The command's resolved config is
now threaded into `scaffold(config=…)`.

## Testing

Tests: `tests/test_role_configurator.py`, `tests/test_flow_composition.py`
