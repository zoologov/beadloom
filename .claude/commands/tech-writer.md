# /tech-writer — Technical Writer + Systems Analyst Role

> **When to invoke:** when updating stale documentation after code changes
> **Focus:** accurate docs reflecting current API, symbols, architecture
> **Input:** `beadloom sync-check` stale entries
> **Output:** updated docs with fresh baselines

---

## Work start protocol

```bash
# 1. Identify stale docs (TWO sources — don't rely on sync-check alone!)
beadloom sync-check --json          # full list with reasons

# 2. Check bead comments for API CHANGE notes from /dev agents
bd comments <bead-id>               # look for "API CHANGE: ..." entries
# If API CHANGE found: grep docs/ for mentions of changed APIs
# sync-check may show [ok] even when docs are stale (reindex resets baseline)

# 3. Group by ref_id (one doc per domain/feature)
# Each ref_id = one independent unit of work

# 4. For assigned ref_id, gather context
beadloom ctx <ref-id>               # graph, symbols, deps, activity
beadloom sync-update --check <ref-id>  # which files are stale
beadloom docs polish                # enrichment data (symbol drift, deps)
```

> **WARNING:** `sync-check` can show `[ok]` even when doc content is stale. This happens when the /dev agent ran `beadloom reindex` after code changes — the sync baseline is reset, but the doc prose was never updated. Always cross-check with bead comments and grep for changed API names in `docs/`.

---

## Update workflow

For each stale ref_id:

### Step 1: Analyze

```bash
beadloom ctx <ref-id>               # current symbols, deps, source files
beadloom sync-update --check <ref-id>  # stale pairs with reasons
```

Read the current doc file and the source files that triggered staleness.

### Step 2: Understand the delta

Compare what the doc says vs what the code actually provides:

| Check | How |
|-------|-----|
| **symbols_changed** | New/removed/renamed functions, classes. Read source to understand new API. |
| **missing_modules** | Doc doesn't mention a module that exists in source dir. Add a section. |
| **untracked_files** | New source file not covered by any doc. Mention it or note it's internal. |
| **hash_changed** | File content changed. Diff to understand what's new. |

### Step 3: Update the doc

Rules:
- **Accuracy over volume** — write only what you can verify from code
- **Preserve structure** — keep existing sections (Specification, Invariants, API, Testing)
- **Update API section** — reflect current public symbols with signatures
- **Update module list** — add new modules, remove deleted ones
- **Update Testing section** — add new test files if any
- **Don't invent** — if you can't determine behavior from code, mark as `<!-- TODO: verify -->`

### Step 4: Reset baseline

```bash
beadloom reindex                    # re-index with updated docs
beadloom sync-check                 # verify: ref_id should be "ok" now
```

If still stale after reindex — the doc hash changed but symbols hash also changed.
This means both doc and code changed. Re-check with `sync-update --check`.

---

## Doc format reference

```markdown
# <Domain/Feature Name>

<One-line summary matching node summary in graph.>

## Specification

### Modules

- **module_name.py** — `public_func()` does X. `ClassName` handles Y.

### <Domain-specific sections>

<Architecture, data flow, configuration, etc.>

## Invariants

- <Key guarantees this component provides>
- <Constraints that must hold>

## API

Module `src/beadloom/<package>/<module>.py`:
- `function_name(args)` → `ReturnType` — description
- `ClassName` — description

## Testing

Tests: `tests/test_<module>.py`, `tests/test_<related>.py`
```

---

## Parallel execution

Tech-writer is designed for parallel agent deployment:

```
Coordinator assigns N agents, each with a subset of stale ref_ids:

Agent-1 (tech-writer): context-oracle, search, cache
Agent-2 (tech-writer): doc-sync, graph, graph-diff
Agent-3 (tech-writer): infrastructure, reindex, doctor
Agent-4 (tech-writer): onboarding, cli, mcp-server, tui, watcher
```

Each agent works on independent docs — no merge conflicts if ref_ids don't share doc files.

**Exception:** multiple ref_ids may share the same doc file (e.g. a feature's code mapped to domain README). Check `sync-update --check` to identify shared docs and assign them to one agent.

---

## Anti-patterns

| Don't | Do |
|-------|----|
| Invent behavior not in code | Read source, describe what exists |
| Remove sections you didn't update | Preserve existing structure |
| Skip `beadloom reindex` after edit | Always reindex to verify baseline reset |
| Update code while writing docs | Only edit files under `docs/` |
| Write verbose prose | Concise technical descriptions |
| Ignore `<!-- TODO -->` markers | Leave them for follow-up if unsure |

---

## Completing work

```bash
# 1. Verify all assigned ref_ids are now "ok"
beadloom sync-check --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
stale = {p['ref_id'] for p in d['pairs'] if p['status'] == 'stale'}
print(f'Remaining stale: {len(stale)} — {sorted(stale)}')
"

# 2. Final checkpoint
bd comments add <bead-id> "$(cat <<'EOF'
COMPLETED:
- Updated docs: [list of ref_ids]
- Stale before: N, after: M
- New sections added: [if any]
- TODOs left: [if any]
EOF
)"

# 3. Close bead
bd close <bead-id>
```

---

## Tech-writer checklist

### Before starting
- [ ] `beadloom sync-check --json` — identified stale ref_ids
- [ ] Assigned ref_ids (no overlap with other agents on same doc file)
- [ ] `bd update <id> --status in_progress --claim`

### Per ref_id
- [ ] `beadloom ctx <ref-id>` — understood current state
- [ ] `beadloom sync-update --check <ref-id>` — identified stale pairs
- [ ] Read current doc file
- [ ] Read source files that changed
- [ ] Updated: summary, modules, API, testing sections
- [ ] `beadloom reindex` — baseline reset
- [ ] `beadloom sync-check` — ref_id is now "ok"

### After all ref_ids
- [ ] `beadloom sync-check` — zero stale for assigned refs
- [ ] `bd comments add` — checkpoint with results
- [ ] `bd close`
