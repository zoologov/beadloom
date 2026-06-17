# Atomic IO (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/atomic_io.py`

---

## Overview

A domain-agnostic, dependency-free primitive that writes a YAML file with
**crash-safe integrity**, so a partial write can never replace the
source-of-truth graph YAML (`.beadloom/_graph/*.yml`, and the onboarding
`services.yml` / `imported.yml` / `rules.yml` / `config.yml`) with a truncated
or half-written file.

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

## What it guarantees (integrity, not durability)

`write_yaml_atomic` guarantees **integrity**, not full durability — the two
are deliberately distinct, and the boundary is documented here so callers do
not over-rely on it.

- **Integrity (guaranteed).** A crash, exception, or interruption at any point
  during the write never leaves a torn file in place. The target is always one
  complete YAML document: either the prior contents or the new contents. This
  holds because the bytes are fully written and `fsync`ed to a temp file
  *before* the single `os.replace` commit, and a failed/interrupted write
  removes the temp file and leaves the target untouched.
- **Durability boundary (not guaranteed).** The parent **directory** entry is
  *not* `fsync`ed after the rename. The file's data is flushed, but the
  directory metadata recording the rename is left to the OS. So across an
  OS-level or power crash immediately after a commit, the filesystem may roll
  the rename back and the reader sees the **prior** complete file — the latest
  commit can be lost, but the file is **never corrupted**. This is an
  acceptable, deliberate trade-off: the invariant we need is integrity (the
  graph YAML is always parseable), and a lost last write is recovered by
  re-running the command. Full directory-`fsync` durability is a possible
  future hardening if a use case ever needs it.

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
> direct `yaml.dump` -> `write_text` path. Integrity is guaranteed; the
> parent-directory is not `fsync`ed, so the last commit may be lost (never
> corrupted) across an OS/power crash — a documented boundary, not a defect.
