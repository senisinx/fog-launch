"""Reading and changing the game's Unreal Engine settings files.

Two rules keep this safe: a value is only changed where its key already
exists in the file, and every line that is not changed is written back
exactly as it was read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .store import FogError, write_bytes_atomic

GAME_SECTION = "/Script/DeadByDaylight.DBDGameUserSettings"
SCALABILITY_SECTION = "ScalabilityGroups"

QUALITY_KEYS = (
    "sg.ViewDistanceQuality",
    "sg.AntiAliasingQuality",
    "sg.ShadowQuality",
    "sg.GlobalIlluminationQuality",
    "sg.ReflectionQuality",
    "sg.PostProcessQuality",
    "sg.TextureQuality",
    "sg.EffectsQuality",
    "sg.FoliageQuality",
    "sg.ShadingQuality",
    "sg.LandscapeQuality",
    "sg.AnimationQuality",
)


def _whole(value: int) -> str:
    return str(int(value))


def _decimal(value: int) -> str:
    return f"{float(value):.6f}"


def _truth(value: bool) -> str:
    return "True" if value else "False"


@dataclass(frozen=True)
class Field:
    """One value in the graphics editor and the keys in the file it stands for.

    The first key is the one the value is read from; all of them are written.
    """

    name: str
    kind: str  # "int", "bool" or "quality"
    keys: tuple[tuple[str, str, object], ...]
    low: int = 0
    high: int = 0


FIELDS: tuple[Field, ...] = (
    Field(
        "width",
        "int",
        (
            (GAME_SECTION, "ResolutionSizeX", _whole),
            (GAME_SECTION, "LastUserConfirmedResolutionSizeX", _whole),
        ),
        640,
        16384,
    ),
    Field(
        "height",
        "int",
        (
            (GAME_SECTION, "ResolutionSizeY", _whole),
            (GAME_SECTION, "LastUserConfirmedResolutionSizeY", _whole),
        ),
        360,
        8640,
    ),
    Field(
        "fullscreen",
        "int",
        (
            (GAME_SECTION, "FullscreenMode", _whole),
            (GAME_SECTION, "LastConfirmedFullscreenMode", _whole),
            (GAME_SECTION, "PreferredFullscreenMode", _whole),
        ),
        0,
        2,
    ),
    Field(
        "fps",
        "int",
        (
            (GAME_SECTION, "FrameRateLimit", _decimal),
            (GAME_SECTION, "FPSLimitMode", _whole),
        ),
        0,
        1000,
    ),
    Field(
        "render_scale",
        "int",
        (
            (GAME_SECTION, "ScreenRenderSize", _whole),
            (SCALABILITY_SECTION, "sg.ResolutionQuality", _whole),
        ),
        10,
        100,
    ),
    Field("vsync", "bool", ((GAME_SECTION, "bUseVSync", _truth),)),
    Field(
        "dynamic_resolution",
        "bool",
        ((GAME_SECTION, "bUseDynamicResolution", _truth),),
    ),
    Field("main_volume", "int", ((GAME_SECTION, "MainVolume", _whole),), 0, 100),
    Field(
        "menu_music_volume",
        "int",
        ((GAME_SECTION, "MenuMusicVolume", _whole),),
        0,
        100,
    ),
) + tuple(
    Field(key, "quality", ((SCALABILITY_SECTION, key, _whole),), 0, 4)
    for key in QUALITY_KEYS
)


class IniError(FogError):
    pass


def read_ini(path: Path) -> tuple[str, str]:
    """Return the text of a settings file and the encoding it was stored in."""
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        raise IniError("'{file}' could not be read: {error}", file=path, error=error) from error
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace"), "cp1252"


def write_ini(path: Path, text: str, encoding: str) -> None:
    write_bytes_atomic(Path(path), text.encode(encoding, errors="replace"))


def _section_of(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1]
    return None


def parse_values(text: str) -> dict[tuple[str, str], str]:
    """All `key=value` lines as {(section, key): value}; a later line wins."""
    values: dict[tuple[str, str], str] = {}
    section = None
    for line in text.splitlines():
        found = _section_of(line)
        if found is not None:
            section = found
            continue
        stripped = line.strip()
        if section is None or not stripped or stripped[0] in ";#" or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[(section, key.strip())] = value.strip()
    return values


def update_values(text: str, updates: dict[tuple[str, str], str]) -> str:
    """Set the given keys where they exist. Keys the file lacks are left out."""
    output = []
    section = None
    for line in text.splitlines(keepends=True):
        found = _section_of(line)
        if found is not None:
            section = found
        elif section is not None and "=" in line and line.strip()[0] not in ";#":
            key = line.split("=", 1)[0].strip()
            if (section, key) in updates:
                ending = line[len(line.rstrip("\r\n")):]
                line = f"{key}={updates[(section, key)]}{ending}"
        output.append(line)
    return "".join(output)


def graphics_from_text(text: str) -> dict[str, object]:
    """The editor values a file holds. A field the file lacks is absent."""
    values = parse_values(text)
    settings: dict[str, object] = {}
    for field in FIELDS:
        section, key, _format = field.keys[0]
        raw = values.get((section, key))
        if raw is None:
            continue
        if field.kind == "bool":
            settings[field.name] = raw.casefold() == "true"
            continue
        try:
            settings[field.name] = int(float(raw))
        except ValueError:
            continue
    return settings


def graphics_to_text(text: str, settings: dict[str, object]) -> str:
    """Write editor values into a file's text, after checking their range."""
    updates: dict[tuple[str, str], str] = {}
    for field in FIELDS:
        if field.name not in settings:
            continue
        value = settings[field.name]
        if field.kind == "bool":
            value = bool(value)
        else:
            try:
                value = int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError) as error:
                raise IniError("'{value}' is not a whole number.", value=settings[field.name]) from error
            if not field.low <= value <= field.high:
                raise IniError(
                    "{value} is outside the range {low} to {high}.",
                    value=value,
                    low=field.low,
                    high=field.high,
                )
        for section, key, format_value in field.keys:
            updates[(section, key)] = format_value(value)  # type: ignore[operator]
    return update_values(text, updates)


