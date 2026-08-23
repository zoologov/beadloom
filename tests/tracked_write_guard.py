"""Fail the test that writes to a git-TRACKED file of the repository under test.

Why this exists, measured rather than argued
--------------------------------------------
BDL-UX #177 was traced to a **test**: ``TestSyncAgenticFlow`` called
``sync_agentic_flow`` against this repo's live ``.claude/``, which rewrote the
shipped ``CLAUDE.md`` package template from one project's local file — and the
test PASSED while doing it. ``pytest`` runs inside ``beadloom ci`` and ``beadloom
ci`` runs on every push, so the propagation repeated on every commit and shipped
a project-local paragraph to adopters.

The class of defect is "the measurement mutates what it measures", the same one
as a lint that writes its own index (BDL-UX #147). It is invisible to
``git status`` whenever the write happens to be byte-identical, which is exactly
why it survived: the remaining four ``agents/*.md.txt`` writes were idempotent on
an unchanged tree and left no trace — until somebody edited a live role file,
after which one red run and one green run put the edit in the shipped artifact
(measured in a clean room at HEAD: template sha ``77dfc84…`` → ``b8bf376…``, run
1 failed, run 2 passed with the edit inside the package).

So the property is enforced structurally instead of by review: a test may write
anywhere it likes — ``tmp_path``, a temp git repo, the index under
``.beadloom/`` — but not to a file this repository tracks in git.

Honest limits, because a guard that overstates its reach is the thing it guards
against:

* it sees the Python-level write surface listed in :data:`_PATCHED_OPERATIONS`;
  a write through a C extension, an editor subprocess or ``git`` itself is not
  visible to it;
* it needs ``git ls-files`` to know what "tracked" means. In a clean room (a
  ``git archive`` extraction has no ``.git``) there is no tracked set, the guard
  is INERT, and it says so once per session rather than reporting a silent pass;
* it is measured on macOS + CPython 3.13 only. The path arithmetic is
  separator-normalised and the tracked set is decoded independently of the
  ambient locale, but ONE PLATFORM IS NOT VERIFIED: another OS is unknown until
  CI runs it.
"""

from __future__ import annotations

import builtins
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

#: The write operations the guard intercepts. Named here so the docstring's
#: claim about its reach is a list somebody can check, not an adjective.
_PATCHED_OPERATIONS: tuple[str, ...] = (
    "builtins.open",
    "Path.open",
    "Path.write_text",
    "Path.write_bytes",
    "Path.touch",
    "Path.unlink",
    "Path.rename",
    "Path.replace",
    "os.replace",
    "os.rename",
    "os.remove",
    "os.unlink",
    "shutil.copyfile",
    "shutil.copy",
    "shutil.copy2",
    "shutil.move",
    "shutil.rmtree",
    "shutil.copytree",
)

_WRITE_MODE_CHARS = ("w", "a", "x", "+")


def _absolute(raw: str) -> str:
    """``raw`` as a normalised absolute path string, without touching the disk."""
    if not os.path.isabs(raw):  # noqa: PTH117 - see relpath(): string-level on purpose
        raw = os.path.join(os.getcwd(), raw)  # noqa: PTH109,PTH118 - same reason
    return os.path.normpath(raw)


def _is_write_mode(mode: object) -> bool:
    return isinstance(mode, str) and any(c in mode for c in _WRITE_MODE_CHARS)


def tracked_files(root: Path) -> frozenset[str]:
    """Project-relative paths git tracks in ``root`` (empty when git cannot answer).

    Empty is a legitimate answer — a clean-room extraction has no ``.git`` — and
    the caller is expected to report the guard as inert rather than as clean.
    """
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(root), "ls-files", "-z"],  # noqa: S607 - git on PATH
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    # Decoded here rather than by `text=True`: the ambient codec of a C-locale
    # image would mangle a non-ASCII tracked path into one the guard could never
    # match, and a guard that quietly stops covering a file is this epic's own
    # subject (BDL-061 `.37`). `surrogateescape` round-trips whatever git emits,
    # and matches how `os.fspath` hands the same bytes back.
    names = completed.stdout.decode("utf-8", "surrogateescape")
    return frozenset(p for p in names.split("\0") if p)


