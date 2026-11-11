"""Starting Fog Launch: the window, or a launch without it.

    FogLaunch.exe                     the window
    FogLaunch.exe --sequence "Duo"    run a launch sequence, no window
    FogLaunch.exe --profile "Main"    launch one profile, no window

Python copies use `pythonw -m fog_launch` with the same options. Desktop
shortcuts made in the window use exactly these commands.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .core import Manager, check_name
from .i18n import set_language, t
from .runner import Runner
from .store import APP_NAME, FogError
from .windows import Tracker

WAIT_FOR_WINDOWS = 300  # seconds a run without window stays to place the game windows


def parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fog_launch", description=APP_NAME)
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sequence", metavar="NAME", help="run a launch sequence without opening the window")
    group.add_argument("--profile", metavar="NAME", help="launch one profile without opening the window")
    return parser.parse_args(argv)


def show_error(text: str) -> None:
    """An error box, for runs without window. Falls back to the console."""
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, text)
        root.destroy()
    except Exception:  # noqa: BLE001 - no display either: print is all that is left
        print(text, file=sys.stderr)


def run_without_window(manager: Manager, sequence: str | None, profile: str | None,
                       tracker: Tracker | None = None) -> int:
    """Launch a sequence or one profile. The log goes to last-run.log in the data folder."""
    set_language(manager.config.get("language") or "auto")
    tracker = tracker or Tracker()
    log_file = manager.config.dir / "last-run.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as log:
        log.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {APP_NAME} {__version__}\n")

        def emit(kind: str, text: str) -> None:
            if kind == "log":
                log.write(text)
                log.flush()

        runner = Runner(manager, emit, t, tracker)
        try:
            manager.seal_leftovers()
            if sequence is not None:
                runner.run_sequence(check_name(sequence))
            else:
                runner.launch_one(check_name(profile or ""))
        except FogError as error:
            runner.finish()
            text = t(error.template, **error.values)
            log.write(f"ERROR: {text}\n")
            show_error(text)
            return 1
        # Legendary ends once the game runs; only then are the sign-ins encrypted again.
        runner.finish()
        tracker.wait(WAIT_FOR_WINDOWS)
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = parse(argv)
    if arguments.sequence is not None or arguments.profile is not None:
        return run_without_window(Manager(), arguments.sequence, arguments.profile)
    from .gui import main as open_window

    open_window()
    return 0


# ------------------------------------------------------------ shortcuts


def shortcut_target(kind: str, name: str, program: Path | None = None) -> tuple[str, str, str, str]:
    """What a desktop shortcut runs: (program, arguments, working folder, icon)."""
    check_name(name)  # names cannot contain quotation marks, so quoting is safe
    option = "--sequence" if kind == "sequence" else "--profile"
    if getattr(sys, "frozen", False):
        exe = str(Path(sys.executable).resolve())
        return exe, f'{option} "{name}"', str(Path(exe).parent), exe
    program = program or Path(__file__).resolve().parent.parent
    python = Path(sys.executable)
    windowless = python.with_name("pythonw.exe")
    if windowless.is_file():
        python = windowless
    icon = program / "fog_launch" / "assets" / "icon.ico"
    return str(python), f'-m fog_launch {option} "{name}"', str(program), str(icon)


SHORTCUT_SCRIPT = (
    "$d=[Environment]::GetFolderPath('Desktop');"
    "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d $env:FL_FILE));"
    "$s.TargetPath=$env:FL_TARGET;$s.Arguments=$env:FL_ARGS;$s.WorkingDirectory=$env:FL_DIR;"
    "$s.IconLocation=$env:FL_ICON;$s.Description=$env:FL_TEXT;$s.Save();"
    "Write-Output (Join-Path $d $env:FL_FILE)"
)


def create_shortcut(kind: str, name: str, label: str) -> str:
    """Put a shortcut on the desktop. Returns its path. Windows only.

    The values go to PowerShell as environment variables, never as part of
    the script, so no name can change what the script does.
    """
    if os.name != "nt":
        raise FogError("Desktop shortcuts can only be created on Windows.")
    target, arguments, folder, icon = shortcut_target(kind, name)
    env = dict(os.environ, FL_FILE=f"{label}.lnk", FL_TARGET=target, FL_ARGS=arguments, FL_DIR=folder,
               FL_ICON=icon, FL_TEXT=f"{APP_NAME}: {name}")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", SHORTCUT_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        creationflags=0x08000000,
        timeout=60,
    )
    if result.returncode != 0:
        raise FogError("The shortcut could not be created: {error}", error=(result.stderr or "").strip()[-300:])
    return result.stdout.strip()
