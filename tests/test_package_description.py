"""The distribution's one-line description, and what can be checked about it.

BDL-062 `.4`. `pyproject.toml`'s `description` is what PyPI shows on the project
page. It said "Context Oracle + Doc Sync Engine for AI-assisted development"
through three major versions -- the 1.x description, naming two of the product's
parts and none of the four added since -- and nothing anywhere compared it to
anything, because there is nothing to compare a sentence to.

**Half of this is checkable and half is not, and the two are kept apart here.**
The same sentence is written twice, in the manifest and in the package
docstring; that they agree IS checkable, and they can drift apart silently
otherwise. Whether the sentence is CURRENTLY TRUE of the product is not
checkable by any test: both copies were in perfect agreement while both were
three majors out of date. That is a judgement a reader makes at release, and
`CONTRIBUTING.md`'s release process is where it is asked for.

That last claim was measured rather than assumed. Reverting BOTH copies to the
1.x sentence leaves this module green, which is the whole reason the description
went three majors without anybody noticing.

**`.15` (BDL-UX #211): the check's population was smaller than the fact's, and
it printed the same word as a complete check.** Agreement between the manifest
and the package docstring is real, but those two were never the whole
population. Measured on the PUBLISHED 3.0.1 wheel: `importlib.metadata` carried
the current sentence while line 3 of `beadloom --help` still read
``Beadloom - Context Oracle + Doc Sync Engine.`` Swept afterwards, the retired
sentence stood in FIVE live surfaces rather than the four the hand-off named --
the fifth being this repository's own `.beadloom/README.md`, scaffolded by
`init` from the same template that carried it.

**So this module now sweeps instead of naming copies.** `.4` wrote a
retired-phrase blocklist here and deleted it, correctly, because the phrase it
guarded (`Doc Sync v2 Engine`) lived in the graph root summary and never in a
guarded copy -- it could not have fired on what it guarded. That reasoning does
not carry to this sweep, and the difference is measurable rather than a matter
of taste: `Context Oracle + Doc Sync Engine` WAS in five guarded copies, so a
sweep for it would have gone red on the commit that missed them.

Three checks, three different failures, stated apart:

* :class:`TestNoShippedSurfaceStatesARetiredDescription` -- the past. A sweep
  for sentences the product has retired. This is the check whose absence let
  3.0.1 ship.
* :class:`TestEveryCopyOfTheDescriptionAgreesWithTheManifest` -- the future. A
  copy added later with a mangled variant is held to the manifest, without
  anybody having listed it.
* :class:`TestThePopulationIsStatedRatherThanAssumed` -- the population itself.
  The number of live copies is recorded, so growing it is a deliberate act that
  updates the record rather than a silent widening of what the check does not
  read. Modelled on `sync-check`'s "declared surface grew" line, for the same
  reason.
"""

from __future__ import annotations

import re
from pathlib import Path

import beadloom

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The manifest's `description` line. Read by pattern rather than by a TOML
#: parser because `tomllib` is 3.11+ and this project supports 3.10; the one
#: line this module is about is a plain top-level string, and the pattern is
#: anchored to the start of a line so a `description` indented under some other
#: table is not what it finds. The count is asserted, so a second top-level
#: `description` is a failure rather than a silent first match.
_DESCRIPTION_RE = re.compile(r'^description\s*=\s*"([^"]*)"', re.MULTILINE)


def _manifest_description() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    matches = _DESCRIPTION_RE.findall(text)
    assert len(matches) == 1, f"expected one top-level description, found {len(matches)}"
    description: str = matches[0]
    return description


def _docstring_description() -> str:
    """The package docstring's sentence, with its `Beadloom - ` prefix removed."""
    doc = beadloom.__doc__ or ""
    collapsed = re.sub(r"\s+", " ", doc).strip().rstrip(".")
    return re.sub(r"^Beadloom - ", "", collapsed)


