"""What ``load_rules`` promises beyond "it raised": its codec, its default and its words.

Written for BDL-073 B1 (bead ``beadloom-l2b7``) BEFORE the loader's dispatch became a
table, so that refactor is proven against these rather than alongside them. Each class
answers one mutant that survived all 827 tests covering ``load_rules`` in the fan-out
analysis on ``beadloom-5isv`` (2026-09-19, run serially with ``PYTHONPATH`` pointing at
``mutants/src``):

* mutant 2 dropped ``encoding="utf-8"`` from the open, and nothing noticed, because
  every room the suite had run in decodes as UTF-8 by default;
* mutant 33 changed the ``rules:`` default from ``[]`` to ``None``, and no test loaded a
  rules file without a ``rules:`` key;
* mutants 15 and 41 upper-cased the two top-level messages, and mutant 233 replaced a
  per-rule message with ``None`` — ``raise ValueError(None)`` still raises, so every
  test that asserted only the outcome passed.

A message is part of the contract here: it is the only thing an adopter sees when
their ``rules.yml`` is wrong, so the tests assert what it says, in full.
"""

from __future__ import annotations

import locale
import re
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.loader import AUTHORING_KEYS, load_rules

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The one authoring key whose value the loader does not require to be a mapping:
#: ``layers`` is read from the rule itself by ``_parse_layer_rule``.
KEY_READ_FROM_THE_RULE = "layers"

#: Every authoring key whose value ``load_rules`` itself checks is a mapping.
MAPPING_KEYS = sorted(AUTHORING_KEYS - {KEY_READ_FROM_THE_RULE})

#: A description no single-byte codec reads back unchanged: two-byte and three-byte
#: UTF-8 sequences, so ASCII refuses it and Latin-1 turns it into mojibake.
NON_ASCII_DESCRIPTION = "café — the rule's description is UTF-8"

#: Locale names that select a non-UTF-8 text codec, per platform spelling. ``C`` is
#: always present; the ISO-8859-1 names exist where the image generated them.
NON_UTF8_LOCALES = {
    "ascii": ("C",),
    "latin-1": ("en_US.ISO8859-1", "en_US.ISO-8859-1", "en_US.iso88591"),
}


def _write(path: Path, text: str) -> Path:
    path.write_bytes(text.encode("utf-8"))
    return path


def _exactly(message: str) -> str:
    """A ``pytest.raises`` pattern that matches *message* and nothing longer or shorter."""
    return rf"\A{re.escape(message)}\Z"


