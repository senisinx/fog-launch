"""Profiles, presets, launch sequences and the commands handed to Legendary.

Nothing in here opens a window or a network connection. Each profile is a
folder; Legendary is pointed at it through XDG_CONFIG_HOME and keeps that
profile's Epic sign-in in `<profile>/legendary/`.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from . import ini
from .store import Config, FogError, read_json, write_json

GAME_APP = "Brill"  # Epic's internal name for Dead by Daylight
GAME_EXE = "DeadByDaylight.exe"
LOGIN_URL = "https://legendary.gl/epiclogin"
KEPT_BACKUPS = 10

_NAME = re.compile(r"[\w .-]+")
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}


def check_name(name: str) -> str:
    """Return a name that is safe as a folder and file name on Windows."""
    name = str(name).strip()
    if (
        not name
        or not _NAME.fullmatch(name)
        or name.endswith(".")
        or name.startswith(".")
        or name.split(".")[0].casefold() in _RESERVED
    ):
        raise FogError(
            "Names may contain letters, digits, spaces, '-', '_' and '.', "
            "and must not start or end with a dot."
        )
    return name


def split_arguments(text: str) -> list[str]:
    """Split extra game arguments the way a Windows command line would."""
    try:
        parts = shlex.split(text, posix=False)
    except ValueError as error:
        raise FogError("The launch arguments have an unclosed quotation mark.") from error
    return [
        part[1:-1] if len(part) >= 2 and part[0] == part[-1] and part[0] in "\"'" else part
        for part in parts
    ]


class Manager:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()

    # ------------------------------------------------------------- locations

    @property
    def library(self) -> Path | None:
        value = self.config.get("library")
        return Path(value) if value else None

    def set_library(self, path: str | Path) -> Path:
        folder = Path(path).expanduser().resolve()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise FogError("The profile folder could not be created: {error}", error=error) from error
        self.config.data["library"] = str(folder)
        if self.config.get("active") not in self.profiles():
            self.config.data["active"] = None
        self.config.save()
        return folder

    @property
    def game_dir(self) -> Path | None:
        value = self.config.get("game_dir")
        return Path(value) if value else None

    @staticmethod
    def check_game_dir(path: str | Path) -> Path:
        folder = Path(path).expanduser().resolve()
        if not (folder / GAME_EXE).is_file():
            raise FogError(
                "'{exe}' is not in '{folder}'. Choose the folder the game is installed in.",
                exe=GAME_EXE,
                folder=folder,
            )
        return folder

    def set_game_dir(self, path: str | Path) -> Path:
        folder = self.check_game_dir(path)
        self.config.set("game_dir", str(folder))
        return folder

    @property
    def settings_ini(self) -> Path:
        value = self.config.get("settings_ini")
        if value:
            return Path(value)
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(local) / "DeadByDaylight" / "Saved" / "Config" / "EGSClient" / "GameUserSettings.ini"

    @property
    def input_ini(self) -> Path:
        value = self.config.get("input_ini")
        return Path(value) if value else self.settings_ini.parent / "Input.ini"

    def set_ini(self, kind: str, path: str | Path) -> Path:
        file = Path(path).expanduser().resolve()
        if not file.is_file():
            raise FogError("'{file}' does not exist.", file=file)
        self.config.set("settings_ini" if kind == "graphics" else "input_ini", str(file))
        return file

    def ini_path(self, kind: str) -> Path:
        return self.settings_ini if kind == "graphics" else self.input_ini

    def legendary(self) -> str:
        """Path of the Legendary program, from the settings or the usual places."""
        names = ("legendary.exe", "legendary") if os.name == "nt" else ("legendary",)
        configured = self.config.get("legendary")
        candidates = [Path(configured)] if configured else []
        app_dir = Path(sys.argv[0]).resolve().parent if sys.argv and sys.argv[0] else Path.cwd()
        for folder in (self.config.dir, app_dir, Path(__file__).resolve().parent.parent):
            candidates.extend(folder / name for name in names)
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        found = shutil.which("legendary")
        if found:
            return found
        raise FogError(
            "Legendary was not found. Run get_legendary.py, or choose legendary.exe in the settings."
        )

    # -------------------------------------------------------------- profiles

    def profiles(self) -> list[str]:
        library = self.library
        if not library or not library.is_dir():
            return []
        return sorted((p.name for p in library.iterdir() if p.is_dir()), key=str.casefold)

    def profile_dir(self, name: str) -> Path:
        if not self.library:
            raise FogError("Choose a profile folder in the settings first.")
        return self.library / check_name(name)

    def _existing_profile(self, name: str) -> Path:
        folder = self.profile_dir(name)
        if not folder.is_dir():
            raise FogError("The profile '{name}' does not exist.", name=name)
        return folder

    def create_profile(self, name: str) -> str:
        folder = self.profile_dir(name)
        if folder.exists():
            raise FogError("The profile '{name}' already exists.", name=folder.name)
        folder.mkdir(parents=True)
        return folder.name

    def rename_profile(self, old: str, new: str) -> str:
        source = self._existing_profile(old)
        target = self.profile_dir(new)
        if target.exists():
            raise FogError("The profile '{name}' already exists.", name=target.name)
        try:
            source.rename(target)
        except OSError as error:
            raise FogError("The profile could not be renamed: {error}", error=error) from error
        if self.config.get("active") == old:
            self.config.data["active"] = target.name
        for sequence in self.sequences().values():
            for entry in sequence["entries"]:
                if entry.get("profile") == old:
                    entry["profile"] = target.name
        self.config.save()
        return target.name

    def delete_profile(self, name: str) -> None:
        """Delete a profile folder, but only if it holds nothing but Legendary's data."""
        folder = self._existing_profile(name)
        extra = sorted(p.name for p in folder.iterdir() if p.name != "legendary")
        if extra:
            raise FogError(
                "'{folder}' also contains {extra}. Fog Launch only deletes folders that "
                "hold nothing but the sign-in data; delete this one yourself.",
                folder=folder,
                extra=", ".join(extra),
            )
        try:
            shutil.rmtree(folder)
        except OSError as error:
            raise FogError("The profile could not be deleted: {error}", error=error) from error
        if self.config.get("active") == name:
            self.config.set("active", None)

    def set_active(self, name: str | None) -> None:
        if name is not None:
            self._existing_profile(name)
        self.config.set("active", name)

    def account_name(self, profile: str) -> str | None:
        """The Epic display name a profile is signed in as, if it is."""
        user = read_json(self.profile_dir(profile) / "legendary" / "user.json")
        if isinstance(user, dict) and user:
            return str(user.get("displayName") or user.get("account_id") or "?")
        return None

    # --------------------------------------------- the game inside a profile

    def _installed_file(self, profile: str) -> Path:
        return self.profile_dir(profile) / "legendary" / "installed.json"

    def _installed(self, profile: str) -> dict[str, Any]:
        data = read_json(self._installed_file(profile))
        return data if isinstance(data, dict) else {}

    def game_entry(self, profile: str) -> dict[str, Any] | None:
        entry = self._installed(profile).get(GAME_APP)
        return entry if isinstance(entry, dict) else None

    def game_dir_of(self, profile: str) -> Path | None:
        entry = self.game_entry(profile)
        return Path(entry["install_path"]) if entry and entry.get("install_path") else None

    def has_metadata(self, profile: str) -> bool:
        """Whether Legendary has cached what it needs to know to launch the game."""
        data = read_json(self.profile_dir(profile) / "legendary" / "metadata" / f"{GAME_APP}.json")
        return (
            isinstance(data, dict)
            and isinstance(data.get("metadata"), dict)
            and isinstance(data.get("asset_infos"), dict)
            and bool(data["asset_infos"])
        )

    @property
    def _template_file(self) -> Path:
        return self.config.dir / "game_template.json"

    def game_template(self) -> dict[str, Any] | None:
        """Legendary's record of the installed game, to give to other profiles."""
        saved = read_json(self._template_file)
        if isinstance(saved, dict) and saved.get("app_name") == GAME_APP:
            return saved
        for profile in self.profiles():
            entry = self.game_entry(profile)
            if entry and entry.get("app_name") == GAME_APP:
                write_json(self._template_file, entry)
                return entry
        return None

    def link_game(self, profiles: list[str] | None = None, game_dir: str | Path | None = None) -> int:
        """Tell the given profiles where the game is installed. Returns how many."""
        folder = self.check_game_dir(game_dir or self.game_dir or "")
        template = self.game_template()
        if not template:
            raise FogError(
                "No profile knows the game yet. Sign in to one profile and choose the game folder again."
            )
        count = 0
        for profile in self.profiles() if profiles is None else profiles:
            installed = self._installed(profile)
            entry = dict(installed.get(GAME_APP) or template)
            if entry.get("install_path") == str(folder) and GAME_APP in installed:
                count += 1
                continue
            entry["install_path"] = str(folder)
            installed[GAME_APP] = entry
            write_json(self._installed_file(profile), installed)
            count += 1
        return count

    # ----------------------------------------------------- Legendary commands

    def command(self, arguments: list[str], profile: str) -> tuple[list[str], dict[str, str]]:
        folder = self._existing_profile(profile)
        env = os.environ.copy()
        env.pop("LEGENDARY_CONFIG_PATH", None)  # would override the profile folder
        env["XDG_CONFIG_HOME"] = str(folder)
        return [self.legendary(), *arguments], env

    def launch_arguments(self) -> list[str]:
        arguments = ["launch", GAME_APP]
        if self.config.get("skip_version_check"):
            arguments.append("--skip-version-check")
        return arguments + split_arguments(self.config.get("launch_args") or "")

    def import_arguments(self, game_dir: str | Path) -> list[str]:
        return ["import", GAME_APP, str(game_dir), "--disable-check", "--skip-dlcs"]

    # --------------------------------------------- graphics and input presets

    def _preset_file(self, kind: str, name: str) -> Path:
        target = self.ini_path(kind)
        return target.parent / f"{target.name}-{check_name(name)}"

    def presets(self, kind: str) -> list[str]:
        """Preset names. A preset is a full copy of the file, stored next to it."""
        target = self.ini_path(kind)
        prefix = f"{target.name}-"
        if not target.parent.is_dir():
            return []
        names = [
            p.name[len(prefix):]
            for p in target.parent.iterdir()
            if p.is_file() and p.name.startswith(prefix) and len(p.name) > len(prefix)
        ]
        return sorted(names, key=str.casefold)

    def preset_source(self, kind: str, name: str | None) -> Path:
        """The file a preset name stands for; None means the game's live file."""
        file = self._preset_file(kind, name) if name else self.ini_path(kind)
        if not file.is_file():
            raise FogError(
                "'{file}' does not exist. Start the game once, or set the path in the settings.",
                file=file,
            )
        return file

    def read_preset(self, kind: str, name: str | None) -> tuple[str, str]:
        return ini.read_ini(self.preset_source(kind, name))

    def write_preset(self, kind: str, name: str | None, text: str, encoding: str) -> Path:
        """Save text as a preset, or to the live file (which is backed up first)."""
        file = self._preset_file(kind, name) if name else self.ini_path(kind)
        try:
            if not name:
                self.backup(kind)
                self.unlock(file)
            ini.write_ini(file, text, encoding)
        except OSError as error:
            raise FogError("'{file}' could not be written: {error}", file=file, error=error) from error
        return file

    def delete_preset(self, kind: str, name: str) -> None:
        file = self._preset_file(kind, name)
        try:
            file.unlink()
        except OSError as error:
            raise FogError("The preset could not be deleted: {error}", error=error) from error
        for sequence in self.sequences().values():
            for entry in sequence["entries"]:
                if entry.get(kind) == name:
                    entry[kind] = None
        self.config.save()

    def backup(self, kind: str) -> Path | None:
        """Copy the live file into Fog Launch's own backup folder."""
        file = self.ini_path(kind)
        if not file.is_file():
            return None
        folder = self.config.dir / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        copy = folder / f"{file.name}.{stamp}"
        shutil.copy2(file, copy)
        self.unlock(copy)
        old = sorted(folder.glob(f"{file.name}.*"))[:-KEPT_BACKUPS]
        for path in old:
            try:
                path.unlink()
            except OSError:
                pass
        return copy

    @staticmethod
    def unlock(file: Path) -> None:
        if file.exists():
            file.chmod(file.stat().st_mode | stat.S_IWRITE)

    @staticmethod
    def lock(file: Path) -> None:
        file.chmod(file.stat().st_mode & ~(stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH))

    def apply_preset(self, kind: str, name: str, lock: bool = False) -> None:
        """Copy a preset over the live file; `lock` then makes it read-only."""
        source = self.preset_source(kind, name)
        target = self.ini_path(kind)
        try:
            self.unlock(target)
            shutil.copyfile(source, target)
            if lock:
                self.lock(target)
        except OSError as error:
            raise FogError("The preset '{name}' could not be applied: {error}", name=name, error=error) from error

    # ------------------------------------------------------- launch sequences

    def sequences(self) -> dict[str, dict[str, Any]]:
        sequences = self.config.data["sequences"]
        for sequence in sequences.values():
            sequence.setdefault("delay", 30)
            sequence.setdefault("entries", [])
        return sequences

    def save_sequence(self, name: str, entries: list[dict[str, Any]], delay: int) -> str:
        name = check_name(name)
        try:
            delay = int(delay)
        except (TypeError, ValueError) as error:
            raise FogError("The delay must be a whole number of seconds.") from error
        if not 0 <= delay <= 3600:
            raise FogError("The delay must be between 0 and 3600 seconds.")
        cleaned = []
        for entry in entries:
            if not entry.get("profile"):
                continue
            cleaned.append(
                {
                    "profile": entry["profile"],
                    "graphics": entry.get("graphics") or None,
                    "input": entry.get("input") or None,
                    "game_dir": str(entry["game_dir"]) if entry.get("game_dir") else None,
                }
            )
        self.config.data["sequences"][name] = {"delay": delay, "entries": cleaned}
        self.config.save()
        return name

    def delete_sequence(self, name: str) -> None:
        self.config.data["sequences"].pop(name, None)
        self.config.save()

    def rename_sequence(self, old: str, new: str) -> str:
        new = check_name(new)
        sequences = self.config.data["sequences"]
        if new in sequences:
            raise FogError("The sequence '{name}' already exists.", name=new)
        sequences[new] = sequences.pop(old)
        self.config.save()
        return new