class TrackedWriteGuard:
    """Records every write attempt against a tracked file of ``root``."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self._prefix = str(self.root) + os.sep
        self.tracked = tracked_files(self.root)
        #: ``{relpath: [operation, ...]}`` recorded since the last :meth:`take`.
        self.hits: dict[str, list[str]] = {}
        self._originals: dict[str, Any] = {}

    @property
    def inert(self) -> bool:
        """True when the guard cannot fire, whatever a test does."""
        return not self.tracked

    @property
    def inert_reason(self) -> str:
        return (
            f"no git-tracked files under {self.root} — `git ls-files` returned "
            "nothing (a clean-room extraction has no .git), so the tracked-write "
            "guard cannot fire and this run does not answer for it"
        )

    # -- recording ---------------------------------------------------------

    def relpath(self, path: object) -> str | None:
        """Project-relative path of ``path`` when it names a TRACKED file."""
        try:
            raw = os.fspath(path)  # type: ignore[arg-type]
        except TypeError:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        # String arithmetic, deliberately: this runs on every `open()` in a
        # ~6000-test suite and must classify paths that do not exist yet, which
        # is what `Path.resolve()` costs and `Path.relative_to` raises over.
        absolute = _absolute(raw)
        if not absolute.startswith(self._prefix):
            return None
        rel = absolute[len(self._prefix) :].replace(os.sep, "/")
        return rel if rel in self.tracked else None

    def note(self, path: object, operation: str) -> None:
        rel = self.relpath(path)
        if rel is None:
            return
        operations = self.hits.setdefault(rel, [])
        if operation not in operations:
            operations.append(operation)

    def note_tree(self, path: object, operation: str) -> None:
        """Record every tracked file under ``path`` (for whole-tree operations)."""
        try:
            raw = os.fspath(path)  # type: ignore[arg-type]
        except TypeError:
            return
        absolute = _absolute(str(raw))
        if not absolute.startswith(self._prefix):
            return
        rel_root = absolute[len(self._prefix) :].replace(os.sep, "/")
        for candidate in self.tracked:
            if candidate == rel_root or candidate.startswith(rel_root + "/"):
                self.note(self.root / candidate, operation)

    def take(self) -> dict[str, list[str]]:
        """Return and clear what has been recorded."""
        recorded, self.hits = self.hits, {}
        return recorded

    def describe(self, recorded: dict[str, list[str]]) -> str:
        """The failure message — names the files, the operations and the rule."""
        lines = [
            "this test wrote to file(s) this repository TRACKS in git:",
            *(f"  - {rel} via {', '.join(ops)}" for rel, ops in sorted(recorded.items())),
            "",
            "A test that mutates the tree it measures cannot be trusted about it "
            "(BDL-UX #147, #177): the write is invisible to `git status` whenever it "
            "is byte-identical, and it ships whatever it is not. Write to `tmp_path` "
            "instead, or redirect the target (e.g. monkeypatch the function that "
            "resolves the destination directory).",
        ]
        return "\n".join(lines)

    # -- patching ----------------------------------------------------------

    def install(self) -> None:
        """Wrap the write surface. Idempotent; safe to call once per session."""
        if self._originals:
            return
        guard = self

        original_open: Callable[..., Any] = builtins.open
        self._originals["builtins.open"] = original_open

        def _open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
            if _is_write_mode(mode):
                guard.note(file, f"open({mode})")
            return original_open(file, mode, *args, **kwargs)

        builtins.open = _open  # type: ignore[assignment]

        def _wrap_method(owner: Any, name: str, label: str, mode_arg: bool = False) -> None:
            original = getattr(owner, name)
            self._originals[label] = original

            def _wrapper(self_or_path: Any, *args: Any, **kwargs: Any) -> Any:
                if mode_arg:
                    mode = args[0] if args else kwargs.get("mode", "r")
                    if _is_write_mode(mode):
                        guard.note(self_or_path, f"{label}({mode})")
                else:
                    guard.note(self_or_path, label)
                return original(self_or_path, *args, **kwargs)

            setattr(owner, name, _wrapper)

        _wrap_method(Path, "open", "Path.open", mode_arg=True)
        _wrap_method(Path, "write_text", "Path.write_text")
        _wrap_method(Path, "write_bytes", "Path.write_bytes")
        _wrap_method(Path, "touch", "Path.touch")
        _wrap_method(Path, "unlink", "Path.unlink")

        def _wrap_two_ended(owner: Any, name: str, label: str, *, src_moves: bool) -> None:
            """Wrap a ``(src, dst)`` operation.

            ``src_moves`` distinguishes a copy from a move: reading a tracked
            file as a copy SOURCE is not a write, and counting it would fail
            every test that snapshots the shipped templates into ``tmp_path`` —
            a guard whose false positives outnumber its findings gets switched
            off, which is the failure mode it exists to prevent.
            """
            original = getattr(owner, name)
            self._originals[label] = original

            def _wrapper(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
                guard.note(dst, f"{label}(dst)")
                if src_moves:
                    guard.note(src, f"{label}(src)")
                return original(src, dst, *args, **kwargs)

            setattr(owner, name, _wrapper)

        _wrap_two_ended(Path, "rename", "Path.rename", src_moves=True)
        _wrap_two_ended(Path, "replace", "Path.replace", src_moves=True)
        _wrap_two_ended(os, "replace", "os.replace", src_moves=True)
        _wrap_two_ended(os, "rename", "os.rename", src_moves=True)
        _wrap_two_ended(shutil, "move", "shutil.move", src_moves=True)
        _wrap_two_ended(shutil, "copyfile", "shutil.copyfile", src_moves=False)
        _wrap_two_ended(shutil, "copy", "shutil.copy", src_moves=False)
        _wrap_two_ended(shutil, "copy2", "shutil.copy2", src_moves=False)

        def _wrap_single(owner: Any, name: str, label: str) -> None:
            original = getattr(owner, name)
            self._originals[label] = original

            def _wrapper(path: Any, *args: Any, **kwargs: Any) -> Any:
                guard.note(path, label)
                return original(path, *args, **kwargs)

            setattr(owner, name, _wrapper)

        _wrap_single(os, "remove", "os.remove")
        _wrap_single(os, "unlink", "os.unlink")

        def _wrap_tree(owner: Any, name: str, label: str, dst_index: int) -> None:
            original = getattr(owner, name)
            self._originals[label] = original

            def _wrapper(*args: Any, **kwargs: Any) -> Any:
                if len(args) > dst_index:
                    guard.note_tree(args[dst_index], label)
                return original(*args, **kwargs)

            setattr(owner, name, _wrapper)

        _wrap_tree(shutil, "rmtree", "shutil.rmtree", 0)
        _wrap_tree(shutil, "copytree", "shutil.copytree", 1)

    def uninstall(self) -> None:
        """Restore every wrapped callable (used by the guard's own tests)."""
        for label, original in self._originals.items():
            owner_name, attribute = label.rsplit(".", 1)
            owner = {"builtins": builtins, "Path": Path, "os": os, "shutil": shutil}[owner_name]
            setattr(owner, attribute, original)
        self._originals = {}
