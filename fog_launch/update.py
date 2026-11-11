"""Going online, which Fog Launch only does when a button is pressed.

Two things live here: updating Fog Launch to its newest release, and
downloading Legendary. Nothing in here runs in the background.

Updates come from the releases of the GitHub repository, not from whatever
is on the main branch at the moment:

- the Windows program (FogLaunch.exe) is replaced by the release's exe,
  after its SHA-256 has been checked against the release's SHA256SUMS.txt;
- a copy made with `git clone` is moved forward to the release's tag;
- a copy from a ZIP download gets the release's source ZIP, and only the
  files inside it are replaced.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import __version__
from .core import KNOWN_LEGENDARY
from .store import FogError, data_dir, write_bytes_atomic

REPOSITORY = "senisinx/Fog-Launch"
LATEST_RELEASE = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
GIT_URL = f"https://github.com/{REPOSITORY}.git"
EXE_NAME = "FogLaunch.exe"
SUMS_NAME = "SHA256SUMS.txt"
MAX_DOWNLOAD = 100 * 1024 * 1024
NEEDED = ("fog_launch/__init__.py", "fog_launch/gui.py", "fog_launch/core.py")
NO_WINDOW = 0x08000000 if os.name == "nt" else 0

LEGENDARY_VERSION = "0.21.1"
LEGENDARY_URL = (
    f"https://github.com/legendary-gl/legendary/releases/download/{LEGENDARY_VERSION}/legendary_windows_x64.exe"
)
LEGENDARY_SHA256 = "6be77857dc0a6dd33ea7442ce8b5291944ec6da53757f81ca95b57ce794baf5b"
assert LEGENDARY_SHA256 in KNOWN_LEGENDARY


def frozen() -> bool:
    """Whether this is the packed FogLaunch.exe rather than Python source."""
    return bool(getattr(sys, "frozen", False))


def program_dir() -> Path:
    """The folder that holds the program: the exe, or `fog_launch/` and README."""
    if frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def version_tuple(text: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", text)
    return tuple(int(number) for number in numbers[:3]) if numbers else (0,)


def fetch(url: str, accept: str | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": f"FogLaunch/{__version__}"})
    if accept:
        request.add_header("Accept", accept)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_DOWNLOAD + 1)
    except urllib.error.HTTPError as error:
        raise FogError("The download failed: {error}", error=f"HTTP {error.code} ({url})") from error
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise FogError("The download failed: {error}", error=error) from error
    if len(data) > MAX_DOWNLOAD:
        raise FogError("The download failed: {error}", error="file too large")
    return data


# ---------------------------------------------------------------- releases


@dataclass
class Release:
    tag: str
    version: tuple[int, ...]
    notes: str
    page: str
    zip_url: str
    assets: dict[str, str]  # file name -> download URL

    @property
    def newer(self) -> bool:
        return self.version > version_tuple(__version__)


def parse_release(data: dict) -> Release:
    try:
        tag = str(data["tag_name"])
        return Release(
            tag=tag,
            version=version_tuple(tag),
            notes=str(data.get("body") or "").strip(),
            page=str(data.get("html_url") or ""),
            zip_url=f"https://github.com/{REPOSITORY}/archive/refs/tags/{tag}.zip",
            assets={str(a["name"]): str(a["browser_download_url"]) for a in data.get("assets") or []},
        )
    except (KeyError, TypeError) as error:
        raise FogError("GitHub's answer about the newest version could not be read.") from error


def latest_release(url: str = LATEST_RELEASE) -> Release:
    try:
        data = json.loads(fetch(url, "application/vnd.github+json"))
    except FogError as error:
        if "HTTP 404" in str(error.values.get("error", "")):
            raise FogError("No version of Fog Launch has been published yet.") from error
        raise
    except ValueError as error:
        raise FogError("GitHub's answer about the newest version could not be read.") from error
    return parse_release(data)


def expected_sum(sums: str, name: str) -> str:
    """The SHA-256 a SHA256SUMS.txt lists for a file name."""
    for line in sums.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1].lstrip("*") == name and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            return parts[0].lower()
    raise FogError("{name} is not listed in {sums}.", name=name, sums=SUMS_NAME)


# ------------------------------------------------------- the three ways


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


def update_with_git(root: Path, tag: str, source: str = GIT_URL) -> int:
    """Move a git copy forward to a release tag. Returns how many files changed."""
    before = _git(root, "rev-parse", "HEAD").stdout.strip()
    fetched = _git(root, "fetch", "--no-tags", source, f"refs/tags/{tag}:refs/tags/{tag}")
    merged = fetched if fetched.returncode != 0 else _git(root, "merge", "--ff-only", f"refs/tags/{tag}")
    if merged.returncode != 0:
        detail = (merged.stderr or merged.stdout).strip().splitlines()
        raise FogError("git could not update Fog Launch: {error}", error=" ".join(detail[-3:]))
    after = _git(root, "rev-parse", "HEAD").stdout.strip()
    if before == after:
        return 0
    changed = _git(root, "diff", "--name-only", before, after).stdout.split("\n")
    return max(1, len([name for name in changed if name.strip()]))


def apply_zip(data: bytes, root: Path) -> int:
    """Replace the program files with those in a GitHub source ZIP. Returns the number changed.

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
            parts = PurePosixPath(member.filename.replace("\\", "/")).parts[1:]  # drop "Fog-Launch-<tag>/"
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


