"""Text I/O states its encoding, so the artifacts we write do not depend on the image (BDL-061.42).

``Path.write_text()``, ``Path.read_text()``, ``open()`` and ``subprocess(text=True)``
all default to ``locale.getpreferredencoding(False)``. Every file this package
*generates* — a git hook, ``AGENTS.md``, a rules adapter, graph YAML, JSON — is a
**contract byte stream**: UTF-8 by definition, read back by us and by other tools,
not a document in the operator's locale. A site that leaves the encoding to the
image therefore has two wrong answers rather than one, and they fail in opposite
directions:

* under an **ASCII** locale the write/read **raises** (loud, and the command aborts);
* under an **8-bit** locale nothing raises and the byte is **silently mangled** —
  the adopter keeps an executable hook with a mojibake byte in it.

Re-measured for this bead on ``HEAD`` (clean-room ``git archive``, one Linux
container, three whole-suite runs changing nothing but the locale, counts read
from ``--junitxml``):

===============================  =========================  ==========
leg                              interpreter                failures
===============================  =========================  ==========
``LC_ALL=C.UTF-8``               preferred/fs = utf-8       3 (noise)
``LC_ALL=C`` + the two knobs     preferred/fs = ascii       111
``LC_ALL=en_US.ISO-8859-1``      preferred/fs = iso8859-1   86
===============================  =========================  ==========

i.e. **108 ASCII / 83 8-bit** locale-attributable failures. They split into two
groups that want different decisions, and only the first is "pass
``encoding='utf-8'``":

* **72 were text I/O with no stated codec** — one product call site (the
  ``install-hooks`` hook writer, which could not write a hook at all: 24 rows
  across ``test_cli_hooks``, ``test_cli_active_sync_hardening`` and
  ``test_integration``), four ``subprocess(text=True)`` seams, and ~45 test-side
  reads of an artifact the product had already written correctly as UTF-8;
* **36 were the FILESYSTEM's encoding**, which is a different question — see
  :mod:`tests.filesystem_names`. There the product's answer was right on every
  image and the tests were asserting the answer a UTF-8 machine gives.

**The knobs are load-bearing and this is measured, not quoted:** a bare
``LC_ALL=C`` is *not* enough — PEP 538/540 coerce UTF-8 mode back on — so
``PYTHONUTF8=0`` and ``PYTHONCOERCECLOCALE=0`` are what make the environment real.
Measured again here on macOS 3.13.7, *correcting* the claim in
``tests/ambient_codec.py`` that an ambient non-UTF-8 codec cannot be arranged on
this machine: with those knobs ``locale.getpreferredencoding(False)`` reports
``US-ASCII`` and ``Path.write_text()`` raises. What macOS forces is the
**filesystem** encoding (still ``utf-8``), not the text-I/O codec — so the
text-I/O half of the dimension runs locally, and only the *filename* half needs a
container. Every subprocess below therefore probes what it actually got and skips
with a stated reason rather than passing vacuously.

Two instruments, because either alone proves too little:

* :class:`TestEveryTextIoSiteStatesItsEncoding` reads the *source* — it fails the
  day a new call site omits ``encoding=``, whatever the content happens to be
  today, and needs no environment. BDL-061.68 selected ruff's ``PLW1514``, which
  asks the same question in the lint job, so the two overlap — but neither
  contains the other, and both facts were MEASURED on ruff 0.16.3 rather than
  read off the rule's description: ``PLW1514`` does not look at
  ``subprocess(text=True)`` at all, and it reports ``read_text`` only where it
  can infer the receiver is a ``Path``, which an unannotated parameter defeats.
  This class keys on the attribute name and needs no inference, so it is what
  actually covers the package; ``PLW1514`` adds ``tests/``, which this class
  does not read. The shared notion of "a call whose codec somebody chooses"
  lives in :mod:`tests.decoding_calls` so the two cannot drift apart;
* :class:`TestTheGeneratedArtifactsSurviveANonUtf8Locale` runs the *real CLI* in a
  real subprocess under a real non-UTF-8 locale and reads the bytes back, so the
  guarantee is proven end-to-end rather than by grep.
"""

from __future__ import annotations

