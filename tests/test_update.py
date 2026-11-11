import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from fog_launch import __version__, update
from fog_launch.store import FogError

PROGRAM = {
    "fog_launch/__init__.py": b"__version__ = '9'\n",
    "fog_launch/gui.py": b"new gui\n",
    "fog_launch/core.py": b"same\n",
    "README.md": b"new readme\n",
}


def github_zip(files, folder="Fog-Launch-0.9.0"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{folder}/", "")
        for name, content in files.items():
            archive.writestr(f"{folder}/{name}", content)
    return buffer.getvalue()


def release_json(tag="v9.0.0", assets=("FogLaunch.exe", "SHA256SUMS.txt")):
    return {
        "tag_name": tag,
        "body": "Notes",
        "html_url": f"https://github.com/senisinx/Fog-Launch/releases/tag/{tag}",
        "assets": [{"name": name, "browser_download_url": f"https://example.invalid/{name}"} for name in assets],
    }


class ReleaseTests(unittest.TestCase):
    def test_versions_compare_as_numbers(self):
        self.assertEqual(update.version_tuple("v0.10.2"), (0, 10, 2))
        self.assertGreater(update.version_tuple("v0.10.0"), update.version_tuple("0.9.9"))
        self.assertTrue(update.parse_release(release_json("v999.0.0")).newer)
        self.assertFalse(update.parse_release(release_json(f"v{__version__}")).newer)
        self.assertFalse(update.parse_release(release_json("v0.0.1")).newer)

    def test_release_fields(self):
        release = update.parse_release(release_json())
        self.assertEqual(release.zip_url, "https://github.com/senisinx/Fog-Launch/archive/refs/tags/v9.0.0.zip")
        self.assertEqual(release.assets["FogLaunch.exe"], "https://example.invalid/FogLaunch.exe")
        with self.assertRaises(FogError):
            update.parse_release({"body": "no tag"})

    def test_latest_release_reads_the_api_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            answer = Path(folder) / "latest.json"
            answer.write_text(json.dumps(release_json("v1.2.3")))
            self.assertEqual(update.latest_release(answer.as_uri()).tag, "v1.2.3")
            with self.assertRaises(FogError):
                update.latest_release((Path(folder) / "missing.json").as_uri())

    def test_checksum_list(self):
        digest = "a" * 64
        sums = f"{digest}  FogLaunch.exe\r\n{'b' * 64} *other.txt\n"
        self.assertEqual(update.expected_sum(sums, "FogLaunch.exe"), digest)
        self.assertEqual(update.expected_sum(sums, "other.txt"), "b" * 64)
        with self.assertRaises(FogError):
            update.expected_sum(sums, "missing.exe")


class ExeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.exe = Path(temp.name) / "FogLaunch.exe"
        self.exe.write_bytes(b"old program")

    def test_matching_checksum_swaps_the_exe(self):
        new = b"new program"
        sums = f"{hashlib.sha256(new).hexdigest()}  FogLaunch.exe\n"
        self.assertEqual(update.replace_exe(new, sums, self.exe), 1)
        self.assertEqual(self.exe.read_bytes(), new)
        self.assertEqual(self.exe.with_name("FogLaunch.exe.old").read_bytes(), b"old program")

    def test_wrong_checksum_changes_nothing(self):
        sums = f"{'0' * 64}  FogLaunch.exe\n"
        with self.assertRaises(FogError):
            update.replace_exe(b"tampered", sums, self.exe)
        self.assertEqual(self.exe.read_bytes(), b"old program")
        self.assertFalse(self.exe.with_name("FogLaunch.exe.old").exists())

    def test_frozen_install_needs_the_built_assets(self):
        release = update.parse_release(release_json(assets=()))
        with mock.patch.object(update, "frozen", return_value=True):
            with self.assertRaises(FogError):
                update.install(release, self.exe.parent)


class ZipUpdateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "fog_launch").mkdir()
        (self.root / "fog_launch" / "gui.py").write_bytes(b"old gui\n")
        (self.root / "fog_launch" / "core.py").write_bytes(b"same\n")
        (self.root / "legendary.exe").write_bytes(b"keep")

    def test_only_changed_files_are_replaced_and_others_kept(self):
        self.assertEqual(update.apply_zip(github_zip(PROGRAM), self.root), 3)
        self.assertEqual((self.root / "fog_launch" / "gui.py").read_bytes(), b"new gui\n")
        self.assertEqual((self.root / "README.md").read_bytes(), b"new readme\n")
        self.assertEqual((self.root / "legendary.exe").read_bytes(), b"keep")
        self.assertEqual(update.apply_zip(github_zip(PROGRAM), self.root), 0)

    def test_paths_leading_outside_are_refused_before_anything_is_written(self):
        for name in ("../evil.py", "fog_launch/../../evil.py", ".git/config", "C:/evil.py"):
            with self.assertRaises(FogError, msg=name):
                update.apply_zip(github_zip({**PROGRAM, name: b"x"}), self.root)
        self.assertEqual((self.root / "fog_launch" / "gui.py").read_bytes(), b"old gui\n")
        self.assertFalse((self.root.parent / "evil.py").exists())

    def test_something_else_than_fog_launch_is_refused(self):
        with self.assertRaises(FogError):
            update.apply_zip(github_zip({"README.md": b"hello"}), self.root)
        with self.assertRaises(FogError):
            update.apply_zip(b"<html>not found</html>", self.root)
        self.assertEqual((self.root / "fog_launch" / "gui.py").read_bytes(), b"old gui\n")

    def test_zip_install_uses_the_release_zip(self):
        release = update.parse_release(release_json())
        with mock.patch.object(update, "fetch", return_value=github_zip(PROGRAM)) as fetch:
            self.assertEqual(update.install(release, self.root), 3)
        fetch.assert_called_once_with(release.zip_url)


