"""The Fog Launch window."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from . import __version__, ini
from .core import (
    LOGIN_URL,
    Manager,
    better_together_dir,
    import_better_together,
    read_better_together,
    split_arguments,
)
from .i18n import set_language, t
from .runner import Cancelled, Runner
from .store import APP_NAME, FogError

GROUND = "#11171a"
PANEL = "#182125"
LINE = "#2b383d"
MIST = "#c9d6d6"
HAZE = "#8a9c9f"
EMBER = "#e39a55"
EMBER_INK = "#1a1109"
OK = "#86c79a"

KEYS = (
    ["LeftMouseButton", "RightMouseButton", "MiddleMouseButton", "ThumbMouseButton", "ThumbMouseButton2"]
    + ["MouseScrollUp", "MouseScrollDown", "SpaceBar", "LeftShift", "LeftControl", "LeftAlt", "Tab"]
    + ["CapsLock", "Enter", "Escape", "Up", "Down", "Left", "Right"]
    + [chr(code) for code in range(ord("A"), ord("Z") + 1)]
    + ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    + [f"F{number}" for number in range(1, 13)]
)

QUALITY_LABELS = {
    "sg.ViewDistanceQuality": "View distance",
    "sg.AntiAliasingQuality": "Anti-aliasing",
    "sg.ShadowQuality": "Shadows",
    "sg.GlobalIlluminationQuality": "Global illumination",
    "sg.ReflectionQuality": "Reflections",
    "sg.PostProcessQuality": "Post-processing",
    "sg.TextureQuality": "Textures",
    "sg.EffectsQuality": "Effects",
    "sg.FoliageQuality": "Foliage",
    "sg.ShadingQuality": "Shading",
    "sg.LandscapeQuality": "Landscape",
    "sg.AnimationQuality": "Animation",
}


def say(error: FogError) -> str:
    """An error in the window's language."""
    return t(error.template, **error.values)


def open_folder(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def apply_style(root: tk.Misc) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    family = "Segoe UI" if os.name == "nt" else "TkDefaultFont"
    font = (family, 10)
    root.option_add("*Font", font)
    root.option_add("*TCombobox*Listbox.background", PANEL)
    root.option_add("*TCombobox*Listbox.foreground", MIST)
    root.option_add("*TCombobox*Listbox.selectBackground", EMBER)
    root.option_add("*TCombobox*Listbox.selectForeground", EMBER_INK)
    style.configure(".", background=GROUND, foreground=MIST, bordercolor=LINE, font=font,
                    lightcolor=LINE, darkcolor=LINE, troughcolor=PANEL, focuscolor=EMBER)
    style.configure("TFrame", background=GROUND)
    style.configure("TLabel", background=GROUND, foreground=MIST)
    style.configure("Hint.TLabel", foreground=HAZE)
    style.configure("Good.TLabel", foreground=OK)
    style.configure("Title.TLabel", font=(family, 15, "bold"))
    style.configure("TButton", background=PANEL, foreground=MIST, padding=(10, 5), borderwidth=1, width=0)
    style.map("TButton", background=[("disabled", GROUND), ("active", LINE)],
              foreground=[("disabled", LINE)])
    style.configure("Accent.TButton", background=EMBER, foreground=EMBER_INK, font=(family, 10, "bold"))
    style.map("Accent.TButton", background=[("disabled", GROUND), ("active", "#f0b377")],
              foreground=[("disabled", LINE)])
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=PANEL, foreground=MIST, insertcolor=MIST,
                        arrowcolor=MIST, background=PANEL, padding=4)
        style.map(name, fieldbackground=[("disabled", GROUND), ("readonly", PANEL)],
                  foreground=[("disabled", LINE)], arrowcolor=[("disabled", LINE)],
                  background=[("disabled", GROUND)], selectbackground=[("readonly", PANEL)],
                  selectforeground=[("readonly", MIST)])
    style.configure("TCheckbutton", background=GROUND, foreground=MIST, indicatorcolor=PANEL)
    style.map("TCheckbutton", background=[("active", GROUND)], foreground=[("disabled", LINE)],
              indicatorcolor=[("selected", EMBER)])
    style.configure("TRadiobutton", background=GROUND, foreground=MIST, indicatorcolor=PANEL)
    style.map("TRadiobutton", background=[("active", GROUND)], indicatorcolor=[("selected", EMBER)])
    style.configure("TNotebook", background=GROUND, borderwidth=0)
    style.configure("TNotebook.Tab", background=GROUND, foreground=HAZE, padding=(16, 8))
    style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", EMBER)])
    style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=MIST,
                    rowheight=26, borderwidth=0)
    style.map("Treeview", background=[("selected", EMBER)], foreground=[("selected", EMBER_INK)])
    style.configure("Treeview.Heading", background=GROUND, foreground=HAZE, relief="flat")
    style.map("Treeview.Heading", background=[("active", GROUND)])
    style.configure("TLabelframe", background=GROUND, bordercolor=LINE)
    style.configure("TLabelframe.Label", background=GROUND, foreground=HAZE)
    style.configure("Vertical.TScrollbar", background=PANEL, arrowcolor=HAZE)


class Dialog(tk.Toplevel):
    """A modal window with OK and Cancel. `self.result` stays None on cancel."""

    def __init__(self, parent: tk.Misc, title: str, ok_text: str | None = None):
        super().__init__(parent)
        self.title(title)
        self.configure(background=GROUND, padx=16, pady=14)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.result: Any = None
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True)
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text=t("Cancel"), command=self.destroy).pack(side="right")
        self.ok_button = ttk.Button(buttons, text=ok_text or t("OK"), style="Accent.TButton", command=self._ok)
        self.ok_button.pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._ok())

    def collect(self) -> Any:
        raise NotImplementedError

    def _ok(self) -> None:
        try:
            result = self.collect()
        except FogError as error:
            messagebox.showerror(APP_NAME, say(error), parent=self)
            return
        if result is not None:
            self.result = result
            self.destroy()

    def show(self) -> Any:
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_reqwidth()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_reqheight()) // 3)
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.wait_window()
        return self.result