# ------------------------------------------------- taking over Better Together


def better_together_dir() -> Path | None:
    """Where Better Together keeps its settings, if it was used on this PC."""
    candidates = [os.environ.get("BETTER_TOGETHER_HOME"), Path.home() / ".egs_manager"]
    for candidate in candidates:
        if candidate and (Path(candidate) / "config.json").is_file():
            return Path(candidate)
    return None


def read_better_together(folder: str | Path) -> dict[str, Any]:
    """What a Better Together settings folder offers, without changing anything."""
    folder = Path(folder)
    config = read_json(folder / "config.json")
    if not isinstance(config, dict):
        raise FogError("No Better Together settings were found in '{folder}'.", folder=folder)
    library = Path(config["account_folder"]) if config.get("account_folder") else None
    profiles = []
    if library and library.is_dir():
        profiles = sorted((p.name for p in library.iterdir() if p.is_dir()), key=str.casefold)
    sequences = {}
    presets = config.get("presets")
    for name, preset in (presets if isinstance(presets, dict) else {}).items():
        if not isinstance(preset, dict):
            continue
        entries = []
        for entry in preset.get("entries") or preset.get("accounts") or []:
            if isinstance(entry, str):
                entry = {"account": entry}
            if isinstance(entry, dict) and entry.get("account"):
                entries.append(
                    {
                        "profile": entry["account"],
                        "graphics": entry.get("graphics_preset") or None,
                        "input": entry.get("input_preset") or None,
                        "game_dir": entry.get("game_path") or None,
                    }
                )
        if entries:
            sequences[str(name)] = {"delay": preset.get("delay_seconds", 30), "entries": entries}
    template = read_json(folder / "dbd_install.json")
    return {
        "folder": folder,
        "library": library,
        "profiles": profiles,
        "sequences": sequences,
        "active": config.get("active"),
        "game_dir": config.get("dbd_path"),
        "settings_ini": config.get("game_settings_path"),
        "input_ini": config.get("input_settings_path"),
        "launch_args": config.get("launch_arguments") or "",
        "template": template if isinstance(template, dict) else None,
    }


