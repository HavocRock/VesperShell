"""Tests for preserving user data when upgrading from TurtleNotes to VesperShell."""
import json
import tempfile
import unittest
from pathlib import Path
from vespershell.model import (NotesStore, SettingsStore, NotesDataError,
                               migrate_legacy_folder, new_note)

class RenameMigrationTests(unittest.TestCase):
    def test_copies_original_bytes_settings_and_backups(self):
        with tempfile.TemporaryDirectory() as base:
            old, new = Path(base)/"TurtleNotes", Path(base)/"VesperShell"
            old.mkdir()
            n = new_note(theme="turtle_grove")
            n["text"] = "नमस्ते Vesper 🐢\nTurtleHide schedule"
            NotesStore(old/"notes.json").save([n])
            SettingsStore(old/"settings.json").save_preferences(theme="moon_violet", stack_clicks=3)
            (old/"note-backups").mkdir()
            (old/"note-backups"/"historic.json").write_bytes(b"original backup")
            (old/"turtlenotes.lock").write_bytes(b"should not migrate")
            original=(old/"notes.json").read_bytes()
            self.assertTrue(migrate_legacy_folder(old,new))
            self.assertEqual((new/"notes.json").read_bytes(),original)
            self.assertEqual((old/"notes.json").read_bytes(),original)
            self.assertEqual(NotesStore(new/"notes.json").load()[0]["text"],n["text"])
            self.assertEqual(SettingsStore(new/"settings.json").load_stack_clicks(),3)
            self.assertEqual((new/"note-backups"/"historic.json").read_bytes(),b"original backup")
            self.assertFalse((new/"turtlenotes.lock").exists())
            self.assertFalse(migrate_legacy_folder(old,new))

    def test_never_overwrites_existing_destination(self):
        with tempfile.TemporaryDirectory() as base:
            old, new = Path(base)/"TurtleNotes", Path(base)/"VesperShell"
            old.mkdir()
            new.mkdir()
            NotesStore(old/"notes.json").save([new_note()])
            dest = new/"notes.json"
            dest.write_bytes(b"do not touch")
            self.assertFalse(migrate_legacy_folder(old,new))
            self.assertEqual(dest.read_bytes(),b"do not touch")

    def test_bad_data_fails_without_creating_destination(self):
        with tempfile.TemporaryDirectory() as base:
            old, new=Path(base)/"TurtleNotes",Path(base)/"VesperShell"
            old.mkdir()
            (old/"notes.json").write_text("{ CORRUPT",encoding="utf-8")
            with self.assertRaises(NotesDataError):
                migrate_legacy_folder(old,new)
            self.assertFalse(new.exists())
            self.assertEqual((old/"notes.json").read_text(encoding="utf-8"),"{ CORRUPT")

    def test_does_not_create_empty_new_directory_without_old_data(self):
        with tempfile.TemporaryDirectory() as base:
            old, new=Path(base)/"TurtleNotes",Path(base)/"VesperShell"
            old.mkdir()
            self.assertFalse(migrate_legacy_folder(old,new))
            self.assertFalse(new.exists())

if __name__=='__main__': unittest.main()
