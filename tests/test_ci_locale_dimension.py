"""BDL-061.38: CI carries an environment DIMENSION — it VARIES the locale.

Why this file exists, in the terms the defect was measured in:

BDL-061.36 shipped a refusal that depended on the ambient locale. It failed on
**all four** Python versions in CI and was invisible to a 5574-test local suite,
because every one of those tests ran on the same UTF-8 macOS. A second defect in
the same bead (``Path.resolve`` raising on a symlink loop on 3.10-3.12 and
raising nothing on 3.13) was invisible for the mirror-image reason: the one
interpreter the owner runs is the one that does not raise. Neither is a coverage
failure — more tests along the existing axis would not have found either. Both
are **dimension** failures.

So the assertions here are about a property of the pipeline, not about any leg
being green:

1. ``ci.yml`` declares a leg that runs the **whole** suite under a **non-UTF-8**
   locale, and
2. ``ci.yml`` never **pins** a UTF-8 locale anywhere. Pinning is the failure mode
   that matters: it would have made .36's defect invisible to us while shipping
   it to every adopter running in a container, which is the default deployment,
   not an edge case. The value is in the DIFFERENCE between legs.
3. The leg cannot be vacuously green. ``LC_ALL=C`` *alone* proves nothing —
   PEP 538 coerces the C locale to C.UTF-8 and PEP 540 auto-enables UTF-8 Mode
   under it, so a bare ``LC_ALL=C`` still reports a UTF-8 preferred encoding
   (measured in .36 on macOS; re-measured for this bead on ``python:3.12-slim``,
   where a bare ``LC_ALL=C`` gives ``preferred=utf-8``). The env that ci.yml
   actually ships is executed here against a real interpreter, so a spelling
   that gets coerced back to UTF-8 fails this suite rather than passing CI
   silently.
"""

from __future__ import annotations

import codecs
import locale
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"

#: The job that carries the dimension.
LOCALE_JOB = "tests-locale"

#: The two knobs that make a C-locale leg non-vacuous. Without BOTH, CPython
#: quietly puts the leg back on UTF-8 (PEP 538 coercion / PEP 540 UTF-8 Mode)
#: and the leg asserts nothing while reading green.
COERCION_KNOBS = {"PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0"}

#: Locale-carrying variables a "fix" would reach for when this leg goes red.
LOCALE_VARS = ("LC_ALL", "LC_CTYPE", "LANG", "LANGUAGE")

_UTF8_VALUE = re.compile(r"utf-?8", re.IGNORECASE)


def _ci() -> dict[str, Any]:
    doc = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def _job(name: str) -> dict[str, Any]:
    jobs = _ci()["jobs"]
    assert isinstance(jobs, dict), "ci.yml has no jobs mapping"
    assert name in jobs, f"ci.yml declares no {name!r} job"
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    return [s for s in steps if isinstance(s, dict)]


def _suite_step(job: dict[str, Any]) -> dict[str, Any]:
    """The step that runs pytest — the one the locale must actually reach."""
    matches = [s for s in _steps(job) if "pytest" in str(s.get("run", ""))]
    assert len(matches) == 1, f"expected exactly one pytest step, got {len(matches)}"
    return matches[0]


def _env_of(step: dict[str, Any], job: dict[str, Any]) -> dict[str, str]:
    """Effective env for a step: the job-level env overlaid by the step's own."""
    merged: dict[str, str] = {}
    for source in (job.get("env"), step.get("env")):
        if isinstance(source, dict):
            merged.update({str(k): str(v) for k, v in source.items()})
    return merged


# --------------------------------------------------------------------------- #
# 1. The dimension exists, and it is the WHOLE suite
# --------------------------------------------------------------------------- #


def test_ci_declares_a_locale_leg() -> None:
    """ci.yml has a job whose axis is the LOCALE, not the Python version."""
    job = _job(LOCALE_JOB)
    axis = job["strategy"]["matrix"]["locale"]
    assert isinstance(axis, list) and axis, "the locale axis must list its legs"
    # fail-fast would cancel the sibling rows on the first red one, and the
    # rows fail in opposite directions (see test_locale_axis_covers_both...).
    assert job["strategy"]["fail-fast"] is False


