#!/usr/bin/env python3
"""Stands in for Legendary in the tests: same commands, no network, no game."""
import json
import os
import sys
from pathlib import Path

home = Path(os.environ["XDG_CONFIG_HOME"]) / "legendary"
home.mkdir(parents=True, exist_ok=True)
args = sys.argv[1:]
record = Path(os.environ["FAKE_LEGENDARY_RECORD"])
with record.open("a", encoding="utf-8") as file:
    ini = os.environ.get("FAKE_LEGENDARY_INI")
    seen = Path(ini).read_text(encoding="utf-8") if ini and Path(ini).exists() else ""
    file.write(json.dumps({"profile": home.parent.name, "args": args, "ini": seen}) + "\n")

if args[0] == "auth":
    if "--delete" in args:
        (home / "user.json").unlink(missing_ok=True)
    elif "--code" in args and args[args.index("--code") + 1] == "bad00000":
        print("Login attempt failed")
    else:
        (home / "user.json").write_text(json.dumps({"displayName": "Epic " + home.parent.name}))
        print("Successfully logged in")
elif args[0] == "import":
    installed = {"Brill": {"app_name": "Brill", "install_path": args[2], "version": "1"}}
    (home / "installed.json").write_text(json.dumps(installed))
elif args[0] == "status":
    (home / "metadata").mkdir(exist_ok=True)
    meta = {"app_name": "Brill", "metadata": {}, "asset_infos": {"Windows": {}}}
    (home / "metadata" / "Brill.json").write_text(json.dumps(meta))
    print("{}")
elif args[0] == "launch":
    if os.environ.get("FAKE_LEGENDARY_FAIL") == home.parent.name:
        print("Game is out of date")
        sys.exit(1)
    print("Launching Brill")
