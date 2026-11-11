"""Bringing Fog Launch up to date from its GitHub repository.

This is the only part of Fog Launch that goes online, and only when the
update button is pressed. A copy made with `git clone` is updated with git;
a copy from a ZIP download gets the newest ZIP, and only the files inside it
are replaced.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from .store import FogError, write_bytes_atomic

REPOSITORY = "senisinx/Fog-Launch"
BRANCH = "main"
GIT_URL = f"https://github.com/{REPOSITORY}.git"
ZIP_URL = f"https://github.com/{REPOSITORY}/archive/refs/heads/{BRANCH}.zip"
MAX_ZIP_BYTES = 50 * 1024 * 1024
NEEDED = ("fog_launch/__init__.py", "fog_launch/gui.py", "fog_launch/core.py")
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def program_dir() -> Path:
    """The folder that holds `fog_launch/`, README and the start file."""
    return Path(__file__).resolve().parent.parent


def uses_git(root: Path) -> bool:
    return (root / ".git").exists() and shutil.which("git") is not None


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        creationflags=NO_WINDOW,
        timeout=120,
    )


def update_with_git(root: Path, source: str = GIT_URL, branch: str = BRANCH) -> int:
    """Fast-forward a git copy. Returns how many files changed."""
    before = _git(root, "rev-parse", "HEAD").stdout.strip()
    pulled = _git(root, "pull", "--ff-only", source, branch)
    if pulled.returncode != 0:
        detail = (pulled.stderr or pulled.stdout).strip().splitlines()
        raise FogError("git could not update Fog Launch: {error}", error=" ".join(detail[-3:]))
    after = _git(root, "rev-parse", "HEAD").stdout.strip()
    if before == after:
        return 0
    changed = _git(root, "diff", "--name-only", before, after).stdout.split("\n")
    return max(1, len([name for name in changed if name.strip()]))


def download_zip(url: str = ZIP_URL) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read(MAX_ZIP_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise FogError("The update could not be downloaded: {error}", error=error) from error
    if len(data) > MAX_ZIP_BYTES:
        raise FogError("The update could not be downloaded: {error}", error="file too large")
    return data


def apply_zip(data: bytes, root: Path) -> int:
    """Replace the program files with those in a GitHub ZIP. Returns the number changed.

    Everything is read and checked before the first file is written. Files
    that are not in the ZIP, such as a legendary.exe next to the program, are
    left alone.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise FogError("The downloaded update is not a valid ZIP file.") from error
    files: dict[str, bytes] = {}
    with archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            parts = PurePosixPath(member.filename.replace("\\", "/")).parts[1:]  # drop "Fog-Launch-main/"
            if not parts or any(part in ("", ".", "..") or ":" in part for part in parts) or parts[0] == ".git":
                raise FogError("The downloaded update contains an unexpected path: {name}", name=member.filename)
            files["/".join(parts)] = archive.read(member)
    if any(name not in files for name in NEEDED):
        raise FogError("The downloaded update does not look like Fog Launch.")
    changed = 0
    try:
        for name, content in files.items():
            target = root.joinpath(*name.split("/"))
            if target.is_file() and target.read_bytes() == content:
                continue
            write_bytes_atomic(target, content)
            changed += 1
    except OSError as error:
        raise FogError("The update could not be written: {error}", error=error) from error
    return changed


def update(root: Path | None = None) -> int:
    """Update the program in place. Returns how many files changed (0: up to date)."""
    root = root or program_dir()
    if uses_git(root):
        return update_with_git(root)
    return apply_zip(download_zip(), root)