class TestTheDescriptionIsWrittenOnceInEffect:
    def test_the_manifest_and_the_package_docstring_say_the_same_thing(self) -> None:
        manifest = _manifest_description()
        docstring = _docstring_description()
        assert docstring.casefold() == manifest.casefold(), (
            "pyproject.toml `description` and beadloom.__doc__ have drifted apart:\n"
            f"  manifest:  {manifest}\n"
            f"  docstring: {docstring}"
        )


# --------------------------------------------------------------------------
# `.15` -- the sweep. The population below is DERIVED by reading files, not by
# listing copies, so a surface nobody thought of is still judged.
# --------------------------------------------------------------------------

#: Sentences the product has retired. A live surface stating one of these is a
#: defect regardless of which file it is in. `Doc Sync v2 Engine` is kept even
#: though `.4` measured it out of the manifest: it lived in the graph root
#: summary until BDL-062 `.4`, and a retired phrase that is currently absent is
#: the cheapest possible check to keep -- while `TestThePopulationIsStated...`
#: is what reports a blocklist entry that has gone inert.
RETIRED_DESCRIPTIONS = (
    "Context Oracle + Doc Sync Engine",
    "Context Oracle + Doc Sync v2 Engine",
)

#: The directories the sweep reads: everything the project SHIPS or applies to
#: itself. Excluded, with the reason, because each is a record of history rather
#: than a statement about the product now:
#:   CHANGELOG.md              -- every release's description, by definition
#:   .claude/development/**    -- PRDs, RFCs and the BDL-UX log quote the defect
#:   .beads/**                 -- the tracker export quotes bead text verbatim
#:   site/, presentation/      -- generated or local-only
#:   this file                 -- it names the retired sentences in order to ban them
_SWEPT_ROOTS = ("src", ".beadloom", "docs", "README.md", "README.ru.md", "pyproject.toml")
_SWEPT_SUFFIXES = (".py", ".md", ".txt", ".toml", ".yml", ".yaml")
_SWEEP_EXCLUDED_PARTS = ("_graph",)


def _swept_files() -> list[Path]:
    """Every shipped text file the description could be stated in.

    Derived from the tree rather than listed, because a file added next year is
    exactly the case this sweep exists for. ``.beadloom/_graph`` is skipped: the
    node summaries there are checked by the ``graph_summary_facts`` rule against
    the project's computed facts, which is a different mechanism with a
    different failure, and reading them here would report one defect twice.
    """
    found: list[Path] = []
    for root in _SWEPT_ROOTS:
        target = REPO_ROOT / root
        if target.is_file():
            found.append(target)
            continue
        if not target.is_dir():
            continue
        for path in sorted(target.rglob("*")):
            if not path.is_file() or path.suffix not in _SWEPT_SUFFIXES:
                continue
            if any(part in _SWEEP_EXCLUDED_PARTS for part in path.relative_to(REPO_ROOT).parts):
                continue
            found.append(path)
    return found


