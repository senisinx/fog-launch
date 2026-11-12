"""Geometry for arranging game windows on the monitors (no window code here).

Rectangles are (x, y, width, height) in Windows screen coordinates, the same
numbers SetWindowPos takes. A monitor has its full area and its work area
(without the taskbar); layouts fill the work area.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Rect = tuple[int, int, int, int]

MIN_SIZE = 200          # the smallest window a layout or a drag may produce
SNAP = 16               # screen pixels within which an edge snaps to another


@dataclass(frozen=True)
class Monitor:
    area: Rect          # the whole monitor
    work: Rect          # without the taskbar
    primary: bool = False

    @property
    def label(self) -> str:
        return f"{self.area[2]}×{self.area[3]}"


def bounds(monitors: list[Monitor]) -> Rect:
    """The rectangle around all monitors (the virtual desktop)."""
    left = min(m.area[0] for m in monitors)
    top = min(m.area[1] for m in monitors)
    right = max(m.area[0] + m.area[2] for m in monitors)
    bottom = max(m.area[1] + m.area[3] for m in monitors)
    return left, top, right - left, bottom - top


def ordered(monitors: list[Monitor]) -> list[Monitor]:
    """Monitors from left to right, then top to bottom, as the user sees them."""
    return sorted(monitors, key=lambda m: (m.area[0], m.area[1]))


# ------------------------------------------------------------------ layouts


def grid(count: int, area: Rect, columns: int | None = None) -> list[Rect]:
    """``count`` windows in rows and columns filling ``area``; the last row is centred."""
    if count <= 0:
        return []
    columns = columns or math.ceil(math.sqrt(count))
    rows = math.ceil(count / columns)
    x0, y0, width, height = area
    cell_w, cell_h = width // columns, height // rows
    rects = []
    for index in range(count):
        row, column = divmod(index, columns)
        in_row = min(columns, count - row * columns)
        offset = (columns - in_row) * cell_w // 2
        rects.append((x0 + offset + column * cell_w, y0 + row * cell_h, cell_w, cell_h))
    return rects


def side_by_side(count: int, area: Rect) -> list[Rect]:
    """All windows in one row."""
    return grid(count, area, columns=max(1, count))


def stacked(count: int, area: Rect) -> list[Rect]:
    """All windows in one column."""
    return grid(count, area, columns=1)


def spread(count: int, monitors: list[Monitor], layout=grid) -> list[Rect]:
    """Share the windows out over the monitors (left ones first) and lay them out on each with ``layout``."""
    screens = ordered(monitors)
    if count <= 0 or not screens:
        return []
    per = [count // len(screens) + (1 if i < count % len(screens) else 0) for i in range(len(screens))]
    rects: list[Rect] = []
    for screen, n in zip(screens, per):
        rects.extend(layout(n, screen.work))
    return rects


def one_per_monitor(count: int, monitors: list[Monitor]) -> list[Rect]:
    """Each window fills a monitor's work area; more windows than monitors share them as a grid."""
    return spread(count, monitors, grid)


LAYOUTS = {"row": side_by_side, "column": stacked, "grid": grid}


def layout(kind: str, count: int, monitors: list[Monitor]) -> list[Rect]:
    """The windows of a layout button: on one monitor directly, on several spread out first."""
    if kind == "monitors":
        return one_per_monitor(count, monitors)
    if len(monitors) == 1:
        return LAYOUTS[kind](count, monitors[0].work)
    return spread(count, monitors, LAYOUTS[kind])