class AskName(Dialog):
    def __init__(self, parent: tk.Misc, title: str, label: str, initial: str = ""):
        super().__init__(parent, title)
        ttk.Label(self.body, text=label).pack(anchor="w")
        self.value = tk.StringVar(value=initial)
        entry = ttk.Entry(self.body, textvariable=self.value, width=36)
        entry.pack(fill="x", pady=(6, 0))
        entry.focus_set()
        entry.select_range(0, "end")

    def collect(self) -> Any:
        return self.value.get().strip() or None


class SignIn(Dialog):
    """Asks how to sign in. Result: ("window", None) or ("code", text)."""

    def __init__(self, parent: tk.Misc, profile: str):
        super().__init__(parent, t("Sign in: {name}", name=profile), t("Sign in with this code"))
        wrap = 460
        ttk.Label(self.body, text=t("Way 1: Legendary's own sign-in window"), style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            self.body,
            wraplength=wrap,
            justify="left",
            text=t(
                "Legendary opens a window with Epic's sign-in page. "
                "You type your password there, not into Fog Launch."
            ),
        ).pack(anchor="w", pady=(4, 8))
        ttk.Button(self.body, text=t("Open sign-in window"), command=self._window).pack(anchor="w")
        ttk.Label(self.body, text=t("Way 2: your browser and a code"), style="Title.TLabel").pack(
            anchor="w", pady=(18, 0)
        )
        ttk.Label(
            self.body,
            wraplength=wrap,
            justify="left",
            text=t(
                "Sign in to Epic in your browser with the account for this profile. "
                "The page then shows a short text containing \"authorizationCode\". "
                "Paste that text or just the code here. Use a private browser window "
                "if the browser is signed in to a different Epic account."
            ),
        ).pack(anchor="w", pady=(4, 8))
        ttk.Button(self.body, text=t("Open Epic's page in the browser"), command=lambda: webbrowser.open(LOGIN_URL)).pack(
            anchor="w"
        )
        self.code = tk.StringVar()
        ttk.Entry(self.body, textvariable=self.code, width=60).pack(fill="x", pady=(8, 0))

    def _window(self) -> None:
        self.result = ("window", None)
        self.destroy()

    def collect(self) -> Any:
        code = self.code.get().strip()
        return ("code", code) if code else None


class SequenceEntry(Dialog):
    def __init__(self, parent: tk.Misc, manager: Manager, entry: dict[str, Any] | None = None):
        super().__init__(parent, t("Profile in the sequence"))
        self.manager = manager
        entry = entry or {}
        self.current = t("(current settings)")
        self.profile = tk.StringVar(value=entry.get("profile") or "")
        self.graphics = tk.StringVar(value=entry.get("graphics") or self.current)
        self.input = tk.StringVar(value=entry.get("input") or self.current)
        self.game_dir = tk.StringVar(value=entry.get("game_dir") or "")
        rows = (
            (t("Profile"), self.profile, manager.profiles()),
            (t("Graphics preset"), self.graphics, [self.current, *manager.presets("graphics")]),
            (t("Input preset"), self.input, [self.current, *manager.presets("input")]),
        )
        for row, (label, variable, values) in enumerate(rows):
            ttk.Label(self.body, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 12))
            ttk.Combobox(self.body, textvariable=variable, values=values, state="readonly", width=34).grid(
                row=row, column=1, columnspan=2, sticky="ew", pady=4
            )
        ttk.Label(self.body, text=t("Game folder")).grid(row=3, column=0, sticky="w", pady=4, padx=(0, 12))
        ttk.Entry(self.body, textvariable=self.game_dir, width=30).grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Button(self.body, text=t("Browse…"), command=self._browse).grid(row=3, column=2, padx=(6, 0))
        ttk.Label(self.body, text=t("Empty: the folder from the settings."), style="Hint.TLabel").grid(
            row=4, column=1, columnspan=2, sticky="w"
        )

    def _browse(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title=t("Game folder"))
        if chosen:
            self.game_dir.set(chosen)

    def collect(self) -> Any:
        if not self.profile.get():
            return None
        game_dir = self.game_dir.get().strip()
        if game_dir:
            game_dir = str(self.manager.check_game_dir(game_dir))
        return {
            "profile": self.profile.get(),
            "graphics": None if self.graphics.get() == self.current else self.graphics.get(),
            "input": None if self.input.get() == self.current else self.input.get(),
            "game_dir": game_dir or None,
        }


