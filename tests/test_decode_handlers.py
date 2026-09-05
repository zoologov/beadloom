"""The decode family, and the two mechanisms that make the next instance fail (BDL-061.68).

THE FINDING IS NOT A BUG, IT IS A REPEAT. One shape has been repaired five
times in this epic: *text decoded without an explicit rule, behind a handler
narrower than what the call can raise.* ``beadloom-mr2l.36`` found two
instances, ``.37`` the tracker probes, ``.40`` four call sites, ``.42`` swept
about forty — and then ``doc_sync/doc_quality.py``, written **after** all four,
took the whole ``docs quality`` gate down the same way (``.66``). Nobody was
careless. The knowledge simply did not reach the next author, and it never
will; only a mechanism can.

TWO HALVES, because one call site can be wrong in two independent ways and no
single check sees both.

**Half one — the codec is stated.** ``Path.read_text()``, ``open()`` in text
mode and ``subprocess(text=True)`` all default to
``locale.getpreferredencoding(False)``, so on a non-UTF-8 image they decode our
own artifacts with the operator's codec. ruff's ``PLW1514``
(``unspecified-encoding``) is this check, it is one line of configuration, and
it needed **no** code change to switch on: ``.42``'s sweep had already paid the
whole debt. It closes less of that half than its name suggests, and the limit
was measured rather than assumed — the rule reports ``read_text`` only where it can
infer the receiver is a ``Path``, and it does not look at
``subprocess(text=True)`` at all, so ``.42``'s receiver-agnostic AST sweep is
still what covers the package and ``PLW1514`` is what covers ``tests/``.
:class:`TestTheEncodingRuleIsSelectedAndBites` holds both the rule and that
boundary in place — see its docstring for the false green it exists to catch.

**Half two — the handler is as wide as the call.** No linter checks *"the
except clause covers what the try body can raise"*, and a stated encoding does
not make the read total: ``read_text(encoding="utf-8")`` still raises
``UnicodeDecodeError`` on a byte that is not UTF-8. ``except OSError`` around
it is a handler that catches the file being absent and not the file being
unreadable. :func:`test_every_narrow_handler_is_judged` is an AST ledger of
every such block in the package.

WHY A LEDGER AND NOT A VERDICT. Twenty-eight blocks match today (measured, see
below). They are **not** twenty-eight defects: each needs ``.42``'s per-site
judgement — is this stream a UTF-8 *contract* (a planning document, an index we
wrote, our own YAML) or the user's locale, and what is the honest behaviour
when it cannot be decoded? That judgement is ``beadloom-mr2l.67``'s, one site
at a time. What this file buys in the meantime is the difference between an
accident and a decision on the record: every existing block is listed with the
stream it reads and the reason it is still here, a **new** one fails the suite,
and a listed one that is fixed or moved fails the suite too, so ``.67`` cannot
close a site without deleting its row.

WHAT KEEPS THE LEDGER FROM GOING VACUOUS, which is the failure mode this epic
has now watched four times (a skip-list, a rule-liveness check, a pin table and
an anti-vacuity guard, each narrower than its own sentence):

1. **It keys on the CALL, never on the exception name.** Review ``.15`` M7
   recorded how the ``sys.platform`` ledger in :mod:`tests.test_windows_dimension`
   was evaded in one line: it looks for conditions that *name* ``sys.platform``,
   so anything spelled differently walks past. ``read_text`` cannot be renamed
   away, and the caught set is read as *evidence*, not as the key.
2. **The verdict is taken over the whole ``try``, not one handler.** A narrow
   ``except OSError`` beside an ``except Exception`` is covered, and flagging it
   would put a non-defect on the ledger — which is how a ledger stops being read.
3. **A call that cannot raise is not a site.** ``errors="replace"`` decides the
   question at the call, and two of ``.66``'s twenty-nine are exactly that
   (``context_oracle/test_mapper.py``). A ledger that lists them is asking for a
   judgement that has already been made.
4. **``contextlib.suppress`` and ``subprocess(text=True)`` are in the
   definition**, though neither matches anything in ``src/`` today. The first is
   the one-line escape from a ``try``-only scan; the second is the shape
   ``.40`` actually found in ``infrastructure/git_activity.py``
   (``UnicodeDecodeError`` past ``except (OSError, SubprocessError)``). Both are
   held open by planted fixtures in :class:`TestTheScanItselfBites`, so a leg
   that matches nothing cannot rot unnoticed.
5. **The population is asserted, not the guilt.** ``.67`` will drive the narrow
   count to zero, and a guard that reads "the scan must find something wrong"
   would then redden on success. :func:`test_the_scan_reads_a_live_population`
   asserts instead that modules are parsed and that guarded decoding blocks
   exist — the denominator, which survives the fix.

MEASURED ON THIS TREE (commit ``30cf11f`` plus this slice): 203 modules parsed
— the same 203 ``mypy --strict`` reports — 55 ``try``/``suppress`` blocks whose
body decodes text, and 28 of them narrow.

``.66``'s prototype reported 29 over the same package. Its definition is not
reproduced here and the difference is not reconciled row by row, so neither
number should be quoted as *the* count: two of the rows ``.66`` listed
(``context_oracle/test_mapper.py``) read with ``errors="replace"`` and cannot
raise at all, and points 2 and 3 above move others in and out by design. The
count worth trusting is the one this file recomputes on every run.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.decoding_calls import (
    called_name,
    decoding_can_raise,
    is_text_open,
    is_text_subprocess,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_SRC_ROOT = _REPO_ROOT / "src" / "beadloom"

#: ruff ships in the same ``dev`` extra as pytest, so a process that can run
#: this module can run ruff. Asserting that beats skipping on it: a skip here
#: would be inert on every leg that has the tool and silent on every leg that
#: does not, which is the "skip that can never fail" this epic keeps removing.
_RUFF = Path(sys.executable).parent / "ruff"


def _run_ruff(*args: str) -> subprocess.CompletedProcess[str]:
    """ruff, driven with THIS project's configuration and nothing implicit."""
    assert _RUFF.exists(), (
        f"ruff is not installed beside {sys.executable}. It comes from the same "
        "`dev` extra as pytest, so this suite cannot be running without it — "
        "install with `uv sync --extra dev` rather than skipping the check."
    )
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [str(_RUFF), "check", "--config", str(_PYPROJECT), "--no-cache", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _plw1514_findings(*paths: Path) -> list[dict[str, object]]:
    """Every ``unspecified-encoding`` ruff reports for *paths*, as data."""
    completed = _run_ruff("--output-format", "json", *(str(p) for p in paths))
    reported = json.loads(completed.stdout or "[]")
    return [item for item in reported if item["code"] == "PLW1514"]


class TestTheEncodingRuleIsSelectedAndBites:
    """Half one, and the false green it would otherwise be.

    ``PLW1514`` is a **preview** rule in ruff 0.16.3. Selecting it without
    enabling preview is not an error and not a failure: ruff prints ``warning:
    Selection `PLW1514` has no effect because preview is not enabled`` on
    stderr and exits **0** (measured with ``--isolated``). A configuration line
    that reads as a gate while checking nothing is precisely the class BDL-UX
    #172/#173 are about, so the check here is not "the code appears in
    ``select``" but "ruff, run with this project's own configuration, reports a
    planted site".

    One honest caveat about that measurement on *this* tree: dropping ``preview``
    happens to redden ``ruff check`` anyway, because the ``RUF002`` ``noqa`` in
    ``tests/test_decoding_symmetry.py`` that preview mode requires would then go
    unused and ``RUF100`` fires. That coupling is an accident of one comment and
    would vanish with it, so the guarantee rests on the planted site below and
    not on it.
    """

    @pytest.fixture(autouse=True)
    def _planting_ground(self, tmp_path: Path) -> None:
        self._tmp = tmp_path
        self._planted = 0

    def _plant(self, source: str) -> Path:
        """Write *source* to a fresh module and hand back its path."""
        self._planted += 1
        path = self._tmp / f"planted_{self._planted}.py"
        path.write_text(source, encoding="utf-8")
        return path

    def test_a_read_without_an_encoding_is_reported(self) -> None:
        """The planted module is the whole proof: two calls, two findings."""
        planted = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p: Path) -> str:\n"
            "    first = p.read_text()\n"
            "    with p.open() as handle:\n"
            "        second = handle.read()\n"
            "    return first + second\n"
        )

        reported = _plw1514_findings(planted)

        assert [item["location"]["row"] for item in reported] == [5, 6], (
            "ruff run with this project's configuration did not report text I/O "
            "without an explicit `encoding=`. Either PLW1514 left "
            "[tool.ruff.lint] select, or preview was turned off underneath it — "
            "in which case `ruff check` still exits 0 and the gate is off.\n"
            f"reported: {reported}"
        )

    def test_a_stated_encoding_is_not_reported(self) -> None:
        """The other direction, so the rule is not simply refusing everything."""
        planted = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p: Path) -> str:\n"
            '    return p.read_text(encoding="utf-8")\n'
        )

        assert _plw1514_findings(planted) == []

    def test_the_package_and_the_suite_are_clean_under_it(self) -> None:
        """Enabling the rule cost no code change, and this is what says so.

        ``.42`` swept about forty call sites before this rule was ever run, so
        the population it guards was already at zero. That is why half one is
        one configuration line: it locks a state that was reached by hand, and
        the next ``read_text()`` without an encoding fails the lint job of every
        leg of every pull request.
        """
        reported = _plw1514_findings(_REPO_ROOT / "src", _REPO_ROOT / "tests")

        rendered = "\n".join(
            f"  {item['filename']}:{item['location']['row']} {item['message']}"
            for item in reported
        )
        assert not reported, f"text I/O with no stated codec:\n{rendered}"

    def test_the_reach_of_the_rule_is_the_one_that_was_measured(self) -> None:
        """``PLW1514`` needs to KNOW the receiver is a ``Path``, and often cannot.

        Found by sabotage, not by reading the documentation: planting
        ``path.read_text()`` in ``graph/linter.py`` behind an *unannotated*
        parameter left ``ruff check src/ tests/`` at exit 0, and only the
        BDL-061.42 AST sweep reddened. Annotating the same parameter ``path:
        Path`` made ruff report it. ``open()`` has no receiver to infer and is
        reported either way.

        THE CONSEQUENCE IS WHY TWO INSTRUMENTS EXIST. Over ``src/`` the reach is
        broad because ``mypy --strict`` makes annotations mandatory there. Over
        ``tests/`` — which nothing type-checks — it is partial, and the
        receiver-agnostic AST sweep is what actually covers the package. Anyone
        tempted to delete that sweep as redundant should redden this row first.

        If a later ruff widens the rule and this row fails, that is the good
        outcome and the answer is to re-scope the sweep deliberately, not to
        weaken the row.
        """
        unannotated = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p):\n"
            "    return p.read_text()\n"
        )
        annotated = self._plant(
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def read(p: Path) -> str:\n"
            "    return p.read_text()\n"
        )

        assert _plw1514_findings(unannotated) == [], (
            "ruff now reports a read_text() on an inferred-nothing receiver. The "
            "AST sweep's unique reach just shrank — re-scope it on purpose."
        )
        assert len(_plw1514_findings(annotated)) == 1

    def test_the_selection_is_not_inert(self) -> None:
        """The exact warning ruff prints when the rule is selected but asleep.

        Kept beside the planted-site test rather than instead of it: this one
        names the knob that went missing, and the planted site proves the rule
        actually runs. Either alone would have let the other's failure through.
        """
        completed = _run_ruff(str(_SRC_ROOT))

        assert "has no effect because preview is not enabled" not in completed.stderr, (
            "ruff says a selected rule is inert. `[tool.ruff.lint] preview` and "
            "`explicit-preview-rules` travel WITH the PLW1514 selection; "
            "removing either leaves a green lint that checks nothing.\n"
            f"{completed.stderr}"
        )


