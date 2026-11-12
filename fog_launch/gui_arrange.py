"""The window "Arrange windows": the monitors as a picture, one rectangle per game window."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from . import arrange
from .arrange import Monitor, Rect
from .core import Manager, check_position
from .gui import EMBER, EMBER_INK, GROUND, HAZE, LINE, MIST, PANEL, Dialog
from .i18n import t
from .store import APP_NAME
from .windows import Tracker

CANVAS_W, CANVAS_H = 760, 430
HANDLE = 7                      # half the size of a corner handle, in canvas pixels
COLOURS = ("#e39a55", "#6fb7c9", "#b59be0", "#86c79a", "#e0809a", "#d9c46a", "#7fa0e6", "#c98a5a")


def monitors_from(tracker: Tracker, root: tk.Misc) -> tuple[list[Monitor], bool]:
    """The monitors Windows reports, or the screen Tk sees. The flag says whether they are real."""
    found = [Monitor(area, work, primary) for area, work, primary in tracker.monitors()]
    if found:
        return found, True
    area = (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
    return [Monitor(area, area, True)], False


class ArrangeDialog(Dialog):
    """Place each entry of a launch sequence on the monitors. Result: the new positions, per entry."""

    def __init__(self, parent: tk.Misc, manager: Manager, tracker: Tracker, entries: list[dict[str, Any]]):
        super().__init__(parent, t("Arrange windows"), t("Apply"))
        self.manager = manager
        self.tracker = tracker
        self.entries = entries
        self.monitors, real = monitors_from(tracker, self)
        self.view = arrange.View(arrange.bounds(self.monitors), CANVAS_W, CANVAS_H)
        self.rects: list[Rect | None] = [
            tuple(entry["position"]) if entry.get("position") else None for entry in entries  # type: ignore[misc]
        ]
        self.selected: int | None = 0 if entries else None
        self.drag: dict[str, Any] | None = None

        top = ttk.Frame(self.body)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text=t("Layout")).pack(side="left")
        self.screen_names = [t("All monitors")] + [
            t("Monitor {number}", number=index + 1) + f" · {m.label}" for index, m in enumerate(arrange.ordered(self.monitors))
        ]
        self.screen = tk.StringVar(value=self.screen_names[1] if len(self.monitors) == 1 else self.screen_names[0])
        ttk.Combobox(top, textvariable=self.screen, values=self.screen_names, state="readonly", width=22).pack(
            side="left", padx=(8, 8))
        for label, kind in ((t("Side by side"), "row"), (t("Stacked"), "column"), (t("Grid"), "grid"),
                            (t("One per monitor"), "monitors")):
            ttk.Button(top, text=label, command=lambda kind=kind: self.preset(kind)).pack(side="left", padx=(0, 6))
        self.ratio = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text=t("Keep 16:9"), variable=self.ratio).pack(side="left", padx=(10, 0))

        middle = ttk.Frame(self.body)
        middle.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(middle, width=CANVAS_W, height=CANVAS_H, background="#0c1113",
                                highlightthickness=1, highlightbackground=LINE, cursor="arrow")
        self.canvas.pack(side="left")
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.motion)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        self.canvas.bind("<Motion>", self.hover)

        side = ttk.Frame(middle, padding=(14, 0, 0, 0))
        side.pack(side="left", fill="y")
        ttk.Label(side, text=t("Windows")).pack(anchor="w")
        self.list = tk.Listbox(side, width=26, height=8, exportselection=False, background=PANEL, foreground=MIST,
                               selectbackground=EMBER, selectforeground=EMBER_INK, highlightthickness=0,
                               borderwidth=0, activestyle="none")
        self.list.pack(fill="x", pady=(4, 10))
        self.list.bind("<<ListboxSelect>>", lambda _event: self.pick_from_list())
        fields = ttk.Frame(side)
        fields.pack(fill="x")
        self.values = [tk.StringVar() for _ in range(4)]
        for index, (label, variable) in enumerate(zip(("X", "Y", t("Width"), t("Height")), self.values)):
            ttk.Label(fields, text=label, style="Hint.TLabel").grid(row=index // 2 * 2, column=index % 2, sticky="w",
                                                                   padx=(0, 8))
            entry = ttk.Entry(fields, textvariable=variable, width=9)
            entry.grid(row=index // 2 * 2 + 1, column=index % 2, sticky="w", padx=(0, 8), pady=(0, 6))
            entry.bind("<Return>", lambda _event: (self.apply_fields(), "break")[1])
            entry.bind("<FocusOut>", lambda _event: self.apply_fields())
        ttk.Button(side, text=t("Place"), command=self.place_selected).pack(fill="x", pady=(4, 0))
        ttk.Button(side, text=t("Do not arrange"), command=self.clear_selected).pack(fill="x", pady=(6, 0))
        ttk.Button(side, text=t("Take from running windows"), command=self.from_running).pack(fill="x", pady=(18, 0))
        self.snap = tk.BooleanVar(value=True)
        ttk.Checkbutton(side, text=t("Snap to edges"), variable=self.snap).pack(anchor="w", pady=(10, 0))

        hint = t("Drag a window to move it, drag a corner to resize it. Arranging works with the display mode "
                 "\"Window\" or \"Borderless window\".")
        if not real:
            hint += " " + t("The monitors could not be read; this shows only the main screen.")
        ttk.Label(self.body, text=hint, style="Hint.TLabel", wraplength=CANVAS_W + 230, justify="left").pack(
            anchor="w", pady=(10, 0))
        self.bind("<Return>", lambda _event: None)       # Return belongs to the fields here
        self.fill_list()
        self.draw()

    # ------------------------------------------------------------- helpers

    def colour(self, index: int) -> str:
        return COLOURS[index % len(COLOURS)]

    def others(self, index: int) -> list[Rect]:
        return [rect for i, rect in enumerate(self.rects) if rect is not None and i != index]

    def target_area(self) -> list[Monitor]:
        """The monitors the layout buttons fill."""
        choice = self.screen_names.index(self.screen.get())
        return self.monitors if choice == 0 else [arrange.ordered(self.monitors)[choice - 1]]

    def fill_list(self) -> None:
        self.list.delete(0, "end")
        for index, entry in enumerate(self.entries):
            rect = self.rects[index]
            where = f"{rect[2]}×{rect[3]}" if rect else t("not arranged")
            self.list.insert("end", f"{index + 1}. {entry['profile']}  ·  {where}")
            self.list.itemconfigure(index, foreground=self.colour(index) if rect else HAZE)
        if self.selected is not None:
            self.list.selection_clear(0, "end")
            self.list.selection_set(self.selected)
        self.show_fields()

    def show_fields(self) -> None:
        rect = self.rects[self.selected] if self.selected is not None else None
        for variable, value in zip(self.values, rect or ("", "", "", "")):
            variable.set(str(value))

    def select(self, index: int | None) -> None:
        self.selected = index
        self.fill_list()
        self.draw()

    def changed(self) -> None:
        self.fill_list()
        self.draw()

    # -------------------------------------------------------------- drawing

    def draw(self) -> None:
        c = self.canvas
        c.delete("all")
        for number, monitor in enumerate(arrange.ordered(self.monitors), start=1):
            x0, y0, x1, y1 = self.view.to_canvas(monitor.area)
            c.create_rectangle(x0, y0, x1, y1, fill=PANEL, outline=LINE, width=2)
            wx0, wy0, wx1, wy1 = self.view.to_canvas(monitor.work)
            if (wx0, wy0, wx1, wy1) != (x0, y0, x1, y1):
                c.create_rectangle(x0, y0, x1, y1, fill="#141d21", outline="")
                c.create_rectangle(wx0, wy0, wx1, wy1, fill=PANEL, outline="")
                c.create_rectangle(x0, y0, x1, y1, outline=LINE, width=2)
            label = f"{number} · {monitor.label}" + (f" · {t('main')}" if monitor.primary else "")
            c.create_text(x0 + 8, y0 + 6, text=label, anchor="nw", fill=HAZE, font=("TkDefaultFont", 9))
        order = [i for i in range(len(self.rects)) if i != self.selected] + (
            [self.selected] if self.selected is not None else [])
        for index in order:
            rect = self.rects[index]
            if rect is None:
                continue
            x0, y0, x1, y1 = self.view.to_canvas(rect)
            colour = self.colour(index)
            chosen = index == self.selected
            c.create_rectangle(x0, y0, x1, y1, fill="#1d2a30" if chosen else GROUND, outline=colour,
                               width=3 if chosen else 2)
            c.create_rectangle(x0, y0, x1, y0 + 18, fill=colour, outline=colour)
            name = f"{index + 1}. {self.entries[index]['profile']}"
            c.create_text(x0 + 6, y0 + 9, text=name, anchor="w", fill=EMBER_INK, font=("TkDefaultFont", 9, "bold"))
            c.create_text((x0 + x1) / 2, (y0 + y1) / 2 + 8, text=f"{rect[2]} × {rect[3]}", fill=MIST,
                          font=("TkDefaultFont", 10))
            if chosen:
                for hx, hy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                    c.create_rectangle(hx - HANDLE, hy - HANDLE, hx + HANDLE, hy + HANDLE, fill=colour,
                                       outline=EMBER_INK)

    # ------------------------------------------------------------ the mouse

    def hit(self, cx: float, cy: float) -> tuple[int, str | None] | None:
        """The window under the mouse (selected one first) and the corner, if the mouse is on one."""
        order = ([self.selected] if self.selected is not None else []) + [
            i for i in reversed(range(len(self.rects))) if i != self.selected]
        for index in order:
            rect = self.rects[index]
            if rect is None:
                continue
            x0, y0, x1, y1 = self.view.to_canvas(rect)
            for corner, (hx, hy) in (("nw", (x0, y0)), ("ne", (x1, y0)), ("sw", (x0, y1)), ("se", (x1, y1))):
                if abs(cx - hx) <= HANDLE + 2 and abs(cy - hy) <= HANDLE + 2:
                    return index, corner
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                return index, None
        return None

    def hover(self, event: tk.Event) -> None:
        found = self.hit(event.x, event.y)
        cursors = {"nw": "top_left_corner", "ne": "top_right_corner", "sw": "bottom_left_corner",
                   "se": "bottom_right_corner"}
        self.canvas.configure(cursor="arrow" if not found else cursors.get(found[1] or "", "fleur"))

    def press(self, event: tk.Event) -> None:
        found = self.hit(event.x, event.y)
        if not found:
            self.drag = None
            return
        index, corner = found
        if index != self.selected:
            self.select(index)
        self.drag = {"index": index, "corner": corner, "start": (event.x, event.y), "rect": self.rects[index]}

    def motion(self, event: tk.Event) -> None:
        if not self.drag:
            return
        index, corner, start, rect = self.drag["index"], self.drag["corner"], self.drag["start"], self.drag["rect"]
        dx = self.view.distance(event.x - start[0])
        dy = self.view.distance(event.y - start[1])
        distance = self.view.distance(8)
        if corner:
            new = arrange.resize(rect, corner, dx, dy)
            if self.snap.get():
                new = arrange.snap_resize(new, corner, self.monitors, self.others(index), distance)
        else:
            new = (rect[0] + dx, rect[1] + dy, rect[2], rect[3])
            if self.snap.get():
                new = arrange.snap_move(new, self.monitors, self.others(index), distance)
        if arrange.on_screen(new, self.monitors):
            self.rects[index] = new
            self.show_fields()
            self.draw()

    def release(self, _event: tk.Event) -> None:
        if self.drag:
            self.drag = None
            self.fill_list()

    # -------------------------------------------------------------- actions

    def pick_from_list(self) -> None:
        selection = self.list.curselection()
        if selection:
            self.select(selection[0])

    def preset(self, kind: str) -> None:
        count = len(self.entries)
        if not count:
            return
        rects = arrange.layout(kind, count, self.target_area())
        if self.ratio.get():
            rects = arrange.keep_ratio(rects)
        self.rects = [arrange.normalise(rect) for rect in rects]
        self.changed()

    def place_selected(self) -> None:
        if self.selected is None:
            return
        work = arrange.ordered(self.target_area())[0].work
        width, height = min(1280, work[2]), min(720, work[3])
        step = 40 * self.selected
        rect = (work[0] + step, work[1] + step, width, height)
        self.rects[self.selected] = rect if arrange.on_screen(rect, self.monitors) else (work[0], work[1], width, height)
        self.changed()

    def clear_selected(self) -> None:
        if self.selected is not None:
            self.rects[self.selected] = None
            self.changed()

    def apply_fields(self) -> None:
        if self.selected is None:
            return
        values = [variable.get().strip() for variable in self.values]
        if not all(values):
            return
        try:
            rect = tuple(check_position(values) or ())
        except Exception:  # noqa: BLE001 - a half-typed number: keep the old rectangle
            self.show_fields()
            return
        if rect and rect != self.rects[self.selected]:
            self.rects[self.selected] = rect  # type: ignore[assignment]
            self.changed()

    def from_running(self) -> None:
        if not self.tracker.available:
            messagebox.showinfo(APP_NAME, t("Game windows can only be found and arranged on Windows."), parent=self)
            return
        taken = 0
        for index, entry in enumerate(self.entries):
            rect = self.tracker.position_of(entry["profile"])
            if rect:
                self.rects[index] = rect
                taken += 1
        if not taken:
            messagebox.showinfo(APP_NAME, t("None of these profiles has a game window open that Fog Launch launched."),
                                parent=self)
            return
        self.changed()

    def collect(self) -> Any:
        self.apply_fields()
        return [list(rect) if rect else None for rect in self.rects]
