"""Note and timer model: deliberately independent of Qt and the desktop GUI."""
from __future__ import annotations

import json
import math
from datetime import datetime
import shutil
import os
from pathlib import Path
import tempfile
import time
import uuid

from .themes import DEFAULT_THEME, THEMES

SCHEMA_VERSION = 1  # Intentionally retain compatibility with v0.1.x notes.json.
DEFAULT_WIDTH = 350
DEFAULT_HEIGHT = 288


class NotesDataError(Exception):
    """A persisted note or settings file cannot be safely read or saved."""


def new_note(x: int = 150, y: int = 150, *, theme: str = DEFAULT_THEME) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "text": "",
        "color": theme if theme in THEMES else DEFAULT_THEME,
        "pinned": False,
        "visible": True,
        "geometry": {"x": x, "y": y, "width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT},
        "timer": None,
        "schedule": None,
    }


def make_timer(minutes: int, hours: int = 0, *, now: float | None = None) -> dict:
    if type(minutes) is not int or type(hours) is not int:
        raise ValueError("Countdown hours and minutes must be whole numbers")
    total = hours * 3600 + minutes * 60
    if not (60 <= total <= 999 * 3600 + 59 * 60):
        raise ValueError("Countdown must be 1 minute to 999 hours 59 minutes")
    if now is None:
        now = time.time()
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError("Countdown requires a valid system clock")
    deadline = float(now) + total
    if not math.isfinite(deadline):
        raise ValueError("Countdown deadline is outside the supported range")
    return {"deadline_epoch": deadline, "duration_seconds": total}


def remaining_seconds(timer: dict | None, *, now: float | None = None) -> int:
    if timer is None:
        return 0
    if now is None:
        now = time.time()
    return max(0, math.ceil(timer["deadline_epoch"] - now))


def progress(timer: dict | None, *, now: float | None = None) -> float:
    if timer is None:
        return 0.0
    return max(0.0, min(1.0, remaining_seconds(timer, now=now) / timer["duration_seconds"]))


