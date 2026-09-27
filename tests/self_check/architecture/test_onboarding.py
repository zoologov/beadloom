"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/integration/onboarding/scanner/test_onboarding.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

#: The real re-index, handed to `init` the way `beadloom init` hands it in.
#: Onboarding is a domain and the re-index is an application use case, so the
#: caller supplies it rather than the domain importing it (BDL-070
#: `beadloom-46am`). These tests assert what `init` does WITH a real index, so
#: they pass the real one and their behaviour is unchanged.
from beadloom.onboarding import (
    scan_project,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestScannerTypedDictShapes:
    """The TypedDict migration must preserve the runtime dict shape exactly.

    ``ScanResult`` / ``ClusterEntry`` are TypedDicts whose only job is to
    sharpen static typing; the produced mappings must still carry exactly the
    declared keys with the declared value types. These tests assert the runtime
    contract so a future field rename in the TypedDict (without a producer
    change, or vice-versa) is caught.
    """

    _SCAN_KEYS: ClassVar[set[str]] = {
        "manifests",
        "source_dirs",
        "file_count",
        "languages",
    }


    def test_live_repo_scan_has_typeddict_shape(
        self, self_check_snapshot: Path
    ) -> None:
        """A real-repo scan (read-only) still yields the exact ScanResult shape.

        scan_project only reads the filesystem, so this does not mutate the
        shared live DB; the fixture is reused per the bead's instruction.
        """
        result = scan_project(self_check_snapshot)
        assert set(result.keys()) == self._SCAN_KEYS
        assert isinstance(result["file_count"], int)
        assert result["file_count"] > 0
        assert "src" in result["source_dirs"]
        assert "pyproject.toml" in result["manifests"]
