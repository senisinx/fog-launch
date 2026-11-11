# Third-party parts

Fog Launch's own code uses only Python's standard library. These parts come from others and keep their
own licenses:

| Part | Where it comes in | License |
| --- | --- | --- |
| [Legendary](https://github.com/legendary-gl/legendary) | Downloaded separately (button in the settings or `get_legendary.py`), not part of Fog Launch | GPL-3.0 |
| [Python](https://www.python.org/) | Packed into `FogLaunch.exe` | Python Software Foundation License |
| [Tcl/Tk](https://www.tcl-lang.org/) | Packed into `FogLaunch.exe` for the window | Tcl/Tk license (BSD-style) |
| [PyInstaller](https://pyinstaller.org/) | Its bootloader starts `FogLaunch.exe` | GPL-2.0 with an exception that allows packed programs under any license |

Fog Launch talks to Legendary only by starting it as a separate program.
