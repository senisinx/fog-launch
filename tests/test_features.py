"""Tests for window tracking, encrypted sign-ins, the Legendary check and runs without window."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from fog_launch import cli, windows
from fog_launch.core import UnknownLegendary, check_position
from fog_launch.store import Cipher, FogError

from .test_fog_launch import Sandbox


class FakeWindows(windows.Backend):
    available = True

    def __init__(self):
        self.open: list[int] = []
        self.moves: list[tuple] = []
        self.closed: list[int] = []
        self.rects: dict[int, tuple] = {}

    def game_windows(self):
        return list(self.open)

    def alive(self, window):
        return window in self.open

    def move(self, window, x, y, width, height):
        self.moves.append((window, x, y, width, height))

    def rect(self, window):
        return self.rects.get(window)

    def close(self, window):
        self.closed.append(window)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.screen = FakeWindows()
        self.clock = Clock()
        self.tracker = windows.Tracker(self.screen, clock=self.clock)
        # step() is driven by hand; the watcher thread is not wanted here
        self.tracker._thread = mock.Mock(is_alive=lambda: True)

    def test_windows_go_to_launches_in_order_and_old_windows_are_ignored(self):
        self.screen.open = [1]  # a game that was already running
        self.tracker = windows.Tracker(self.screen, clock=self.clock)
        self.tracker._thread = mock.Mock(is_alive=lambda: True)
        self.tracker.expect("A", (0, 0, 800, 600))
        self.tracker.expect("B", None)
        self.screen.open += [7]
        self.tracker.step()
        self.screen.open += [9]
        self.tracker.step()
        self.assertEqual(self.tracker.running(), {"A": 7, "B": 9})
        self.assertEqual(self.tracker.unknown_windows(), [1])
        self.assertEqual(self.screen.moves, [(7, 0, 0, 800, 600)])

    def test_the_window_is_moved_again_while_the_game_starts(self):
        self.tracker.expect("A", (10, 20, 800, 600))
        self.screen.open = [5]
        for seconds in range(0, 40):
            self.clock.now = 1000.0 + seconds
            self.tracker.step()
        self.assertEqual(len(self.screen.moves), len(windows.MOVE_AGAIN_AFTER))
        self.assertFalse(self.tracker.busy())

    def test_a_launch_stops_waiting_after_the_time_limit(self):
        self.tracker.expect("A")
        self.clock.now += windows.WAIT_FOR_WINDOW + 1
        self.screen.open = [5]
        self.tracker.step()
        self.assertEqual(self.tracker.running(), {})
        self.assertFalse(self.tracker.busy())

    def test_closing(self):
        self.tracker.expect("A")
        self.screen.open = [5, 6]
        self.tracker.step()
        self.assertTrue(self.tracker.close("A"))
        self.assertFalse(self.tracker.close("B"))
        self.assertEqual(self.tracker.close_all(), 2)
        self.assertEqual(self.screen.closed, [5, 5, 6])

    def test_closed_windows_are_no_longer_running(self):
        self.tracker.expect("A")
        self.screen.open = [5]
        self.tracker.step()
        self.screen.rects[5] = (1, 2, 300, 400)
        self.assertEqual(self.tracker.position_of("A"), (1, 2, 300, 400))
        self.screen.open = []
        self.assertEqual(self.tracker.running(), {})
        self.assertIsNone(self.tracker.position_of("A"))

    def test_off_windows_nothing_is_found(self):
        tracker = windows.Tracker(windows.Backend())
        self.assertFalse(tracker.available)
        self.assertEqual(tracker.close_all(), 0)

    def test_positions(self):
        self.assertIsNone(check_position(None))
        self.assertIsNone(check_position(["", "", "", ""][0:0]))
        self.assertEqual(check_position(["-1920", "0", "1280", "720"]), [-1920, 0, 1280, 720])
        for bad in (["a", 0, 800, 600], [0, 0, 800], [0, 0, 10, 10], [99999, 0, 800, 600]):
            with self.assertRaises(FogError, msg=bad):
                check_position(bad)


class XorCipher(Cipher):
    """Stands in for DPAPI: reversible, and plainly not the original bytes."""

    available = True

    def protect(self, data):
        return b"SEALED" + bytes(byte ^ 0x5A for byte in data)

    def unprotect(self, data):
        if not data.startswith(b"SEALED"):
            raise FogError("not sealed")
        return bytes(byte ^ 0x5A for byte in data[6:])


class EncryptionTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.manager.cipher = XorCipher()

    def files(self, profile):
        folder = self.root / "profiles" / profile / "legendary"
        return folder / "user.json", folder / "user.json.fogsealed"

    def test_sign_ins_are_only_readable_while_legendary_runs(self):
        self.signed_in("one")
        plain, sealed = self.files("one")
        self.assertTrue(plain.exists())
        self.assertEqual(self.manager.set_encryption(True), 1)
        self.assertFalse(plain.exists())
        self.assertNotIn(b"Epic one", sealed.read_bytes())
        self.assertEqual(self.manager.account_name("one"), "Epic one")

        self.runner.launch_one("one")
        launch = [call for call in self.calls() if call["args"][0] == "launch"][0]
        self.assertEqual(launch["profile"], "one")
        self.assertFalse(plain.exists(), "readable again after Legendary finished")
        self.assertTrue(sealed.exists())

    def test_new_sign_ins_and_sign_outs_while_encrypted(self):
        self.manager.set_encryption(True)
        self.signed_in("two")
        plain, sealed = self.files("two")
        self.assertFalse(plain.exists())
        self.assertEqual(self.manager.account_name("two"), "Epic two")
        self.runner.sign_out("two")
        self.assertFalse(sealed.exists())
        self.assertIsNone(self.manager.account_name("two"))

    def test_leftovers_from_a_crash_are_encrypted_at_the_next_start(self):
        self.signed_in("one")
        self.manager.set_encryption(True)
        plain, sealed = self.files("one")
        self.manager.open_signin("one")  # Legendary started …
        self.assertTrue(plain.exists())
        # … and Fog Launch crashed before closing it
        restarted = type(self.manager)(self.manager.config, XorCipher())
        restarted.seal_leftovers()
        self.assertFalse(plain.exists())
        self.assertTrue(sealed.exists())

    def test_turning_it_off_restores_the_plain_files(self):
        self.signed_in("one")
        self.manager.set_encryption(True)
        self.assertEqual(self.manager.set_encryption(False), 1)
        plain, sealed = self.files("one")
        self.assertEqual(json.loads(plain.read_text())["displayName"], "Epic one")
        self.assertFalse(sealed.exists())

    def test_nested_use_keeps_it_open_until_the_last_close(self):
        self.signed_in("one")
        self.manager.set_encryption(True)
        plain, _sealed = self.files("one")
        self.manager.open_signin("one")
        self.manager.open_signin("one")
        self.manager.close_signin("one")
        self.assertTrue(plain.exists())
        self.manager.close_signin("one")
        self.assertFalse(plain.exists())

    def test_refused_without_dpapi(self):
        self.manager.cipher = Cipher()
        with self.assertRaises(FogError):
            self.manager.set_encryption(True)
        self.assertFalse(self.manager.encrypting)


class LegendaryCheckTests(Sandbox):
    def test_unknown_builds_are_refused_until_trusted(self):
        self.manager.config.data["trusted_legendary"] = []
        with self.assertRaises(UnknownLegendary) as caught:
            self.manager.legendary()
        self.manager.trust_legendary(caught.exception.sha256)
        self.assertEqual(self.manager.legendary(), self.manager.config.get("legendary"))

    def test_a_changed_file_is_noticed(self):
        copy = self.root / "legendary.py"
        copy.write_bytes(Path(self.manager.config.get("legendary")).read_bytes() + b"\n# a copy\n")
        self.manager.config.data["legendary"] = str(copy)
        with self.assertRaises(UnknownLegendary):
            self.manager.legendary()
        self.manager.trust_legendary(__import__("fog_launch.core").core.sha256_of(copy))
        self.manager.legendary()
        with open(copy, "a", encoding="utf-8") as file:
            file.write("\n# changed\n")
        os.utime(copy, ns=(1, 1))
        with self.assertRaises(UnknownLegendary):
            self.manager.legendary()


class CommandLineTests(Sandbox):
    def test_arguments(self):
        self.assertEqual(cli.parse(["--sequence", "Duo"]).sequence, "Duo")
        self.assertEqual(cli.parse(["--profile", "Main"]).profile, "Main")
        with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
            cli.parse(["--sequence", "a", "--profile", "b"])

    def test_sequence_without_window(self):
        self.signed_in("one", "two")
        self.manager.save_sequence("duo", [{"profile": "one"}, {"profile": "two"}], 1)
        tracker = windows.Tracker(windows.Backend())
        self.assertEqual(cli.run_without_window(self.manager, "duo", None, tracker), 0)
        launches = [call["profile"] for call in self.calls() if call["args"][0] == "launch"]
        self.assertEqual(launches, ["one", "two"])
        self.assertIn("[two] started", (self.manager.config.dir / "last-run.log").read_text(encoding="utf-8"))

    def test_errors_are_shown_and_logged(self):
        shown = []
        with mock.patch.object(cli, "show_error", shown.append):
            code = cli.run_without_window(self.manager, "missing", None, windows.Tracker(windows.Backend()))
        self.assertEqual(code, 1)
        self.assertEqual(len(shown), 1)
        self.assertIn("ERROR", (self.manager.config.dir / "last-run.log").read_text(encoding="utf-8"))

    def test_shortcut_target(self):
        program = Path("C:/Games/Fog-Launch")
        target, arguments, folder, icon = cli.shortcut_target("sequence", "Duo 2", program)
        self.assertEqual(arguments, '-m fog_launch --sequence "Duo 2"')
        self.assertEqual(Path(folder), program)
        self.assertTrue(icon.endswith("icon.ico"))
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", "C:/Apps/FogLaunch.exe"):
            target, arguments, folder, icon = cli.shortcut_target("profile", "Main", program)
        self.assertEqual((Path(target).name, arguments), ("FogLaunch.exe", '--profile "Main"'))
        with self.assertRaises(FogError):
            cli.shortcut_target("profile", 'evil" & calc', program)


if __name__ == "__main__":
    unittest.main()