class LegendaryDownloadTests(unittest.TestCase):
    def test_only_the_known_file_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "legendary.exe"
            with mock.patch.object(update, "fetch", return_value=b"something else"):
                with self.assertRaises(FogError):
                    update.download_legendary(target)
            self.assertFalse(target.exists())
            good = b"pretend legendary"
            with mock.patch.object(update, "fetch", return_value=good), \
                    mock.patch.object(update, "LEGENDARY_SHA256", hashlib.sha256(good).hexdigest()):
                update.download_legendary(target)
            self.assertEqual(target.read_bytes(), good)


@unittest.skipUnless(shutil.which("git"), "needs git")
class GitUpdateTests(unittest.TestCase):
    def git(self, folder, *arguments):
        identity = ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "-C", str(folder), *identity, *arguments], check=True, capture_output=True)

    def commit(self, message, **files):
        for name, text in files.items():
            (self.origin / name).write_text(text)
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-m", message)

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.origin = Path(temp.name) / "origin"
        self.copy = Path(temp.name) / "copy"
        self.origin.mkdir()
        self.git(self.origin, "init", "-b", "main")
        self.commit("one", **{"a.txt": "1"})
        self.git(self.origin, "tag", "v1.0.0")
        subprocess.run(["git", "clone", str(self.origin), str(self.copy)], check=True, capture_output=True)

    def test_moves_to_the_tag_not_to_newer_commits(self):
        self.assertTrue(update.uses_git(self.copy))
        self.assertEqual(update.update_with_git(self.copy, "v1.0.0", str(self.origin)), 0)
        self.commit("two", **{"a.txt": "2", "b.txt": "new"})
        self.git(self.origin, "tag", "v1.1.0")
        self.commit("unreleased", **{"a.txt": "work in progress"})
        self.assertEqual(update.update_with_git(self.copy, "v1.1.0", str(self.origin)), 2)
        self.assertEqual((self.copy / "a.txt").read_text(), "2")

    def test_local_changes_in_the_way_are_reported_not_overwritten(self):
        self.commit("two", **{"a.txt": "2"})
        self.git(self.origin, "tag", "v1.1.0")
        (self.copy / "a.txt").write_text("mine")
        with self.assertRaises(FogError):
            update.update_with_git(self.copy, "v1.1.0", str(self.origin))
        self.assertEqual((self.copy / "a.txt").read_text(), "mine")


if __name__ == "__main__":
    unittest.main()