def test_locale_axis_covers_both_failure_directions() -> None:
    """One ASCII row (undecodable bytes RAISE) and one 8-bit row (they do NOT).

    These are different defects, which is why one row is not enough: under
    ASCII an undecodable byte raises — loud, fail-closed-but-wrong; under an
    8-bit codec nothing raises and the byte is silently mangled into a
    character nobody sent. .36 measured exactly this: its first sabotage passed
    302/302 until a latin-1 row was added, because a decoder that accepts every
    byte escapes nothing.
    """
    axis = [str(v) for v in _job(LOCALE_JOB)["strategy"]["matrix"]["locale"]]
    assert "C" in axis, "the cheap high-value ASCII row is missing"
    eight_bit = [v for v in axis if "8859" in v or "CP" in v.upper()]
    assert eight_bit, f"no 8-bit (non-raising) locale row in {axis}"


def test_locale_leg_runs_the_whole_suite() -> None:
    """No ``-k`` / ``-m`` / path narrowing: a subset narrows the dimension to
    the code we already suspect, which is the mistake this bead corrects — .36's
    defect was invisible to a 5574-test suite, not to a small one."""
    run = str(_suite_step(_job(LOCALE_JOB))["run"])
    for narrowing in (" -k ", " -m ", " tests/"):
        assert narrowing not in run, f"the locale leg narrows the suite: {narrowing!r}"


def test_locale_leg_mirrors_the_tests_leg_dependencies() -> None:
    """Same extras as ``tests``, so the ONLY difference between the legs is the
    locale — otherwise a red leg cannot be attributed to the dimension."""
    def _install(job_name: str) -> str:
        steps = _steps(_job(job_name))
        installs = [str(s.get("run", "")) for s in steps if "uv sync" in str(s.get("run", ""))]
        assert len(installs) == 1, f"{job_name}: expected one `uv sync` step"
        return installs[0]

    assert _install(LOCALE_JOB).split() == _install("tests").split()


# --------------------------------------------------------------------------- #
# 2. The leg cannot be vacuous (the knobs, and the in-CI assertion of them)
# --------------------------------------------------------------------------- #


def test_locale_leg_defeats_pep538_and_pep540_coercion() -> None:
    """``LC_ALL=C`` alone is a leg that proves nothing — both knobs are required."""
    job = _job(LOCALE_JOB)
    env = _env_of(_suite_step(job), job)
    for key, value in COERCION_KNOBS.items():
        assert env.get(key) == value, (
            f"{LOCALE_JOB} does not set {key}={value}; without it CPython puts "
            "the leg back on UTF-8 (PEP 538/540) and it reads green while "
            "asserting nothing"
        )
    assert _UTF8_VALUE.search(env.get("LC_ALL", "")) is None
    assert "${{ matrix.locale }}" in env.get("LC_ALL", "")


def test_locale_leg_asserts_its_own_encoding_before_running_the_suite() -> None:
    """A step must fail the leg if the runner image coerces it back to UTF-8.

    The knobs above are what we ship; this is the leg checking that what it
    shipped had the intended effect on that image. Without it, a future runner
    (or a CPython default change) turns the dimension into theatre silently.
    """
    steps = _steps(_job(LOCALE_JOB))
    probes = [
        i
        for i, s in enumerate(steps)
        if "getpreferredencoding" in str(s.get("run", ""))
    ]
    assert probes, "no step asserts the leg is genuinely non-UTF-8"
    suite_index = steps.index(_suite_step(_job(LOCALE_JOB)))
    assert min(probes) < suite_index, "the encoding assertion must precede the suite"


# --------------------------------------------------------------------------- #
# 3. Vary, never pin (the invariant that outlives this bead)
# --------------------------------------------------------------------------- #