class BindingDialog(Dialog):
    def __init__(self, parent: tk.Misc, names: list[str], binding: ini.Binding | None = None):
        super().__init__(parent, t("Key binding"))
        self.binding = binding
        self.kinds = {t("Action"): "action", t("Axis"): "axis"}
        kind_label = next(label for label, kind in self.kinds.items() if kind == (binding.kind if binding else "action"))
        self.kind = tk.StringVar(value=kind_label)
        self.name = tk.StringVar(value=binding.name if binding else "")
        self.key = tk.StringVar(value=binding.key if binding else "")
        self.scale = tk.StringVar(value=binding.scale if binding else "1.000000")
        self.held = {
            name: tk.BooleanVar(value=bool(binding and getattr(binding, name)))
            for name in ("shift", "ctrl", "alt", "cmd")
        }
        rows = (
            (t("Type"), ttk.Combobox(self.body, textvariable=self.kind, values=list(self.kinds), state="readonly")),
            (t("Name in the game"), ttk.Combobox(self.body, textvariable=self.name, values=names, width=34)),
            (t("Key"), ttk.Combobox(self.body, textvariable=self.key, values=KEYS)),
        )
        for row, (label, widget) in enumerate(rows):
            ttk.Label(self.body, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 12))
            widget.grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Label(self.body, text=t("Held with it (actions)")).grid(row=3, column=0, sticky="w", pady=4, padx=(0, 12))
        held = ttk.Frame(self.body)
        held.grid(row=3, column=1, sticky="w")
        for name, variable in self.held.items():
            ttk.Checkbutton(held, text=name.capitalize(), variable=variable).pack(side="left", padx=(0, 10))
        ttk.Label(self.body, text=t("Scale (axes)")).grid(row=4, column=0, sticky="w", pady=4, padx=(0, 12))
        ttk.Entry(self.body, textvariable=self.scale, width=12).grid(row=4, column=1, sticky="w", pady=4)
        ttk.Label(
            self.body,
            style="Hint.TLabel",
            text=t("Key names are Unreal Engine's, for example E, SpaceBar or LeftMouseButton."),
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def collect(self) -> Any:
        name, key = self.name.get().strip(), self.key.get().strip()
        if not name or not key:
            return None
        for text in (name, key):
            if any(character in text for character in '",()=\n'):
                raise FogError("Names and keys must not contain quotation marks, commas, brackets or '='.")
        try:
            scale = f"{float(self.scale.get().replace(',', '.')):.6f}"
        except ValueError as error:
            raise FogError("The scale must be a number, for example 1 or -1.") from error
        return ini.Binding(
            self.kinds[self.kind.get()],
            name,
            key,
            *(variable.get() for variable in self.held.values()),
            scale=scale,
            section=self.binding.section if self.binding else None,
        )


class TakeOver(Dialog):
    """Choose how to take over Better Together. Result: (folder, copy_to or None)."""

    def __init__(self, parent: tk.Misc, folder: Path | None):
        super().__init__(parent, t("Take over from Better Together"), t("Take over"))
        self.folder = tk.StringVar(value=str(folder or ""))
        self.mode = tk.StringVar(value="direct")
        self.copy_to = tk.StringVar()
        self.summary = tk.StringVar()
        wrap = 520
        ttk.Label(self.body, text=t("Better Together's settings folder")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(self.body, textvariable=self.folder, width=58).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(self.body, text=t("Browse…"), command=self._browse_source).grid(row=1, column=1, padx=(6, 0))
        ttk.Label(self.body, textvariable=self.summary, style="Good.TLabel", wraplength=wrap, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(2, 10)
        )
        ttk.Radiobutton(
            self.body, variable=self.mode, value="direct", text=t("Use Better Together's profile folder as it is (recommended)")
        ).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Label(
            self.body,
            style="Hint.TLabel",
            wraplength=wrap,
            justify="left",
            text=t(
                "Nothing is copied or changed. Both programs then share the same sign-ins, "
                "and you can keep using either."
            ),
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=(22, 0))
        ttk.Radiobutton(self.body, variable=self.mode, value="copy", text=t("Copy the profiles to a new folder")).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Label(
            self.body,
            style="Hint.TLabel",
            wraplength=wrap,
            justify="left",
            text=t(
                "The originals stay untouched. Epic may sign a copy out as soon as the "
                "other copy is used, so stop using Better Together afterwards."
            ),
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=(22, 0))
        ttk.Entry(self.body, textvariable=self.copy_to).grid(row=7, column=0, sticky="ew", pady=4, padx=(22, 0))
        ttk.Button(self.body, text=t("Browse…"), command=self._browse_target).grid(row=7, column=1, padx=(6, 0))
        self.folder.trace_add("write", lambda *_: self._describe())
        self._describe()

    def _describe(self) -> None:
        try:
            found = read_better_together(self.folder.get())
        except (FogError, OSError):
            self.summary.set(t("No Better Together settings here."))
            return
        self.summary.set(
            t(
                "Found – profiles: {profiles}, launch presets: {sequences}, profile folder: {library}",
                profiles=len(found["profiles"]),
                sequences=len(found["sequences"]),
                library=found["library"] or "–",
            )
        )

    def _browse_source(self) -> None:
        chosen = filedialog.askdirectory(parent=self, initialdir=str(Path.home()))
        if chosen:
            self.folder.set(chosen)

    def _browse_target(self) -> None:
        chosen = filedialog.askdirectory(parent=self)
        if chosen:
            self.copy_to.set(chosen)
            self.mode.set("copy")

    def collect(self) -> Any:
        read_better_together(self.folder.get())
        if self.mode.get() == "copy":
            if not self.copy_to.get().strip():
                raise FogError("Choose the folder the profiles are copied to.")
            return (self.folder.get(), self.copy_to.get().strip())
        return (self.folder.get(), None)


def table(parent: tk.Misc, columns: list[tuple[str, str, int]], height: int = 8) -> ttk.Treeview:
    """A list with headings. `columns` holds (id, heading, width)."""
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", height=height, selectmode="browse")
    for name, heading, width in columns:
        tree.heading(name, text=heading, anchor="w")
        tree.column(name, width=width, anchor="w", stretch=True)
    bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=bar.set)
    tree.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")
    tree.frame = frame  # type: ignore[attr-defined]
    return tree


def selected_index(tree: ttk.Treeview) -> int | None:
    selection = tree.selection()
    return tree.index(selection[0]) if selection else None


class Tab(ttk.Frame):
    title = ""

    def __init__(self, app: "App"):
        super().__init__(app.notebook, padding=14)
        self.app = app
        self.manager = app.manager
        self.actions: list[ttk.Button] = []  # disabled while Legendary is working

    def button(self, parent: tk.Misc, text: str, command: Callable[[], None], accent: bool = False,
               action: bool = False) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=self.app.guard(command),
                            style="Accent.TButton" if accent else "TButton")
        if action:
            self.actions.append(button)
        return button

    def refresh(self) -> None:
        pass


