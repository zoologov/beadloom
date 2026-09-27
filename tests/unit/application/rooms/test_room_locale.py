"""The locale dimension of a room (BDL-068 S6, BDL-UX #248 and #249).

The acceptance scenarios in ``tests/acceptance/application/room_locale.feature``
run against this process's real locale, which is the only way to prove the
answer is about the environment and not about a fixture. These tests cover what
one environment cannot show: the locale names this machine does not have, the
codesets it does not carry, and the precedence between the three variables that
can name a locale.

Nothing here doubles ``locale.getpreferredencoding``. It reads the codec the C
library resolved when the interpreter started, so a monkeypatch of it would
change what the derivation reads and not what the process is in — the same
finding ``tests/support/ambient_codec.py`` records. Where a real locale is needed, a
child process is started under it, which is what a developer reproducing a leg
does.
"""

from __future__ import annotations

import codecs
import json
import locale
import os
import platform
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from beadloom.application import rooms
from beadloom.application.rooms import (
    LOCALE_ASKED_DIMENSION,
    LOCALE_DIMENSION,
    Room,
    codec_of_locale_name,
    current_room,
    requested_locale_name,
    room_line,
    take_census,
)
from tests.support.locale_probes import codec_of_a_child, declared_locales

if TYPE_CHECKING:
    from pathlib import Path

#: The three variables POSIX lets a locale be named in, most specific first.
_LOCALE_VARS = ("LC_ALL", "LC_CTYPE", "LANG")

#: Run `beadloom rooms` in a child, so the child's own locale decides the room.
_ROOMS_IN_A_CHILD = (
    "import sys; from beadloom.services.cli import main; "
    "main(['rooms', '--project', sys.argv[1], '--json'], standalone_mode=False)"
)


def _codec_here() -> str:
    """This process's ambient codec, stated with the stdlib rather than borrowed."""
    return codecs.lookup(locale.getpreferredencoding(False)).name


@pytest.fixture()
def no_locale_named(monkeypatch: pytest.MonkeyPatch) -> None:
    """An environment naming no locale, so a test can add exactly one."""
    for name in _LOCALE_VARS:
        monkeypatch.delenv(name, raising=False)


class TestTheCodecALocaleNameDeclares:
    """A locale name is a spelling; what it declares is a codec.

    The pair that decided BDL-UX #249 is the first two rows: `en_US.ISO-8859-1`
    and `en_US.ISO8859-1` declare the same codec, and macOS has only the second
    as a locale. The difference is the platform's, and the census must not
    inherit it.
    """

    @pytest.mark.parametrize(
        ("name", "codec"),
        [
            ("en_US.ISO-8859-1", "iso8859-1"),
            ("en_US.ISO8859-1", "iso8859-1"),
            ("C", "ascii"),
            ("POSIX", "ascii"),
            ("C.UTF-8", "utf-8"),
            ("en_US.UTF-8", "utf-8"),
            ("ru_RU.CP1251", "cp1251"),
            ("de_DE.ISO-8859-15@euro", "iso8859-15"),
            ("  C  ", "ascii"),
        ],
    )
    def test_a_name_that_declares_a_codec(self, name: str, codec: str) -> None:
        assert codec_of_locale_name(name) == codec

    @pytest.mark.parametrize(
        "name",
        ["en_US", "", "   ", "en_US.NO-SUCH-CODESET", "en_US.iso88591"],
    )
    def test_a_name_that_declares_none_is_unresolved_rather_than_guessed(
        self, name: str
    ) -> None:
        """`en_US.iso88591` is not a typo: it is how `locale -a` spells the
        codeset on glibc, and `codecs.lookup` refuses it. Guessing a
        normalisation here would be this module owning a spelling rule, which is
        the thing it refuses to do."""
        assert codec_of_locale_name(name) is None