def keep_ratio(rects: list[Rect], ratio: float = 16 / 9) -> list[Rect]:
    """Shrink each rectangle to ``ratio`` and centre it, so the game is not letterboxed inside its window."""
    out = []
    for x, y, width, height in rects:
        if width / height > ratio:
            new_w, new_h = round(height * ratio), height
        else:
            new_w, new_h = width, round(width / ratio)
        out.append((x + (width - new_w) // 2, y + (height - new_h) // 2, new_w, new_h))
    return out


# ------------------------------------------------------------ dragging


def _snap_value(value: int, targets: list[int], distance: int) -> int:
    best = min(targets, key=lambda target: abs(target - value), default=None)
    return best if best is not None and abs(best - value) <= distance else value


def edges(monitors: list[Monitor], others: list[Rect]) -> tuple[list[int], list[int]]:
    """The x and y lines a window edge may snap to: monitor and work-area edges and the other windows."""
    xs: list[int] = []
    ys: list[int] = []
    for rect in [m.area for m in monitors] + [m.work for m in monitors] + others:
        x, y, width, height = rect
        xs += [x, x + width]
        ys += [y, y + height]
    return xs, ys


def snap_move(rect: Rect, monitors: list[Monitor], others: list[Rect], distance: int = SNAP) -> Rect:
    """Move a dragged window so its nearest edges line up with nearby edges; the size stays."""
    x, y, width, height = rect
    xs, ys = edges(monitors, others)
    left = _snap_value(x, xs, distance)
    right = _snap_value(x + width, xs, distance)
    top = _snap_value(y, ys, distance)
    bottom = _snap_value(y + height, ys, distance)
    if left != x and (right == x + width or abs(left - x) <= abs(right - x - width)):
        x = left
    elif right != x + width:
        x = right - width
    if top != y and (bottom == y + height or abs(top - y) <= abs(bottom - y - height)):
        y = top
    elif bottom != y + height:
        y = bottom - height
    return x, y, width, height


def snap_resize(rect: Rect, corner: str, monitors: list[Monitor], others: list[Rect],
                distance: int = SNAP) -> Rect:
    """Snap the dragged corner ("nw", "ne", "sw" or "se") of a window; the opposite corner stays."""
    x, y, width, height = rect
    right, bottom = x + width, y + height
    xs, ys = edges(monitors, others)
    if "w" in corner:
        x = _snap_value(x, xs, distance)
    else:
        right = _snap_value(right, xs, distance)
    if "n" in corner:
        y = _snap_value(y, ys, distance)
    else:
        bottom = _snap_value(bottom, ys, distance)
    return normalise((x, y, right - x, bottom - y), corner)


def normalise(rect: Rect, corner: str = "se") -> Rect:
    """Keep a window at least MIN_SIZE wide and high, growing away from the dragged corner's opposite."""
    x, y, width, height = rect
    if width < MIN_SIZE:
        if "w" in corner:
            x -= MIN_SIZE - width
        width = MIN_SIZE
    if height < MIN_SIZE:
        if "n" in corner:
            y -= MIN_SIZE - height
        height = MIN_SIZE
    return int(x), int(y), int(width), int(height)


def resize(rect: Rect, corner: str, dx: int, dy: int) -> Rect:
    """Move one corner of a window by (dx, dy)."""
    x, y, width, height = rect
    right, bottom = x + width, y + height
    if "w" in corner:
        x += dx
    else:
        right += dx
    if "n" in corner:
        y += dy
    else:
        bottom += dy
    return normalise((x, y, right - x, bottom - y), corner)


def overlaps(a: Rect, b: Rect) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def on_screen(rect: Rect, monitors: list[Monitor]) -> bool:
    """Whether at least a corner of the window lies on a monitor (so it can still be grabbed)."""
    return any(overlaps(rect, m.area) for m in monitors)


# ------------------------------------------------------- canvas mapping


@dataclass(frozen=True)
class View:
    """Maps screen coordinates to a canvas of a given size, keeping the proportions."""

    screen: Rect
    width: int
    height: int
    margin: int = 16

    @property
    def scale(self) -> float:
        _x, _y, w, h = self.screen
        return min((self.width - 2 * self.margin) / w, (self.height - 2 * self.margin) / h)

    def _offset(self) -> tuple[float, float]:
        x, y, w, h = self.screen
        s = self.scale
        return (self.width - w * s) / 2 - x * s, (self.height - h * s) / 2 - y * s

    def to_canvas(self, rect: Rect) -> tuple[float, float, float, float]:
        ox, oy = self._offset()
        s = self.scale
        x, y, w, h = rect
        return ox + x * s, oy + y * s, ox + (x + w) * s, oy + (y + h) * s

    def to_screen(self, cx: float, cy: float) -> tuple[int, int]:
        ox, oy = self._offset()
        s = self.scale
        return round((cx - ox) / s), round((cy - oy) / s)

    def distance(self, canvas_pixels: float) -> int:
        return round(canvas_pixels / self.scale)
