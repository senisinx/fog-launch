"""Where Fog Launch keeps its own files, and how it writes them."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_NAME = "Fog Launch"

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "language": "auto",
    "library": None,
    "active": None,
    "game_dir": None,
    "settings_ini": None,
    "input_ini": None,
    "legendary": None,
    "launch_args": "",
    "skip_version_check": True,
    "encrypt_signins": False,
    "trusted_legendary": [],
    "sequences": {},
}


class FogError(Exception):
    """A problem the user can do something about.

    Holds the English text with `{placeholders}` and their values apart, so
    the window can show the same message in another language.
    """

    def __init__(self, template: str, **values: Any):
        self.template = template
        self.values = values
        super().__init__(template.format(**values) if values else template)


class Cancelled(Exception):
    """The user pressed Cancel while a job was running."""


class Cipher:
    """Encrypts the Epic sign-ins. This one is for systems without DPAPI."""

    available = False

    def protect(self, data: bytes) -> bytes:
        raise FogError("Encrypting the sign-ins is only possible on Windows.")

    def unprotect(self, data: bytes) -> bytes:
        raise FogError("Encrypting the sign-ins is only possible on Windows.")


class DpapiCipher(Cipher):
    """Windows' own encryption, tied to the signed-in Windows user (DPAPI).

    Only the same Windows user on the same PC can decrypt the data, and no
    password has to be stored for it.
    """

    available = True
    ENTROPY = b"Fog Launch sign-in"

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        class Blob(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        self.ctypes = ctypes
        self.Blob = Blob
        self.crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    def _blob(self, data: bytes) -> Any:
        buffer = self.ctypes.create_string_buffer(data, len(data))
        return self.Blob(len(data), self.ctypes.cast(buffer, self.ctypes.POINTER(self.ctypes.c_char))), buffer

    def _run(self, function: Any, data: bytes) -> bytes:
        source, _keep = self._blob(data)
        entropy, _keep_entropy = self._blob(self.ENTROPY)
        result = self.Blob()
        ui_forbidden = 0x1
        if not function(self.ctypes.byref(source), None, self.ctypes.byref(entropy), None, None, ui_forbidden,
                        self.ctypes.byref(result)):
            raise FogError("Windows could not encrypt or decrypt a sign-in (error {code}).",
                           code=self.ctypes.get_last_error())
        try:
            return self.ctypes.string_at(result.pbData, result.cbData)
        finally:
            self.kernel32.LocalFree(result.pbData)

    def protect(self, data: bytes) -> bytes:
        return self._run(self.crypt32.CryptProtectData, data)

    def unprotect(self, data: bytes) -> bytes:
        return self._run(self.crypt32.CryptUnprotectData, data)


def default_cipher() -> Cipher:
    if os.name == "nt":
        try:
            return DpapiCipher()
        except (OSError, AttributeError):
            pass
    return Cipher()


def data_dir() -> Path:
    """Folder for the configuration, backups and an optional Legendary copy."""
    override = os.environ.get("FOG_LAUNCH_HOME")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "FogLaunch"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "fog-launch"


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Replace a file in one step, so a crash never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write_json(path: Path, data: Any) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    write_bytes_atomic(path, text.encode("utf-8"))


def read_json(path: Path) -> Any:
    """Return the parsed file, or None when it is missing or unreadable."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


class Config:
    """The settings file. Unknown keys are kept, missing ones get defaults."""

    def __init__(self, directory: Path | None = None):
        self.dir = Path(directory) if directory else data_dir()
        self.path = self.dir / "config.json"
        loaded = read_json(self.path)
        self.data: dict[str, Any] = deepcopy(DEFAULTS)
        if isinstance(loaded, dict):
            self.data.update(loaded)
        if not isinstance(self.data.get("sequences"), dict):
            self.data["sequences"] = {}

    def get(self, key: str) -> Any:
        return self.data.get(key)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def save(self) -> None:
        write_json(self.path, self.data)
