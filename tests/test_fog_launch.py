import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fog_launch import ini, runner
from fog_launch.core import (
    GAME_EXE,
    Manager,
    UnknownLegendary,
    check_name,
    check_position,
    sha256_of,
    import_better_together,
    read_better_together,
    split_arguments,
)
from fog_launch.store import Config, FogError

SETTINGS = (
    "[/Script/DeadByDaylight.DBDGameUserSettings]\r\n"
    "ResolutionSizeX=1920\r\n"
    "ResolutionSizeY=1080\r\n"
    "FrameRateLimit=120.000000\r\n"
    "bUseVSync=False\r\n"
    "; a comment=stays\r\n"
    "Unrelated=keep me\r\n"
    "\r\n"
    "[ScalabilityGroups]\r\n"
    "sg.ShadowQuality=3\r\n"
)

INPUT = (
    "[/Script/Engine.InputSettings]\n"
    "bUseMouseForTouch=False\n"
    'ActionMappings=(ActionName="Interact",bShift=False,bCtrl=False,bAlt=False,bCmd=False,Key=LeftMouseButton)\n'
    'ActionMappings=(ActionName="Crouch",bShift=False,bCtrl=True,bAlt=False,bCmd=False,Key=C)\n'
    'AxisMappings=(AxisName="MoveForward",Scale=-1.000000,Key=S)\n'
    "Tail=1\n"
)


class IniTests(unittest.TestCase):
    def test_graphics_round_trip_changes_only_existing_keys(self):
        settings = ini.graphics_from_text(SETTINGS)
        self.assertEqual(settings["width"], 1920)
        self.assertEqual(settings["fps"], 120)
        self.assertIs(settings["vsync"], False)
        self.assertNotIn("main_volume", settings)

        settings.update(width=1280, height=720, fps=60, vsync=True, main_volume=40)
        settings["sg.ShadowQuality"] = 0
        text = ini.graphics_to_text(SETTINGS, settings)
        self.assertIn("ResolutionSizeX=1280\r\n", text)
        self.assertIn("FrameRateLimit=60.000000\r\n", text)
        self.assertIn("bUseVSync=True\r\n", text)
        self.assertIn("sg.ShadowQuality=0\r\n", text)
        self.assertIn("; a comment=stays\r\n", text)
        self.assertIn("Unrelated=keep me\r\n", text)
        self.assertNotIn("MainVolume", text)
        self.assertEqual(len(text.splitlines()), len(SETTINGS.splitlines()))

    def test_unchanged_graphics_give_identical_text(self):
        self.assertEqual(ini.graphics_to_text(SETTINGS, ini.graphics_from_text(SETTINGS)), SETTINGS)

    def test_graphics_out_of_range_is_refused(self):
        with self.assertRaises(ini.IniError):
            ini.graphics_to_text(SETTINGS, {"width": 10})

    def test_bindings_round_trip_is_identical(self):
        bindings = ini.bindings_from_text(INPUT)
        self.assertEqual([b.name for b in bindings], ["Interact", "Crouch", "MoveForward"])
        self.assertTrue(bindings[1].ctrl)
        self.assertEqual(bindings[2].scale, "-1.000000")
        self.assertEqual(ini.bindings_to_text(INPUT, bindings), INPUT)

    def test_bindings_edit_add_and_remove(self):
        bindings = ini.bindings_from_text(INPUT)
        bindings[0].key = "E"
        bindings[0].raw = None
        del bindings[1]
        bindings.append(ini.Binding("action", "Drop", "R"))
        text = ini.bindings_to_text(INPUT, bindings)
        self.assertIn('ActionName="Interact",bShift=False,bCtrl=False,bAlt=False,bCmd=False,Key=E)', text)
        self.assertNotIn("Crouch", text)
        self.assertIn('ActionName="Drop"', text)
        self.assertTrue(text.startswith("[/Script/Engine.InputSettings]\nbUseMouseForTouch=False\n"))
        self.assertTrue(text.endswith("Tail=1\n"))

    def test_file_encoding_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "a.ini"
            file.write_bytes(SETTINGS.encode("utf-16"))
            text, encoding = ini.read_ini(file)
            self.assertEqual((text, encoding), (SETTINGS, "utf-16"))
            ini.write_ini(file, text, encoding)
            self.assertEqual(file.read_bytes(), SETTINGS.encode("utf-16"))


