"""Can THIS process create a symlink — measured, not assumed (BDL-061.39).

WHY THIS REPLACES ``skipif(sys.platform == "win32")``. Six guard tests were
skipped on Windows with the reason "POSIX symlink semantics". That reason names
the wrong obstacle, and naming it wrongly is what made the skip permanent:

* Windows **has** symbolic links (NTFS reparse points, ``os.symlink`` since
  Python 3.2 with the ``target_is_directory`` argument these tests already
  pass), and ``Path.resolve`` follows them there exactly as it does here. The
  *semantics* the six tests assert — a resolved target is the file the writer
  will touch, so an exclusion follows the link rather than the spelling — are
  not POSIX-specific at all.
* What a Windows process may lack is the **privilege to create one**
  (``SeCreateSymbolicLinkPrivilege``), granted by Developer Mode or by an
  elevated shell. That is a property of the *process*, it varies between two
  Windows machines, and it is decidable in about a millisecond.

So the skip is taken on the measured refusal, and it carries the operating
system's own error text. Three consequences, all of them the point:

1. On a runner that has the privilege the six tests RUN — which is the whole
   reason a ``windows-latest`` leg is worth paying for. A leg that merely
   re-skips them would buy a green check that proves nothing.
2. If the privilege is missing the skip says so **in the words of the failure**,
   so the reader can act (enable Developer Mode) instead of concluding that
   Windows is out of scope.
3. It also covers cases nobody had thought about — a POSIX filesystem mounted
   without symlink support, a container with restricted capabilities — where the
   old mark would have produced a confusing hard failure rather than a skip.

FAKES PROVE FAKES, applied to a predicate: the probe does not ask
``sys.platform`` or ``os.name`` anything. It creates a real link in a real
temporary directory and reads it back, so it cannot agree with a wrong platform
assumption by sharing it.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SymlinkCapability:
    """What this process could actually do, and what stopped it if it could not."""

    #: A link to a regular file could be created and read back.
    files: bool
    #: A link to a directory could be created and read back. Separate from
    #: :attr:`files` because Windows needs ``target_is_directory=True`` and
    #: treats a directory link as a distinct object (a junction-like reparse
    #: point), so one can be available while the other is not.
    directories: bool
    #: The operating system's own words for the refusal, or ``""`` when nothing
    #: refused. Carried into the skip reason so it is a measurement a reader can
    #: act on rather than a platform name.
    refusal: str

    @property
    def both(self) -> bool:
        """True when every link shape the guard tests need is available."""
        return self.files and self.directories


def _probe() -> SymlinkCapability:
    """Create one file link and one directory link, and report what happened."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target_file = root / "target.txt"
        target_file.write_text("probe\n", encoding="utf-8")
        target_dir = root / "target-dir"
        target_dir.mkdir()

        files, first = _can_link(root / "link.txt", target_file, is_dir=False)
        directories, second = _can_link(root / "link-dir", target_dir, is_dir=True)
    return SymlinkCapability(
        files=files, directories=directories, refusal=first or second
    )


def _can_link(link: Path, target: Path, *, is_dir: bool) -> tuple[bool, str]:
    """Make *link* point at *target* and read it back; never raise."""
    try:
        # PTH211 (`Path.symlink_to`) is declined deliberately: this
        # function's whole purpose is to MEASURE what `os.symlink` does, and
        # putting pathlib between the measurement and the syscall would mean the
        # probe and ci.yml's Windows probe (which cannot import this module) no
        # longer call the same thing.
        os.symlink(target, link, target_is_directory=is_dir)  # noqa: PTH211
    except (OSError, NotImplementedError, AttributeError) as exc:
        # OSError covers the Windows privilege refusal (WinError 1314) and a
        # filesystem that does not support links (EPERM/ENOSYS); the other two
        # cover an implementation that does not offer os.symlink at all.
        return False, f"{type(exc).__name__}: {exc}"
    try:
        resolved = link.resolve()
    except OSError as exc:  # a link that exists but cannot be followed
        return False, f"{type(exc).__name__}: {exc}"
    if resolved != target.resolve():
        return False, (
            f"a link was created but resolved to {resolved} instead of {target}"
        )
    return True, ""


#: Measured once per session — the probe touches the disk, and every mark in the
#: suite asks the same question of the same process.
SYMLINK_CAPABILITY = _probe()

#: The condition the six former ``skipif(win32)`` guard tests are marked with.
SYMLINKS_UNAVAILABLE = not SYMLINK_CAPABILITY.both

#: What the reader is told when they are skipped. It names the measurement, not
#: a platform, so a machine that CAN link never sees it.
SYMLINK_SKIP_REASON = (
    "this process could not create a symbolic link, so the behaviour under test "
    f"cannot be set up here: {SYMLINK_CAPABILITY.refusal or 'no reason recorded'}"
    " (on Windows this is the SeCreateSymbolicLinkPrivilege — enable Developer "
    "Mode or run elevated; the semantics themselves are not POSIX-specific)"
)