class ProfilesTab(Tab):
    title = "Profiles"

    def __init__(self, app: "App"):
        super().__init__(app)
        self.tree = table(
            self,
            [("profile", t("Profile"), 180), ("account", t("Epic account"), 200), ("game", t("Game folder"), 380)],
            height=9,
        )
        self.tree.frame.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _event: self.app.guard(self.launch)())
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(10, 0))
        self.button(bar, t("New…"), self.new).pack(side="left")
        self.button(bar, t("Rename…"), self.rename, action=True).pack(side="left", padx=(6, 0))
        self.button(bar, t("Delete"), self.delete, action=True).pack(side="left", padx=(6, 0))
        self.button(bar, t("Sign in…"), self.sign_in, action=True).pack(side="left", padx=(24, 0))
        self.button(bar, t("Sign out"), self.sign_out, action=True).pack(side="left", padx=(6, 0))
        self.button(bar, t("Launch"), self.launch, accent=True, action=True).pack(side="right")
        self.hint = ttk.Label(self, style="Hint.TLabel", wraplength=780, justify="left")
        self.hint.pack(anchor="w", pady=(10, 0))

    def selected(self) -> str:
        index = selected_index(self.tree)
        if index is None:
            raise FogError("Select a profile first.")
        return self.manager.profiles()[index]

    def refresh(self) -> None:
        keep = selected_index(self.tree)
        self.tree.delete(*self.tree.get_children())
        profiles = self.manager.profiles()
        for profile in profiles:
            try:
                account = self.manager.account_name(profile) or t("not signed in")
                game = self.manager.game_dir_of(profile) or "–"
            except FogError:
                account, game = "?", "–"
            self.tree.insert("", "end", values=(profile, account, game))
        children = self.tree.get_children()
        if children:
            active = self.manager.config.get("active")
            index = profiles.index(active) if keep is None and active in profiles else min(keep or 0, len(children) - 1)
            self.tree.selection_set(children[index])
        if not self.manager.library:
            self.hint.configure(text=t("Start in the settings: choose a profile folder, or take over Better Together."))
        elif not profiles:
            self.hint.configure(text=t("No profiles yet. Create one, then sign it in to Epic."))
        else:
            self.hint.configure(text=t("Double-click a profile to launch it. Each profile keeps its own Epic sign-in."))

    def new(self) -> None:
        if not self.manager.library:
            raise FogError("Choose a profile folder in the settings first.")
        name = AskName(self, t("New profile"), t("Name of the profile")).show()
        if name:
            self.manager.create_profile(name)
            self.app.refresh()

    def rename(self) -> None:
        old = self.selected()
        name = AskName(self, t("Rename profile"), t("Name of the profile"), old).show()
        if name and name != old:
            self.manager.rename_profile(old, name)
            self.app.refresh()

    def delete(self) -> None:
        name = self.selected()
        question = t("Delete the profile '{name}' and its Epic sign-in? This cannot be undone.", name=name)
        if messagebox.askyesno(APP_NAME, question, parent=self, icon="warning"):
            self.manager.delete_profile(name)
            self.app.refresh()

    def sign_in(self) -> None:
        name = self.selected()
        choice = SignIn(self, name).show()
        if choice:
            self.app.work(t("Signing in {name}", name=name), lambda runner: runner.sign_in(name, choice[1]))

    def sign_out(self) -> None:
        name = self.selected()
        if messagebox.askyesno(APP_NAME, t("Sign the profile '{name}' out of Epic?", name=name), parent=self):
            self.app.work(t("Signing out {name}", name=name), lambda runner: runner.sign_out(name))

    def launch(self) -> None:
        name = self.selected()
        self.manager.set_active(name)
        self.app.work(t("Launching {name}", name=name), lambda runner: runner.launch_one(name))