import ast
import codecs
import io
import locale
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from beadloom.infrastructure.console_streams import (
    TOLERANT_ERRORS,
    tolerate_unencodable_output,
)
from tests import filesystem_names
from tests.adopter_project import typescript_project
from tests.decoding_calls import (
    SUBPROCESS_CALLS,
    TEXT_READWRITE,
    called_name,
    is_true,
    keyword,
    open_mode,
)

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "beadloom"
_BEADLOOM = shutil.which("beadloom") or str(Path(sys.executable).parent / "beadloom")

#: The knobs that make a non-UTF-8 locale real. A bare ``LC_ALL=C`` is coerced
#: back to UTF-8 by PEP 538/540 and would make every test below vacuous.
_ASCII_ENV = {"LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}

#: Sites that genuinely want the *operator's* locale rather than a contract, each
#: named with its reason. Empty on purpose: everything this package writes or
#: reads back is a file some other program parses, so nothing here is prose in the
#: user's encoding. An entry is how a future exception is made *visible*.
_LOCALE_BY_DESIGN: dict[tuple[str, int], str] = {}


def _module_sources() -> list[tuple[Path, ast.Module]]:
    """Every module of the package, parsed once."""
    parsed = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        parsed.append((path, ast.parse(path.read_text(encoding="utf-8"))))
    return parsed


def _ambient_text_io_sites() -> list[tuple[Path, int, str]]:
    """Every call in the package whose codec the *image* would choose."""
    sites: list[tuple[Path, int, str]] = []
    for path, tree in _module_sources():
        rel = path.relative_to(_SRC_ROOT.parent.parent)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or keyword(node, "encoding") is not None:
                continue
            name = called_name(node)
            if name in TEXT_READWRITE:
                sites.append((rel, node.lineno, f"{name}()"))
            elif name == "open" and "b" not in open_mode(node):
                sites.append((rel, node.lineno, f"open(mode={open_mode(node)!r})"))
            elif name in SUBPROCESS_CALLS and (
                is_true(keyword(node, "text")) or is_true(keyword(node, "universal_newlines"))
            ):
                sites.append((rel, node.lineno, f"subprocess.{name}(text=True)"))
    return [s for s in sites if (str(s[0]), s[1]) not in _LOCALE_BY_DESIGN]


class TestEveryTextIoSiteStatesItsEncoding:
    """The source-level half: no call site leaves the codec to the image."""

    def test_no_module_reads_or_writes_text_in_the_images_codec(self) -> None:
        sites = _ambient_text_io_sites()
        rendered = "\n".join(f"  {p}:{line} {what}" for p, line, what in sites)
        assert not sites, (
            "text I/O without an explicit `encoding=` — the codec is whatever the "
            f"image's locale says, which is a wrong answer twice over:\n{rendered}"
        )

    def test_the_sweep_can_actually_see_a_site(self) -> None:
        """The sweep is not vacuous: it finds a planted call it should reject."""
        planted = ast.parse("from pathlib import Path\nPath('x').write_text('y')\n")
        calls = [n for n in ast.walk(planted) if isinstance(n, ast.Call)]
        offending = [c for c in calls if called_name(c) == "write_text"]
        assert offending, "the AST walk no longer recognises a write_text() call"
        assert keyword(offending[0], "encoding") is None


def _run_under(
    env_extra: dict[str, str], argv: list[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **env_extra}
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        argv,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",  # the harness states its own codec; the child's is the subject
        errors="replace",
        env=env,
        check=False,
    )


def _preferred_encoding_under(env_extra: dict[str, str]) -> str:
    """What a child interpreter actually gets — never assumed, always probed."""
    probe = "import codecs, locale; print(codecs.lookup(locale.getpreferredencoding(False)).name)"
    done = _run_under(env_extra, [sys.executable, "-c", probe], Path.cwd())
    return done.stdout.strip()


@pytest.fixture(scope="module")
def ascii_locale_is_real() -> str:
    """Skip with a stated reason rather than assert nothing (see .38's vacuity locks)."""
    got = _preferred_encoding_under(_ASCII_ENV)
    if got == "utf-8":
        pytest.skip(
            f"this image coerces {_ASCII_ENV['LC_ALL']} back to UTF-8 (preferred={got}), "
            "so the non-UTF-8 direction cannot be arranged here and this test would "
            "assert nothing"
        )
    return got


#: A name carrying a byte no codec can decode, built rather than written: a
#: source file cannot hold a lone surrogate (it is not encodable as UTF-8), and
#: pytest's assertion rewriter refuses to compile a module whose constants are.
#: ``os.fsencode`` round-trips it, so it names a file that can really exist —
#: which is why the predicate must call it NAMEABLE.
_LONE_SURROGATE_NAME = "src/" + chr(0xDCFF) + ".py"

#: Spellings of one 8-bit locale, because the name is not portable: macOS
#: resolves ``en_US.ISO8859-1`` and rejects the hyphenated form, while a Debian
#: image built by ``localedef -i en_US -f ISO-8859-1`` answers to the hyphenated
#: one. Each is probed rather than assumed.
_EIGHT_BIT_CANDIDATES = ("en_US.ISO8859-1", "en_US.ISO-8859-1", "en_US.iso88591")


def _stdout_policy_under(env_extra: dict[str, str]) -> tuple[str, str]:
    """``(encoding, errors)`` a child's stdout actually gets — probed, not assumed."""
    probe = "import codecs, sys; print(codecs.lookup(sys.stdout.encoding).name, sys.stdout.errors)"
    done = _run_under(env_extra, [sys.executable, "-c", probe], Path.cwd())
    parts = done.stdout.split()
    return (parts[0], parts[1]) if len(parts) == 2 else ("", "")


@pytest.fixture(scope="module")
def eight_bit_terminal() -> dict[str, str]:
    """An environment whose stdout is a real 8-bit codec with a *strict* handler.

    Both halves are load-bearing and neither is portable, so both are probed. A
    codec that comes back UTF-8 makes the test vacuous; and an ASCII stdout is
    not the same environment — CPython already hands the C locale
    ``backslashreplace``, which is why this defect is invisible to the ``C`` row
    and reachable only from the 8-bit one.
    """
    for name in _EIGHT_BIT_CANDIDATES:
        env = {"LC_ALL": name, "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
        encoding, errors = _stdout_policy_under(env)
        if encoding not in ("", "utf-8", "ascii") and errors == "strict":
            return env
    pytest.skip(
        "no 8-bit locale on this image resolves to a strict non-UTF-8 stdout "
        f"(tried {', '.join(_EIGHT_BIT_CANDIDATES)}), so the direction this test "
        "is about cannot be arranged here"
    )
    raise AssertionError  # unreachable; pytest.skip raises


class TestTheConsoleSurvivesATerminalItCannotSpell:
    """The third group the dimension found, and the one where UTF-8 is wrong.

    A terminal's codec is the operator's locale, so the fix is the error handler
    rather than the encoding — see
    :mod:`beadloom.infrastructure.console_streams` for the measurement and the
    reasons.
    """

    def test_the_harness_help_is_printed_rather_than_raising(
        self, eight_bit_terminal: dict[str, str]
    ) -> None:
        """MEASURED before the fix on both macOS and Debian: exit 1, stdout empty.

        ``UnicodeEncodeError: 'latin-1' codec can't encode character '\u2192'``
        out of ``click.echo`` — a help text nobody can read is not a smaller
        defect than a wrong one.
        """
        done = _run_under(
            eight_bit_terminal,
            [sys.executable, "-m", "beadloom.ai_agents.ai_techwriter", "--help"],
            Path.cwd(),
        )

        assert done.returncode == 0, done.stderr
        assert "--platform" in done.stdout, done.stdout

    def test_the_character_it_cannot_show_is_named_rather_than_dropped(
        self, eight_bit_terminal: dict[str, str]
    ) -> None:
        """Degrading must stay visible: ``backslashreplace``, not silence."""
        done = _run_under(
            eight_bit_terminal,
            [sys.executable, "-m", "beadloom.ai_agents.ai_techwriter", "--help"],
            Path.cwd(),
        )

        assert r"\u2192" in done.stdout, done.stdout

    @pytest.mark.skipif(
        not Path(_BEADLOOM).exists(), reason="beadloom console script not installed"
    )
    def test_the_same_holds_through_the_installed_console_script(
        self, eight_bit_terminal: dict[str, str]
    ) -> None:
        """The other entry point, because they are separate Click objects."""
        done = _run_under(eight_bit_terminal, [_BEADLOOM, "guard", "--help"], Path.cwd())

        assert done.returncode == 0, done.stderr


class TestTheStreamPolicyDoesOnlyWhatItSays:
    """``tolerate_unencodable_output`` is applied to every run, so it needs pinning."""

    def test_a_strict_stream_is_relaxed_and_reported(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        with target.open("w", encoding="ascii", errors="strict") as stream:
            relaxed = tolerate_unencodable_output([stream])

            assert relaxed == (str(target),)
            assert stream.errors == TOLERANT_ERRORS
            stream.write("\u2192")  # would raise under `strict`

        assert r"\u2192" in target.read_text(encoding="ascii")

    def test_an_explicit_handler_outranks_ours(self, tmp_path: Path) -> None:
        """An operator's ``PYTHONIOENCODING=...:replace`` is a decision, not a default."""
        target = tmp_path / "out.txt"
        with target.open("w", encoding="ascii", errors="replace") as stream:
            assert tolerate_unencodable_output([stream]) == ()
            assert stream.errors == "replace"

    def test_a_stream_that_cannot_be_reconfigured_is_left_alone(self) -> None:
        """Click's runner, a captured pipe: no ``reconfigure``, and no crash."""
        buffer = io.StringIO()

        assert tolerate_unencodable_output([buffer]) == ()

    def test_the_codec_is_never_changed(self, tmp_path: Path) -> None:
        """The terminal's encoding belongs to the operator; only the handler moves."""
        target = tmp_path / "out.txt"
        with target.open("w", encoding="ascii", errors="strict") as stream:
            tolerate_unencodable_output([stream])

            assert stream.encoding == "ascii"


def _git_project(tmp_path: Path) -> Path:
    """A repository that is **not** Beadloom, with somewhere to install a hook.

    The project axis of ONE PLATFORM IS NOT VERIFIED (``tests.adopter_project``,
    added by BDL-061.58): ``install-hooks`` writes into somebody else's tree, and
    a guarantee measured only on this repository is a guarantee about this
    repository. A TypeScript service is used deliberately — nothing about its
    manifest, its stack or its version can make us accidentally right.
    """
    project = tmp_path / "orders-web"
    typescript_project(project)
    (project / ".git" / "hooks").mkdir(parents=True)
    return project


class TestTheGeneratedArtifactsSurviveANonUtf8Locale:
    """The end-to-end half: the real CLI, a real subprocess, a real ASCII locale."""

    @pytest.mark.skipif(
        not Path(_BEADLOOM).exists(), reason="beadloom console script not installed"
    )
    def test_install_hooks_writes_a_utf8_hook_under_an_ascii_locale(
        self, tmp_path: Path, ascii_locale_is_real: str
    ) -> None:
        """The hook an adopter keeps is UTF-8 wherever it was generated.

        Its template contains an em dash, so on an ASCII image the write raises and
        the command aborts; on an 8-bit image it lands as a mojibake byte inside an
        executable script. Both are the file *we* generate, not the user's prose.
        """
        project = _git_project(tmp_path)
        done = _run_under(
            _ASCII_ENV, [_BEADLOOM, "install-hooks", "--project", str(project)], tmp_path
        )

        assert done.returncode == 0, (
            f"install-hooks failed under preferred={ascii_locale_is_real}: "
            f"{done.stdout}{done.stderr}"
        )
        hook = project / ".git" / "hooks" / "pre-commit"
        assert hook.exists(), "no pre-commit hook was written"
        hook.read_bytes().decode("utf-8")  # raises if the codec was the image's

    @pytest.mark.skipif(
        not Path(_BEADLOOM).exists(), reason="beadloom console script not installed"
    )
    def test_the_hook_is_byte_identical_to_the_one_a_utf8_image_writes(
        self, tmp_path: Path, ascii_locale_is_real: str
    ) -> None:
        """The artifact is a function of its inputs, not of the machine that ran us."""
        ascii_project = _git_project(tmp_path / "a")
        utf8_project = _git_project(tmp_path / "b")

        _run_under(
            _ASCII_ENV, [_BEADLOOM, "install-hooks", "--project", str(ascii_project)], tmp_path
        )
        _run_under(
            {"LC_ALL": "C.UTF-8", "PYTHONUTF8": "1"},
            [_BEADLOOM, "install-hooks", "--project", str(utf8_project)],
            tmp_path,
        )

        under_ascii = (ascii_project / ".git" / "hooks" / "pre-commit").read_bytes()
        under_utf8 = (utf8_project / ".git" / "hooks" / "pre-commit").read_bytes()
        assert under_ascii == under_utf8, "the installed hook differs by locale"


class TestNothingInThePackageAsksTheImageForACodecAtRuntime:
    """``PYTHONWARNDEFAULTENCODING`` reaches sites whose content is ASCII *today*."""

    @pytest.mark.skipif(
        not Path(_BEADLOOM).exists(), reason="beadloom console script not installed"
    )
    def test_a_real_run_emits_no_encoding_warning_from_our_own_modules(
        self, tmp_path: Path
    ) -> None:
        """CPython names every unencoded text-I/O site; we own the ones under `beadloom/`.

        Third-party frames are excluded deliberately — a dependency's default is not
        ours to fix here, and including it would make this test about `click`.
        """
        project = _git_project(tmp_path)
        done = _run_under(
            {"PYTHONWARNDEFAULTENCODING": "1", "PYTHONWARNINGS": "always::EncodingWarning"},
            [_BEADLOOM, "install-hooks", "--project", str(project)],
            tmp_path,
        )
        ours = [
            line
            for line in done.stderr.splitlines()
            if "EncodingWarning" in line and f"{os.sep}beadloom{os.sep}" in line
        ]
        assert not ours, "our own modules asked the image for a codec:\n" + "\n".join(ours)


class TestTheFilesystemNamePredicateHasItsOwnContract:
    """:mod:`tests.filesystem_names` decides ~36 rows, so it needs proving itself."""

    @pytest.mark.parametrize(
        ("codec", "expected"),
        [("utf-8", True), ("latin-1", False), ("ascii", False)],
    )
    def test_the_predicate_follows_the_codec_it_is_given(
        self, monkeypatch: pytest.MonkeyPatch, codec: str, expected: bool
    ) -> None:
        """Injected rather than arranged: macOS cannot be given an ASCII filesystem."""
        monkeypatch.setattr(filesystem_names, "filesystem_encoding", lambda: codec)

        assert filesystem_names.filesystem_can_name("src/файл.py") is expected

    def test_a_round_trippable_byte_is_still_nameable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The half that must NOT be refused: a lone surrogate names a real file.

        ``os.fsencode`` carries it back to the byte it came from, so a predicate
        that called it unnameable would invert four rows that are about exactly
        that (``src/`` + a lone surrogate + ``.py``).
        """
        monkeypatch.setattr(filesystem_names, "filesystem_encoding", lambda: "ascii")

        assert filesystem_names.filesystem_can_name(_LONE_SURROGATE_NAME) is True

    def test_the_delivered_form_carries_the_same_bytes_on_any_image(self) -> None:
        """What every rewritten fixture depends on, asserted rather than assumed.

        On a UTF-8 image this is the identity; on an ASCII one the returned string
        is surrogate-escaped and ``os.fsencode`` puts the original UTF-8 bytes
        back. Either way the child process, the branch and the directory see the
        same bytes, which is why the assertions in those tests did not move.
        """
        for name in ("features/тест", "Иван Петров", "проект", "日本語-ø"):
            delivered = filesystem_names.as_the_process_receives(name)

            assert os.fsencode(delivered) == name.encode("utf-8"), name

    def test_the_predicate_agrees_with_the_criterion_the_product_applies(self) -> None:
        """Two independent routes to the same answer on the image running this.

        The predicate asks the codec by name; the product calls ``os.fsencode``.
        They must not drift — if they did, the rows would assert a refusal the
        product does not make, or accept one it does.
        """
        names = (
            "src/app.py",
            "src/файл.py",
            "src/" + chr(0x1F600) + ".py",
            _LONE_SURROGATE_NAME,
        )
        for name in names:
            try:
                os.fsencode(name)
            except UnicodeEncodeError:
                product_can = False
            else:
                product_can = True

            assert filesystem_names.filesystem_can_name(name) is product_can, name


class TestTheInstrumentItselfIsHonest:
    """A probe that cannot report a non-UTF-8 image would make every skip above a lie."""

    def test_the_probe_reports_this_interpreters_own_encoding(self) -> None:
        assert (
            _preferred_encoding_under({}) == codecs.lookup(locale.getpreferredencoding(False)).name
        )
