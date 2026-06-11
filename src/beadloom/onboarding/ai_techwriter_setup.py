# beadloom:domain=onboarding
# beadloom:feature=ai-techwriter-setup
"""Scaffold the AI tech-writer into any repo (BDL-047 / F4.1, G8).

``beadloom setup-ai-techwriter --platform github|gitlab`` makes opt-in a
one-command affair. This module owns the mechanics; the Click command in
:mod:`beadloom.services.cli` is a thin shell over :func:`scaffold`.

Harness-provisioning decision (v2, BDL-051 / S2) — **no vendoring**
-------------------------------------------------------------------
The deterministic harness now lives **inside the installed ``beadloom``
package** at :mod:`beadloom.ai_agents.ai_techwriter` (see ``pyproject.toml``
``packages = ["src/beadloom"]``). Adopters declare ``beadloom`` as a dependency,
so the CI wrapper's ``python -m beadloom.ai_agents.ai_techwriter`` resolves
directly — there is nothing to copy. So the BDL-047/048 vendoring machinery
(``HARNESS_MODULES`` + the ``*.py.txt`` assets + ``sync_vendored_harness`` +
its byte-identical drift-guard) has been **retired**.

What the scaffold emits now:

* the chosen platform's **CI workflow** (which calls the installed module);
* the **getting-started guide**;
* the **operator artifacts** ``recipe.yaml`` + ``provision-runner.sh`` copied
  from the harness package data (``importlib.resources``) into the target's
  ``tools/ai_techwriter/`` — the recipe as a readable reference of the agent's
  blast-radius, the provisioner so the operator can stand up the runner. The
  *harness itself* is never copied (it ships in the wheel).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

#: Harness package shipping the recipe + provisioner as package data.
_HARNESS_PACKAGE = "beadloom.ai_agents.ai_techwriter"

#: Supported CI platforms (RFC Q5 table) — both first-class.
PLATFORMS: tuple[str, ...] = ("github", "gitlab")

#: rwxr-xr-x — the provisioner is dropped executable so the operator can run it
#: directly (``./provision-runner.sh ...``).
_EXEC_MODE = 0o755

#: GitLab CI job marker, used to detect "already wired" in an existing file.
_GITLAB_JOB_MARKER = "ai-techwriter:"


def templates_root() -> Path:
    """Directory holding the packaged AI-tech-writer scaffold assets."""
    return Path(__file__).resolve().parent / "templates" / "ai_techwriter"


def _read_asset(name: str) -> str:
    return (templates_root() / name).read_text(encoding="utf-8")


def _read_harness_data(name: str) -> str:
    """Read a harness package-data file (recipe / provisioner) via resources."""
    return (resources.files(_HARNESS_PACKAGE) / name).read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _scaffold_github(target_root: Path) -> Path:
    wf = target_root / ".github" / "workflows" / "ai-techwriter.yml"
    _write(wf, _read_asset("github-workflow.yml"))
    return wf


def _scaffold_gitlab(target_root: Path) -> Path:
    job = _read_asset("gitlab-ci-job.yml")
    ci = target_root / ".gitlab-ci.yml"
    if ci.exists():
        existing = ci.read_text(encoding="utf-8")
        if _GITLAB_JOB_MARKER in existing:
            # Already wired — leave the user's file untouched (idempotent).
            return ci
        # Append the job without destroying the user's other stages.
        sep = "" if existing.endswith("\n") else "\n"
        _write(ci, existing + sep + "\n" + _job_only(job))
        return ci
    _write(ci, job)
    return ci


def _job_only(job: str) -> str:
    """Strip the standalone ``stages:`` header when appending to an existing
    pipeline (the user already declares stages)."""
    lines = job.splitlines(keepends=True)
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped.startswith("stages:"):
            skipping = True
            continue
        if skipping:
            if stripped.startswith("  - ") or stripped == "":
                continue
            skipping = False
        out.append(line)
    return "".join(out).lstrip("\n")


def _scaffold_guide(target_root: Path) -> Path:
    guide = target_root / "docs" / "guides" / "ai-techwriter.md"
    _write(guide, _read_asset("guide.md.txt"))
    return guide


def _scaffold_recipe(target_root: Path) -> Path:
    """Drop a readable copy of the Goose recipe (package data) for reference.

    The harness reads its own shipped recipe at run time; this copy lets the
    operator inspect the agent's tool allow/deny blast radius. Clean overwrite
    on re-run (idempotent)."""
    recipe = target_root / "tools" / "ai_techwriter" / "recipe.yaml"
    _write(recipe, _read_harness_data("recipe.yaml"))
    return recipe


def _scaffold_provision_runner(target_root: Path) -> Path:
    """Drop the hardened, idempotent ``provision-runner.sh`` (package data),
    executable so the operator can run it directly. Clean overwrite on re-run
    (idempotent)."""
    script = target_root / "tools" / "ai_techwriter" / "provision-runner.sh"
    _write(script, _read_harness_data("provision-runner.sh"))
    script.chmod(_EXEC_MODE)
    return script


def scaffold(target_root: Path, *, platform: str) -> list[Path]:
    """Scaffold the AI tech-writer into ``target_root`` for ``platform``.

    Returns the created/updated paths (CI wrapper + guide + operator recipe +
    provisioner). The harness itself is NOT copied — it ships inside the
    installed ``beadloom`` package and is invoked as
    ``python -m beadloom.ai_agents.ai_techwriter``. Idempotent: generated files
    are cleanly overwritten on re-run.
    """
    if platform not in PLATFORMS:
        msg = f"unknown platform {platform!r}; expected one of {PLATFORMS}"
        raise ValueError(msg)
    created: list[Path] = []
    if platform == "gitlab":
        created.append(_scaffold_gitlab(target_root))
    else:
        created.append(_scaffold_github(target_root))
    created.append(_scaffold_recipe(target_root))
    created.append(_scaffold_provision_runner(target_root))
    created.append(_scaffold_guide(target_root))
    return created