class SequencesTab(Tab):
    title = "Launch sequences"

    def __init__(self, app: "App"):
        super().__init__(app)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        self.names = tk.Listbox(left, width=22, height=10, exportselection=False, background=PANEL, foreground=MIST,
                                selectbackground=EMBER, selectforeground=EMBER_INK, highlightthickness=0,
                                borderwidth=0, activestyle="none")
        self.names.pack(fill="both", expand=True)
        self.names.bind("<<ListboxSelect>>", lambda _event: self.show_entries())
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(10, 0))
        self.button(bar, t("New…"), self.new).pack(side="left")
        self.button(bar, t("Rename…"), self.rename).pack(side="left", padx=(6, 0))
        self.button(bar, t("Delete"), self.delete).pack(side="left", padx=(6, 0))

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        self.tree = table(
            right,
            [("number", "#", 30), ("profile", t("Profile"), 130), ("graphics", t("Graphics preset"), 150),
             ("input", t("Input preset"), 150), ("game", t("Game folder"), 170)],
            height=8,
        )
        self.tree.frame.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _event: self.app.guard(self.edit)())
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(10, 0))
        self.button(bar, t("Add…"), self.add).pack(side="left")
        self.button(bar, t("Edit…"), self.edit).pack(side="left", padx=(6, 0))
        self.button(bar, t("Remove"), self.remove).pack(side="left", padx=(6, 0))
        self.button(bar, "↑", lambda: self.move(-1)).pack(side="left", padx=(18, 0))
        self.button(bar, "↓", lambda: self.move(1)).pack(side="left", padx=(6, 0))
        self.button(bar, t("Launch sequence"), self.launch, accent=True, action=True).pack(side="right")
        delay = ttk.Frame(right)
        delay.pack(fill="x", pady=(10, 0))
        ttk.Label(delay, text=t("Seconds between two launches")).pack(side="left")
        self.delay = tk.StringVar(value="30")
        spin = ttk.Spinbox(delay, from_=0, to=3600, textvariable=self.delay, width=6, command=self.app.guard(self.store))
        spin.pack(side="left", padx=(8, 0))
        spin.bind("<FocusOut>", lambda _event: self.app.guard(self.store)())
        ttk.Label(right, style="Hint.TLabel", wraplength=600, justify="left",
                  text=t("With a preset, Fog Launch waits at least 30 seconds so the game can read it.")).pack(
            anchor="w", pady=(6, 0))

    def name(self) -> str | None:
        selection = self.names.curselection()
        return self.names.get(selection[0]) if selection else None

    def need_name(self) -> str:
        name = self.name()
        if not name:
            raise FogError("Select or create a sequence first.")
        return name

    def entries(self) -> list[dict[str, Any]]:
        return self.manager.sequences()[self.need_name()]["entries"]

    def refresh(self) -> None:
        keep = self.name()
        names = sorted(self.manager.sequences(), key=str.casefold)
        self.names.delete(0, "end")
        for name in names:
            self.names.insert("end", name)
        if names:
            self.names.selection_set(names.index(keep) if keep in names else 0)
        self.show_entries()

    def show_entries(self, select: int | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        name = self.name()
        if not name:
            return
        sequence = self.manager.sequences()[name]
        self.delay.set(str(sequence["delay"]))
        current = t("(current settings)")
        for number, entry in enumerate(sequence["entries"], start=1):
            self.tree.insert("", "end", values=(
                number, entry["profile"], entry.get("graphics") or current, entry.get("input") or current,
                entry.get("game_dir") or t("(from the settings)"),
            ))
        children = self.tree.get_children()
        if children and select is not None:
            self.tree.selection_set(children[max(0, min(select, len(children) - 1))])

    def store(self, entries: list[dict[str, Any]] | None = None, select: int | None = None) -> None:
        name = self.name()
        if not name:
            return
        if entries is None:
            entries = self.manager.sequences()[name]["entries"]
        delay = self.delay.get().strip() or "0"
        self.manager.save_sequence(name, entries, delay)  # type: ignore[arg-type]
        self.show_entries(select if select is not None else selected_index(self.tree))

    def new(self) -> None:
        name = AskName(self, t("New sequence"), t("Name of the sequence")).show()
        if name:
            if name in self.manager.sequences():
                raise FogError("The sequence '{name}' already exists.", name=name)
            name = self.manager.save_sequence(name, [], 30)
            self.refresh()
            self.names.selection_clear(0, "end")
            self.names.selection_set(sorted(self.manager.sequences(), key=str.casefold).index(name))
            self.show_entries()

    def rename(self) -> None:
        old = self.need_name()
        name = AskName(self, t("Rename sequence"), t("Name of the sequence"), old).show()
        if name and name != old:
            name = self.manager.rename_sequence(old, name)
            self.refresh()
            self.names.selection_clear(0, "end")
            self.names.selection_set(sorted(self.manager.sequences(), key=str.casefold).index(name))
            self.show_entries()

    def delete(self) -> None:
        name = self.need_name()
        if messagebox.askyesno(APP_NAME, t("Delete the sequence '{name}'?", name=name), parent=self):
            self.manager.delete_sequence(name)
            self.refresh()

    def add(self) -> None:
        entries = self.entries()
        entry = SequenceEntry(self, self.manager).show()
        if entry:
            self.store([*entries, entry], select=len(entries))

    def edit(self) -> None:
        entries = self.entries()
        index = selected_index(self.tree)
        if index is None:
            raise FogError("Select an entry first.")
        entry = SequenceEntry(self, self.manager, entries[index]).show()
        if entry:
            self.store([*entries[:index], entry, *entries[index + 1:]], select=index)

    def remove(self) -> None:
        entries = self.entries()
        index = selected_index(self.tree)
        if index is not None:
            self.store([*entries[:index], *entries[index + 1:]], select=index)

    def move(self, step: int) -> None:
        entries = list(self.entries())
        index = selected_index(self.tree)
        if index is None or not 0 <= index + step < len(entries):
            return
        entries[index], entries[index + step] = entries[index + step], entries[index]
        self.store(entries, select=index + step)

    def launch(self) -> None:
        name = self.need_name()
        self.store()
        self.app.work(t("Sequence {name}", name=name), lambda runner: runner.run_sequence(name))


class PresetTab(Tab):
    """Shared by the graphics and the input tab: choose, edit and save a preset."""

    kind = ""

    def __init__(self, app: "App"):
        super().__init__(app)
        self.live = t("Current game settings")
        self.text = ""
        self.encoding = "utf-8"
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text=t("Editing")).pack(side="left")
        self.choice = tk.StringVar(value=self.live)
        self.chooser = ttk.Combobox(bar, textvariable=self.choice, state="readonly", width=24)
        self.chooser.pack(side="left", padx=(8, 0))
        self.chooser.bind("<<ComboboxSelected>>", lambda _event: self.app.guard(self.load)())
        self.button(bar, t("Save"), self.save, accent=True).pack(side="left", padx=(12, 0))
        self.button(bar, t("Save as new preset…"), self.save_as).pack(side="left", padx=(6, 0))
        self.button(bar, t("Delete preset"), self.delete).pack(side="left", padx=(6, 0))
        second = ttk.Frame(self)
        second.pack(fill="x", pady=(8, 8))
        self.button(second, t("Use in the game now"), self.apply).pack(side="right", padx=(10, 0))
        self.note = ttk.Label(second, style="Hint.TLabel", wraplength=700, justify="left")
        self.note.pack(side="left")
        self.area = ttk.Frame(self)
        self.area.pack(fill="both", expand=True)

    def preset(self) -> str | None:
        return None if self.choice.get() == self.live else self.choice.get()

    def refresh(self) -> None:
        names = self.manager.presets(self.kind)
        self.chooser.configure(values=[self.live, *names])
        if self.choice.get() not in (self.live, *names):
            self.choice.set(self.live)
        self.load(quiet=True)

    def load(self, quiet: bool = False) -> None:
        try:
            self.text, self.encoding = self.manager.read_preset(self.kind, self.preset())
        except FogError as error:
            self.text = ""
            self.show("")
            self.note.configure(text=say(error))
            if not quiet:
                raise
            return
        self.note.configure(text=str(self.manager.preset_source(self.kind, self.preset())))
        self.show(self.text)

    def show(self, text: str) -> None:
        raise NotImplementedError

    def edited(self) -> str:
        raise NotImplementedError

    def save(self) -> None:
        if not self.text:
            raise FogError("There is nothing loaded to save.")
        self.manager.write_preset(self.kind, self.preset(), self.edited(), self.encoding)
        self.load()
        self.app.say(t("Saved: {file}", file=self.manager.preset_source(self.kind, self.preset())))

    def save_as(self) -> None:
        if not self.text:
            raise FogError("There is nothing loaded to save.")
        name = AskName(self, t("New preset"), t("Name of the preset")).show()
        if not name:
            return
        if name in self.manager.presets(self.kind) and not messagebox.askyesno(
            APP_NAME, t("Replace the preset '{name}'?", name=name), parent=self
        ):
            return
        file = self.manager.write_preset(self.kind, name, self.edited(), self.encoding)
        self.app.refresh()
        self.choice.set(file.name[len(self.manager.ini_path(self.kind).name) + 1:])
        self.load()

    def delete(self) -> None:
        name = self.preset()
        if not name:
            raise FogError("Choose a preset first. The current game settings cannot be deleted.")
        if messagebox.askyesno(APP_NAME, t("Delete the preset '{name}'?", name=name), parent=self):
            self.manager.delete_preset(self.kind, name)
            self.choice.set(self.live)
            self.app.refresh()

    def apply(self) -> None:
        name = self.preset()
        if not name:
            raise FogError("Choose a preset first.")
        self.manager.backup(self.kind)
        self.manager.apply_preset(self.kind, name)
        self.app.say(t("The preset '{name}' is now the game's setting. The previous file is in the backups.", name=name))


