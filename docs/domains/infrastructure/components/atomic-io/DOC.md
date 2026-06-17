# Atomic IO (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/atomic_io.py`

---

## Overview

A domain-agnostic, dependency-free primitive that writes a YAML file
**atomically**, so a crash mid-write can never corrupt the source-of-truth
graph YAML (`.beadloom/_graph/*.yml`, and the onboarding `services.yml` /
`imported.yml` / `rules.yml` / `config.yml`).

`write_yaml_atomic` serializes the data, writes it to a temporary file in the
*same* directory as the target, `flush`es + `fsync`s it, then commits with
`os.replace` — an atomic rename on POSIX. A reader therefore always observes
either the complete old file or the complete new file, never a half-written
one. On any failure the temp file is removed and the prior target is left
untouched (the rename is the single commit point).

It lives in `infrastructure` (the lowest layer) so that every graph-YAML
writer — the `graph` loader/patcher, the `services` link patcher, and the
`onboarding` scaffolders — routes through one crash-safe commit point instead
of a raw `open(..., 'w')` / `yaml.dump` -> `write_text` that can truncate a file
on interruption.

## Public surface

- `write_yaml_atomic(path, data, **dump_kwargs)` — serialize `data` with
  `yaml.dump(data, **dump_kwargs)` and write it to `path` atomically. The
  `dump_kwargs` (e.g. `sort_keys=False`, `default_flow_style=False`,
  `allow_unicode=True`) are passed through verbatim so the emitted bytes are
  **identical** to the prior direct-dump call-site (behavior-preserving).

## Collaborators

- `graph/loader.py` — patches node `summary` / `source` back to disk.
- `services/commands/index_ops.py` — the `link` add/remove patcher.
- `onboarding/scanner/bootstrap.py` — writes `services.yml` + `config.yml`.
- `onboarding/scanner/doc_classify.py` — writes `imported.yml`.
- `onboarding/scanner/rules_gen.py` — writes `rules.yml`.
- `onboarding/doc_generator.py` — the `_patch_docs_field` writer.

> Component doc (BDL-060 S1 / G6). Public surface verified against
> `atomic_io.py`. Behavior-preserving: identical output bytes vs the prior
> direct `yaml.dump` -> `write_text` path.