def _declared_env_pairs() -> list[tuple[str, str, str]]:
    """(where, key, value) for every ``env:`` mapping declared in ci.yml."""
    pairs: list[tuple[str, str, str]] = []

    def walk(node: object, where: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "env" and isinstance(value, dict):
                    pairs.extend(
                        (where, str(k), str(v)) for k, v in value.items()
                    )
                walk(value, f"{where}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{where}[{index}]")

    walk(_ci(), "ci.yml")
    return pairs


def test_ci_never_pins_a_utf8_locale() -> None:
    """No job may hard-set a locale variable to a UTF-8 value.

    This is the invariant the bead is actually about: pinning UTF-8 makes every
    leg agree, which is indistinguishable from having no dimension at all. It is
    also the tempting "fix" the first time this leg goes red — so it is asserted
    here rather than left to reviewer memory.
    """
    offenders = [
        (where, key, value)
        for where, key, value in _declared_env_pairs()
        if key in LOCALE_VARS and _UTF8_VALUE.search(value)
    ]
    assert not offenders, f"ci.yml pins a UTF-8 locale: {offenders}"


def test_ci_never_pins_a_utf8_locale_inline_in_a_run_script() -> None:
    """Same invariant, via the other spelling: ``LC_ALL=C.UTF-8 uv run ...``."""
    inline = re.compile(
        rf"\b({'|'.join(LOCALE_VARS)})=[\"']?[A-Za-z0-9_@.-]*utf-?8",
        re.IGNORECASE,
    )
    offenders: list[str] = []
    for job_name, job in _ci()["jobs"].items():
        for step in _steps(job):
            script = str(step.get("run", ""))
            body = "\n".join(
                line for line in script.splitlines() if not line.lstrip().startswith("#")
            )
            offenders.extend(f"{job_name}: {m.group(0)}" for m in inline.finditer(body))
    assert not offenders, f"ci.yml pins a UTF-8 locale inline: {offenders}"


# --------------------------------------------------------------------------- #
# 4. The shipped env, executed. Not read — RUN.
# --------------------------------------------------------------------------- #


def _shipped_env(locale_value: str) -> dict[str, str]:
    """ci.yml's env for the suite step, with the matrix placeholder resolved."""
    job = _job(LOCALE_JOB)
    declared = _env_of(_suite_step(job), job)
    resolved = {
        key: value.replace("${{ matrix.locale }}", locale_value)
        for key, value in declared.items()
    }
    env = dict(os.environ)
    for stale in LOCALE_VARS + tuple(COERCION_KNOBS) + ("PYTHONIOENCODING",):
        env.pop(stale, None)
    env.update(resolved)
    return env


_PROBE = (
    "import codecs, locale, sys;"
    "print(codecs.lookup(locale.getpreferredencoding(False)).name,"
    "codecs.lookup(sys.getfilesystemencoding()).name, sys.flags.utf8_mode)"
)


def _probe(locale_value: str) -> tuple[str, str, int]:
    out = subprocess.run(  # noqa: S603 — fixed argv (this interpreter), no shell
        [sys.executable, "-c", _PROBE],
        env=_shipped_env(locale_value),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return out[0], out[1], int(out[2])


def test_shipped_env_disables_utf8_mode_on_every_platform() -> None:
    """PEP 540 UTF-8 Mode is OFF under the env ci.yml ships — anywhere.

    This is the half of the effect that is platform-independent, so it executes
    on the developer's machine too: drop ``PYTHONUTF8=0`` (or let something set
    it to 1) and the leg silently becomes a fifth UTF-8 leg, and this fails.
    """
    _, _, utf8_mode = _probe("C")
    assert utf8_mode == 0, "the shipped env leaves PEP 540 UTF-8 Mode enabled"


@pytest.mark.skipif(
    sys.platform != "linux",
    reason=(
        "CPython FORCES a UTF-8 filesystem encoding on macOS/Windows, so the "
        "locale cannot govern the encodings there and this assertion would be "
        "false for a reason that is not a defect. It is not a skip that can "
        "never fail: the CI legs are ubuntu-latest, so it executes on every "
        "leg of every PR — which is exactly where the dimension lives."
    ),
)
def test_shipped_env_is_genuinely_non_utf8_on_linux() -> None:
    """The C row really is ASCII on Linux — the spelling defeats the coercion.

    Measured for this bead on ``python:3.12-slim``: a bare ``LC_ALL=C`` reports
    ``preferred=utf-8`` (PEP 538 coercion + PEP 540 auto-enable); adding
    ``PYTHONCOERCECLOCALE=0`` and ``PYTHONUTF8=0`` gives ``preferred=ascii``.
    """
    preferred, filesystem, _ = _probe("C")
    assert codecs.lookup(preferred).name != "utf-8", preferred
    assert codecs.lookup(filesystem).name != "utf-8", filesystem


# --------------------------------------------------------------------------- #
# 5. The anti-vacuity guard, executed. It is a script in a YAML string, which
#    is normally the least-tested code in a repo — so the suite runs it.
# --------------------------------------------------------------------------- #


def _probe_script() -> str:
    """The heredoc body of ci.yml's 'Assert the leg is genuinely non-UTF-8'."""
    steps = _steps(_job(LOCALE_JOB))
    run = next(
        str(s["run"]) for s in steps if "getpreferredencoding" in str(s.get("run", ""))
    )
    body = run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    return textwrap.dedent(body)


def _run_probe(
    monkeypatch: pytest.MonkeyPatch, *, declared: str, preferred: str, filesystem: str
) -> str | None:
    """Execute the probe with the encodings it would see on a runner.

    Returns the refusal message, or ``None`` when the probe accepted the leg.
    """
    monkeypatch.setenv("LC_ALL", declared)
    monkeypatch.setattr(locale, "getpreferredencoding", lambda do_setlocale=True: preferred)
    monkeypatch.setattr(sys, "getfilesystemencoding", lambda: filesystem)
    try:
        # `exec` is the point, not a shortcut: the test executes ci.yml's OWN
        # script rather than a copy of it, so it cannot drift from the workflow.
        # The input is a file in this repo, read from a fixed path.
        exec(compile(_probe_script(), "<ci.yml probe>", "exec"), {})  # noqa: S102
    except SystemExit as exit_:
        return str(exit_)
    return None


def test_probe_accepts_a_genuinely_ascii_c_leg(monkeypatch: pytest.MonkeyPatch) -> None:
    """The measured good case: LC_ALL=C with the knobs gives ANSI_X3.4-1968."""
    assert _run_probe(
        monkeypatch, declared="C", preferred="ANSI_X3.4-1968", filesystem="ascii"
    ) is None


def test_probe_accepts_a_genuinely_8bit_leg(monkeypatch: pytest.MonkeyPatch) -> None:
    """The measured good case for the 8-bit row (localedef on ubuntu:24.04)."""
    assert _run_probe(
        monkeypatch,
        declared="en_US.ISO-8859-1",
        preferred="iso8859-1",
        filesystem="iso8859-1",
    ) is None


def test_probe_refuses_a_leg_the_runner_put_back_on_utf8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The failure the knobs exist to prevent — and the one measured as the
    DEFAULT: a bare ``LC_ALL=C`` on python:3.12-slim reports utf-8/utf-8. If a
    future image or CPython default does that despite the knobs, the leg must
    die here rather than pass 5600 tests and call it a dimension."""
    message = _run_probe(
        monkeypatch, declared="C", preferred="utf-8", filesystem="utf-8"
    )
    assert message is not None and "VACUOUS" in message


def test_probe_refuses_an_8bit_row_that_silently_fell_back_to_ascii(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The subtler one: if ``localedef`` never ran, glibc falls back to POSIX and
    the 8-bit row becomes a SECOND ASCII row — non-UTF-8, green, and no longer
    covering the direction it was added for (bytes that mangle rather than
    raise). Non-UTF-8 is necessary but not sufficient; the row must be the codec
    it claims."""
    message = _run_probe(
        monkeypatch,
        declared="en_US.ISO-8859-1",
        preferred="ANSI_X3.4-1968",
        filesystem="ascii",
    )
    assert message is not None and "DEGRADED" in message


def test_the_8bit_row_is_built_with_localedef_not_locale_gen() -> None:
    """``locale-gen en_US.ISO-8859-1`` is REJECTED on ubuntu:24.04 — measured:
    'not a supported language or locale', because /usr/share/i18n/SUPPORTED
    spells that entry ``en_US ISO-8859-1``. The row would then silently degrade
    to ASCII (the probe above catches that, but the leg should simply work)."""
    steps = _steps(_job(LOCALE_JOB))
    builders = [str(s.get("run", "")) for s in steps if "locale" in str(s.get("run", "")).lower()]
    build = next(s for s in builders if "localedef" in s or "locale-gen" in s)
    assert "locale-gen" not in build, "locale-gen cannot build en_US.ISO-8859-1"
    assert "localedef" in build