class GraphicsTab(PresetTab):
    title = "Graphics"
    kind = "graphics"

    def __init__(self, app: "App"):
        super().__init__(app)
        self.modes = [t("Fullscreen"), t("Borderless window"), t("Window")]
        self.levels = [t("Low"), t("Medium"), t("High"), t("Ultra"), "4"]
        self.variables: dict[str, tk.Variable] = {}
        self.widgets: dict[str, tk.Widget] = {}
        general = ttk.LabelFrame(self.area, text=t("Display and sound"), padding=10)
        general.pack(side="left", fill="y", padx=(0, 14))
        labels = {
            "width": "Width", "height": "Height", "fullscreen": "Display mode", "fps": "FPS limit (0 = none)",
            "render_scale": "Render scale in %", "vsync": "VSync", "dynamic_resolution": "Dynamic resolution",
            "main_volume": "Main volume", "menu_music_volume": "Menu music volume",
        }
        quality = ttk.LabelFrame(self.area, text=t("Quality"), padding=10)
        quality.pack(side="left", fill="y")
        ttk.Label(quality, style="Hint.TLabel", wraplength=440, justify="left",
                  text=t("Greyed-out fields are not in this file and stay untouched.")).grid(
            row=20, column=0, columnspan=4, sticky="w", pady=(14, 0))
        half = (len(ini.QUALITY_KEYS) + 1) // 2
        rows = {general: 0, quality: 0}
        for field in ini.FIELDS:
            parent = quality if field.kind == "quality" else general
            row = rows[parent]
            rows[parent] += 1
            label = QUALITY_LABELS[field.name] if field.kind == "quality" else labels[field.name]
            column = 0
            if field.kind == "quality" and row >= half:
                row, column = row - half, 2
            ttk.Label(parent, text=t(label)).grid(
                row=row, column=column, sticky="w", pady=3, padx=(18 if column else 0, 14))
            if field.kind == "bool":
                variable: tk.Variable = tk.BooleanVar()
                widget: tk.Widget = ttk.Checkbutton(parent, variable=variable)
            elif field.kind == "quality":
                variable = tk.StringVar()
                widget = ttk.Combobox(parent, textvariable=variable, values=self.levels, state="readonly", width=9)
            elif field.name == "fullscreen":
                variable = tk.StringVar()
                widget = ttk.Combobox(parent, textvariable=variable, values=self.modes, state="readonly", width=18)
            else:
                variable = tk.StringVar()
                widget = ttk.Spinbox(parent, textvariable=variable, from_=field.low, to=field.high, width=8)
            widget.grid(row=row, column=column + 1, sticky="w", pady=3)
            self.variables[field.name] = variable
            self.widgets[field.name] = widget

    def _choices(self, field: ini.Field) -> list[str] | None:
        if field.kind == "quality":
            return self.levels
        if field.name == "fullscreen":
            return self.modes
        return None

    def show(self, text: str) -> None:
        settings = ini.graphics_from_text(text)
        for field in ini.FIELDS:
            variable, widget = self.variables[field.name], self.widgets[field.name]
            present = field.name in settings
            choices = self._choices(field)
            if isinstance(widget, ttk.Combobox):
                widget.configure(state="readonly" if present else "disabled")
            else:
                widget.configure(state="normal" if present else "disabled")
            if not present:
                variable.set(False if field.kind == "bool" else "")
            elif choices:
                value = int(settings[field.name])  # type: ignore[call-overload]
                variable.set(choices[value] if 0 <= value < len(choices) else str(value))
            else:
                variable.set(settings[field.name])

    def edited(self) -> str:
        known = ini.graphics_from_text(self.text)
        settings: dict[str, object] = {}
        for field in ini.FIELDS:
            if field.name not in known:
                continue
            value = self.variables[field.name].get()
            choices = self._choices(field)
            if choices:
                value = choices.index(value) if value in choices else value
            settings[field.name] = value
        return ini.graphics_to_text(self.text, settings)