# --------------------------------------------------------------------------- #
# Half two — the handler as wide as the call.
# --------------------------------------------------------------------------- #

#: Catching any of these catches a ``UnicodeDecodeError``: the exception itself,
#: its base ``UnicodeError``, ``ValueError`` above that, or a blanket clause.
#: ``json.JSONDecodeError`` is deliberately NOT here — it is a *sibling*
#: subclass of ``ValueError``, so catching it catches nothing this file is about,
#: and reading it as wide would silently excuse a third of the ledger.
#: ``<bare except>`` is the label :func:`_caught_names` gives ``except:`` — it
#: catches everything, so it belongs here. ``ruff``'s E722 keeps it out of this
#: package, which is why the row that covers it is a planted fixture and not a
#: live site: a definition with a leg nothing exercises is a definition that
#: rots.
_WIDE_ENOUGH = frozenset(
    {
        "UnicodeDecodeError",
        "UnicodeError",
        "ValueError",
        "Exception",
        "BaseException",
        "<bare except>",
    }
)


@dataclass(frozen=True)
class DecodeBlock:
    """A ``try`` / ``suppress`` block whose body decodes text."""

    #: ``<package-relative path>::<enclosing scope>#<ordinal in that scope>``.
    #: Deliberately not a line number: a ledger keyed on lines reddens for every
    #: edit above a site, and a ledger that cries wolf is deleted.
    key: str
    #: What the body calls, so the ledger is keyed on the CALL and never on the
    #: exception name — an exception can be renamed away, ``read_text`` cannot.
    decodes: tuple[str, ...]
    #: The caught set exactly as the source spells it, kept as evidence: a site
    #: that changes what it catches must have its row restated.
    catches: str
    lineno: int


