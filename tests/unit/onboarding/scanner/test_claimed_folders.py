"""The directory reading of ``init`` leaves out only the folders another reading claims.

BDL-076 R2 finding 2 (``beadloom-fht7``), fixed by ``beadloom-ujzb.19``. The JVM and
Swift layout readers account for a module's or a package's folder; until this fix the
directory clustering and the scan paths dropped the whole TOP-LEVEL folder holding it,
so a Python or TypeScript service beside it in ``services/`` or ``apps/`` vanished.
These tests hold the two subtractions on their own: the clusters and the scan paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.project_scan import (
    _cluster_with_children,
    is_claimed,
    unclaimed_folders,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, *paths: str) -> None:
    for rel_path in paths:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n", encoding="utf-8")


class TestIsClaimed:
    def test_the_folder_itself_and_anything_below_it(self) -> None:
        assert is_claimed("services/billing", {"services/billing"})
        assert is_claimed("services/billing/src/A.java", {"services/billing"})

    def test_not_a_sibling_sharing_a_prefix_nor_the_parent(self) -> None:
        assert not is_claimed("services/billing-api", {"services/billing"})
        assert not is_claimed("services", {"services/billing"})
        assert not is_claimed("services/notify", {"services/billing"})


class TestTheClustersLeaveOutOnlyTheClaimedFolders:
    def test_a_sibling_of_a_claimed_folder_is_still_a_cluster(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "services/billing/src/main/java/A.java",
            "services/notify/notify/__init__.py",
            "services/notify/sender/mail.py",
        )

        clusters = _cluster_with_children(
            tmp_path, source_dirs=["services"], claimed={"services/billing"}
        )

        assert list(clusters) == ["notify"]
        assert set(clusters["notify"]["children"]) == {"notify", "sender"}

    def test_a_claimed_folder_deeper_down_leaves_its_cluster_and_its_files(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "services/payments/billing/src/main/java/A.java",
            "services/payments/gateway/client.py",
            "services/payments/main.py",
        )

        clusters = _cluster_with_children(
            tmp_path, source_dirs=["services"], claimed={"services/payments/billing"}
        )

        assert set(clusters["payments"]["children"]) == {"gateway"}
        assert set(clusters["payments"]["files"]) == {
            "services/payments/main.py",
            "services/payments/gateway/client.py",
        }

    def test_without_a_claim_the_clusters_are_what_they_were(self, tmp_path: Path) -> None:
        _write(tmp_path, "services/billing/src/A.java", "services/notify/n.py")

        assert _cluster_with_children(tmp_path, source_dirs=["services"]) == (
            _cluster_with_children(tmp_path, source_dirs=["services"], claimed=())
        )
        assert set(_cluster_with_children(tmp_path, source_dirs=["services"])) == {
            "billing",
            "notify",
        }


class TestTheScanPathsLeaveOutOnlyTheClaimedFolders:
    def test_a_folder_holding_no_claim_is_kept_whole(self, tmp_path: Path) -> None:
        _write(tmp_path, "lib/a.py", "services/billing/src/A.java")

        assert unclaimed_folders(tmp_path, ["lib"], {"services/billing"}) == ["lib"]

    def test_a_claimed_top_level_folder_is_dropped(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/main/java/A.java")

        assert unclaimed_folders(tmp_path, ["src"], {"src"}) == []

    def test_a_folder_holding_a_claim_gives_its_other_subfolders_with_code(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "services/billing/src/main/java/A.java",
            "services/notify/notify/__init__.py",
            "services/search/index.ts",
        )
        (tmp_path / "services" / "empty").mkdir()
        (tmp_path / "services" / "node_modules" / "x").mkdir(parents=True)
        (tmp_path / "services" / "node_modules" / "x" / "i.js").write_text("", "utf-8")

        assert unclaimed_folders(tmp_path, ["services"], {"services/billing"}) == [
            "services/notify",
            "services/search",
        ]

    def test_the_paths_never_overlap_a_claimed_folder(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "services/payments/billing/src/main/java/A.java",
            "services/payments/gateway/client.py",
            "services/notify/n.py",
        )

        kept = unclaimed_folders(tmp_path, ["services"], {"services/payments/billing"})

        assert kept == ["services/notify", "services/payments/gateway"]
        assert not any(is_claimed(path, {"services/payments/billing"}) for path in kept)
