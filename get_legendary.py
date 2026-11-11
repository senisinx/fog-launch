"""Download Legendary for Fog Launch and check that it is the official file.

Fog Launch itself never goes online. This separate script fetches one file,
the Windows build of Legendary from its official GitHub releases, and keeps
it only if its SHA-256 checksum is the one written down below. You can also
download the file yourself and choose it in Fog Launch's settings.

    python get_legendary.py
"""

import hashlib
import sys
import urllib.request

from fog_launch.store import data_dir, write_bytes_atomic

VERSION = "0.21.1"
URL = f"https://github.com/legendary-gl/legendary/releases/download/{VERSION}/legendary_windows_x64.exe"
SHA256 = "6be77857dc0a6dd33ea7442ce8b5291944ec6da53757f81ca95b57ce794baf5b"


def main() -> int:
    target = data_dir() / "legendary.exe"
    print(f"Downloading Legendary {VERSION} from\n  {URL}")
    with urllib.request.urlopen(URL, timeout=60) as response:
        data = response.read()
    found = hashlib.sha256(data).hexdigest()
    if found != SHA256:
        print(f"Checksum mismatch, nothing was saved.\n  expected {SHA256}\n  got      {found}")
        return 1
    write_bytes_atomic(target, data)
    print(f"Checksum is correct. Saved to\n  {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