def countdown_text(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, sec = divmod(rem, 60)
    return (f"{days}d {hours:02}:{minutes:02}:{sec:02}" if days else
            f"{hours:02}:{minutes:02}:{sec:02}")


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    t = max(0.0, min(1.0, t))
    return "#" + "".join(f"{round(x * (1 - t) + y * t):02x}" for x, y in zip(a, b))


def urgency_color(fraction: float) -> str:
    """Stable, continuously interpolated urgency, independent of note theme."""
    stops = [(0.0, (219, 75, 76)), (0.20, (232, 133, 59)),
             (0.48, (232, 188, 65)), (0.74, (135, 185, 80)),
             (1.0, (42, 170, 116))]
    p = max(0.0, min(1.0, fraction))
    for (lo, color_a), (hi, color_b) in zip(stops, stops[1:]):
        if p <= hi:
            return _blend(color_a, color_b, (p - lo) / (hi - lo))
    return "#2aaa74"



def make_once_schedule(hide_at: float, show_at: float, *, now: float | None = None) -> dict:
    """Local-clock one-time hide window with a persisted transition phase."""
    if (type(hide_at) not in (int, float) or type(show_at) not in (int, float)
            or not math.isfinite(hide_at) or not math.isfinite(show_at)
            or show_at <= hide_at):
        raise ValueError("Show time must be after the hide time")
    if now is None:
        now = time.time()
    return {"mode": "once", "hide_at": float(hide_at), "show_at": float(show_at),
            "phase": "before"}


def make_daily_schedule(hide_minute: int, show_minute: int) -> dict:
    """Daily hide interval in device-local time; supports crossing midnight."""
    if (type(hide_minute) is not int or type(show_minute) is not int
            or not 0 <= hide_minute < 1440 or not 0 <= show_minute < 1440
            or hide_minute == show_minute):
        raise ValueError("Daily hide and show times must be different valid times")
    return {"mode": "daily", "hide_minute": hide_minute,
            "show_minute": show_minute, "phase": "shown"}


def schedule_phase(schedule: dict, *, now: float | None = None) -> str:
    """Phase at current real time; local clock for recurring daily intervals."""
    if now is None:
        now = time.time()
    if schedule["mode"] == "once":
        if now < schedule["hide_at"]:
            return "before"
        return "hidden" if now < schedule["show_at"] else "shown"
    local = time.localtime(now)
    minute = local.tm_hour * 60 + local.tm_min
    hide, show = schedule["hide_minute"], schedule["show_minute"]
    inside = (hide <= minute < show if hide < show else (minute >= hide or minute < show))
    return "hidden" if inside else "shown"


def _validate_schedule(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise NotesDataError("Invalid visibility schedule")
    phase = value.get("phase")
    if value.get("mode") == "once":
        if phase not in ("before", "hidden", "shown"):
            raise NotesDataError("Invalid one-time schedule phase")
        try:
            validated = make_once_schedule(value.get("hide_at"), value.get("show_at"))
        except ValueError as exc:
            raise NotesDataError("Invalid one-time schedule") from exc
    elif value.get("mode") == "daily":
        if phase not in ("shown", "hidden"):
            raise NotesDataError("Invalid daily schedule phase")
        try:
            validated = make_daily_schedule(value.get("hide_minute"), value.get("show_minute"))
        except ValueError as exc:
            raise NotesDataError("Invalid daily schedule") from exc
    else:
        raise NotesDataError("Unknown visibility schedule mode")
    validated["phase"] = phase
    return validated


def _parse_note(raw: object) -> dict:
    if (not isinstance(raw, dict) or not isinstance(raw.get("id"), str)
            or not 1 <= len(raw["id"]) <= 128):
        raise NotesDataError("Malformed note ID")
    if not isinstance(raw.get("text"), str):
        raise NotesDataError("Invalid note text")
    geometry = raw.get("geometry")
    if not isinstance(geometry, dict):
        raise NotesDataError("Invalid note geometry")
    validated = {}
    for key in ("x", "y", "width", "height"):
        n = geometry.get(key)
        if type(n) is not int or abs(n) > 200000:
            raise NotesDataError("Invalid note geometry values")
        validated[key] = n
    if validated["width"] < 200 or validated["height"] < 120:
        raise NotesDataError("Invalid note dimensions")
    timer = raw.get("timer")
    if timer is not None:
        if not isinstance(timer, dict):
            raise NotesDataError("Malformed countdown")
        end, duration = timer.get("deadline_epoch"), timer.get("duration_seconds")
        if (type(end) not in (int, float) or not math.isfinite(end)
                or type(duration) is not int or not 60 <= duration <= 999 * 3600 + 59 * 60):
            raise NotesDataError("Invalid countdown data")
        timer = {"deadline_epoch": float(end), "duration_seconds": duration}
    theme_id = raw.get("color")
    return {
        "id": raw["id"], "text": raw["text"],
        "color": theme_id if isinstance(theme_id, str) and theme_id in THEMES else DEFAULT_THEME,
        "pinned": raw.get("pinned") is True,
        "visible": raw.get("visible") is not False,
        "geometry": validated, "timer": timer,
        "schedule": _validate_schedule(raw.get("schedule")),
    }


def _validate_notes(notes: object) -> list[dict]:
    if not isinstance(notes, list):
        raise NotesDataError("Notes must be a list")
    parsed = [_parse_note(note) for note in notes]
    ids = [note["id"] for note in parsed]
    if len(ids) != len(set(ids)):
        raise NotesDataError("Duplicate note identifiers")
    return parsed


def atomic_json_write(path: Path, payload: dict) -> None:
    temp_path = None
    try:
        text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".vespershell-", suffix=".tmp", delete=False) as fh:
            temp_path = fh.name
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, path)
    except (OSError, TypeError, ValueError) as exc:
        raise NotesDataError(f"Cannot safely save {path}: {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def migrate_legacy_folder(legacy_dir: Path | str, new_dir: Path | str) -> bool:
    """Copy existing TurtleNotes user data into the new VesperShell location.

    This is a one-time, NONDESTRUCTIVE migration: original files and backups
    stay in place. Never merge directories or silently overwrite new data.
    Caller must serialize migration and lock the legacy application folder.

    Returns True when a full copy has been safely installed.
    """
    source = Path(legacy_dir)
    target = Path(new_dir)
    if source == target or not source.is_dir() or target.exists():
        return False
    if not (source / "notes.json").exists() and not (source / "settings.json").exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".vespershell-migrate-", dir=target.parent))
    try:
        # Ignore live lock files and temporary writes, but preserve all other
        # user-owned files, including backups and legacy upgrade markers.
        def ignore(_folder: str, names: list[str]) -> set[str]:
            return {n for n in names if n.endswith(".lock") or
                    (n.startswith((".turtlenotes-", ".vespershell-")) and n.endswith(".tmp"))}
        shutil.copytree(source, staging, dirs_exist_ok=True, ignore=ignore)
        # Fail safely on invalid data before the destination becomes visible.
        NotesStore(staging / "notes.json").load()
        SettingsStore(staging / "settings.json").load_preferences()
        if target.exists():
            return False
        staging.rename(target)
        return True
    except (OSError, shutil.Error, NotesDataError) as exc:
        raise NotesDataError("Could not safely migrate old TurtleNotes files: " + str(exc)) from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging)


class NotesStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise NotesDataError(f"Cannot read {self.path}: {exc}") from exc
        if (not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION
                or not isinstance(data.get("notes"), list)):
            raise NotesDataError(f"Unknown or malformed notes file: {self.path}")
        return _validate_notes(data["notes"])

    def save(self, notes: list[dict]) -> None:
        valid = _validate_notes(notes)
        atomic_json_write(self.path, {"version": SCHEMA_VERSION, "notes": valid})


class SettingsStore:
    """Separate UI preferences, backward compatible with v0.2 settings.json."""
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load_preferences(self) -> dict:
        if not self.path.exists():
            return {"default_theme": DEFAULT_THEME, "stack_clicks": 2}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError("unknown or malformed settings format")
            theme = data.get("default_theme", DEFAULT_THEME)
            clicks = data.get("stack_clicks", 2)
            if type(clicks) is not int or clicks not in (0, 2, 3):
                raise ValueError("invalid click gesture preference")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise NotesDataError(f"Cannot safely read settings {self.path}: {exc}") from exc
        return {"default_theme": (theme if isinstance(theme, str) and theme in THEMES else DEFAULT_THEME),
                "stack_clicks": clicks}

    def load(self) -> str:
        return self.load_preferences()["default_theme"]

    def load_stack_clicks(self) -> int:
        return self.load_preferences()["stack_clicks"]

    def save_preferences(self, *, theme: str, stack_clicks: int) -> None:
        if theme not in THEMES or type(stack_clicks) is not int or stack_clicks not in (0, 2, 3):
            raise NotesDataError("Invalid theme or click gesture setting")
        atomic_json_write(self.path, {"version": 1, "default_theme": theme,
                                      "stack_clicks": stack_clicks})

    def save(self, theme: str) -> None:
        self.save_preferences(theme=theme, stack_clicks=self.load_stack_clicks())

    def save_stack_clicks(self, clicks: int) -> None:
        self.save_preferences(theme=self.load(), stack_clicks=clicks)


def backup_before_theme_upgrade(data_dir: Path | str) -> Path | None:
    """One-time, immutable local backup of a pre-v0.2 notes file.

    A backup is created before the new version writes any note data. It is
    deliberately never removed by this program. On a fresh installation a
    marker is written without creating an unnecessary backup. Returns the
    backup path if a copy was made, otherwise None.
    """
    folder = Path(data_dir)
    original = folder / "notes.json"
    marker = folder / "theme_upgrade_backup_v020.json"
    if marker.exists():
        return None
    if not original.exists():
        # A brand-new install has no previous notes to protect. Record that
        # now, before the first note is created, so its next launch cannot
        # falsely label a v0.2 note as a pre-v0.2 backup.
        atomic_json_write(marker, {"version": 1, "backup": None})
        return None
    if not original.is_file():
        raise NotesDataError(f"Expected a regular notes file at {original}")
    backup_dir = folder / "note-backups"
    name = "notes-pre-v020-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"
    target = backup_dir / name
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        with original.open("rb") as source, target.open("xb") as destination:
            shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
        atomic_json_write(marker, {"version": 1, "backup": target.name})
    except (OSError, NotesDataError) as exc:
        raise NotesDataError("Could not create the pre-upgrade local notes backup: " + str(exc)) from exc
    return target


def backup_before_schedule_upgrade(data_dir: Path | str) -> Path | None:
    """Protect existing notes once before v0.3 writes schedule fields.

    On a new installation, create only the marker. Backups are never removed.
    """
    folder = Path(data_dir)
    original = folder / "notes.json"
    marker = folder / "schedule_upgrade_backup_v030.json"
    if marker.exists():
        return None
    if not original.exists():
        atomic_json_write(marker, {"version": 1, "backup": None})
        return None
    if not original.is_file():
        raise NotesDataError(f"Expected notes file at {original}")
    directory = folder / "note-backups"
    target = directory / ("notes-pre-v030-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with original.open("rb") as source, target.open("xb") as destination:
            shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
        atomic_json_write(marker, {"version": 1, "backup": target.name})
    except (OSError, NotesDataError) as exc:
        raise NotesDataError("Could not create a v0.3 pre-upgrade backup: " + str(exc)) from exc
    return target
