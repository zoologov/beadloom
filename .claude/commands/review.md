# /review — Reviewer Role

> **When to invoke:** during code review, checking code quality
> **Focus:** quality, architecture, security, Python idioms

---

## Review protocol

```bash
# 1. Get project context
beadloom prime                    # compact architecture + health overview

# 2. Get information about the bead
bd show <bead-id>
bd comments <bead-id>

# 3. Understand the changed area via Beadloom
beadloom ctx <ref-id>             # architecture context for the component
beadloom why <ref-id>             # impact: what depends on this?
beadloom search "<keyword>"       # find related code and docs

# 4. Read epic context (if applicable)
# - CONTEXT.md — architectural decisions
# - RFC.md — technical specification
```

---

## Code Quality Checklist

### Readability
- [ ] Code is readable and understandable without comments
- [ ] No duplication (DRY)
- [ ] Functions do one thing (SRP)
- [ ] No deep nesting (max 3 levels)
- [ ] Variable/function names are clear (snake_case)

### Architecture
- [ ] Layer separation is respected: Services → Domains → Infrastructure
- [ ] Domains do not depend on Services (CLI/MCP/TUI)
- [ ] No circular imports
- [ ] Matches the DDD package structure (`infrastructure/`, `context_oracle/`, `doc_sync/`, `onboarding/`, `graph/`)
- [ ] `pathlib.Path` instead of `os.path`

### Typing
- [ ] No `Any` without justification
- [ ] No `# type: ignore` without comment
- [ ] Type hints on all public functions
- [ ] `mypy --strict` passes without errors
- [ ] Using `str | None` instead of `Optional[str]` (Python 3.10+)

### Python idioms
- [ ] `dataclass(frozen=True)` for immutable models
- [ ] Context managers for resources (`with` for files, connections)
- [ ] Generators and comprehensions where appropriate
- [ ] `from __future__ import annotations` not needed (Python 3.10+)

### Error handling
- [ ] Errors are handled explicitly
- [ ] No bare `except:` (only `except SpecificError:`)
- [ ] Custom exceptions inherit from `BeadloomError`
- [ ] CLI errors are displayed via Rich with exit code

---

## Testing Checklist

- [ ] Unit tests cover business logic (pytest)
- [ ] Tests are independent of each other
- [ ] Tests are fast (< 100ms each)
- [ ] Tests are readable (AAA pattern: Arrange-Act-Assert)
- [ ] Edge cases are covered
- [ ] Coverage >= 80% (pytest-cov)
- [ ] Fixtures in `conftest.py`, not duplicated
- [ ] `tmp_path` for temporary files, no hardcoded paths

---

## Security Checklist

- [ ] No hardcoded secrets (API keys via env vars)
- [ ] SQL: only parameterized queries (`?`), no f-strings
- [ ] YAML: `yaml.safe_load()`, no `yaml.load()`
- [ ] Paths: path traversal checks (`resolve()`, prefix validation)
- [ ] Only safe data is logged (no PII, tokens)
- [ ] No `subprocess.shell=True` with user input

---

## Beadloom Checklist

- [ ] `beadloom prime` — reviewed project health (stale docs, lint violations)
- [ ] `beadloom why <ref-id>` — impact analysis for changed components
- [ ] `beadloom sync-check` — no stale doc-code pairs
- [ ] `beadloom lint --strict` — no architecture violations
- [ ] `beadloom doctor` — graph integrity ok
- [ ] If graph YAML changed: edges are correct, no orphaned nodes
- [ ] If new domain/feature added: has documentation in docs/ (`beadloom docs generate`)

---

## Review result

### If everything is ok:
```bash
bd comments add <bead-id> "REVIEW PASSED: [brief comment]"
```

### If there are findings:
```bash
bd comments add <bead-id> "$(cat <<'EOF'
REVIEW: changes required

Critical:
- [critical issues]

Major:
- [important findings]

Minor:
- [minor improvements]
EOF
)"
```

---

## Feedback format

```markdown
## File: src/beadloom/core/context.py

### Line XX: [Severity]
**Issue:** description
**Recommendation:** how to fix
**Example:**
```python
# Before
data = yaml.load(f)

# After
data = yaml.safe_load(f)
```
```

---

## Severity levels

| Level | Description | Action |
|-------|-------------|--------|
| **Critical** | Bugs, vulnerabilities, data loss | Blocks merge |
| **Major** | Architecture violation, poor code | Requires fix |
| **Minor** | Style, improvements | At author's discretion |
| **Nitpick** | Trivial matters | Can be ignored |