class InputTab(PresetTab):
    title = "Input"
    kind = "input"

    def __init__(self, app: "App"):
        super().__init__(app)
        self.bindings: list[ini.Binding] = []
        self.tree = table(
            self.area,
            [("kind", t("Type"), 70), ("name", t("Name in the game"), 300), ("key", t("Key"), 180),
             ("held", t("Held with it"), 120), ("scale", t("Scale"), 90)],
            height=9,
        )
        self.tree.frame.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _event: self.app.guard(self.edit)())
        bar = ttk.Frame(self.area)
        bar.pack(fill="x", pady=(10, 0))
        self.button(bar, t("Add…"), self.add).pack(side="left")
        self.button(bar, t("Edit…"), self.edit).pack(side="left", padx=(6, 0))
        self.button(bar, t("Remove"), self.remove).pack(side="left", padx=(6, 0))
        ttk.Label(bar, style="Hint.TLabel", text=t("Changes take effect once you press Save.")).pack(
            side="left", padx=(14, 0))

    def show(self, text: str) -> None:
        self.bindings = ini.bindings_from_text(text) if text else []
        self.fill()

    def fill(self, select: int | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for binding in self.bindings:
            action = binding.kind == "action"
            self.tree.insert("", "end", values=(
                t("Action") if action else t("Axis"), binding.name, binding.key,
                binding.modifiers() if action else "", "" if action else binding.scale,
            ))
        children = self.tree.get_children()
        if children and select is not None:
            item = children[max(0, min(select, len(children) - 1))]
            self.tree.selection_set(item)
            self.tree.see(item)

    def names(self) -> list[str]:
        return sorted({binding.name for binding in self.bindings}, key=str.casefold)

    def add(self) -> None:
        if not self.text:
            raise FogError("There is nothing loaded to save.")
        binding = BindingDialog(self, self.names()).show()
        if binding:
            self.bindings.append(binding)
            self.fill(len(self.bindings) - 1)

    def edit(self) -> None:
        index = selected_index(self.tree)
        if index is None:
            raise FogError("Select an entry first.")
        binding = BindingDialog(self, self.names(), self.bindings[index]).show()
        if binding:
            self.bindings[index] = binding
            self.fill(index)

    def remove(self) -> None:
        index = selected_index(self.tree)
        if index is not None:
            del self.bindings[index]
            self.fill(index)

    def edited(self) -> str:
        return ini.bindings_to_text(self.text, self.bindings)


class SettingsTab(Tab):
    title = "Settings"

    def __init__(self, app: "App"):
        super().__init__(app)
        self.columnconfigure(1, weight=1)
        self.paths: dict[str, tk.StringVar] = {}
        rows = (
            ("library", t("Profile folder"), self.choose_library),
            ("game_dir", t("Dead by Daylight folder"), self.choose_game),
            ("settings_ini", "GameUserSettings.ini", lambda: self.choose_ini("graphics")),
            ("input_ini", "Input.ini", lambda: self.choose_ini("input")),
            ("legendary", "Legendary", self.choose_legendary),
        )
        for row, (key, label, command) in enumerate(rows):
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 14))
            self.paths[key] = tk.StringVar()
            ttk.Entry(self, textvariable=self.paths[key], state="readonly").grid(row=row, column=1, sticky="ew", pady=5)
            self.button(self, t("Browse…"), command).grid(row=row, column=2, padx=(6, 0))
        row = len(rows)
        ttk.Label(self, text=t("Extra game arguments")).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 14))
        self.arguments = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self.arguments)
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        entry.bind("<FocusOut>", lambda _event: self.app.guard(self.store)())
        self.skip = tk.BooleanVar()
        ttk.Checkbutton(
            self, variable=self.skip, command=self.app.guard(self.store),
            text=t("Skip Legendary's version check when launching (needed for shared installations)"),
        ).grid(row=row + 1, column=1, columnspan=2, sticky="w", pady=5)
        ttk.Label(self, text=t("Language")).grid(row=row + 2, column=0, sticky="w", pady=5, padx=(0, 14))
        self.languages = {t("Automatic"): "auto", "Deutsch": "de", "English": "en"}
        self.language = tk.StringVar()
        chooser = ttk.Combobox(self, textvariable=self.language, values=list(self.languages), state="readonly", width=16)
        chooser.grid(row=row + 2, column=1, sticky="w", pady=5)
        chooser.bind("<<ComboboxSelected>>", lambda _event: self.app.guard(self.store_language)())
        bar = ttk.Frame(self)
        bar.grid(row=row + 3, column=0, columnspan=3, sticky="w", pady=(18, 0))
        self.button(bar, t("Take over from Better Together…"), self.app.take_over, action=True).pack(side="left")
        self.button(bar, t("Open Fog Launch's data folder"), lambda: open_folder(self.manager.config.dir)).pack(
            side="left", padx=(6, 0))
        ttk.Label(
            self, style="Hint.TLabel", wraplength=800, justify="left",
            text=t(
                "The profile folder holds one subfolder per profile with that profile's Epic sign-in. "
                "Treat it like a password: do not share it or put it in a synced folder."
            ),
        ).grid(row=row + 4, column=0, columnspan=3, sticky="w", pady=(18, 0))

    def refresh(self) -> None:
        manager = self.manager
        self.paths["library"].set(str(manager.library or ""))
        self.paths["game_dir"].set(str(manager.game_dir or ""))
        self.paths["settings_ini"].set(str(manager.settings_ini))
        self.paths["input_ini"].set(str(manager.input_ini))
        try:
            self.paths["legendary"].set(manager.legendary())
        except FogError:
            self.paths["legendary"].set(t("not found – run get_legendary.py or choose legendary.exe"))
        self.arguments.set(manager.config.get("launch_args") or "")
        self.skip.set(bool(manager.config.get("skip_version_check")))
        code = manager.config.get("language")
        self.language.set(next((label for label, value in self.languages.items() if value == code), t("Automatic")))

    def choose_library(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title=t("Profile folder"))
        if chosen:
            self.manager.set_library(chosen)
            self.app.refresh()

    def choose_game(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title=t("Dead by Daylight folder"))
        if chosen:
            self.manager.set_game_dir(chosen)
            if self.manager.game_template():
                self.manager.link_game()
            self.app.refresh()

    def choose_ini(self, kind: str) -> None:
        current = self.manager.ini_path(kind)
        chosen = filedialog.askopenfilename(
            parent=self, initialdir=str(current.parent) if current.parent.is_dir() else None,
            filetypes=[("INI", "*.ini"), ("*", "*")],
        )
        if chosen:
            self.manager.set_ini(kind, chosen)
            self.app.refresh()

    def choose_legendary(self) -> None:
        chosen = filedialog.askopenfilename(parent=self, title="Legendary")
        if chosen:
            self.manager.config.set("legendary", chosen)
            self.app.refresh()

    def store(self) -> None:
        split_arguments(self.arguments.get())
        self.manager.config.data["launch_args"] = self.arguments.get().strip()
        self.manager.config.data["skip_version_check"] = bool(self.skip.get())
        self.manager.config.save()

    def store_language(self) -> None:
        self.manager.config.set("language", self.languages[self.language.get()])
        self.app.say(t("The language changes the next time Fog Launch starts."))