# ---------------------------------------------------------------- key bindings

_BINDING_LINE = re.compile(r"^\s*(ActionMappings|AxisMappings)=\((.*)\)\s*$")
_BINDING_PART = re.compile(r'(\w+)=(?:"([^"]*)"|([^,()]*))')


@dataclass
class Binding:
    """One `ActionMappings` or `AxisMappings` line of Input.ini."""

    kind: str  # "action" or "axis"
    name: str
    key: str
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    cmd: bool = False
    scale: str = "1.000000"
    section: str | None = None
    raw: str | None = None  # the line as read; None once the binding changed

    def line(self) -> str:
        if self.raw is not None:
            return self.raw
        if self.kind == "axis":
            return f'AxisMappings=(AxisName="{self.name}",Scale={self.scale},Key={self.key})'
        return (
            f'ActionMappings=(ActionName="{self.name}",'
            f"bShift={_truth(self.shift)},bCtrl={_truth(self.ctrl)},"
            f"bAlt={_truth(self.alt)},bCmd={_truth(self.cmd)},Key={self.key})"
        )

    def modifiers(self) -> str:
        names = (("Shift", self.shift), ("Ctrl", self.ctrl), ("Alt", self.alt), ("Cmd", self.cmd))
        return "+".join(name for name, held in names if held)


def _parse_binding(line: str, section: str | None) -> Binding | None:
    match = _BINDING_LINE.match(line)
    if not match:
        return None
    parts = {
        part.group(1): part.group(2) if part.group(2) is not None else part.group(3).strip()
        for part in _BINDING_PART.finditer(match.group(2))
    }

    def held(name: str) -> bool:
        return parts.get(name, "False").casefold() == "true"

    raw = line.strip()
    if match.group(1) == "AxisMappings":
        if "AxisName" not in parts:
            return None
        return Binding(
            "axis",
            parts["AxisName"],
            parts.get("Key", ""),
            scale=parts.get("Scale", "1.000000"),
            section=section,
            raw=raw,
        )
    if "ActionName" not in parts:
        return None
    return Binding(
        "action",
        parts["ActionName"],
        parts.get("Key", ""),
        held("bShift"),
        held("bCtrl"),
        held("bAlt"),
        held("bCmd"),
        section=section,
        raw=raw,
    )


def bindings_from_text(text: str) -> list[Binding]:
    bindings = []
    section = None
    for line in text.splitlines():
        found = _section_of(line)
        if found is not None:
            section = found
            continue
        binding = _parse_binding(line, section)
        if binding:
            bindings.append(binding)
    return bindings


def bindings_to_text(text: str, bindings: list[Binding]) -> str:
    """Replace the binding lines of a file, keeping everything else in place.

    The new lines go where the first binding line of their section was. A
    binding without a section joins the first section that has bindings.
    """
    ending = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    sections_with_bindings: list[str | None] = []
    section = None
    for line in lines:
        found = _section_of(line)
        if found is not None:
            section = found
        elif _BINDING_LINE.match(line) and section not in sections_with_bindings:
            sections_with_bindings.append(section)
    if not sections_with_bindings:
        raise IniError("This file has no key bindings.")
    home = sections_with_bindings[0]

    def lines_for(target: str | None) -> list[str]:
        return [
            binding.line() + ending
            for binding in bindings
            if binding.key
            and (
                binding.section == target
                or (target == home and binding.section not in sections_with_bindings)
            )
        ]

    output = []
    written: set[str | None] = set()
    section = None
    for line in lines:
        found = _section_of(line)
        if found is not None:
            section = found
        elif _BINDING_LINE.match(line):
            if section not in written:
                output.extend(lines_for(section))
                written.add(section)
            continue
        output.append(line)
    return "".join(output)