def _decoding_calls(body: list[ast.stmt]) -> tuple[str, ...]:
    """Labels for every call in *body* that decodes text and can fail doing so."""
    found: list[str] = []
    for statement in body:
        for node in ast.walk(statement):
            if not isinstance(node, ast.Call) or not decoding_can_raise(node):
                continue
            name = called_name(node)
            if name in {"read_text", "decode"}:
                found.append(f"{name}()")
            elif is_text_open(node):
                found.append("open()")
            elif is_text_subprocess(node):
                found.append(f"subprocess.{name}(text=True)")
    return tuple(sorted(set(found)))


def _caught_names(handler: ast.ExceptHandler) -> list[str]:
    if handler.type is None:
        return ["<bare except>"]
    if isinstance(handler.type, ast.Tuple):
        return [ast.unparse(element) for element in handler.type.elts]
    return [ast.unparse(handler.type)]


class _DecodeBlockFinder(ast.NodeVisitor):
    """Every guarded decoding block in one module, with what guards it."""

    def __init__(self, relative: str) -> None:
        self._relative = relative
        self._scope: list[str] = []
        self._seen: dict[str, int] = {}
        self.blocks: list[DecodeBlock] = []

    def _enter(self, node: ast.AST, name: str) -> None:
        self._scope.append(name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._enter(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter(node, node.name)

    def _record(self, node: ast.AST, decodes: tuple[str, ...], caught: list[str]) -> None:
        scope = f"{self._relative}::{'::'.join(self._scope) or '<module>'}"
        # The ordinal counts every guarded decoding block in the scope, not only
        # the narrow ones, so repairing the first does not renumber the second.
        self._seen[scope] = self._seen.get(scope, 0) + 1
        self.blocks.append(
            DecodeBlock(
                key=f"{scope}#{self._seen[scope]}",
                decodes=decodes,
                catches=", ".join(caught),
                lineno=getattr(node, "lineno", 0),
            )
        )

    def visit_Try(self, node: ast.Try) -> None:
        decodes = _decoding_calls(node.body)
        if decodes:
            self._record(node, decodes, [c for h in node.handlers for c in _caught_names(h)])
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            expression = item.context_expr
            if not isinstance(expression, ast.Call) or called_name(expression) != "suppress":
                continue
            decodes = _decoding_calls(node.body)
            if decodes:
                self._record(node, decodes, [ast.unparse(a) for a in expression.args])
        self.generic_visit(node)


def _blocks_in(source: str, relative: str) -> list[DecodeBlock]:
    finder = _DecodeBlockFinder(relative)
    finder.visit(ast.parse(source))
    return finder.blocks


def _is_narrow(block: DecodeBlock) -> bool:
    """A block is narrow when NO handler on it catches a decode failure.

    The verdict is taken over the whole ``try`` on purpose: ``except OSError``
    beside ``except Exception`` is covered, and listing it would put a
    non-defect on the ledger.
    """
    caught = {name.strip() for name in block.catches.split(",")}
    return not (caught & _WIDE_ENOUGH)


def _package_blocks() -> tuple[list[DecodeBlock], int]:
    """Every guarded decoding block in ``src/beadloom``, and the modules read."""
    blocks: list[DecodeBlock] = []
    modules = 0
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        modules += 1
        relative = path.relative_to(_SRC_ROOT).as_posix()
        blocks.extend(_blocks_in(path.read_text(encoding="utf-8"), relative))
    return blocks, modules


#: What retires every row below. One event, stated once: these twenty-eight are
#: one sweep, and ``beadloom-mr2l.67`` closes them one site at a time. The
#: mechanism that makes the entry be remembered is not this string — an ``until``
#: naming an event is prose nothing can check, as ``.beadloom/_graph/rules.yml``
#: says of its own exemptions — it is that a row whose site is fixed or moved
#: FAILS this file, so ``.67`` cannot close a site without deleting its row.
_JUDGED_BY_67 = "beadloom-mr2l.67 judges this site against BDL-061.42's framework"


@dataclass(frozen=True)
class NarrowDecode:
    """One decoding block whose handler is narrower than what its body can raise."""

    #: The stream, named specifically enough to decide the only question that
    #: matters: is this a UTF-8 CONTRACT (a file beadloom wrote) or somebody
    #: else's document? That fact is what ``.67`` judges on.
    reads: str
    #: The caught set as the source spells it. Machine-checked against the scan,
    #: so a site that is partly repaired cannot keep an unchanged row.
    catches: str
    #: What the handler answers today, and what happens instead when the bytes
    #: are not UTF-8. A row with no consequence named is a row nobody can act on.
    reason: str
    #: The event that retires the row.
    until: str


#: EVERY narrow decoding block in ``src/beadloom``, judged. A block that is not
#: here fails :func:`test_every_narrow_handler_is_judged`; a row whose block is
#: gone fails it too.
JUDGED_NARROW_DECODES: dict[str, NarrowDecode] = {
    "application/active_table/reconcile.py::_reconcile_one#1": NarrowDecode(
        reads="the epic's ACTIVE.md, a planning document beadloom itself rewrites",
        catches="OSError",
        reason=(
            "returns without touching the table, so an absent ACTIVE.md means 'nothing to "
            "reconcile'; a byte that is not UTF-8 leaves the function unhandled instead, in the "
            "middle of `beadloom active-sync`"
        ),
        until=_JUDGED_BY_67,
    ),
    "application/active_table/table.py::set_active_table_status#1": NarrowDecode(
        reads="the same ACTIVE.md, read to rewrite one status cell in its table",
        catches="OSError",
        reason=(
            "answers False, which the caller reads as 'no row updated'; an undecodable byte "
            "escapes rather than reaching that False, so a status write ends in a traceback"
        ),
        until=_JUDGED_BY_67,
    ),
    "application/debt_report/config.py::load_debt_weights#1": NarrowDecode(
        reads=(
            ".beadloom/config.yml, the only site on this ledger opened through open() rather than "
            "read_text()"
        ),
        catches="OSError, yaml.YAMLError",
        reason=(
            "warns and falls back to DebtWeights(), so an absent config and a malformed one both "
            "have an answer; a decode failure has none and escapes `beadloom debt`"
        ),
        until=_JUDGED_BY_67,
    ),
    "application/doctor.py::_check_agent_instructions#1": NarrowDecode(
        reads="CLAUDE.md, composed by beadloom and then edited by hand",
        catches="OSError",
        reason=(
            "logs at debug and checks whatever the other file holds, so one unreadable file still "
            "leaves a verdict; a decode failure escapes `beadloom doctor` before it"
        ),
        until=_JUDGED_BY_67,
    ),
    "application/doctor.py::_check_agent_instructions#2": NarrowDecode(
        reads="AGENTS.md, generated by beadloom from MCP_TOOL_CATALOG",
        catches="OSError",
        reason=(
            "the same debug-and-continue answer one branch down; because both reads sit in one "
            "function, an undecodable byte in EITHER file ends the whole agent-instructions "
            "check, not just its own half"
        ),
        until=_JUDGED_BY_67,
    ),
    "application/gate.py::_step_federate#1": NarrowDecode(
        reads="a satellite's export artifact, named to the federate step of the Gate",
        catches="OSError, json.JSONDecodeError",
        reason=(
            "turns an unreadable export into a failed GateStep naming the file, which is already "
            "the honest shape; a decode failure walks past it and out of `beadloom ci`, so the "
            "gate crashes where it was built to report"
        ),
        until=_JUDGED_BY_67,
    ),
    "application/guards/config.py::load_guards_config#1": NarrowDecode(
        reads=".beadloom/flow.yml, read on every guard invocation",
        catches="yaml.YAMLError",
        reason=(
            "raises GuardConfigError('invalid YAML'), a message the agent can act on; the caught "
            "set omits OSError too, so this row is narrow in two directions and a decode failure "
            "reaches the agent's hook as a bare traceback"
        ),
        until=_JUDGED_BY_67,
    ),
    "doc_sync/audit.py::FactRegistry::_parse_version#1": NarrowDecode(
        reads="a version-bearing manifest (pyproject.toml, package.json, Cargo.toml)",
        catches="OSError",
        reason=(
            "warns and answers None, so an unreadable manifest carries no version fact. MEASURED "
            "containment: the caller wraps this in `except Exception`, so a decode failure "
            "becomes 'Failed to parse version' — the fault here is silence, not a crash"
        ),
        until=_JUDGED_BY_67,
    ),
    "doc_sync/audit.py::FactRegistry::_parse_version#2": NarrowDecode(
        reads="a Python source file named by [tool.hatch.version], read for __version__",
        catches="OSError",
        reason=(
            "the dynamic-version branch has no answer of its own and falls through to the static "
            "search below; the same outer `except Exception` contains a decode failure, so a "
            "dynamically versioned project reports no version at all and says why to nobody"
        ),
        until=_JUDGED_BY_67,
    ),
    "doc_sync/doc_shape.py::_documents_by_node_kind#1": NarrowDecode(
        reads="a project document whose path the index declares",
        catches="OSError",
        reason=(
            "drops the document with `continue`, so it leaves the section-shape denominator "
            "silently. This is review .15's C1, and .66 reported it repaired: doc_shape.py was "
            "ADDED at 30cf11f carrying this handler, so the repair is not in the tree"
        ),
        until=_JUDGED_BY_67,
    ),
    # `doc_sync/engine.py::_resolve_reference_docs_dir#1` was judged here and is
    # gone: `beadloom-mr2l.75` collapsed three readers of the `docs_dir` key into
    # `infrastructure/doc_roots.resolve_docs_dir`, whose handler catches
    # `(OSError, UnicodeDecodeError, yaml.YAMLError)` and is therefore not narrow.
    # The row is removed rather than repointed, because this test fails on a row
    # with no block behind it — a list of exclusions that outlives the code it
    # excused reads as approval for something nobody checked.
    "doc_sync/surface.py::flow_signature#1": NarrowDecode(
        reads=".beadloom/flow.yml, canonicalised and hashed into the surface signature",
        catches="OSError, yaml.YAMLError",
        reason=(
            "answers the empty digest, which downstream reads as 'no flow configured'; a decode "
            "failure escapes instead, so surface drift cannot be computed at all"
        ),
        until=_JUDGED_BY_67,
    ),
    "doc_sync/surface_ledger.py::read_ledger#1": NarrowDecode(
        reads="the surface ledger JSON beadloom writes under .beadloom/",
        catches="OSError, json.JSONDecodeError",
        reason=(
            "answers None, meaning 'no ledger recorded yet', which every caller already handles; "
            "a file we wrote ourselves failing to decode escapes that path entirely"
        ),
        until=_JUDGED_BY_67,
    ),
    "graph/loader.py::_fold_graphql_surface#1": NarrowDecode(
        reads="a GraphQL SDL file the graph names in source_file, authored outside beadloom",
        catches="OSError",
        reason=(
            "records a warning naming the edge and folds `exposed: []`, so the graph still loads; "
            "a decode failure escapes the loader and takes `beadloom reindex` with it"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/config_sync.py::_adapter_drifts#1": NarrowDecode(
        reads="an IDE rules adapter file beadloom wrote (.cursor/rules and its siblings)",
        catches="OSError",
        reason=(
            "skips the file with `continue`, so an unreadable adapter reports no drift; the "
            "honest answer for text nobody could read is 'drift unknown', and the loop has no way "
            "to say it"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/config_sync.py::_agentic_flow_drifts#1": NarrowDecode(
        reads="a vendored role adapter beadloom wrote into the agent's own directory",
        catches="OSError",
        reason=(
            "the same `continue` one loop over, and it compares against a vendored asset, so a "
            "file that cannot be decoded is reported identical to the asset it may well differ "
            "from"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/config_sync.py::_agents_md_drift#1": NarrowDecode(
        reads="AGENTS.md as it stands on disk, compared against a regeneration held in memory",
        catches="OSError",
        reason=(
            "answers None, which the caller reads as 'no drift to report' — the worst available "
            "answer for an undecodable file, because the comparison it stands for never ran"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/config_sync.py::_claude_md_body_drift#1": NarrowDecode(
        reads="CLAUDE.md, read to find the composed-body marker that proves ownership",
        catches="OSError",
        reason=(
            "answers None, 'no drift', again; ownership is decided from a marker inside text "
            "nobody could read, so this site could not answer honestly even if it caught"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/flow_config.py::load_flow_config#1": NarrowDecode(
        reads=".beadloom/flow.yml, on the configuration path rather than the guard path",
        catches="yaml.YAMLError",
        reason=(
            "raises FlowConfigError('invalid YAML'), which the CLI renders as a message; the "
            "caught set omits OSError here too, and a decode failure arrives as an unnamed "
            "traceback out of config loading"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/flow_manifest.py::read_manifest#1": NarrowDecode(
        reads="the flow manifest JSON beadloom writes to record what it generated",
        catches="OSError, json.JSONDecodeError",
        reason=(
            "answers ({}, False) — an empty manifest explicitly marked NOT usable, which is the "
            "distinction the rest of onboarding turns on; a decode failure loses that flag by "
            "never producing it"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/flow_manifest.py::state_of#1": NarrowDecode(
        reads="a generated artifact on disk, read to classify it against the text expected there",
        catches="OSError",
        reason=(
            "treats the file as absent (on_disk=None), which classify() reports as missing; an "
            "undecodable artifact is a third state, and today it is neither reported nor "
            "reachable because the read escapes"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/guard_hooks.py::_load_settings#1": NarrowDecode(
        reads="the agent tool's own settings.json, authored outside beadloom",
        catches="OSError, json.JSONDecodeError",
        reason=(
            "answers None, which the caller distinguishes from {} as 'exists but unusable' — "
            "exactly the shape this family wants; a decode failure escapes before that "
            "distinction is ever reached"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/presets.py::detect_preset#1": NarrowDecode(
        reads="an adopter's package.json, read to detect a React Native or Expo project",
        catches="json.JSONDecodeError, OSError",
        reason=(
            "falls through to the next preset probe, so an unreadable manifest means only 'not "
            "this preset'; a decode failure escapes `beadloom init` on somebody else's "
            "repository, which is the widest blast radius on this ledger"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/scanner/claude_md.py::refresh_claude_md#1": NarrowDecode(
        reads="the adopter's CLAUDE.md, read to locate the composed markers before rewriting it",
        catches="OSError",
        reason=(
            "answers an empty change list, so nothing is rewritten; of every row here this one "
            "sits closest to a write, and a decode failure ends the refresh with the file's "
            "future undecided"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/scanner/project_scan.py::_detect_project_name#1": NarrowDecode(
        reads="an adopter's package.json, read for the project name",
        catches="json.JSONDecodeError, KeyError",
        reason=(
            "falls back to the directory name, so a missing name is not fatal; the caught set "
            "names no OSError at all, and only an is_file() check ahead of it keeps that second "
            "narrowness unreachable"
        ),
        until=_JUDGED_BY_67,
    ),
    "onboarding/scanner/project_scan.py::_read_manifest_deps#1": NarrowDecode(
        reads="the same package.json, read for `workspace:` and `file:` dependency links",
        catches="json.JSONDecodeError, KeyError",
        reason=(
            "returns the links collected so far, so a malformed manifest yields fewer edges "
            "rather than none; a decode failure ends the scan instead of shortening it"
        ),
        until=_JUDGED_BY_67,
    ),
    "services/commands/docsync.py::_has_active_table#1": NarrowDecode(
        reads="each candidate ACTIVE.md, read only to ask whether it carries a status table",
        catches="OSError",
        reason=(
            "skips the candidate with `continue` and keeps looking, so a question with a boolean "
            "answer always gets one; a decode failure turns that boolean into a traceback in the "
            "CLI"
        ),
        until=_JUDGED_BY_67,
    ),
    "services/commands/federation.py::_load_export_artifacts#1": NarrowDecode(
        reads="a satellite export artifact named on the `beadloom federate` command line",
        catches="OSError, json.JSONDecodeError",
        reason=(
            "prints 'Error: cannot read export <path>' and answers None, so the operator learns "
            "which file; a decode failure prints nothing and exits through a traceback"
        ),
        until=_JUDGED_BY_67,
    ),
}


def test_every_narrow_handler_is_judged() -> None:
    """The ledger and the package agree, in both directions.

    A new narrow block is a suite failure, which is the point of the file. A row
    with no block behind it is a failure as well, because that is how a list of
    exclusions outlives the code it excused and starts reading as approval for
    something nobody checked.
    """
    blocks, _ = _package_blocks()
    narrow = {block.key: block for block in blocks if _is_narrow(block)}

    unjudged = sorted(set(narrow) - set(JUDGED_NARROW_DECODES))
    stale = sorted(set(JUDGED_NARROW_DECODES) - set(narrow))
    rendered = "\n".join(
        f"    {key!r}: NarrowDecode(reads=..., catches={narrow[key].catches!r}, "
        f"reason=..., until=_JUDGED_BY_67),  # {narrow[key].decodes} at line "
        f"{narrow[key].lineno}"
        for key in unjudged
    )
    assert not unjudged and not stale, (
        "the decode ledger and src/beadloom disagree.\n"
        f"  narrow and unjudged ({len(unjudged)}):\n{rendered}\n"
        f"  judged but no longer narrow ({len(stale)}): {stale}\n"
        "A handler around a decoding read must catch what the read can raise "
        "(`read_text(encoding='utf-8')` raises UnicodeDecodeError on a byte "
        "that is not UTF-8, and `except OSError` is not that), or the site "
        "belongs in JUDGED_NARROW_DECODES with the stream it reads and the "
        "consequence of leaving it."
    )

    disagreed = {
        key: (entry.catches, narrow[key].catches)
        for key, entry in JUDGED_NARROW_DECODES.items()
        if entry.catches != narrow[key].catches
    }
    assert not disagreed, (
        "a judged site now catches something else, so its row describes code "
        f"that no longer exists — restate it: {disagreed}"
    )


def test_no_row_is_excused_without_a_reason_of_its_own() -> None:
    """An unnamed exclusion is how a gate is quietly switched off (CONTEXT.md).

    Uniqueness is the checkable part. Twenty-eight rows that read alike are a
    copy-paste, and a copy-pasted reason is the shape an exclusion list takes
    just before it stops being read; twenty-eight rows that name different
    streams and different consequences are a list somebody can work through.
    """
    empty = sorted(
        key
        for key, entry in JUDGED_NARROW_DECODES.items()
        if not entry.reads.strip() or not entry.reason.strip() or not entry.until.strip()
    )
    assert not empty, f"ledger rows with an empty field: {empty}"

    by_reason: dict[str, list[str]] = {}
    for key, entry in JUDGED_NARROW_DECODES.items():
        by_reason.setdefault(entry.reason, []).append(key)
    shared = {reason: keys for reason, keys in by_reason.items() if len(keys) > 1}
    assert not shared, (
        "these rows share one reason, so at least one of them was not judged: "
        f"{ {reason[:60]: keys for reason, keys in shared.items()} }"
    )


def test_the_package_uses_no_except_star_the_scan_would_walk_past() -> None:
    """The one escape this scan knows it does not cover, turned into a check.

    ``try/except*`` (PEP 654, Python 3.11) is a separate AST node, and
    :class:`_DecodeBlockFinder` visits ``Try`` only — so an ``except* OSError``
    around a ``read_text`` would be invisible. Today it cannot occur: ruff's
    ``target-version`` is ``py310`` and CI runs a 3.10 leg, where that syntax
    does not parse. Stating the limit in prose would leave it true until the day
    it silently was not, so it is asserted here instead: raise the target and
    this row fails, naming the scan that has to grow with it.
    """
    offending = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offending.extend(
            f"{path.relative_to(_SRC_ROOT).as_posix()}:{node.lineno}"
            for node in ast.walk(tree)
            if type(node).__name__ == "TryStar"
        )

    assert not offending, (
        "`except*` blocks the decode ledger cannot see, because "
        "_DecodeBlockFinder visits ast.Try and not ast.TryStar: "
        f"{offending}. Teach the finder the node before shipping these."
    )


def test_the_scan_reads_a_live_population() -> None:
    """The denominator, asserted — never the guilt.

    ``.67`` will drive the narrow count to zero, so "the scan must find
    something wrong" would redden on success and get deleted. What must stay
    true after ``.67`` is that the scan still parses the package and still finds
    blocks that guard a decoding read. If either goes to zero the instrument
    broke, whatever the ledger says.
    """
    blocks, modules = _package_blocks()

    assert modules > 100, f"only {modules} modules parsed under {_SRC_ROOT}"
    assert blocks, (
        "no try/suppress block in the package decodes text. Either the package "
        "stopped reading files, or the call set in tests/decoding_calls.py no "
        "longer recognises the calls it did — check before trusting the ledger."
    )


class TestTheScanItselfBites:
    """A ledger is worth exactly what its scan can still see.

    Each row here plants source and asks the finder for a verdict, so the two
    legs that match nothing in ``src/`` today — ``contextlib.suppress`` and
    ``subprocess(text=True)`` — are held open by something that fails when they
    break. A leg with no live instance and no fixture is a leg that quietly
    stops working, which is how ``.15`` M7 describes the ledger this one is
    modelled on.
    """

    def test_a_narrow_handler_around_a_read_is_found(self) -> None:
        blocks = _blocks_in(
            "def load(p):\n"
            "    try:\n"
            '        return p.read_text(encoding="utf-8")\n'
            "    except OSError:\n"
            "        return None\n",
            "planted.py",
        )

        assert [(b.key, b.decodes, b.catches, _is_narrow(b)) for b in blocks] == [
            ("planted.py::load#1", ("read_text()",), "OSError", True)
        ]

    def test_a_handler_that_catches_the_decode_failure_is_not_narrow(self) -> None:
        blocks = _blocks_in(
            "def load(p):\n"
            "    try:\n"
            '        return p.read_text(encoding="utf-8")\n'
            "    except (OSError, UnicodeDecodeError):\n"
            "        return None\n",
            "planted.py",
        )

        assert [_is_narrow(b) for b in blocks] == [False]

    def test_a_narrow_clause_beside_a_wide_one_is_covered(self) -> None:
        """The verdict is over the ``try``, so this is not a defect and not a row."""
        blocks = _blocks_in(
            "def load(p):\n"
            "    try:\n"
            '        return p.read_text(encoding="utf-8")\n'
            "    except OSError:\n"
            "        return None\n"
            "    except Exception:\n"
            "        raise\n",
            "planted.py",
        )

        assert [_is_narrow(b) for b in blocks] == [False]

    def test_a_read_that_cannot_raise_is_not_a_site_at_all(self) -> None:
        """``errors="replace"`` answers the question at the call site."""
        blocks = _blocks_in(
            "def load(p):\n"
            "    try:\n"
            '        return p.read_text(encoding="utf-8", errors="replace")\n'
            "    except OSError:\n"
            "        return None\n",
            "planted.py",
        )

        assert blocks == []

    def test_contextlib_suppress_is_the_same_shape_and_is_seen(self) -> None:
        """The one-line escape from a ``try``-only scan, closed."""
        blocks = _blocks_in(
            "import contextlib\n"
            "\n"
            "def load(p):\n"
            "    with contextlib.suppress(OSError):\n"
            '        return p.read_text(encoding="utf-8")\n'
            "    return None\n",
            "planted.py",
        )

        assert [(b.decodes, b.catches, _is_narrow(b)) for b in blocks] == [
            (("read_text()",), "OSError", True)
        ]

    def test_a_decoding_subprocess_is_seen(self) -> None:
        """BDL-061.40's git_activity defect, in its original shape.

        ``PLW1514`` does not cover ``subprocess`` — measured on ruff 0.16.3 — so
        if this leg stops working nothing else in the repository is looking.
        """
        blocks = _blocks_in(
            "import subprocess\n"
            "\n"
            "def log():\n"
            "    try:\n"
            '        return subprocess.run(["git"], text=True, check=False).stdout\n'
            "    except (OSError, subprocess.SubprocessError):\n"
            "        return None\n",
            "planted.py",
        )

        assert [(b.decodes, _is_narrow(b)) for b in blocks] == [
            (("subprocess.run(text=True)",), True)
        ]

    def test_a_bare_except_is_wide_enough_to_be_off_the_ledger(self) -> None:
        blocks = _blocks_in(
            "def load(p):\n"
            "    try:\n"
            '        return p.read_text(encoding="utf-8")\n'
            "    except:\n"
            "        return None\n",
            "planted.py",
        )

        assert [(b.catches, _is_narrow(b)) for b in blocks] == [("<bare except>", False)]

    def test_two_blocks_in_one_function_get_stable_ordinals(self) -> None:
        """Repairing the first must not renumber the second, or ``.67`` churns."""
        blocks = _blocks_in(
            "def load(p, q):\n"
            "    try:\n"
            '        a = p.read_text(encoding="utf-8")\n'
            "    except (OSError, UnicodeDecodeError):\n"
            "        a = ''\n"
            "    try:\n"
            '        b = q.read_text(encoding="utf-8")\n'
            "    except OSError:\n"
            "        b = ''\n"
            "    return a + b\n",
            "planted.py",
        )

        assert [(b.key, _is_narrow(b)) for b in blocks] == [
            ("planted.py::load#1", False),
            ("planted.py::load#2", True),
        ]

    def test_a_method_row_carries_its_class(self) -> None:
        blocks = _blocks_in(
            "class Registry:\n"
            "    def load(self, p):\n"
            "        try:\n"
            '            return p.read_text(encoding="utf-8")\n'
            "        except OSError:\n"
            "            return None\n",
            "planted.py",
        )

        assert [b.key for b in blocks] == ["planted.py::Registry::load#1"]
