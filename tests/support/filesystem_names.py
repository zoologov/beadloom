"""Which names this image's filesystem can represent at all (BDL-061.42).

The guard's accepted path shape is **ambient by design**: ``flow-guards/SPEC.md``
says a well-formed edit target must be "encodable for this filesystem", and
:func:`beadloom.application.guards.paths.rejection_reason` implements that with
:func:`os.fsencode`, whose codec is ``sys.getfilesystemencoding()``. So the
accepted *set* is a property of the machine, not a constant — and that is the
correct design rather than a defect: a string the filesystem cannot encode names
no file, so a guard that "accepted" it would be reasoning about a write that can
never happen.

What that makes wrong is a **test** which hard-codes the answer a UTF-8
filesystem gives. Measured for BDL-061.42 on ``LC_ALL=C`` +
``PYTHONUTF8=0``/``PYTHONCOERCECLOCALE=0`` (a real Linux container, filesystem
encoding ``ascii``): rows asserting that ``src/файл.py``, an emoji or a homoglyph
directory are *accepted* failed — while the product's answer, "it cannot be
encoded for this filesystem", was right. The rows that use this module therefore
assert the answer that is true **on the image running them**, in both
directions, instead of skipping or being taught to expect the mangling.

The predicate deliberately does **not** call ``os.fsencode``: it asks the codec
named by ``sys.getfilesystemencoding()`` directly, so it cannot agree with the
code under test by sharing its defect (standing rule FAKES PROVE FAKES, applied
to a predicate rather than a double).

macOS/Windows note, since it decides where this module has any effect: CPython
forces a UTF-8 filesystem encoding there, so :func:`filesystem_can_name` returns
``True`` for every name and the rows below behave exactly as they always have.
It is the Linux legs of ``tests-locale`` that exercise the other branch.
"""

from __future__ import annotations

import os
import sys

#: Stated by the product when a name cannot be encoded for the filesystem; the
#: rows assert this fragment so that a *different* refusal cannot pass for it.
UNENCODABLE_FRAGMENT = "cannot be encoded for this filesystem"


def filesystem_encoding() -> str:
    """The codec this image encodes file names with."""
    return sys.getfilesystemencoding()


def filesystem_can_name(raw: str) -> bool:
    """True when *raw* can name a file on this image.

    ``surrogateescape`` is passed because it is the handler ``os.fsencode`` uses:
    a lone surrogate is how Python carries a byte no codec could decode, and such
    a name *does* round-trip to a real file. Only characters the codec genuinely
    cannot represent make this False.
    """
    try:
        raw.encode(filesystem_encoding(), "surrogateescape")
    except UnicodeEncodeError:
        return False
    return True


def as_the_process_receives(value: str) -> str:
    """*value*'s UTF-8 bytes, decoded the way CPython decodes argv and the environment.

    A fixture that hands a non-ASCII name to a subprocess — a branch name, an
    author, a directory to create — is really handing over BYTES: the terminal,
    the JSON payload or the harness encodes them (UTF-8 in every case here), and
    CPython decodes them again with the filesystem encoding and
    ``surrogateescape``. On a UTF-8 image that round trip is the identity, which
    is why passing the ``str`` straight through has always worked. On an image
    whose filesystem encoding cannot represent the name it is not: passing the
    ``str`` raises ``UnicodeEncodeError`` before the child is even spawned, while
    the real caller's bytes would have arrived intact and the file, branch or
    author would exist exactly as it does everywhere else.

    So this returns what a real process actually receives. It makes the fixture
    byte-faithful rather than image-dependent — measured for BDL-061.42: through
    the installed binary, ``--context path=src/файл.py`` is ACCEPTED under an
    ASCII locale (argv arrives surrogate-escaped and ``os.fsencode`` round-trips
    it), while the same string built inside the test process is refused. The
    tests were asserting the second, and only the first can happen in production.
    """
    return os.fsdecode(value.encode("utf-8", "surrogateescape"))


def unnameable_reason(raw: str) -> str:
    """Why a row was skipped/inverted, in words a reader can act on."""
    return (
        f"this image encodes file names as {filesystem_encoding()}, which cannot "
        f"represent {raw!r} — the name cannot exist here, so the behaviour this "
        "row is about does not arise"
    )