class Sandbox(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.game = self.root / "game"
        self.game.mkdir()
        (self.game / GAME_EXE).touch()
        self.config_dir = self.root / "cfg"
        self.config_dir.mkdir()
        self.settings = self.config_dir / "GameUserSettings.ini"
        self.settings.write_text(SETTINGS, encoding="utf-8", newline="")
        (self.config_dir / "Input.ini").write_text(INPUT, encoding="utf-8", newline="")
        self.record = self.root / "record.jsonl"
        fake = Path(__file__).with_name("fake_legendary.py")
        patch = mock.patch.dict(
            os.environ,
            {
                "FAKE_LEGENDARY_RECORD": str(self.record),
                "FAKE_LEGENDARY_INI": str(self.settings),
                "LEGENDARY_CONFIG_PATH": "/somewhere/else",
            },
        )
        patch.start()
        self.addCleanup(patch.stop)
        self.manager = Manager(Config(self.root / "data"))
        self.manager.config.data.update(
            legendary=str(fake),
            settings_ini=str(self.settings),
            input_ini=str(self.config_dir / "Input.ini"),
            trusted_legendary=[sha256_of(fake)],
        )
        self.manager.set_library(self.root / "profiles")
        self.manager.set_game_dir(self.game)
        self.log: list[tuple[str, str]] = []
        self.runner = runner.Runner(self.manager, lambda kind, text: self.log.append((kind, text)))
        patch = mock.patch("fog_launch.runner.time.sleep", lambda _seconds: None)
        patch.start()
        self.addCleanup(patch.stop)
        start = self.runner._start

        def start_and_finish(arguments, profile):
            # The waits are skipped in tests, so let each command finish first.
            process = start(arguments, profile)
            process.wait()
            process.reader.join()
            return process

        self.runner._start = start_and_finish

    def calls(self):
        if not self.record.exists():
            return []
        return [json.loads(line) for line in self.record.read_text(encoding="utf-8").splitlines()]

    def signed_in(self, *names):
        for name in names:
            self.manager.create_profile(name)
            self.runner.sign_in(name, code="abc12345")


class ManagerTests(Sandbox):
    def test_names(self):
        self.assertEqual(check_name("  Main 1 "), "Main 1")
        for bad in ("", "..", "a/b", "a\\b", "con", "x.", ".x", "a:b"):
            with self.assertRaises(FogError):
                check_name(bad)

    def test_split_arguments(self):
        self.assertEqual(split_arguments('-a "b c" -d'), ["-a", "b c", "-d"])
        with self.assertRaises(FogError):
            split_arguments('"open')

    def test_command_points_legendary_at_the_profile(self):
        self.manager.create_profile("one")
        command, env = self.manager.command(["status"], "one")
        self.assertEqual(command[-2:], [self.manager.config.get("legendary"), "status"])
        self.assertEqual(env["XDG_CONFIG_HOME"], str(self.root / "profiles" / "one"))
        self.assertNotIn("LEGENDARY_CONFIG_PATH", env)

    def test_profile_lifecycle(self):
        self.signed_in("one")
        self.assertEqual(self.manager.account_name("one"), "Epic one")
        self.manager.save_sequence("s", [{"profile": "one"}], 5)
        self.manager.set_active("one")
        self.manager.rename_profile("one", "two")
        self.assertEqual(self.manager.profiles(), ["two"])
        self.assertEqual(self.manager.config.get("active"), "two")
        self.assertEqual(self.manager.sequences()["s"]["entries"][0]["profile"], "two")
        self.runner.sign_out("two")
        self.assertIsNone(self.manager.account_name("two"))
        self.manager.delete_profile("two")
        self.assertEqual(self.manager.profiles(), [])

    def test_delete_refuses_folders_with_other_content(self):
        self.manager.create_profile("one")
        (self.root / "profiles" / "one" / "holiday.jpg").touch()
        with self.assertRaises(FogError):
            self.manager.delete_profile("one")
        self.assertTrue((self.root / "profiles" / "one" / "holiday.jpg").exists())

    def test_extract_code(self):
        self.assertEqual(runner.extract_code(' "abc123DEF" '), "abc123DEF")
        pasted = '{"redirectUrl":"x","authorizationCode":"0123456789abcdef","sid":null}'
        self.assertEqual(runner.extract_code(pasted), "0123456789abcdef")
        for bad in ("", "{}", "--delete", "a b"):
            with self.assertRaises(FogError):
                runner.extract_code(bad)

    def test_failed_sign_in_is_reported(self):
        self.manager.create_profile("one")
        with self.assertRaises(FogError):
            self.runner.sign_in("one", code="bad00000")
        shown = "".join(text for _kind, text in self.log)
        self.assertNotIn("bad00000", shown.split("Login attempt failed")[0])
        self.assertIn("--code ***", shown)

    def test_presets_are_files_next_to_the_settings(self):
        text, encoding = self.manager.read_preset("graphics", None)
        low = ini.graphics_to_text(text, {"width": 1280, "height": 720})
        self.manager.write_preset("graphics", "low", low, encoding)
        self.assertEqual(self.manager.presets("graphics"), ["low"])
        self.assertTrue((self.config_dir / "GameUserSettings.ini-low").is_file())
        self.manager.apply_preset("graphics", "low", lock=True)
        self.assertFalse(self.settings.stat().st_mode & stat.S_IWRITE)
        self.assertIn("ResolutionSizeX=1280", self.settings.read_text())
        self.manager.write_preset("graphics", None, text, encoding)
        self.assertEqual(self.settings.read_bytes().decode(), SETTINGS)
        self.assertEqual(len(list((self.root / "data" / "backups").iterdir())), 1)
        self.manager.delete_preset("graphics", "low")
        self.assertEqual(self.manager.presets("graphics"), [])


class LaunchTests(Sandbox):
    def test_first_launch_imports_then_other_profiles_reuse_the_record(self):
        self.signed_in("one", "two")
        self.runner.launch_one("one")
        self.runner.launch_one("two")
        commands = [(call["profile"], call["args"][0]) for call in self.calls()[2:]]
        self.assertEqual(
            commands,
            [("one", "import"), ("one", "status"), ("one", "launch"), ("two", "status"), ("two", "launch")],
        )
        self.assertEqual(self.manager.game_dir_of("two"), self.game)
        self.assertEqual(self.calls()[-1]["args"], ["launch", "Brill", "--skip-version-check"])

    def test_launch_needs_a_sign_in(self):
        self.manager.create_profile("one")
        with self.assertRaises(FogError):
            self.runner.launch_one("one")
        self.assertEqual(self.calls(), [])

    def test_sequence_applies_presets_in_order_and_unlocks(self):
        self.signed_in("one", "two")
        text, encoding = self.manager.read_preset("graphics", None)
        self.manager.write_preset("graphics", "low", ini.graphics_to_text(text, {"width": 1280}), encoding)
        self.manager.write_preset("graphics", "tiny", ini.graphics_to_text(text, {"width": 800}), encoding)
        other = self.root / "game2"
        other.mkdir()
        (other / GAME_EXE).touch()
        self.manager.save_sequence(
            "duo",
            [
                {"profile": "one", "graphics": "low"},
                {"profile": "two", "graphics": "tiny", "game_dir": str(other)},
            ],
            5,
        )
        self.runner.run_sequence("duo")
        launches = [call for call in self.calls() if call["args"][0] == "launch"]
        self.assertEqual([call["profile"] for call in launches], ["one", "two"])
        self.assertIn("ResolutionSizeX=1280", launches[0]["ini"])
        self.assertIn("ResolutionSizeX=800", launches[1]["ini"])
        self.assertEqual(self.manager.game_dir_of("one"), self.game)
        self.assertEqual(self.manager.game_dir_of("two"), other)
        self.assertTrue(self.settings.stat().st_mode & stat.S_IWRITE)
        backups = list((self.root / "data" / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes().decode(), SETTINGS)

    def test_sequence_stops_when_a_launch_fails(self):
        self.signed_in("one", "two")
        self.manager.save_sequence("duo", [{"profile": "one"}, {"profile": "two"}], 5)
        with mock.patch.dict(os.environ, {"FAKE_LEGENDARY_FAIL": "one"}):
            with self.assertRaises(FogError):
                self.runner.run_sequence("duo")
        launches = [call["profile"] for call in self.calls() if call["args"][0] == "launch"]
        self.assertEqual(launches, ["one"])

    def test_cancel_stops_before_the_next_profile(self):
        self.signed_in("one", "two")
        self.manager.save_sequence("duo", [{"profile": "one"}, {"profile": "two"}], 5)
        original = self.runner._start

        def start_and_cancel(arguments, profile):
            process = original(arguments, profile)
            if arguments[0] == "launch":
                self.runner.cancel.set()
            return process

        self.runner._start = start_and_cancel
        with self.assertRaises(runner.Cancelled):
            self.runner.run_sequence("duo")
        launches = [call["profile"] for call in self.calls() if call["args"][0] == "launch"]
        self.assertEqual(launches, ["one"])


class BetterTogetherTests(Sandbox):
    def make_better_together(self):
        home = self.root / "bt"
        library = self.root / "bt-profiles"
        for name in ("Alpha", "Beta"):
            folder = library / name / "legendary"
            folder.mkdir(parents=True)
            (folder / "user.json").write_text(json.dumps({"displayName": name.lower()}))
            (folder / "user.json.lock").touch()
            (folder / "installed.json").write_text(
                json.dumps({"Brill": {"app_name": "Brill", "install_path": str(self.game)}})
            )
        home.mkdir()
        (home / "config.json").write_text(
            json.dumps(
                {
                    "schema_version": 3,
                    "active": "Beta",
                    "account_folder": str(library),
                    "dbd_path": str(self.game),
                    "game_settings_path": str(self.settings),
                    "input_settings_path": None,
                    "launch_arguments": "-nosplash",
                    "presets": {
                        "Duo": {
                            "delay_seconds": 30,
                            "entries": [
                                {"account": "Alpha", "graphics_preset": "low", "input_preset": None, "game_path": None},
                                "Beta",
                            ],
                        }
                    },
                }
            )
        )
        (home / "dbd_install.json").write_text(json.dumps({"app_name": "Brill", "version": "9"}))
        return home, library

    def test_take_over_in_place(self):
        home, library = self.make_better_together()
        before = sorted(str(p) for p in library.rglob("*"))
        self.assertEqual(read_better_together(home)["profiles"], ["Alpha", "Beta"])
        notes = import_better_together(self.manager, home)
        self.assertEqual(notes, [])
        self.assertEqual(self.manager.library, library)
        self.assertEqual(self.manager.profiles(), ["Alpha", "Beta"])
        self.assertEqual(self.manager.account_name("Alpha"), "alpha")
        self.assertEqual(self.manager.config.get("active"), "Beta")
        self.assertEqual(self.manager.config.get("launch_args"), "-nosplash")
        self.assertEqual(
            self.manager.sequences()["Duo"]["entries"],
            [
                {"profile": "Alpha", "graphics": "low", "input": None, "game_dir": None},
                {"profile": "Beta", "graphics": None, "input": None, "game_dir": None},
            ],
        )
        self.assertEqual(self.manager.game_template()["version"], "9")
        self.assertEqual(sorted(str(p) for p in library.rglob("*")), before)

    def test_take_over_as_copy_keeps_existing_things(self):
        home, library = self.make_better_together()
        self.manager.save_sequence("Duo", [{"profile": "mine"}], 1)
        target = self.root / "copied"
        (target / "Beta").mkdir(parents=True)
        notes = import_better_together(self.manager, home, copy_to=target)
        self.assertEqual(len(notes), 2)
        self.assertEqual(self.manager.library, target)
        self.assertEqual(self.manager.account_name("Alpha"), "alpha")
        self.assertFalse((target / "Alpha" / "legendary" / "user.json.lock").exists())
        self.assertIsNone(self.manager.account_name("Beta"))
        self.assertEqual(self.manager.sequences()["Duo"]["entries"][0]["profile"], "mine")
        self.assertTrue((library / "Alpha" / "legendary" / "user.json").exists())

    def test_copy_into_the_source_is_refused(self):
        home, library = self.make_better_together()
        with self.assertRaises(FogError):
            import_better_together(self.manager, home, copy_to=library / "inside")


if __name__ == "__main__":
    unittest.main()
