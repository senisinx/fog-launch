"""Finding, arranging and closing the game's windows.

Only ordinary window functions of Windows are used, the same ones any window
manager uses: list the top-level windows, read their class and title, move
them, and ask them to close. Fog Launch opens no handle to the game's process
and does not touch its memory or input.

Which window belongs to which profile is not something Windows can tell. Fog
Launch notes the order it launched the profiles in and gives each newly
appearing game window to the oldest launch still waiting for one.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

GAME_CLASS = "UnrealWindow"
WAIT_FOR_WINDOW = 240  # seconds a launch waits for its window
MOVE_AGAIN_AFTER = (0, 5, 15, 30)  # seconds after the window appeared; the game may resize itself


class Backend:
    """What the tracker needs from the system. Off Windows nothing is found."""

    available = False

    def game_windows(self) -> list[int]:
        return []

    def alive(self, window: int) -> bool:
        return False

    def move(self, window: int, x: int, y: int, width: int, height: int) -> None:
        pass

    def rect(self, window: int) -> tuple[int, int, int, int] | None:
        return None

    def close(self, window: int) -> None:
        pass

    def monitors(self) -> list[tuple[tuple[int, int, int, int], tuple[int, int, int, int], bool]]:
        """(area, work area, primary) of every monitor; empty where the system cannot tell."""
        return []


class WindowsBackend(Backend):
    available = True

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user32.EnumWindows.argtypes = [self.enum_proc, wintypes.LPARAM]
        for name in ("IsWindowVisible", "IsWindow"):
            getattr(self.user32, name).argtypes = [wintypes.HWND]
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND] + [ctypes.c_int] * 4 + [wintypes.UINT]
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]

    def _text(self, function: Callable[..., int], window: int) -> str:
        buffer = self.ctypes.create_unicode_buffer(256)
        function(window, buffer, 256)
        return buffer.value

    def game_windows(self) -> list[int]:
        found: list[int] = []

        def visit(window: int, _parameter: int) -> bool:
            if self.user32.IsWindowVisible(window) and self._text(self.user32.GetClassNameW, window) == GAME_CLASS:
                title = self._text(self.user32.GetWindowTextW, window).replace(" ", "").casefold()
                if "deadbydaylight" in title:
                    found.append(int(window))
            return True

        self.user32.EnumWindows(self.enum_proc(visit), 0)
        return found

    def alive(self, window: int) -> bool:
        return bool(self.user32.IsWindow(window))

    def move(self, window: int, x: int, y: int, width: int, height: int) -> None:
        swp_nozorder, swp_noactivate = 0x0004, 0x0010
        self.user32.ShowWindow(window, 9)  # SW_RESTORE, in case it is maximised
        self.user32.SetWindowPos(window, None, x, y, width, height, swp_nozorder | swp_noactivate)

    def rect(self, window: int) -> tuple[int, int, int, int] | None:
        box = self.wintypes.RECT()
        if not self.user32.GetWindowRect(window, self.ctypes.byref(box)):
            return None
        return box.left, box.top, box.right - box.left, box.bottom - box.top

    def close(self, window: int) -> None:
        self.user32.PostMessageW(window, 0x0010, 0, 0)  # WM_CLOSE, the same as the window's X

    def monitors(self) -> list[tuple[tuple[int, int, int, int], tuple[int, int, int, int], bool]]:
        ctypes, wintypes = self.ctypes, self.wintypes

        class MonitorInfo(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                           ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        self.user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, callback_type, wintypes.LPARAM]
        self.user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
        found = []

        def box(r: object) -> tuple[int, int, int, int]:
            return r.left, r.top, r.right - r.left, r.bottom - r.top  # type: ignore[attr-defined]

        def visit(monitor: int, _dc: int, _rect: object, _parameter: int) -> bool:
            info = MonitorInfo()
            info.cbSize = ctypes.sizeof(MonitorInfo)
            if self.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                found.append((box(info.rcMonitor), box(info.rcWork), bool(info.dwFlags & 1)))
            return True

        self.user32.EnumDisplayMonitors(None, None, callback_type(visit), 0)
        return found


def default_backend() -> Backend:
    if os.name == "nt":
        try:
            return WindowsBackend()
        except (OSError, AttributeError):
            pass
    return Backend()


Position = tuple[int, int, int, int]


@dataclass
class _Waiting:
    profile: str
    position: Position | None
    deadline: float


@dataclass
class _Placing:
    window: int
    position: Position
    times: list[float] = field(default_factory=list)


class Tracker:
    """Keeps track of which game window belongs to which profile."""

    def __init__(self, backend: Backend | None = None, clock: Callable[[], float] = time.monotonic,
                 poll: float = 0.5):
        self.backend = backend or default_backend()
        self.clock = clock
        self.poll = poll
        self._lock = threading.Lock()
        self._known: set[int] = set(self.backend.game_windows())
        self._owner: dict[str, int] = {}
        self._waiting: list[_Waiting] = []
        self._placing: list[_Placing] = []
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return self.backend.available

    def expect(self, profile: str, position: Position | None = None) -> None:
        """A profile was just launched: its window is the next new one to appear."""
        if not self.available:
            return
        with self._lock:
            self._known.update(self.backend.game_windows())
            self._waiting.append(_Waiting(profile, position, self.clock() + WAIT_FOR_WINDOW))
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._watch, daemon=True)
                self._thread.start()

    def step(self) -> None:
        """One look at the windows. The watcher calls this; tests call it directly."""
        now = self.clock()
        with self._lock:
            windows = self.backend.game_windows()
            for window in windows:
                if window in self._known:
                    continue
                self._known.add(window)
                self._waiting = [w for w in self._waiting if w.deadline > now]
                if not self._waiting:
                    continue
                waiting = self._waiting.pop(0)
                self._owner[waiting.profile] = window
                if waiting.position:
                    self._placing.append(_Placing(window, waiting.position, [now + s for s in MOVE_AGAIN_AFTER]))
            self._waiting = [w for w in self._waiting if w.deadline > now]
            for placing in self._placing:
                due = [moment for moment in placing.times if moment <= now]
                if due and self.backend.alive(placing.window):
                    self.backend.move(placing.window, *placing.position)
                placing.times = [moment for moment in placing.times if moment > now]
            self._placing = [p for p in self._placing if p.times and self.backend.alive(p.window)]

    def busy(self) -> bool:
        with self._lock:
            return bool(self._waiting or self._placing)

    def _watch(self) -> None:
        while True:
            self.step()
            if not self.busy():
                with self._lock:
                    if not self._waiting and not self._placing:
                        self._thread = None
                        return
            time.sleep(self.poll)

    def wait(self, timeout: float) -> None:
        """Block until no launch waits for its window any more, or the time is up."""
        end = time.monotonic() + timeout
        while self.busy() and time.monotonic() < end:
            time.sleep(self.poll)

    def window_of(self, profile: str) -> int | None:
        with self._lock:
            window = self._owner.get(profile)
        if window is not None and self.backend.alive(window):
            return window
        return None

    def running(self) -> dict[str, int]:
        """Profiles whose game window is open."""
        with self._lock:
            owners = dict(self._owner)
        return {profile: window for profile, window in owners.items() if self.backend.alive(window)}

    def unknown_windows(self) -> list[int]:
        """Open game windows that no profile launched by this Fog Launch owns."""
        owned = set(self.running().values())
        return [window for window in self.backend.game_windows() if window not in owned]

    def position_of(self, profile: str) -> Position | None:
        window = self.window_of(profile)
        return self.backend.rect(window) if window is not None else None

    def close(self, profile: str) -> bool:
        window = self.window_of(profile)
        if window is None:
            return False
        self.backend.close(window)
        return True

    def monitors(self) -> list:
        return self.backend.monitors()

    def close_all(self) -> int:
        windows = self.backend.game_windows()
        for window in windows:
            self.backend.close(window)
        return len(windows)