def import_better_together(
    manager: Manager, folder: str | Path, copy_to: str | Path | None = None
) -> list[FogError]:
    """Take over profiles, paths and launch presets from Better Together.

    Without `copy_to`, Fog Launch uses Better Together's profile folder as it
    is. With it, every profile is copied there and the original is left alone.
    Returns notes on what was skipped. Nothing of Better Together is changed.
    """
    found = read_better_together(folder)
    source: Path | None = found["library"]
    if not source or not source.is_dir():
        raise FogError("Better Together has no profile folder set, or it no longer exists.")
    notes: list[FogError] = []
    if copy_to:
        target = Path(copy_to).expanduser().resolve()
        if target == source.resolve() or source.resolve() in target.parents:
            raise FogError("Choose a folder outside Better Together's profile folder for the copy.")
        target.mkdir(parents=True, exist_ok=True)
        for profile in found["profiles"]:
            if (target / profile).exists():
                notes.append(
                    FogError("The profile '{name}' already exists in the target and was not copied.", name=profile)
                )
                continue
            try:
                shutil.copytree(
                    source / profile,
                    target / profile,
                    ignore=shutil.ignore_patterns("*.lock", "tmp", "__pycache__"),
                )
            except OSError as error:
                notes.append(FogError("The profile '{name}' could not be copied: {error}", name=profile, error=error))
        manager.set_library(target)
    else:
        manager.set_library(source)

    data = manager.config.data
    for key in ("settings_ini", "input_ini"):
        if found[key] and Path(found[key]).is_file():
            data[key] = str(found[key])
    if found["game_dir"]:
        if (Path(found["game_dir"]) / GAME_EXE).is_file():
            data["game_dir"] = str(found["game_dir"])
        else:
            notes.append(
                FogError(
                    "The game folder '{folder}' no longer contains {exe}.",
                    folder=found["game_dir"],
                    exe=GAME_EXE,
                )
            )
    if found["launch_args"] and not data.get("launch_args"):
        data["launch_args"] = found["launch_args"]
    if found["active"] in manager.profiles():
        data["active"] = found["active"]
    if found["template"] and found["template"].get("app_name") == GAME_APP:
        write_json(manager.config.dir / "game_template.json", found["template"])
    for name, sequence in found["sequences"].items():
        if name in data["sequences"]:
            notes.append(FogError("The sequence '{name}' already exists and was kept as it is.", name=name))
        else:
            data["sequences"][name] = sequence
    manager.config.save()
    return notes