@pytest.fixture(params=sorted(NON_UTF8_LOCALES))
def non_utf8_ambient_codec(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[str]:
    """Set the process's LC_CTYPE to a non-UTF-8 locale for one test, then restore it.

    ``open()`` without an encoding asks the C library for the locale codec on every
    call, so an in-process ``setlocale`` reaches it — measured on macOS 3.13.7, where
    ``C`` makes it ASCII and ``en_US.ISO8859-1`` makes it ISO8859-1. The fixture
    PROBES the codec it arranged rather than trusting the call, and skips with the
    reason where the room cannot arrange one (PEP 540 UTF-8 mode, or a locale the
    image does not carry): a test that passes there would not be a check.
    """
    probe = tmp_path / "probe.txt"
    probe.write_bytes("é".encode())
    previous = locale.setlocale(locale.LC_CTYPE)
    arranged: str | None = None
    for name in NON_UTF8_LOCALES[request.param]:
        try:
            locale.setlocale(locale.LC_CTYPE, name)
        except locale.Error:
            continue
        arranged = name
        break
    try:
        if arranged is None:
            names = ", ".join(NON_UTF8_LOCALES[request.param])
            pytest.skip(f"no {request.param} locale on this image (tried {names})")
        if _default_decode(probe) == "é":
            pytest.skip(f"LC_CTYPE={arranged} still decodes UTF-8 here (UTF-8 mode?)")
        yield arranged
    finally:
        locale.setlocale(locale.LC_CTYPE, previous)


def _default_decode(path: Path) -> str | None:
    """What ``open()`` with no stated codec reads, or ``None`` if it cannot decode.

    Spelled ``encoding="locale"`` (Python 3.10+), which names the codec ``open()``
    falls back to when none is given, so the probe says what it decodes with.
    """
    try:
        with path.open("r", encoding="locale") as fh:
            return fh.read()
    except UnicodeDecodeError:
        return None


class TestTheCodecIsUtf8WhateverTheLocale:
    """Mutant 2: ``rules_path.open("r", encoding=None)``."""

    def test_a_non_ascii_description_survives_a_non_utf8_locale(
        self, tmp_path: Path, non_utf8_ambient_codec: str
    ) -> None:
        rules_path = _write(
            tmp_path / "rules.yml",
            "version: 1\n"
            "rules:\n"
            "  - name: no-cycles\n"
            f'    description: "{NON_ASCII_DESCRIPTION}"\n'
            "    forbid_cycles:\n"
            "      edge_kind: depends_on\n",
        )

        rules = load_rules(rules_path)

        assert [rule.description for rule in rules] == [NON_ASCII_DESCRIPTION], (
            f"under LC_CTYPE={non_utf8_ambient_codec} the loader decoded rules.yml "
            f"with the locale's codec instead of UTF-8"
        )


class TestAFileWithoutARulesKeyHasNoRules:
    """Mutant 33: ``data.get("rules", None)``."""

    def test_a_version_alone_loads_as_no_rules(self, tmp_path: Path) -> None:
        rules_path = _write(tmp_path / "rules.yml", "version: 1\n")

        assert load_rules(rules_path) == []


class TestTheTopLevelMessagesSayWhatIsWrong:
    """Mutants 15 and 41: the two top-level message texts."""

    @pytest.mark.parametrize(
        "text",
        ["", "- version: 1\n", "just a string\n"],
        ids=["empty-file", "a-list", "a-scalar"],
    )
    def test_a_document_that_is_not_a_mapping(self, tmp_path: Path, text: str) -> None:
        rules_path = _write(tmp_path / "rules.yml", text)

        with pytest.raises(ValueError, match=_exactly("rules.yml must be a YAML mapping")):
            load_rules(rules_path)

    @pytest.mark.parametrize(
        "value",
        ["{deny: {}}", "not-a-list"],
        ids=["a-mapping", "a-string"],
    )
    def test_a_rules_key_that_is_not_a_list(self, tmp_path: Path, value: str) -> None:
        rules_path = _write(tmp_path / "rules.yml", f"version: 1\nrules: {value}\n")

        with pytest.raises(ValueError, match=_exactly("rules.yml: 'rules' must be a list")):
            load_rules(rules_path)


class TestEveryPerRuleMessageNamesTheRuleAndTheKey:
    """Mutant 233 and its eleven siblings: ``msg = None`` in a per-rule branch.

    One row per authoring key whose value the loader checks is a mapping, so each
    branch of the dispatch is held to its own message — mutant 233 is the ``check``
    row; the other rows answer the same mutation of the other branches.
    """

    def test_the_rows_are_every_authoring_key_but_the_one_read_from_the_rule(self) -> None:
        assert KEY_READ_FROM_THE_RULE in AUTHORING_KEYS
        assert set(MAPPING_KEYS) | {KEY_READ_FROM_THE_RULE} == AUTHORING_KEYS
        assert len(MAPPING_KEYS) == len(AUTHORING_KEYS) - 1

    @pytest.mark.parametrize("key", MAPPING_KEYS)
    def test_a_value_that_is_not_a_mapping(self, tmp_path: Path, key: str) -> None:
        rules_path = _write(
            tmp_path / "rules.yml",
            f"version: 1\nrules:\n  - name: the-rule\n    {key}: not-a-mapping\n",
        )

        expected = f"Rule 'the-rule': '{key}' must be a mapping"
        with pytest.raises(ValueError, match=_exactly(expected)):
            load_rules(rules_path)