class TestTheLocaleThisEnvironmentAsksFor:
    """Which variable names the locale, and what an empty one means."""

    def test_lc_all_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LC_ALL", "C")
        monkeypatch.setenv("LC_CTYPE", "en_US.UTF-8")
        monkeypatch.setenv("LANG", "en_US.UTF-8")

        assert requested_locale_name() == "C"

    def test_lc_ctype_is_read_before_lang(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.setenv("LC_CTYPE", "en_US.ISO8859-1")
        monkeypatch.setenv("LANG", "en_US.UTF-8")

        assert requested_locale_name() == "en_US.ISO8859-1"

    def test_an_empty_variable_names_nothing(
        self, monkeypatch: pytest.MonkeyPatch, no_locale_named: None
    ) -> None:
        """POSIX: an empty value is not a locale name, it is the absence of one."""
        monkeypatch.setenv("LC_ALL", "")
        monkeypatch.setenv("LANG", "C")

        assert requested_locale_name() == "C"

    def test_an_environment_naming_no_locale(self, no_locale_named: None) -> None:
        assert requested_locale_name() is None


class TestTheRoomThisRunIsIn:
    """The dimension is derived, and the second one appears only when it must."""

    def test_the_current_room_names_the_codec_in_force(self) -> None:
        assert current_room().dimensions[LOCALE_DIMENSION] == _codec_here()

    def test_a_locale_that_applied_adds_no_second_dimension(self) -> None:
        dimensions = rooms.locale_dimensions("iso8859-1", "en_US.ISO8859-1")

        assert dimensions == {LOCALE_DIMENSION: "iso8859-1"}

    def test_a_locale_that_did_not_apply_names_what_was_asked_for(self) -> None:
        dimensions = rooms.locale_dimensions("ascii", "en_US.ISO-8859-1")

        assert dimensions == {
            LOCALE_DIMENSION: "ascii",
            LOCALE_ASKED_DIMENSION: "en_US.ISO-8859-1",
        }

    def test_a_name_declaring_no_codec_is_not_a_failure_to_apply(self) -> None:
        """`LANG=en_US` names no codeset, so nothing was promised and nothing broke."""
        assert rooms.locale_dimensions("utf-8", "en_US") == {LOCALE_DIMENSION: "utf-8"}

    def test_an_environment_naming_no_locale_still_names_the_codec(self) -> None:
        assert rooms.locale_dimensions("utf-8", None) == {LOCALE_DIMENSION: "utf-8"}

    def test_a_codec_that_cannot_be_read_adds_no_dimension(self) -> None:
        """The rule this module states everywhere: an inability is not an answer."""
        assert rooms.locale_dimensions(None, "C") == {}

    def test_the_room_line_names_the_locale(self) -> None:
        line = room_line(
            Room(dimensions={"os": "Darwin", LOCALE_DIMENSION: "ascii"}, source="x")
        )

        assert "locale ascii" in line

    def test_the_room_line_names_a_locale_that_did_not_apply(self) -> None:
        line = room_line(
            Room(
                dimensions={
                    "os": "Darwin",
                    LOCALE_DIMENSION: "ascii",
                    LOCALE_ASKED_DIMENSION: "en_US.ISO-8859-1",
                },
                source="x",
            )
        )

        assert "locale ascii" in line
        assert "en_US.ISO-8859-1" in line
        assert "did not apply" in line


class TestTheComparison:
    """Both sides resolve to a codec, and every other outcome is `not entered`."""

    def test_the_same_codec_enters_the_room(self, no_locale_named: None) -> None:
        assert rooms._locale_difference("iso8859-1", "en_US.ISO-8859-1") is None

    def test_a_different_codec_names_both(self, no_locale_named: None) -> None:
        difference = rooms._locale_difference("ascii", "en_US.ISO-8859-1")

        assert difference is not None
        assert "iso8859-1" in difference
        assert "ascii" in difference

    def test_a_run_that_cannot_describe_its_locale_does_not_enter(
        self, no_locale_named: None
    ) -> None:
        difference = rooms._locale_difference(None, "C")

        assert difference is not None
        assert "cannot describe" in difference

    def test_a_leg_naming_no_codec_does_not_enter(self, no_locale_named: None) -> None:
        difference = rooms._locale_difference("utf-8", "en_US")

        assert difference is not None
        assert "no character encoding" in difference

    def test_the_name_this_environment_asked_for_is_named_as_a_phantom(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """#249: the leg's own name was requested and resolved somewhere else."""
        monkeypatch.setenv("LC_ALL", "en_US.ISO-8859-1")

        difference = rooms._locale_difference("ascii", "en_US.ISO-8859-1")

        assert difference is not None
        assert "did not apply" in difference
        assert "ascii" in difference

    def test_a_leg_naming_no_codec_is_reported_unresolved(self, tmp_path: Path) -> None:
        declared = Room(
            dimensions={LOCALE_DIMENSION: "en_US"}, source="ci.yml: tests-locale"
        )

        census = take_census(tmp_path, declared=(declared,))

        assert not census.comparisons[0].entered
        assert any("en_US" in u.why for u in census.unresolved), census.unresolved


class TestTheNamesThisProjectPublishes:
    """The reproduction #249 is about, taken against this repository's own legs.

    A developer reproducing a locale leg copies the name out of `ci.yml`. These
    rows start a child under each of those names and ask the census what room
    that child is in. They are room-independent by construction: they assert the
    census AGREES with the child's own codec, never that a given name degrades —
    which it does on Darwin and does not on the leg that builds the locale.
    """


    @pytest.mark.parametrize("name", declared_locales())
    def test_the_census_reports_the_codec_the_child_actually_has(
        self, name: str, tmp_path: Path
    ) -> None:
        codec = codec_of_a_child(name)

        payload = _rooms_in_a_child(_a_project_declaring(tmp_path, name), name)

        assert payload["current"][LOCALE_DIMENSION] == codec

    @pytest.mark.parametrize("name", declared_locales())
    def test_the_locale_axis_separates_the_run_only_when_the_name_resolved_elsewhere(
        self, name: str, tmp_path: Path
    ) -> None:
        """The invariant, in the one direction that can manufacture coverage.

        Read off the LOCALE clause of the reason rather than off `entered`,
        because `entered` also carries the platform: this repository's legs are
        Ubuntu, so a Darwin run enters none of them whatever its locale, and an
        assertion on `entered` would be about the machine. It is also the arm a
        suite-wide `tests/support/room_simulation.py` run breaks, since the fixture's
        platform would be the parent's fabricated one and the child's is real.
        """
        codec = codec_of_a_child(name)
        wanted = codec_of_locale_name(name)

        leg = _rooms_in_a_child(_a_project_declaring(tmp_path, name), name)["declared"][0]

        assert (f"{LOCALE_DIMENSION}:" in leg["why"]) == (codec != wanted), leg

    @pytest.mark.parametrize("name", declared_locales())
    def test_a_name_that_did_not_apply_says_so_rather_than_reading_as_unset(
        self, name: str, tmp_path: Path
    ) -> None:
        """#249's own sentence: the developer asked for it and did not get it."""
        codec = codec_of_a_child(name)
        if codec == codec_of_locale_name(name):
            pytest.skip(f"`{name}` applied in this room, so nothing degraded here")

        payload = _rooms_in_a_child(_a_project_declaring(tmp_path, name), name)

        assert payload["current"][LOCALE_ASKED_DIMENSION] == name
        assert "did not apply" in payload["declared"][0]["why"]


def _a_project_declaring(root: Path, name: str) -> Path:
    """A project whose one leg declares *name* on this run's own platform."""
    labels = {"Linux": "ubuntu-latest", "Darwin": "macos-latest", "Windows": "windows-latest"}
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n"
        "  tests-locale:\n"
        f"    runs-on: {labels[platform.system()]}\n"
        "    strategy:\n"
        "      matrix:\n"
        f'        locale: ["{name}"]\n',
        encoding="utf-8",
    )
    return root


def _rooms_in_a_child(root: Path, name: str) -> dict[str, object]:
    """`beadloom rooms --json`, as a process running under the locale *name*."""
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-c", _ROOMS_IN_A_CHILD, str(root)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={
            **os.environ,
            "LC_ALL": name,
            "PYTHONUTF8": "0",
            "PYTHONCOERCECLOCALE": "0",
        },
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload: dict[str, object] = json.loads(completed.stdout)
    return payload


