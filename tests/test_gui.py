"""The window: unsaved preset edits, and that it opens at all.

Skipped where Python has no Tk; the smoke test also needs a display (CI runs
it under xvfb on Linux and directly on Windows).
"""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import tkinter as tk

    from fog_launch import gui
except ImportError:  # Python built without Tk
    gui = None


@unittest.skipIf(gui is None, "needs tkinter")
class UnsavedEditTests(unittest.TestCase):
    def tab(self, edited="changed", shown="loaded", text="file text", choice="High"):
        loads = []
        value = [choice]
        tab = SimpleNamespace(
            live="Current game settings",
            text=text,
            shown=shown,
            edited=lambda: edited,
            manager=SimpleNamespace(presets=lambda kind: ["High", "Low"]),
            chooser=SimpleNamespace(configure=lambda **_: None),
            choice=SimpleNamespace(get=lambda: value[0], set=lambda new: value.__setitem__(0, new)),
            load=lambda quiet=False: loads.append(quiet),
            kind="graphics",
        )
        tab.dirty = lambda: gui.PresetTab.dirty(tab)
        return tab, loads, value

    def test_unsaved_edits_survive_a_refresh(self):
        tab, loads, _ = self.tab()
        gui.PresetTab.refresh(tab)
        self.assertEqual(loads, [])

    def test_an_unchanged_preset_is_read_again(self):
        tab, loads, _ = self.tab(edited="same", shown="same")
        gui.PresetTab.refresh(tab)
        self.assertEqual(loads, [True])

    def test_a_deleted_preset_is_left_even_with_edits(self):
        tab, loads, value = self.tab(choice="Gone")
        gui.PresetTab.refresh(tab)
        self.assertEqual(value[0], tab.live)
        self.assertEqual(loads, [True])

    def test_nothing_loaded_is_never_dirty(self):
        tab, _, _ = self.tab(text="")
        self.assertFalse(gui.PresetTab.dirty(tab))


@unittest.skipIf(gui is None, "needs tkinter")
class WindowSmokeTest(unittest.TestCase):
    def test_the_window_opens_and_closes(self):
        try:
            probe = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"no display: {error}")
        probe.destroy()
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"FOG_LAUNCH_HOME": home}), \
                mock.patch.object(gui, "better_together_dir", return_value=None):
            app = gui.App(gui.Manager())
            try:
                app.update()
                self.assertEqual(len(app.tabs), 5)
                app.refresh()
                app.update()
            finally:
                app.close()


if __name__ == "__main__":
    unittest.main()
