# Fog Launch

Starts Dead by Daylight (Epic Games version) with several Epic accounts from one installation: one profile
per account, launch sequences that start several profiles one after another, and graphics and input presets
per profile. For Windows 10 and 11; the window is in English or German.

Fog Launch is a small Python program without third-party packages. It does the Epic part through
[Legendary](https://github.com/legendary-gl/legendary), the open-source replacement for the Epic Games
Launcher, which you download separately.

## Start

1. Install [Python 3.11 or newer](https://www.python.org/downloads/windows/) (the normal installer; it
   includes Tk, which the window needs).
2. Download this repository and open its folder.
3. Get Legendary, either with the script, which checks the file against a fixed SHA-256 checksum:

   ```bash
   python get_legendary.py
   ```

   or by downloading `legendary_windows_x64.exe` from
   [Legendary's releases](https://github.com/legendary-gl/legendary/releases) yourself and choosing it under
   **Settings → Legendary**.
4. Double-click `fog_launch.pyw`, or run:

   ```bash
   python -m fog_launch
   ```

Dead by Daylight has to be installed through the Epic Games Launcher and started once before.

## Taking over Better Together

If [Better Together](https://github.com/Analagentin/Better-Together-Dead-By-Daylight-Launcher) was used on
the PC, Fog Launch offers on first start to take over its profiles, paths and launch presets
(later: **Settings → Take over from Better Together…**). There are two ways:

- **Use its profile folder as it is** (recommended). Nothing is copied or changed. The profiles stay signed
  in, and both programs keep working.
- **Copy the profiles to a new folder.** The originals stay untouched. Epic may sign one copy out once the
  other is used, so stop using Better Together afterwards.

Graphics and input presets need no import: both programs store them as files next to the game's settings
(`GameUserSettings.ini-<name>`, `Input.ini-<name>`), and Fog Launch lists what is there.

## What it does on your PC

- **Profiles.** A profile is a folder in the profile folder you choose. Legendary is started with
  `XDG_CONFIG_HOME` pointing at it and keeps that account's sign-in in `<profile>/legendary/`.
  **These files work like a password.** Do not share them or put them in a synced folder.
- **Signing in.** Either Legendary's own sign-in window, or Epic's page in your browser and the code it
  shows. Fog Launch never sees your password.
- **Launching.** `legendary launch Brill` (Epic's name for the game), by default with
  `--skip-version-check`, because the profiles share one installation record.
- **Presets.** A preset is a full copy of `GameUserSettings.ini` or `Input.ini`. In a launch sequence it is
  copied over the game's file and set read-only until the game has read it; the file from before is kept in
  Fog Launch's `backups` folder (the last ten). The editors only change keys that already exist in the file
  and leave every other line as it was.
- **Own files.** Settings and backups are in `%APPDATA%\FogLaunch`.
- **Network.** Fog Launch opens no connection. Legendary talks to Epic; `get_legendary.py` downloads one
  file from GitHub; the sign-in by code opens a page in your browser.

It does not touch the game's files, memory or anti-cheat. Whether running several accounts at once is
acceptable is between you, Epic and Behaviour.

## Layout

| File | Purpose |
| --- | --- |
| `fog_launch/core.py` | Profiles, presets, sequences, the commands for Legendary, taking over Better Together |
| `fog_launch/runner.py` | Runs Legendary and works through a launch sequence |
| `fog_launch/ini.py` | Reads and changes the game's settings files |
| `fog_launch/gui.py` | The window |
| `fog_launch/i18n.py` | German texts; the English text is the key |
| `fog_launch/store.py` | Fog Launch's own settings file |
| `get_legendary.py` | Downloads Legendary and checks its checksum |

## Tests

```bash
python -m unittest discover -s tests -t .
```

The tests use a stand-in for Legendary (`tests/fake_legendary.py`), so they need neither an Epic account
nor the game. A new or changed English text needs its German version in `fog_launch/i18n.py`; a test names
the missing ones.
