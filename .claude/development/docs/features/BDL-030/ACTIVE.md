# ACTIVE: BDL-030 — Agent Instructions Freshness

> **Last updated:** 2026-02-21
> **Phase:** Completed

---

## Bead Map

| Bead ID | BEAD | Name | Agent | Status |
|---------|------|------|-------|--------|
| beadloom-8mq.1 | BEAD-01 | Doctor check (12.12.1) | /dev | Done |
| beadloom-8mq.2 | BEAD-02 | Setup-rules --refresh (12.12.2) | /dev | Done |
| beadloom-8mq.3 | BEAD-03 | Test verification | /test | Done |
| beadloom-8mq.4 | BEAD-04 | Code review | /review | Done |
| beadloom-8mq.5 | BEAD-05 | Doc update | /tech-writer | Done |

## Waves

### Wave 1 (dev) — BEAD-01
- [x] BEAD-01: Agent instructions doctor check

### Wave 2 (dev) — BEAD-02
- [x] BEAD-02: Setup-rules --refresh + CLAUDE.md markers

### Wave 3 (test + review) — BEAD-03 then BEAD-04
- [x] BEAD-03: Test verification
- [x] BEAD-04: Code review

### Wave 4 (tech-writer) — BEAD-05
- [x] BEAD-05: BDL-UX-Issues.md + doc update

## Results

### BEAD-01: Doctor Check
- Added `_check_agent_instructions(project_root)` to `infrastructure/doctor.py`
- 6 fact-extraction helpers for version, packages, CLI commands, MCP tools, stack keywords, test framework
- Wired into `run_checks()` via optional `project_root` param
- 16 tests in `tests/test_doctor_instructions.py`

### BEAD-02: Setup-rules --refresh
- Added `_parse_markers()`, `_auto_insert_markers()`, `_render_project_info_section()`, `refresh_claude_md()` to `onboarding/scanner.py`
- Added `--refresh` and `--dry-run` flags to `setup-rules` CLI command
- Added `<!-- beadloom:auto-start/auto-end -->` markers to `.claude/CLAUDE.md` section 0.1
- 15 tests in `tests/test_refresh_claude_md.py`

### BEAD-03: Test Verification
- Full suite: 2527 passed, 0 failed
- New tests: 31/31 passed (16 doctor + 15 refresh)
- Coverage: doctor.py instructions ~90%, scanner.py new code ~92%
- ruff clean, mypy clean, beadloom lint 0 violations

### BEAD-04: Code Review
- Type safety: all functions properly typed with Python 3.10+ syntax
- Error handling: graceful degradation for missing files, malformed markers
- Edge cases: missing CLAUDE.md, missing AGENTS.md, unclosed markers, no section 0.1
- No anti-patterns found; clean architecture separation (doctor=read, scanner=write)

### BEAD-05: Doc Update
- 0 new UX issues discovered
- Updated infrastructure README (doctor.py new functions, test file)
- Updated onboarding README (scanner.py new functions, CLI flags, test file)
- Infrastructure and onboarding sync-check resolved

## Notes

- Parent bead: beadloom-8mq
- All 5 beads completed sequentially as planned
- Pre-existing issue noted: MCP tool count drift (13 vs 14) in AGENTS.md — not caused by BDL-030