def replace_exe(new: bytes, sums: str, exe: Path) -> int:
    """Swap the running exe for a new one whose checksum matches the release.

    Windows does not let a running program be overwritten, but it can be
    renamed: the old exe becomes FogLaunch.exe.old and is deleted at the next
    start (see remove_old_exe).
    """
    found = hashlib.sha256(new).hexdigest()
    expected = expected_sum(sums, EXE_NAME)
    if found != expected:
        raise FogError("The downloaded program does not match its checksum. Nothing was changed.")
    old = exe.with_name(exe.name + ".old")
    try:
        old.unlink(missing_ok=True)
        exe.replace(old)
        try:
            write_bytes_atomic(exe, new)
        except OSError:
            old.replace(exe)
            raise
    except OSError as error:
        raise FogError("The update could not be written: {error}", error=error) from error
    return 1


def remove_old_exe() -> None:
    if frozen():
        try:
            Path(sys.executable).with_name(Path(sys.executable).name + ".old").unlink(missing_ok=True)
        except OSError:
            pass


def install(release: Release, root: Path | None = None) -> int:
    """Bring this copy to the given release. Returns how many files changed."""
    root = root or program_dir()
    if frozen():
        if EXE_NAME not in release.assets or SUMS_NAME not in release.assets:
            raise FogError("The program file of version {tag} is still being built. Try again in a few minutes.",
                           tag=release.tag)
        sums = fetch(release.assets[SUMS_NAME]).decode("utf-8", errors="replace")
        return replace_exe(fetch(release.assets[EXE_NAME]), sums, Path(sys.executable).resolve())
    if uses_git(root):
        return update_with_git(root, release.tag)
    return apply_zip(fetch(release.zip_url), root)


def restart_command() -> list[str]:
    if frozen():
        return [sys.executable]
    return [sys.executable, "-m", "fog_launch"]


# --------------------------------------------------------------- Legendary


def download_legendary(target: Path | None = None) -> Path:
    """Fetch the official Legendary build and keep it only if its checksum is right."""
    target = target or data_dir() / "legendary.exe"
    data = fetch(LEGENDARY_URL)
    found = hashlib.sha256(data).hexdigest()
    if found != LEGENDARY_SHA256:
        raise FogError("The downloaded Legendary does not match its checksum. Nothing was saved.")
    write_bytes_atomic(target, data)
    return target
