"""Run without PySide6 to check notes, themes, storage, and upgrade safety."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vespershell.model import (
    NotesStore, NotesDataError, SettingsStore, backup_before_theme_upgrade,
    countdown_text, make_timer, new_note, progress, remaining_seconds, urgency_color,
)
from vespershell.themes import (
    CLASSIC_THEMES, DEFAULT_THEME, SIGNATURE_THEMES, THEMES, get_theme, text_contrast,
)


class ModelTests(unittest.TestCase):
    def test_new_note_default_and_custom_theme(self):
        self.assertEqual(new_note()["color"], DEFAULT_THEME)
        self.assertEqual(new_note(theme="moon_violet")["color"], "moon_violet")
        self.assertEqual(new_note(theme="nonexistent")["color"], DEFAULT_THEME)

    def test_one_way_to_change_theme_without_touching_text(self):
        note = new_note()
        note["text"] = "Keep my content"
        note["color"] = "amber_ember"
        self.assertEqual(note["text"], "Keep my content")

    def test_all_signature_themes_and_legacy_colors_exist(self):
        self.assertEqual(len(SIGNATURE_THEMES), 3)
        self.assertEqual(len(CLASSIC_THEMES), 5)
        self.assertEqual(set(THEMES), set(SIGNATURE_THEMES) | set(CLASSIC_THEMES))

    def test_legible_text_palette(self):
        for key, t in THEMES.items():
            with self.subTest(theme=key):
                self.assertGreaterEqual(text_contrast(t.text, t.background), 7.0)
                self.assertGreaterEqual(text_contrast(t.muted, t.background), 4.5)
                self.assertGreaterEqual(text_contrast(t.muted, t.surface), 4.5)
                self.assertGreaterEqual(text_contrast(t.text, t.border), 4.5)

    def test_legacy_v011_roundtrip_and_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "notes.json"
            legacy = new_note(theme="sand")
            legacy["text"] = "Do not lose me 🐢 हिन्दी text\nImportant!"
            legacy["timer"] = make_timer(5, now=1000)
            NotesStore(path).save([legacy])
            original = path.read_bytes()
            backup = backup_before_theme_upgrade(folder)
            self.assertIsNotNone(backup)
            self.assertEqual(backup.read_bytes(), original)
            self.assertIsNone(backup_before_theme_upgrade(folder))
            legacy_loaded = NotesStore(path).load()
            self.assertEqual(legacy_loaded[0]["color"], "sand")
            self.assertEqual(legacy_loaded[0]["text"], legacy["text"])
            legacy_loaded[0]["color"] = "moon_violet"
            NotesStore(path).save(legacy_loaded)
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(NotesStore(path).load()[0]["color"], "moon_violet")

    def test_fresh_install_never_creates_false_legacy_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.assertIsNone(backup_before_theme_upgrade(folder))
            self.assertTrue((folder / "theme_upgrade_backup_v020.json").exists())
            store = NotesStore(folder / "notes.json")
            store.save([new_note(theme="moon_violet")])
            self.assertIsNone(backup_before_theme_upgrade(folder))
            self.assertFalse((folder / "note-backups").exists())

    def test_upgrade_backup_keeps_older_bytes_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "notes.json"
            path.write_bytes(b'{ corrupt old text!')
            exact = path.read_bytes()
            b = backup_before_theme_upgrade(folder)
            self.assertIsNotNone(b)
            self.assertEqual(b.read_bytes(), exact)
            self.assertEqual(path.read_bytes(), exact)
            self.assertIsNone(backup_before_theme_upgrade(folder))

    def test_json_preserves_unicode_without_replacement_characters(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            note = new_note()
            note["text"] = "हिन्दी में लिखें। नमस्ते! 🐢\nअक्षर और मात्राएँ"
            store.save([note])
            self.assertEqual(store.load()[0]["text"], note["text"])
            self.assertIn("हिन्दी", store.path.read_text(encoding="utf-8"))
            self.assertNotIn("\ufffd", store.path.read_text(encoding="utf-8"))

    def test_geometry_visibility_timer_and_pinning_survive(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            first = new_note(34, 56, theme="turtle_grove")
            first["geometry"] = {"x": -75, "y": 25, "width": 400, "height": 300}
            first["pinned"] = True
            first["visible"] = False
            first["timer"] = make_timer(1, now=1000)
            second = new_note(theme="amber_ember")
            store.save([first, second])
            self.assertEqual(store.load(), [first, second])

    def test_settings_default_and_reload(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = SettingsStore(Path(temp) / "settings.json")
            self.assertEqual(settings.load(), DEFAULT_THEME)
            settings.save("amber_ember")
            self.assertEqual(settings.load(), "amber_ember")
            with self.assertRaises(NotesDataError):
                settings.save("nonexistent")
            self.assertEqual(settings.load(), "amber_ember")

    def test_timer_accuracy_after_sleep(self):
        t = make_timer(2, now=1000)
        self.assertEqual(remaining_seconds(t, now=1045), 75)
        self.assertEqual(remaining_seconds(t, now=10000), 0)
        self.assertEqual(progress(t, now=1060), .5)
        self.assertEqual(progress(t, now=10000), 0)

    def test_timer_input_validation(self):
        for minutes, hours in ((0, 0), (True, 0), (1.5, 0), (1, 0.5), (-1, 0), (1, 1000)):
            with self.subTest(minutes=minutes, hours=hours):
                with self.assertRaises(ValueError):
                    make_timer(minutes, hours)
        for now in (math.nan, math.inf, -math.inf, True):
            with self.subTest(now=now):
                with self.assertRaises(ValueError):
                    make_timer(1, now=now)

    def test_timer_display(self):
        self.assertEqual(countdown_text(3661), "01:01:01")
        self.assertEqual(countdown_text(90061), "1d 01:01:01")
        self.assertEqual(countdown_text(-7), "00:00:00")

    def test_timer_color_endpoints(self):
        self.assertEqual(urgency_color(0), "#db4b4c")
        self.assertEqual(urgency_color(1), "#2aaa74")
        self.assertNotEqual(urgency_color(.3), urgency_color(.8))

    def test_corrupt_json_preserved_on_load_error(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            store.path.write_text("{ corrupt", encoding="utf-8")
            with self.assertRaises(NotesDataError):
                store.load()
            self.assertEqual(store.path.read_text(encoding="utf-8"), "{ corrupt")

    def test_unknown_schema_does_not_open(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            store.path.write_text(json.dumps({"version": 17, "notes": []}))
            with self.assertRaises(NotesDataError):
                store.load()

    def test_duplicate_note_id_disallowed(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            note = new_note()
            with self.assertRaises(NotesDataError):
                store.save([note, note])

    def test_invalid_data_never_overwrites_valid_file(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            store.save([new_note()])
            valid = store.path.read_bytes()
            bad = new_note()
            bad["geometry"]["width"] = 0
            with self.assertRaises(NotesDataError):
                store.save([bad])
            self.assertEqual(store.path.read_bytes(), valid)

    def test_failed_atomic_swap_leaves_original_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            store.save([new_note()])
            valid = store.path.read_bytes()
            with patch("vespershell.model.os.replace", side_effect=OSError("simulated write failure")):
                with self.assertRaises(NotesDataError):
                    store.save([new_note()])
            self.assertEqual(store.path.read_bytes(), valid)
            self.assertFalse(list(Path(temp).glob(".vespershell-*.tmp")))

    def test_future_settings_version_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = SettingsStore(Path(temp) / "settings.json")
            settings.path.write_text(json.dumps({"version": 99, "default_theme": "moon_violet"}))
            with self.assertRaises(NotesDataError):
                settings.load()

    def test_settings_corruption_does_not_reset_silently(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = SettingsStore(Path(temp) / "settings.json")
            settings.path.write_text("!broken")
            with self.assertRaises(NotesDataError):
                settings.load()


if __name__ == "__main__":
    unittest.main()
