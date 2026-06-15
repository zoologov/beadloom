# AI Tech-Writer Setup

The `setup-ai-techwriter` scaffolder, in the onboarding domain.

**Source:** `src/beadloom/onboarding/ai_techwriter_setup.py`

---

## Specification

### Purpose

Make adopting the AI tech-writer a one-command affair. `beadloom
setup-ai-techwriter --platform github|gitlab` emits the CI workflow, the
operator recipe, a provisioner, and the guide that wire the **packaged** harness
(`beadloom.ai_agents.ai_techwriter`) into a target repo. The harness ships
inside the installed `beadloom` package, so there is **no Python vendoring** —
adopters depend on `beadloom`, and the scaffold only emits the workflow that
invokes the installed module as `python -m beadloom.ai_agents.ai_techwriter`.

### Output

`scaffold(target_root, *, platform)` writes the platform CI wrapper (a GitHub
Actions job or a GitLab CI include), the operator recipe, the provisioner
runner, and the guide. An unknown platform raises `ValueError`. Re-running
cleanly overwrites the generated files.

## Invariants

- No harness source is copied into the target repo; the workflow invokes the
  installed `beadloom` module.
- The scaffold is idempotent — generated files are cleanly overwritten on re-run.
- Only `github` and `gitlab` are accepted platforms.

## API

Module `src/beadloom/onboarding/ai_techwriter_setup.py`:

- `scaffold(target_root: Path, *, platform: str) -> list[Path]` — emit the CI
  wrapper + recipe + provisioner + guide; returns the paths written.

## Testing

Tests: `tests/test_cli_setup_ai_techwriter.py`,
`tests/test_ai_techwriter_cli.py`
