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
