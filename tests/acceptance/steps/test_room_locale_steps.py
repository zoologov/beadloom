"""Step implementations for `features/room_locale.feature` (BDL-068 S6, #248/#249).

Thin by design: each step writes a real workflow on disk and runs the real
`beadloom rooms` command. Nothing is doubled, because the answer is a property
of the environment the process is in, and a double of the environment proves the
double.

One step runs a CHILD process, and it has to. `locale.getpreferredencoding` reads
the codec the C library resolved when the interpreter started, so setting
`LC_ALL` inside a running test changes nothing at all — which is the same reason
`tests/ambient_codec.py` constructs its codec instead of arranging one. A
developer reproducing a locale leg starts a new process, so that is what this
scenario does.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import codecs
import json
import locale
import os
import platform
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/room_locale.feature")

#: The locale leg the fixture declares. This project's own 8-bit spelling, so
#: the scenario is about the name `ci.yml` publishes rather than an invention.
_A_LOCALE_LEG = "en_US.ISO-8859-1"

#: A locale no platform has. `xx` is not an ISO 639 language, so this cannot
#: resolve on any image — including the CI leg that builds a real 8-bit locale,
#: where a name that DID apply would make this scenario room-dependent.
_A_LOCALE_NO_PLATFORM_HAS = "xx_XX.ISO-8859-1"

#: A locale name with no codeset. `POSIX` and `C` name one by definition; a bare
#: language-and-territory names none, and the census must say so rather than
#: comparing against a guess.
_A_LOCALE_NAMING_NO_CODEC = "en_US"

#: Run `beadloom rooms` in a child, so the child's own locale is the room.
_ROOMS_IN_A_CHILD = (
    "import sys; from beadloom.services.cli import main; "
    "main(['rooms', '--project', sys.argv[1], '--json'], standalone_mode=False)"
)


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path}


def _codec_here() -> str:
    """The codec this process's locale chose, stated independently of the product.

    The same two calls `ci.yml`'s anti-vacuity step makes. Written out rather
    than imported from `beadloom.application.rooms`, because a scenario that
    borrows the derivation it judges can only prove the derivation agrees with
    itself — the rule `steps/room_judgement.py` already states.
    """
    return codecs.lookup(locale.getpreferredencoding(False)).name


def _write_workflow(world: dict[str, Any], job: str) -> None:
    workflows = world["root"] / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(f"name: CI\non: [push]\njobs:\n{job}", encoding="utf-8")


def _locale_job(value: str) -> str:
    """A job varying only the locale, spelled the way this project's own leg is."""
    return (
        "  tests-locale:\n"
        "    runs-on: ubuntu-latest\n"
        "    strategy:\n"
        "      matrix:\n"
        f'        locale: ["{value}"]\n'
    )


def _rooms(world: dict[str, Any], *extra: str) -> str:
    outcome = CliRunner().invoke(main, ["rooms", "--project", str(world["root"]), *extra])
    assert outcome.exit_code == 0, outcome.stdout + outcome.stderr
    return outcome.stdout


def _declared(world: dict[str, Any]) -> dict[str, Any]:
    """The one declared leg the fixture wrote, as the report answered about it."""
    payload = world["payload"]
    assert len(payload["declared"]) == 1, payload["declared"]
    leg: dict[str, Any] = payload["declared"][0]
    return leg


@given("a workflow job declaring a locale leg")
def _a_locale_leg(world: dict[str, Any]) -> None:
    _write_workflow(world, _locale_job(_A_LOCALE_LEG))


@given("a workflow job declaring a locale that names no character encoding")
def _a_locale_naming_no_codec(world: dict[str, Any]) -> None:
    _write_workflow(world, _locale_job(_A_LOCALE_NAMING_NO_CODEC))


