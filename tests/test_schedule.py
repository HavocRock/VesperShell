"""Regression tests for TurtleHide schedule data and TurtleFlip preferences."""
import json
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from vespershell.model import (
    NotesDataError, NotesStore, SettingsStore, backup_before_schedule_upgrade,
    make_daily_schedule, make_once_schedule, new_note, schedule_phase,
)


def local_epoch(year, month, day, hour, minute):
    return time.mktime(datetime(year, month, day, hour, minute).timetuple())


class ScheduleTests(unittest.TestCase):
    def test_once_including_exact_boundaries(self):
        schedule = make_once_schedule(1000, 1500)
        self.assertEqual(schedule_phase(schedule, now=999), "before")
        self.assertEqual(schedule_phase(schedule, now=1000), "hidden")
        self.assertEqual(schedule_phase(schedule, now=1499.9), "hidden")
        self.assertEqual(schedule_phase(schedule, now=1500), "shown")
        self.assertEqual(schedule_phase(schedule, now=9000), "shown")

    def test_daily_daytime(self):
        schedule = make_daily_schedule(9*60, 17*60)
        self.assertEqual(schedule_phase(schedule, now=local_epoch(2026, 11, 3, 8, 59)), "shown")
        self.assertEqual(schedule_phase(schedule, now=local_epoch(2026, 11, 3, 9, 0)), "hidden")
        self.assertEqual(schedule_phase(schedule, now=local_epoch(2026, 11, 3, 16, 59)), "hidden")
        self.assertEqual(schedule_phase(schedule, now=local_epoch(2026, 11, 3, 17, 0)), "shown")

    def test_daily_crosses_midnight(self):
        schedule = make_daily_schedule(22*60, 7*60)
        for hour, minute, expected in [(21,59,"shown"), (22,0,"hidden"),
                                       (23,59,"hidden"), (0,0,"hidden"),
                                       (6,59,"hidden"), (7,0,"shown")]:
            with self.subTest(hour=hour, minute=minute):
                self.assertEqual(schedule_phase(schedule, now=local_epoch(2026, 11, 3, hour, minute)), expected)

    def test_invalid_scheduler_input_rejected(self):
        for bad in ((1, 1), (-1, 60), (1, 1440), (True, 10), (1.1, 3)):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    make_daily_schedule(*bad)
        for a, b in ((50, 50), (70, 50), (float('nan'), 200), (10, float('inf'))):
            with self.subTest(a=a,b=b):
                with self.assertRaises(ValueError):
                    make_once_schedule(a, b)

    def test_schedule_roundtrip_and_independent_timer(self):
        with tempfile.TemporaryDirectory() as d:
            store = NotesStore(Path(d) / "notes.json")
            a = new_note(theme="moon_violet")
            a["schedule"] = make_once_schedule(1000, 1500)
            a["schedule"]["phase"] = "hidden"
            a["visible"] = False
            a["text"] = "हिन्दी 🐢\nA test"
            store.save([a])
            self.assertEqual(store.load()[0], a)
            b = store.load()[0]
            b["schedule"] = make_daily_schedule(22*60, 7*60)
            store.save([b])
            self.assertEqual(store.load()[0], b)

    def test_old_notes_without_schedule_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "notes.json"
            note = new_note()
            del note["schedule"]
            path.write_text(json.dumps({"version":1, "notes":[note]}), encoding="utf8")
            loaded = NotesStore(path).load()[0]
            self.assertIsNone(loaded["schedule"])
            self.assertEqual(loaded["text"], "")

    def test_bad_schedule_never_overwrites_good_notes(self):
        with tempfile.TemporaryDirectory() as d:
            store = NotesStore(Path(d) / "notes.json")
            store.save([new_note()])
            valid = store.path.read_bytes()
            for schedule in [
                {"mode":"daily", "phase":"shown", "hide_minute":100, "show_minute":100},
                {"mode":"once", "phase":"before", "hide_at":100, "show_at":99},
                {"mode":"once", "phase":"before", "hide_at":float('nan'), "show_at":200},
                {"mode":"weekly", "phase":"shown"},
                {"mode":"daily", "phase":"wrong", "hide_minute":100, "show_minute":200},
            ]:
                n = new_note()
                n["schedule"] = schedule
                with self.subTest(schedule=schedule), self.assertRaises(NotesDataError):
                    store.save([n])
                self.assertEqual(store.path.read_bytes(), valid)

    def test_gesture_preferences_and_existing_settings(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text(json.dumps({"version":1,"default_theme":"moon_violet"}))
            settings = SettingsStore(path)
            self.assertEqual(settings.load_stack_clicks(), 2)
            settings.save_stack_clicks(3)
            self.assertEqual(settings.load(), "moon_violet")
            self.assertEqual(settings.load_stack_clicks(), 3)
            settings.save("amber_ember")
            self.assertEqual(settings.load_stack_clicks(), 3)
            settings.save_stack_clicks(0)
            self.assertEqual(settings.load_stack_clicks(), 0)
            contents = path.read_bytes()
            with self.assertRaises(NotesDataError):
                settings.save_stack_clicks(4)
            self.assertEqual(path.read_bytes(), contents)

    def test_malformed_gesture_settings_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text(json.dumps({"version":1,"stack_clicks":True}), encoding="utf8")
            with self.assertRaises(NotesDataError):
                SettingsStore(path).load_stack_clicks()

    def test_backup_before_upgrade_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            original = folder / "notes.json"
            original.write_bytes(b'{some old notes, even invalid}')
            backup = backup_before_schedule_upgrade(folder)
            self.assertIsNotNone(backup)
            self.assertEqual(original.read_bytes(), backup.read_bytes())
            self.assertIsNone(backup_before_schedule_upgrade(folder))
            self.assertEqual(len(list((folder / "note-backups").glob('notes-pre-v030-*.json'))), 1)

    def test_fresh_install_has_no_false_upgrade_backup(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.assertIsNone(backup_before_schedule_upgrade(folder))
            NotesStore(folder / "notes.json").save([new_note()])
            self.assertIsNone(backup_before_schedule_upgrade(folder))
            self.assertFalse((folder / "note-backups").exists())


if __name__ == "__main__":
    unittest.main()
