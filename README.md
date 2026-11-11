<img src="fog_launch/assets/icon.png" alt="" width="96" align="right">

# Fog Launch

Starts Dead by Daylight (Epic Games version) with several Epic accounts from one installation: one profile
per account, launch sequences that start several profiles one after another, graphics and input presets per
profile, and window positions for each game. For Windows 10 and 11; the window is in English or German.

Fog Launch does the Epic part through [Legendary](https://github.com/legendary-gl/legendary), the
open-source replacement for the Epic Games Launcher, which you download separately.

## Start

**With the program file (no Python needed).** Download `FogLaunch.exe` from the
[newest release](https://github.com/senisinx/Fog-Launch/releases/latest), put it in a folder of its own and
start it. Windows SmartScreen may warn because the file is not signed; check that it came from this
repository, then choose **More info → Run anyway**. Then press **Settings → Download Legendary**.

**From the source.** Install [Python 3.11 or newer](https://www.python.org/downloads/windows/) (the normal
installer includes Tk, which the window needs), download this repository, and in its folder run:

```bash
python get_legendary.py
```

```bash
python -m fog_launch
```

or double-click `fog_launch.pyw`.

Dead by Daylight has to be installed through the Epic Games Launcher and started once before.

## Checking the program file

`FogLaunch.exe` is built on GitHub from exactly the tagged source (`.github/workflows/release.yml`), never on
someone's PC. Each release lists its SHA-256 in `SHA256SUMS.txt`, and GitHub records where the file was built.
With the [GitHub CLI](https://cli.github.com/):

```bash
gh attestation verify FogLaunch.exe --repo senisinx/Fog-Launch
```

## Taking over Better Together

If [Better Together](https://github.com/Analagentin/Better-Together-Dead-By-Daylight-Launcher) was used on
the PC, Fog Launch offers on first start to take over its profiles, paths and launch presets
(later: **Settings → Take over from Better Together…**). There are two ways:

- **Use its profile folder as it is** (recommended). Nothing is copied or changed. The profiles stay signed
  in, and both programs keep working, unless you turn on encrypted sign-ins.
- **Copy the profiles to a new folder.** The originals stay untouched. Epic may sign one copy out once the
  other is used, so stop using Better Together afterwards.

Graphics and input presets need no import: both programs store them as files next to the game's settings
(`GameUserSettings.ini-<name>`, `Input.ini-<name>`), and Fog Launch lists what is there.

## Shortcuts and the command line

**Desktop shortcut** (on the Profiles and Launch sequences tabs) puts a shortcut on the desktop that launches
a profile or a sequence without opening the window. The same works from the command line:

```bash
FogLaunch.exe --sequence "Duo"
```

```bash
FogLaunch.exe --profile "Main"
```

From the source: `pythonw -m fog_launch --sequence "Duo"`. Errors are shown in a message box; the log of the
last run is `last-run.log` in Fog Launch's data folder.

## Game windows

- **Positions.** Each entry of a launch sequence can have a window position (X, Y, width, height). When the
  game window of that profile appears, Fog Launch moves it there, and again a few times while the game
  starts. **Take from the running window** copies the position of a window you placed by hand. This works
  best with the display mode *Window* or *Borderless window*.
- **Running and closing.** The Profiles tab shows which profiles have a game open. **Close game** and
  **Close all games** ask the window to close, the same as its X button.

Windows cannot tell which window belongs to which account. Fog Launch gives each new game window to the
oldest launch still waiting for one, so a game started some other way at the same time can confuse it.

## What it does on your PC

- **Profiles.** A profile is a folder in the profile folder you choose. Legendary is started with
  `XDG_CONFIG_HOME` pointing at it and keeps that account's sign-in in `<profile>/legendary/user.json`.
  **This file works like a password.** Do not share it or put it in a synced folder.
- **Encrypted sign-ins** (optional, **Settings**). The sign-in is then stored encrypted by Windows (DPAPI),
  tied to your Windows user on this PC. It is decrypted only while Legendary runs for that profile and
  encrypted again right after, because Legendary refreshes it. This protects against copying the folder to
  another PC, not against programs running under your own Windows user. Better Together cannot use encrypted
  profiles.
- **Legendary check.** Before every use, Fog Launch checks Legendary's SHA-256 against the official builds it
  knows. Another file only runs after you confirm it once.
- **Signing in.** Either Legendary's own sign-in window, or Epic's page in your browser and the code it
  shows. Fog Launch never sees your password.
- **Launching.** `legendary launch Brill` (Epic's name for the game), by default with
  `--skip-version-check`, because the profiles share one installation record.
- **Presets.** A preset is a full copy of `GameUserSettings.ini` or `Input.ini`. In a launch sequence it is
  copied over the game's file and set read-only until the game has read it; the file from before is kept in
  Fog Launch's `backups` folder (the last ten). The editors only change keys that already exist in the file
  and leave every other line as it was.
- **Windows.** Game windows are found, moved and closed with Windows' ordinary window functions. Fog Launch
  opens no handle to the game's process.
- **Own files.** Settings, backups and the log are in `%APPDATA%\FogLaunch`.
- **Network.** Fog Launch goes online only when you press **Update Fog Launch…** or **Download Legendary**.
  Otherwise Legendary talks to Epic, and the sign-in by code opens a page in your browser.

It does not touch the game's files (apart from the settings files above), memory or anti-cheat. Whether running several accounts at once is
acceptable is between you, Epic and Behaviour.

## Updating

**Settings → Update Fog Launch…** asks GitHub for the newest
[release](https://github.com/senisinx/Fog-Launch/releases), shows its notes and installs it after asking:

- `FogLaunch.exe` is replaced by the release's file once its SHA-256 matches `SHA256SUMS.txt`;
- a copy made with `git clone` moves forward to the release's tag;
- a copy from a ZIP download gets the release's source ZIP, and only the files inside it are replaced.

Work on `main` that is not released yet is never installed. Profiles, settings and a `legendary.exe` next to
the program are not touched. Nothing is checked or downloaded in the background.

## Publishing a release

1. Raise `__version__` in `fog_launch/__init__.py` and merge that into `main`.
2. On GitHub: **Releases → Draft a new release**, tag `v` plus that version (for example `v0.3.0`), target
   `main`, **Publish release**.
3. The workflow *Release* runs the tests, builds `FogLaunch.exe` and attaches it with `SHA256SUMS.txt`. It
   stops if the tag does not match the version in the code.

## Layout

| File | Purpose |
| --- | --- |
| `fog_launch/core.py` | Profiles, presets, sequences, encrypted sign-ins, the Legendary check, taking over Better Together |
| `fog_launch/runner.py` | Runs Legendary and works through a launch sequence |
| `fog_launch/windows.py` | Finds, moves and closes game windows |
| `fog_launch/ini.py` | Reads and changes the game's settings files |
| `fog_launch/gui.py` | The window |
| `fog_launch/cli.py` | Command line, runs without window, desktop shortcuts |
| `fog_launch/i18n.py` | German texts; the English text is the key |
| `fog_launch/store.py` | Fog Launch's own settings file and the DPAPI encryption |
| `fog_launch/update.py` | Updates and the Legendary download: the only code that goes online |
| `get_legendary.py` | Downloads Legendary from the command line |

## Tests

```bash
python -m unittest discover -s tests -t .
```

They run on GitHub for every pull request, on Windows and Linux. The tests use a stand-in for Legendary
(`tests/fake_legendary.py`) and for the window functions, so they need neither an Epic account nor the game. A new or changed English text needs its German version in `fog_launch/i18n.py`; a test names
the missing ones.

## License

Free to use and to pass on unchanged; changes only with permission. See [LICENSE](LICENSE) and
[THIRD_PARTY.md](THIRD_PARTY.md).
