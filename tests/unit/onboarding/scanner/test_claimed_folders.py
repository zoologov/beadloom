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
    CodeBesideModules,
    UnclaimedCode,
    _cluster_with_children,
    is_claimed,
    unclaimed_code,
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


class TestTheCodeBesideAModuleIsScannedOrNamed:
    """The re-review's finding m3 (``beadloom-ujzb.22``), fixed by ``beadloom-ujzb.24``.

    The scan paths are derived from the folders a layout READS (a module's ``src``),
    not from the module's whole folder: the rest of that folder is scanned. A code
    file lying directly in a folder that is split around a module is no folder, so it
    is returned as a loose file rather than dropped.
    """

    def test_a_modules_other_folders_with_code_are_scan_paths(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "backend/src/main/kotlin/A.kt",
            "backend/src/test/kotlin/ATest.kt",
            "backend/scripts/deploy/helm.py",
            "backend/tools/gen.py",
        )
        (tmp_path / "backend" / "gradle").mkdir()

        found = unclaimed_code(tmp_path, ["backend"], {"backend/src"})

        assert found.folders == ("backend/scripts", "backend/tools")
        assert found.loose_files == ()

    def test_a_file_directly_in_a_split_folder_is_a_loose_file(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "services/billing/src/main/java/A.java",
            "services/notify/n.py",
            "services/run.py",
            "services/README.md",
        )

        found = unclaimed_code(tmp_path, ["services"], {"services/billing/src"})

        assert found.folders == ("services/notify",)
        assert found.loose_files == ("services/run.py",)

    def test_a_file_directly_in_the_modules_own_folder_is_a_loose_file(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "backend/src/main/kotlin/A.kt", "backend/Main.kt")

        found = unclaimed_code(tmp_path, ["backend"], {"backend/src"})

        assert found.folders == ()
        assert found.loose_files == ("backend/Main.kt",)

    def test_a_folder_kept_whole_holds_its_own_files(self, tmp_path: Path) -> None:
        _write(tmp_path, "lib/a.py", "lib/sub/b.py")

        assert unclaimed_code(tmp_path, ["lib"], {"backend/src"}) == UnclaimedCode(
            folders=("lib",)
        )

    def test_the_folders_are_what_unclaimed_folders_returns(self, tmp_path: Path) -> None:
        _write(tmp_path, "services/billing/src/A.java", "services/notify/n.py", "services/x.py")

        found = unclaimed_code(tmp_path, ["services"], {"services/billing/src"})

        assert list(found.folders) == unclaimed_folders(
            tmp_path, ["services"], {"services/billing/src"}
        )


class TestWhatInitSaysAboutTheCodeBesideAModule:
    def test_nothing_when_there_is_none(self) -> None:
        assert CodeBesideModules().sentences() == []

    def test_the_scanned_folders_are_named(self) -> None:
        (sentence,) = CodeBesideModules(scanned=("backend/scripts", "backend/tools")).sentences()

        assert sentence.startswith("Also scanned: backend/scripts, backend/tools - ")
        assert "module" in sentence

    def test_one_unread_file_is_named_with_what_to_do(self) -> None:
        (sentence,) = CodeBesideModules(unread=("services/run.py",)).sentences()

        assert sentence.startswith("Not read: services/run.py - ")
        assert "folder of its own" in sentence

    def test_many_unread_files_are_counted_and_the_first_named(self) -> None:
        unread = tuple(f"services/f{index}.py" for index in range(7))

        (sentence,) = CodeBesideModules(unread=unread).sentences()

        assert sentence.startswith("Not read: 7 code files ")
        assert "services/f0.py" in sentence
        assert "services/f4.py" in sentence
        assert "services/f5.py" not in sentence
        assert "and 2 more" in sentence
        assert "folder of their own" in sentence