@given("a workflow job declaring this run's own platform, interpreter and locale")
def _this_runs_own_room(world: dict[str, Any]) -> None:
    """The one leg a local run can be inside, built from what this run reports.

    The locale is spelled as a territory plus this run's own codec, because a
    leg declares a NAME and the census compares the codec that name declares.
    Which name a platform happens to have is the platform's business and is the
    defect this feature is about; what the census must do is resolve both sides
    to the same codec.
    """
    labels = {"Linux": "ubuntu-latest", "Darwin": "macos-latest", "Windows": "windows-latest"}
    label = labels[platform.system()]
    version = f"{sys.version_info[0]}.{sys.version_info[1]}"
    _write_workflow(
        world,
        (
            "  tests-locale:\n"
            f"    runs-on: {label}\n"
            "    strategy:\n"
            "      matrix:\n"
            f'        python-version: ["{version}"]\n'
            f'        locale: ["en_US.{_codec_here()}"]\n'
        ),
    )


@given("a child process asked for a locale no platform has")
def _a_child_under_an_absent_locale(world: dict[str, Any]) -> None:
    _write_workflow(world, _locale_job(_A_LOCALE_NO_PLATFORM_HAS))
    world["locale"] = _A_LOCALE_NO_PLATFORM_HAS


@when("the rooms are reported")
def _report_the_rooms(world: dict[str, Any]) -> None:
    world["stdout"] = _rooms(world)
    world["payload"] = json.loads(_rooms(world, "--json"))


@when("that child reports its rooms")
def _report_from_the_child(world: dict[str, Any]) -> None:
    """The reproduction a developer makes: a new process under the leg's name."""
    environment = {
        **os.environ,
        "LC_ALL": world["locale"],
        # The two knobs `ci.yml` sets on the same leg: without them PEP 538 and
        # PEP 540 put the process back on UTF-8 and the scenario measures the
        # coercion instead of the locale.
        "PYTHONUTF8": "0",
        "PYTHONCOERCECLOCALE": "0",
    }
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-c", _ROOMS_IN_A_CHILD, str(world["root"])],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    world["payload"] = json.loads(completed.stdout)


@when("the locale axis is asked for")
def _ask_for_the_locale_axis(world: dict[str, Any]) -> None:
    world["stdout"] = _rooms(world, "--dimension", "locale")


@then("the room this run is in names a locale dimension")
def _the_current_room_names_a_locale(world: dict[str, Any]) -> None:
    assert world["payload"]["current"].get("locale") == _codec_here()


@then("that leg is reported as entered")
def _the_leg_is_entered(world: dict[str, Any]) -> None:
    leg = _declared(world)
    assert leg["entered"], leg["why"]


@then("that leg is reported as not entered")
def _the_leg_is_not_entered(world: dict[str, Any]) -> None:
    assert not _declared(world)["entered"]


@then("the reason names the codec the leg declares and the one this run is in")
def _the_reason_names_both_codecs(world: dict[str, Any]) -> None:
    why = _declared(world)["why"]

    assert codecs.lookup(_A_LOCALE_LEG.split(".", 1)[1]).name in why, why
    assert _codec_here() in why, why


@then("the leg declaring that locale is reported as not entered")
def _the_absent_locale_leg_is_not_entered(world: dict[str, Any]) -> None:
    assert not _declared(world)["entered"]


@then("the report says the name did not apply and names the room the run is in")
def _the_report_says_the_name_did_not_apply(world: dict[str, Any]) -> None:
    why = _declared(world)["why"]
    current = world["payload"]["current"]

    assert "did not apply" in why, why
    assert world["locale"] in why, why
    assert current["locale_asked"] == world["locale"], current
    assert current["locale"] in why, why


@then("the report names it as unresolved")
def _the_leg_is_unresolved(world: dict[str, Any]) -> None:
    unresolved = world["payload"]["unresolved"]

    assert any(_A_LOCALE_NAMING_NO_CODEC in u["why"] for u in unresolved), unresolved


@then("the locale that leg declares is printed")
def _the_locale_axis_is_printed(world: dict[str, Any]) -> None:
    assert world["stdout"].split() == [_A_LOCALE_LEG]
