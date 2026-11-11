"""Download Legendary for Fog Launch and check that it is the official file.

The same as the button in Fog Launch's settings. It fetches one file, the
Windows build of Legendary from its official GitHub releases, and keeps it
only if its SHA-256 checksum is the one written down in fog_launch/update.py.
You can also download the file yourself and choose it in the settings.

    python get_legendary.py
"""

import sys

from fog_launch.store import FogError
from fog_launch.update import LEGENDARY_URL, LEGENDARY_VERSION, download_legendary


def main() -> int:
    print(f"Downloading Legendary {LEGENDARY_VERSION} from\n  {LEGENDARY_URL}")
    try:
        target = download_legendary()
    except FogError as error:
        print(error)
        return 1
    print(f"Checksum is correct. Saved to\n  {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