class App(tk.Tk):
    def __init__(self, manager: Manager):
        super().__init__()
        self.manager = manager
        set_language(manager.config.get("language") or "auto")
        self.title(f"{APP_NAME} {__version__}")
        self.configure(background=GROUND)
        self.geometry("980x720")
        self.minsize(900, 640)
        apply_style(self)
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.runner: Runner | None = None

        self.log = tk.Text(self, height=7, background="#0c1113", foreground=HAZE, insertbackground=MIST,
                           borderwidth=0, highlightthickness=0, padx=10, pady=8, state="disabled", wrap="word")
        self.log.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        bottom = ttk.Frame(self, padding=(10, 8, 10, 8))
        bottom.pack(side="bottom", fill="x")
        self.status = tk.StringVar(value=t("Ready"))
        ttk.Label(bottom, textvariable=self.status, style="Good.TLabel").pack(side="left")
        self.cancel_button = ttk.Button(bottom, text=t("Cancel"), command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right")
        ttk.Button(bottom, text=t("Clear log"), command=self.clear_log).pack(side="right", padx=(0, 6))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self.tabs: list[Tab] = [cls(self) for cls in (ProfilesTab, SequencesTab, GraphicsTab, InputTab, SettingsTab)]
        for tab in self.tabs:
            self.notebook.add(tab, text=t(tab.title))

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        self.after(100, self.drain)
        self.after(300, self.first_start)

    # ----------------------------------------------------------------- helpers

    def guard(self, action: Callable[[], None]) -> Callable[[], None]:
        """Wrap a button action so that a FogError becomes a message box."""

        def guarded() -> None:
            try:
                action()
            except FogError as error:
                messagebox.showerror(APP_NAME, say(error), parent=self)
            except OSError as error:
                messagebox.showerror(APP_NAME, str(error), parent=self)

        return guarded

    def refresh(self) -> None:
        for tab in self.tabs:
            tab.refresh()

    def say(self, text: str) -> None:
        self.status.set(text)

    def write_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ------------------------------------------------------- background work

    def work(self, label: str, job: Callable[[Runner], None]) -> None:
        """Run a job that talks to Legendary, without freezing the window."""
        if self.runner:
            raise FogError("Fog Launch is still busy. Wait for it, or press Cancel.")
        self.manager.legendary()  # fail early, with a clear message
        runner = Runner(self.manager, lambda kind, text: self.events.put((kind, text)), t)
        self.runner = runner
        self.set_busy(True)
        self.say(label)

        def run() -> None:
            try:
                job(runner)
            except Cancelled:
                self.events.put(("end", t("Cancelled")))
            except FogError as error:
                self.events.put(("fail", say(error)))
            except Exception as error:  # noqa: BLE001 - shown to the user, never swallowed
                self.events.put(("fail", f"{type(error).__name__}: {error}"))
            else:
                self.events.put(("end", t("Done: {what}", what=label)))

        threading.Thread(target=run, daemon=True).start()

    def set_busy(self, busy: bool) -> None:
        self.cancel_button.configure(state="normal" if busy else "disabled")
        for tab in self.tabs:
            for button in tab.actions:
                button.configure(state="disabled" if busy else "normal")

    def cancel(self) -> None:
        if self.runner:
            self.runner.stop()

    def drain(self) -> None:
        try:
            while True:
                kind, text = self.events.get_nowait()
                if kind == "log":
                    self.write_log(text)
                elif kind == "status":
                    self.say(text)
                else:
                    self.runner = None
                    self.set_busy(False)
                    self.refresh()
                    self.say(text)
                    if kind == "fail":
                        self.write_log(text + "\n")
                        messagebox.showerror(APP_NAME, text, parent=self)
        except queue.Empty:
            pass
        self.after(100, self.drain)

    # ----------------------------------------------------------------- flows

    def take_over(self) -> None:
        choice = TakeOver(self, better_together_dir()).show()
        if not choice:
            return
        notes = import_better_together(self.manager, choice[0], choice[1])
        self.refresh()
        self.notebook.select(0)
        text = t("Taken over: {count} profiles.", count=len(self.manager.profiles()))
        if notes:
            text += "\n\n" + "\n".join(say(note) for note in notes)
        messagebox.showinfo(APP_NAME, text, parent=self)

    def first_start(self) -> None:
        if self.manager.library:
            return
        if better_together_dir():
            question = t("Better Together was used on this PC. Take over its profiles and launch presets now?")
            if messagebox.askyesno(APP_NAME, question, parent=self):
                self.guard(self.take_over)()
                return
        self.notebook.select(len(self.tabs) - 1)

    def close(self) -> None:
        if self.runner:
            self.runner.stop()
        self.destroy()


def main() -> None:
    App(Manager()).mainloop()
