"""The TOML reader the suite uses, on every interpreter it runs on.

``tomllib`` is in the standard library from Python 3.11; on 3.10 pytest
requires ``tomli``, so the else branch resolves on every leg that runs the suite.
The reader is selected on the VERSION and not by catching an ImportError, so
mypy analyses exactly one branch per ``--python-version`` (BDL-UX #227).
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from tomllib import loads as _toml_loads
else:
    from tomli import loads as _toml_loads


def toml_loads(text: str) -> dict[str, object]:
    """The TOML reader, with a stated return type at the untyped boundary."""
    data = _toml_loads(text)
    assert isinstance(data, dict)
    return data
