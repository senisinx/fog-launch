"""Running Legendary and working through a launch sequence.

No window code in here: progress goes out through one `emit(kind, text)`
callback, with kind "log" for output lines and "status" for the status line.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .core import Manager
from .store import FogError

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
SETTLE_SECONDS = 30  # how long a locked preset stays in place for the game to read
SECRET_OPTIONS = {"--code", "--token", "--sid"}

Emit = Callable[[str, str], None]

STARTED = "{name} started, checking for {seconds} s"
NEXT = "Next: {name} in {seconds} s"


class Cancelled(Exception):
    pass


def printable(command: list[str]) -> str:
    """A command line for the log, with sign-in codes blanked out."""
    shown = []
    hide = False
    for part in command:
        shown.append("***" if hide else part)
        hide = part in SECRET_OPTIONS
    return " ".join(f'"{part}"' if " " in part else part for part in shown)


def extract_code(pasted: str) -> str:
    """The authorization code from what Epic's page shows, pasted whole or in part."""
    pasted = pasted.strip()
    if pasted.startswith("{"):
        try:
            pasted = str(json.loads(pasted).get("authorizationCode") or "")
        except ValueError:
            match = re.search(r'"authorizationCode"\s*:\s*"([^"]+)"', pasted)
            pasted = match.group(1) if match else ""
    pasted = pasted.strip().strip('"')
    if not re.fullmatch(r"[0-9A-Za-z]{8,}", pasted):
        raise FogError("That does not look like an authorization code. Copy the value of \"authorizationCode\".")
    return pasted


class Runner:
    def __init__(self, manager: Manager, emit: Emit, translate: Callable[..., str] | None = None):
        self.manager = manager
        self.emit = emit
        self.t = translate or (lambda text, **values: text.format(**values))
        self.cancel = threading.Event()
        self._waited_for: subprocess.Popen[str] | None = None

    # ------------------------------------------------------------ processes

    def _start(self, arguments: list[str], profile: str) -> subprocess.Popen[str]:
        command, env = self.manager.command(arguments, profile)
        self.emit("log", f"[{profile}] > {printable(command[1:])}\n")
        try:
            process = subprocess.Popen(
                command,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=NO_WINDOW,
            )
        except OSError as error:
            raise FogError("Legendary could not be started: {error}", error=error) from error

        def pump() -> None:
            assert process.stdout is not None
            with process.stdout:
                for line in process.stdout:
                    self.emit("log", f"[{profile}] {line.rstrip()}\n")

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        process.reader = reader  # type: ignore[attr-defined]
        return process

    def run(self, arguments: list[str], profile: str) -> int:
        """Run a Legendary command to its end and return its exit code."""
        process = self._start(arguments, profile)
        self._waited_for = process
        try:
            while process.poll() is None:
                if self.cancel.is_set():
                    process.terminate()
                    raise Cancelled()
                time.sleep(0.1)
        finally:
            self._waited_for = None
        process.reader.join(timeout=2)  # type: ignore[attr-defined]
        return process.returncode

    def stop(self) -> None:
        self.cancel.set()

    def _wait(self, seconds: int, text: str, name: str, watched: subprocess.Popen[str] | None = None) -> None:
        for remaining in range(seconds, 0, -1):
            if self.cancel.is_set():
                raise Cancelled()
            if watched is not None and watched.poll() not in (None, 0):
                raise FogError("Legendary stopped with an error (code {code}). See the log.", code=watched.returncode)
            self.emit("status", self.t(text, name=name, seconds=remaining))
            time.sleep(1)

    # --------------------------------------------------------------- actions

    def sign_in(self, profile: str, code: str | None = None) -> None:
        arguments = ["auth"]
        if code:
            arguments += ["--code", extract_code(code)]
        if self.run(arguments, profile) != 0 or not self.manager.account_name(profile):
            raise FogError("Signing in to '{name}' did not work. See the log.", name=profile)

    def sign_out(self, profile: str) -> None:
        self.run(["auth", "--delete"], profile)

    def prepare(self, profile: str, game_dir: str | Path | None = None) -> None:
        """Make sure a profile is signed in and knows the game, before a launch."""
        manager = self.manager
        if not manager.account_name(profile):
            raise FogError("The profile '{name}' is not signed in.", name=profile)
        folder = game_dir or manager.game_dir
        if not folder:
            raise FogError("Choose the Dead by Daylight folder in the settings first.")
        folder = manager.check_game_dir(folder)
        if not manager.game_template():
            self.emit("status", self.t("{name}: registering the game folder", name=profile))
            if self.run(manager.import_arguments(folder), profile) != 0:
                raise FogError("Legendary could not register the game folder. See the log.")
        manager.link_game([profile], folder)
        if not manager.has_metadata(profile):
            self.emit("status", self.t("{name}: loading game data from Epic", name=profile))
            if self.run(["status", "--json"], profile) != 0:
                raise FogError("The game data for '{name}' could not be loaded. See the log.", name=profile)
            if not manager.has_metadata(profile):
                raise FogError("Dead by Daylight is not in the Epic library of '{name}'.", name=profile)

    def launch(self, profile: str, game_dir: str | Path | None = None) -> subprocess.Popen[str]:
        self.prepare(profile, game_dir)
        process = self._start(self.manager.launch_arguments(), profile)
        self.emit("log", f"[{profile}] started\n")
        return process

    def launch_one(self, profile: str) -> None:
        process = self.launch(profile)
        self._wait(3, STARTED, profile, process)

    def run_sequence(self, name: str) -> None:
        manager = self.manager
        sequence = manager.sequences().get(name)
        if not sequence or not sequence["entries"]:
            raise FogError("The sequence '{name}' has no entries.", name=name)
        entries: list[dict[str, Any]] = sequence["entries"]
        known = set(manager.profiles())
        missing = [entry["profile"] for entry in entries if entry["profile"] not in known]
        if missing:
            raise FogError("These profiles no longer exist: {names}", names=", ".join(missing))
        for kind in ("graphics", "input"):
            for preset in {entry.get(kind) for entry in entries} - {None}:
                manager.preset_source(kind, preset)

        locked: set[str] = set()
        try:
            for index, entry in enumerate(entries):
                if self.cancel.is_set():
                    raise Cancelled()
                profile = entry["profile"]
                self.prepare(profile, entry.get("game_dir"))
                used_preset = False
                for kind in ("graphics", "input"):
                    preset = entry.get(kind)
                    if not preset:
                        continue
                    if kind not in locked:
                        manager.backup(kind)
                    manager.apply_preset(kind, preset, lock=True)
                    locked.add(kind)
                    used_preset = True
                    self.emit("log", f"[{profile}] preset: {preset}\n")
                process = self._start(manager.launch_arguments(), profile)
                self.emit("log", f"[{profile}] started\n")
                last = index == len(entries) - 1
                seconds = int(sequence["delay"])
                if used_preset:
                    seconds = max(seconds, SETTLE_SECONDS)
                if last:
                    seconds = SETTLE_SECONDS if used_preset else 3
                    self._wait(seconds, STARTED, profile, process)
                else:
                    self._wait(seconds, NEXT, entries[index + 1]["profile"], process)
        finally:
            for kind in locked:
                try:
                    manager.unlock(manager.ini_path(kind))
                except OSError:
                    pass
