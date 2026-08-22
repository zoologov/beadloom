"""The image's locale codec as a test *parameter* (BDL-061.37, reused by .40).

Why a double rather than an environment: measured on this macOS, ``LC_ALL=C
PYTHONUTF8=0 PYTHONCOERCECLOCALE=0`` still reports preferred encoding ``utf-8``
(PEP 538/540 coercion), and patching ``locale.getpreferredencoding`` does **not**
reach ``TextIOWrapper``, which resolves the locale codec below Python. So an
ambient non-UTF-8 codec cannot be *arranged* from a test on this machine; it is
*constructed* here instead, by re-implementing CPython's documented text-mode
rule with the codec as an argument.

Standing rule 4 ("a test on a fake proves the fake's contract") is answered, not
argued around: every module that uses these rows also carries a row against the
real ``git`` binary, driven by bytes that are undecodable under *any* codec.

Extracted from ``tests/test_guard_probes_encoding.py`` when a second module
(``tests/test_decoding_symmetry.py``) needed the identical double — one
definition, so the two modules cannot drift into disagreeing about what "the
image decides" means.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

    import pytest

#: Every ambient codec the sweep is measured against. ``latin-1`` decodes every
#: byte and so *corrupts silently*; ``ascii`` refuses and so *raises*. Both are
#: real images (an ISO-8859-1 desktop, a bare ``LC_ALL=C`` container).
AMBIENT_CODECS = ("utf-8", "latin-1", "ascii")


class AmbientTextMode:
    """``subprocess.run`` as it behaves on an image whose locale codec is *ambient*.

    CPython's rule, quoted from the ``subprocess`` docs: the streams "will be
    opened in text mode using the encoding and errors of the ``encoding`` and
    ``errors`` arguments, or ``locale.getpreferredencoding(False)`` if neither is
    given". This implements exactly that and nothing else — the child is the real
    one, the pipe is the real one, only the *choice of codec* is injected. A call
    that states its own ``encoding``/``errors`` is decoded with those, which is
    what makes the fix visible: after it, the ambient codec has no say.
    """

    def __init__(self, ambient: str) -> None:
        self._ambient = ambient
        self._real = subprocess.run

    def __call__(self, argv: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        encoding = kwargs.pop("encoding", None)
        errors = kwargs.pop("errors", None)
        text = kwargs.pop("text", None)
        completed = self._real(argv, **kwargs)  # bytes: text mode is emulated here
        if encoding is None and not text:
            return completed
        codec = encoding or self._ambient
        handler = errors or "strict"
        return subprocess.CompletedProcess(
            completed.args,
            completed.returncode,
            completed.stdout.decode(codec, handler),
            completed.stderr.decode(codec, handler),
        )


def under_ambient_codec(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType, codec: str
) -> None:
    """Run *module*'s subprocess calls as if the image's locale codec were *codec*."""
    monkeypatch.setattr(module.subprocess, "run", AmbientTextMode(codec))
