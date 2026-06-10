# beadloom:domain=onboarding
"""Scaffold the AI tech-writer into any repo (BDL-047 / F4.1, G8).

``beadloom setup-ai-techwriter --platform github|gitlab`` makes opt-in a
one-command, 3-step affair. This module owns the mechanics; the Click command
in :mod:`beadloom.services.cli` is a thin shell over :func:`scaffold`.

Harness-provisioning decision (v1) — **vendor**
-----------------------------------------------
The deterministic harness lives in the repo's ``tools/ai_techwriter/`` package
(repo tooling, *not* the installed ``beadloom`` wheel — see ``pyproject.toml``
``packages = ["src/beadloom"]``). On any *other* repo the CI wrapper's
``python -m tools.ai_techwriter`` would not resolve, because those files do not
exist there. So the command **vendors** the harness: it copies the harness
modules + the Goose recipe into the target repo's ``tools/ai_techwriter/``.
The result is self-contained — the runner needs only ``beadloom`` + ``goose``
+ python, no extra packaging. Re-running refreshes the vendored copy (clean
overwrite → idempotent).

To avoid hand-maintained drift (principle 5) the harness is shipped as
**package data** under ``templates/ai_techwriter/`` (inert ``.py.txt`` assets so
they are not imported as ``beadloom`` submodules nor linted as core code), kept
byte-identical to the live ``tools/ai_techwriter`` source by
:func:`sync_vendored_harness` and guarded by a test. ``config-check`` covers
the *agent-config* artifacts (CLAUDE.md / AGENTS.md / IDE rules); the
AI-tech-writer scaffold is a separately-opt-in CI artifact, so it is kept
drift-free by the source<->asset sync test rather than by ``config-check``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

#: Harness python modules vendored into the target (the whole package).
HARNESS_MODULES: tuple[str, ...] = (
    "__init__",
    "__main__",
    "cli",
    "commands",
    "models",
    "packet",
    "provider",
    "runner",
    "runs_store",
    "scope",
    "seams",
)

#: Asset name for the vendored parent ``tools/__init__.py`` (kept distinct from
#: the harness package's own ``__init__`` so it lands one directory up).
_TOOLS_INIT_ASSET = "tools_init.py.txt"

#: Default content for the vendored parent ``tools/__init__.py`` when the live
#: repo's copy is unavailable (sync source of truth is the live file).
_TOOLS_INIT_DEFAULT = '"""Repo tooling (not part of the installed ``beadloom`` wheel)."""\n'

#: Supported CI platforms (RFC Q5 table) — both first-class.
PLATFORMS: tuple[str, ...] = ("github", "gitlab")

#: Asset name for the hardened, idempotent self-hosted-runner provisioner.
_PROVISION_RUNNER_ASSET = "provision-runner.sh.txt"

#: rwxr-xr-x — the provisioner is dropped executable so the operator can run it
#: directly (``./provision-runner.sh ...``).
_EXEC_MODE = 0o755

#: GitLab CI job marker, used to detect "already wired" in an existing file.
_GITLAB_JOB_MARKER = "ai-techwriter:"


def templates_root() -> Path:
    """Directory holding the packaged AI-tech-writer scaffold assets."""
    return Path(__file__).resolve().parent / "templates" / "ai_techwriter"


def vendored_harness_root() -> Path:
    """Directory holding the vendored harness assets (``*.py.txt`` + recipe)."""
    return templates_root() / "harness"


def _read_asset(name: str) -> str:
    return (templates_root() / name).read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def vendor_harness(target_root: Path) -> Path:
    """Copy the vendored harness package into ``target_root/tools/ai_techwriter``.

    Clean overwrite (idempotent): each ``<module>.py.txt`` asset is written as
    ``<module>.py`` and the recipe is copied verbatim. Returns the harness dir.
    """
    src = vendored_harness_root()
    dest = target_root / "tools" / "ai_techwriter"
    dest.mkdir(parents=True, exist_ok=True)
    # Vendor the parent ``tools/__init__.py`` so the target is a regular package
    # (no reliance on implicit namespace packages for ``python -m tools...``).
    _write(target_root / "tools" / "__init__.py", _vendored_tools_init())
    for module in HARNESS_MODULES:
        content = (src / f"{module}.py.txt").read_text(encoding="utf-8")
        _write(dest / f"{module}.py", content)
    _write(dest / "recipe.yaml", (src / "recipe.yaml").read_text(encoding="utf-8"))
    return dest


def _vendored_tools_init() -> str:
    """Content for the vendored ``tools/__init__.py`` (packaged asset or default)."""
    asset = vendored_harness_root() / _TOOLS_INIT_ASSET
    if asset.is_file():
        return asset.read_text(encoding="utf-8")
    return _TOOLS_INIT_DEFAULT


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


def _scaffold_provision_runner(target_root: Path) -> Path:
    """Drop the hardened, idempotent ``provision-runner.sh`` alongside the
    vendored harness (``tools/ai_techwriter/``), executable so the operator can
    run it directly. Clean overwrite on re-run (idempotent)."""
    script = target_root / "tools" / "ai_techwriter" / "provision-runner.sh"
    _write(script, _read_asset(_PROVISION_RUNNER_ASSET))
    script.chmod(_EXEC_MODE)
    return script


def scaffold(target_root: Path, *, platform: str) -> list[Path]:
    """Scaffold the AI tech-writer into ``target_root`` for ``platform``.

    Returns the created/updated paths (harness dir + wrapper + guide).
    Idempotent: generated files are cleanly overwritten on re-run.
    """
    if platform not in PLATFORMS:
        msg = f"unknown platform {platform!r}; expected one of {PLATFORMS}"
        raise ValueError(msg)
    created: list[Path] = [vendor_harness(target_root)]
    if platform == "gitlab":
        created.append(_scaffold_gitlab(target_root))
    else:
        created.append(_scaffold_github(target_root))
    created.append(_scaffold_provision_runner(target_root))
    created.append(_scaffold_guide(target_root))
    return created


def sync_vendored_harness(live_root: Path) -> list[str]:
    """Refresh the packaged ``*.py.txt`` assets from the live harness source.

    Drift guard (principle 5): copies every live ``tools/ai_techwriter`` module
    into the package as inert ``.py.txt`` data. Returns the asset names written.
    Used by maintenance tooling + asserted byte-for-byte in the test suite.
    """
    dest = vendored_harness_root()
    dest.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for module in HARNESS_MODULES:
        content = (live_root / f"{module}.py").read_text(encoding="utf-8")
        (dest / f"{module}.py.txt").write_text(content, encoding="utf-8")
        written.append(f"{module}.py.txt")
    shutil.copyfile(live_root / "recipe.yaml", dest / "recipe.yaml")
    written.append("recipe.yaml")
    # Snapshot the live parent ``tools/__init__.py`` so the vendored target is a
    # regular package (drift-guarded like the harness modules).
    parent_init = live_root.parent / "__init__.py"
    content = (
        parent_init.read_text(encoding="utf-8")
        if parent_init.is_file()
        else _TOOLS_INIT_DEFAULT
    )
    (dest / _TOOLS_INIT_ASSET).write_text(content, encoding="utf-8")
    written.append(_TOOLS_INIT_ASSET)
    return written
