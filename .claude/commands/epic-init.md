# /epic-init — Initializing a New Epic

> **When to invoke:** when creating a new epic/feature
> **Result:** complete project setup with approval

---

## Mandatory sequence

```mermaid
graph LR
    PRD[PRD] -->|approval| RFC[RFC]
    RFC -->|approval| CTX[CONTEXT]
    CTX -->|approval| PLAN[PLAN]
    PLAN -->|start| ACTIVE[ACTIVE]
```

**EACH step requires explicit approval from the user!**

---

## Step 1: Survey the user about standards

```
STANDARDS SETUP: {ISSUE-KEY}

Answer the questions or press Enter for default values:

1. Programming language? [Python 3.10+]
2. Runtime/environment? [uv + venv]
3. Methodologies? [TDD, Clean Code, modular architecture]
4. Linter/formatter? [ruff]
5. Typing? [mypy --strict]
6. Testing framework? [pytest + pytest-cov]
7. Minimum test coverage? [80%]
8. Additional restrictions? [no Any, no bare except, pathlib only]
```

---

## Step 2: Create the structure

```bash
mkdir -p docs/features/{ISSUE-KEY}
```

Create files (use `/templates` for templates):

| File | Description | Approval |
|------|-------------|----------|
| PRD.md | Business requirements, user stories | YES |
| RFC.md | Technical solution, architecture | YES |
| CONTEXT.md | Goal, constraints, code standards | YES |
| PLAN.md | Decomposition into beads, DAG | YES |
| ACTIVE.md | Current focus (created at start) | NO |

---

## Step 3: Create the epic in beads

```bash
# 1. Create the epic
bd create --type epic --title "{ISSUE-KEY}: Epic name" \
  --description "Description of the epic's goal"

# 2. Create beads (subtasks)
bd create --type task --title "BEAD-01: Name" \
  --priority P0 --parent <epic-id> \
  --description "What needs to be done"

# 3. Set up dependencies
bd dep add <bead-id> <depends-on-id>

# 4. Check the graph
bd graph --all
```

---

## Step 4: Record standards in CONTEXT.md

Be sure to add this section:

```markdown
## Code standards

### Language and environment
- **Language:** Python 3.10+ (type hints, `str | None` syntax)
- **Package manager:** uv
- **Virtual environment:** uv venv

### Methodologies
| Methodology | Application |
|-------------|-------------|
| TDD | Red -> Green -> Refactor for each bead |
| Clean Code | Naming (snake_case), SRP, DRY, KISS |
| Modular architecture | CLI -> Core -> Storage, dependencies point inward |

### Testing
- **Framework:** pytest + pytest-cov
- **Coverage:** minimum 80%
- **Fixtures:** conftest.py, tmp_path

### Code quality
- **Linter:** ruff (lint + format)
- **Typing:** mypy --strict

### Restrictions
- [x] No `Any` without justification
- [x] No `print()` / `breakpoint()` — use logging
- [x] No bare `except:` — only `except SpecificError:`
- [x] No `os.path` — use `pathlib.Path`
- [x] No f-strings in SQL — parameterized queries `?`
- [x] No `yaml.load()` — only `yaml.safe_load()`
- [x] No magic numbers — extract into constants
```

---

## Step 5: Plan approval

Display to the user:

```
┌─────────────────────────────────────────────────────────┐
│ PLAN APPROVED: {ISSUE-KEY}                              │
│                                                         │
│ Epic: [name]                                            │
│ Beads: [count]                                          │
│ Critical path: BEAD-XX → BEAD-YY → BEAD-ZZ             │
│                                                         │
│ DAG recorded in beads + PLAN.md                         │
│ Do you confirm the start of development?                │
└─────────────────────────────────────────────────────────┘
```

---

## Initialization checklist

- [ ] Surveyed the user about standards
- [ ] Created the structure `docs/features/{ISSUE-KEY}/`
- [ ] Filled in PRD.md -> **approved**
- [ ] Filled in RFC.md -> **approved**
- [ ] Filled in CONTEXT.md (including code standards) -> **approved**
- [ ] Created epic in beads: `bd create --type epic`
- [ ] Decomposed into beads with priorities
- [ ] Set up dependencies: `bd dep add`
- [ ] Filled in PLAN.md with DAG -> **approved**
- [ ] Received confirmation to start development
