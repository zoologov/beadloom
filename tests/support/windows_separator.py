"""A relative path spelled the way Windows spells it, on a machine that is not Windows.

BDL-083 S2f (``beadloom-27br``, RFC D11, BDL-UX #353). On Windows ``str()`` of a relative
path joins its parts with a backslash, and ``as_posix()`` joins them with a forward slash.
The index used to store ``str(path.relative_to(root))``, so a Windows checkout held
``backend\\src\\digest\\sections.py`` where the graph declares ``backend/src/digest/``, and
every ``source:`` match missed. The Windows CI leg is withdrawn (BDL-074), so this module is
the measurement: :func:`spell_relative_paths_as_windows` makes every path that
``relative_to`` returns print with a backslash, and leaves ``as_posix()`` answering with a
forward slash, as it does on Windows.

**What it simulates, and what it does not.** Only the relative path. An absolute path still
prints as a POSIX path here, a drive letter is never seen, and ``os.sep`` is still ``/``, so
code that splits on ``os.sep`` or compares absolute strings is not exercised. The file
system is the real one: the simulated path hands the operating system its real spelling, so
a file opened through it is the file it names. A green under this simulation is a claim
about the write sites and the match sites of the index, and not a claim about Windows.
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

#: The concrete path class of this platform, which the simulated spelling derives from.
_NATIVE = type(pathlib.Path())

#: ``relative_to`` as this platform defines it, captured before any patch.
_NATIVE_RELATIVE_TO = pathlib.PurePath.relative_to


class WindowsSpelledPath(_NATIVE):  # type: ignore[misc,valid-type]  # a runtime-chosen base
    """A relative path that prints with backslashes and still opens the file it names."""

    def __str__(self) -> str:
        return _NATIVE.__str__(self).replace("/", "\\")

    def __fspath__(self) -> str:
        return _NATIVE.__str__(self)

    def as_posix(self) -> str:
        return _NATIVE.__str__(self)


def _relative_to(self: pathlib.PurePath, *args: Any, **kwargs: Any) -> pathlib.PurePath:
    return WindowsSpelledPath(_NATIVE_RELATIVE_TO(self, *args, **kwargs))


def spell_relative_paths_as_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every ``relative_to`` result print with a backslash until the test ends."""
    monkeypatch.setattr(pathlib.PurePath, "relative_to", _relative_to)
