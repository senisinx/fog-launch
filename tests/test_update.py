import io
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from fog_launch import update
from fog_launch.store import FogError

PROGRAM = {
    "fog_launch/__init__.py": b"__version__ = '9'\n",
    "fog_launch/gui.py": b"new gui\n",
    "fog_launch/core.py": b"same\n",
    "README.md": b"new readme\n",
}


def github_zip(files, folder="Fog-Launch-main"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{folder}/", "")
        for name, content in files.items():
            archive.writestr(f"{folder}/{name}", content)
    return buffer.getvalue()


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

    def test_failed_download_is_reported(self):
        with self.assertRaises(FogError):
            update.download_zip((self.root / "missing.zip").as_uri())


@unittest.skipUnless(shutil.which("git"), "needs git")
class GitUpdateTests(unittest.TestCase):
    def git(self, folder, *arguments):
        identity = ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "-C", str(folder), *identity, *arguments], check=True, capture_output=True)

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.origin = Path(temp.name) / "origin"
        self.copy = Path(temp.name) / "copy"
        self.origin.mkdir()
        self.git(self.origin, "init", "-b", "main")
        (self.origin / "a.txt").write_text("1")
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-m", "one")
        subprocess.run(["git", "clone", str(self.origin), str(self.copy)], check=True, capture_output=True)

    def test_fast_forward_and_up_to_date(self):
        self.assertTrue(update.uses_git(self.copy))
        self.assertEqual(update.update_with_git(self.copy, str(self.origin)), 0)
        (self.origin / "a.txt").write_text("2")
        (self.origin / "b.txt").write_text("new")
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-m", "two")
        self.assertEqual(update.update_with_git(self.copy, str(self.origin)), 2)
        self.assertEqual((self.copy / "a.txt").read_text(), "2")

    def test_local_changes_in_the_way_are_reported_not_overwritten(self):
        (self.origin / "a.txt").write_text("2")
        self.git(self.origin, "commit", "-am", "two")
        (self.copy / "a.txt").write_text("mine")
        with self.assertRaises(FogError):
            update.update_with_git(self.copy, str(self.origin))
        self.assertEqual((self.copy / "a.txt").read_text(), "mine")


if __name__ == "__main__":
    unittest.main()