def _read(path: Path) -> str:
    """Read a swept file, tolerating one that is not text after all."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _collapsed_with_line_map(text: str) -> tuple[str, list[int]]:
    """Whitespace-collapsed *text*, plus the source line number of each character.

    The sweep must read ACROSS line breaks. The description is one long
    sentence, so every prose copy of it wraps -- measured: a line-based sweep
    found it in 1 of the 5 surfaces that state it, and the four it missed
    included both copies `.4` had already corrected. A check that cannot see a
    correct copy cannot see an incorrect one either.
    """
    collapsed: list[str] = []
    lines: list[int] = []
    line = 1
    previous_was_space = True
    for char in text:
        if char == "\n":
            line += 1
        if char.isspace():
            if not previous_was_space:
                collapsed.append(" ")
                lines.append(line)
                previous_was_space = True
            continue
        collapsed.append(char)
        lines.append(line)
        previous_was_space = False
    return "".join(collapsed), lines


def _sweep_for(needle: str) -> list[tuple[str, int]]:
    """Every ``(relative_path, line_number)`` in the swept surface stating *needle*.

    *needle* is matched against the whitespace-collapsed file, so a sentence
    that wraps is found; the line number reported is where the match STARTS.

    The comparison is case-insensitive, matching the agreement test above. The
    package docstring writes the sentence with a lower-case first word because
    it follows ``Beadloom - ``, and a copy that differs only in that capital
    states the same claim. Measured: a case-sensitive sweep found 1 of the 5
    copies and missed one `.4` had already corrected.
    """
    wanted = re.sub(r"\s+", " ", needle).strip().casefold()
    hits: list[tuple[str, int]] = []
    for path in _swept_files():
        raw, line_of = _collapsed_with_line_map(_read(path))
        collapsed = raw.casefold()
        start = collapsed.find(wanted)
        while start != -1:
            hits.append((path.relative_to(REPO_ROOT).as_posix(), line_of[start]))
            start = collapsed.find(wanted, start + 1)
    return hits


#: How many live copies of the current description the swept surface holds.
#: Recorded so that growing the population is a deliberate act rather than a
#: silent widening of what this check does not read.
#:
#: Measured at `.15`. The fact's population was FIVE surfaces and the check read
#: TWO of them. Three were corrected by removing the copy rather than by editing
#: it: `_root.py` now derives `--help` from the package docstring, and the
#: scaffold template takes the sentence as a `{{beadloom_description}}`
#: placeholder the generator fills. So two literal copies remain -- the manifest
#: and the package docstring, which the agreement test above holds together --
#: plus this repository's own scaffolded `.beadloom/README.md`, which is
#: generator OUTPUT and is swept because an adopter's copy would be too.
EXPECTED_LIVE_COPIES = 3


class TestNoShippedSurfaceStatesARetiredDescription:
    """The check whose absence let 3.0.1 ship the 1.x sentence in `--help`."""

    def test_the_retired_sentences_are_gone_from_every_shipped_surface(self) -> None:
        swept = _swept_files()
        assert swept, "the sweep read no files at all, so it proves nothing"
        offenders = [
            (retired, where) for retired in RETIRED_DESCRIPTIONS for where in _sweep_for(retired)
        ]
        listed = "\n".join(
            f"  {path}:{line} states {retired!r}" for retired, (path, line) in offenders
        )
        assert not offenders, (
            f"{len(offenders)} shipped surface(s) of {len(swept)} swept still state a retired "
            f"description:\n{listed}\n"
            "Each is a sentence the product no longer answers 'what is Beadloom' with."
        )


class TestEveryCopyOfTheDescriptionAgreesWithTheManifest:
    """A copy added later is held to the manifest without anybody listing it."""

    def test_the_command_line_help_states_the_current_description(self) -> None:
        from click.testing import CliRunner

        from beadloom.services.commands._root import main

        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0, result.output
        manifest = _manifest_description()
        collapsed = re.sub(r"\s+", " ", result.output)
        assert manifest.casefold() in collapsed.casefold(), (
            "`beadloom --help` does not state the manifest's description.\n"
            f"  manifest: {manifest}\n"
            f"  help said: {collapsed[:220]}"
        )


class TestThePopulationIsStatedRatherThanAssumed:
    """The number of copies is recorded, so widening it cannot happen quietly."""

    def test_the_swept_surface_holds_the_recorded_number_of_copies(self) -> None:
        manifest = _manifest_description()
        copies = _sweep_for(manifest)
        listed = "\n".join(f"  {path}:{line}" for path, line in copies)
        assert len(copies) == EXPECTED_LIVE_COPIES, (
            f"the description surface holds {len(copies)} copies, not the recorded "
            f"{EXPECTED_LIVE_COPIES}:\n{listed}\n"
            "A copy gained or lost is a change to what this check reads. Update "
            "EXPECTED_LIVE_COPIES and say in the commit which surface moved."
        )
