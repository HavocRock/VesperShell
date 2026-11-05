"""Optional GUI smoke tests. Run on a Windows runner with PySide6 installed."""
import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from vespershell.ui import NotesController
    HAS_QT = True
except ImportError:
    HAS_QT = False

from vespershell.model import NotesStore, SettingsStore, make_timer, make_once_schedule


@unittest.skipUnless(HAS_QT, "PySide6 is not installed here")
class WindowsGuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["vesper-tests"])
        cls.app.setQuitOnLastWindowClosed(False)

    @staticmethod
    def close_controller(ctrl):
        ctrl.clock_timer.stop()
        ctrl.save_timer.stop()
        for win in ctrl.windows.values():
            win._allow_close = True
            win.close()
        if ctrl.tray:
            ctrl.tray.hide()

    def test_per_note_themes_unicode_countdown_and_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            store = NotesStore(Path(temp) / "notes.json")
            settings = SettingsStore(Path(temp) / "settings.json")
            c = NotesController(self.app, store, settings)
            try:
                a = next(iter(c.windows))
                c.windows[a].editor.setPlainText("नमस्ते 🐢 Hello")
                c.windows[a].set_theme("moon_violet")
                c.windows[a].data["timer"] = make_timer(1, now=0)
                c.windows[a].update_countdown(time.time())
                self.assertIn("#db4b4c", c.windows[a].timer_bar.styleSheet())
                c.create_note(theme="amber_ember")
                b = next(n for n in c.notes if n != a)
                self.assertEqual(c.notes[b]["color"], "amber_ember")
                c.hide_note(a)
                self.assertTrue(c.save_now())
            finally:
                self.close_controller(c)
            c2 = NotesController(self.app, store, settings)
            try:
                self.assertEqual(len(c2.notes), 2)
                self.assertEqual(c2.notes[a]["text"], "नमस्ते 🐢 Hello")
                self.assertEqual(c2.notes[a]["color"], "moon_violet")
                self.assertEqual(c2.notes[b]["color"], "amber_ember")
                c2.show_note(a)
                self.assertTrue(c2.notes[a]["visible"])
                self.assertTrue(c2.save_now())
                self.assertEqual(c2.stack_clicks, 2)
                c2.windows[a].set_pin_state(True)
                self.assertTrue(c2.notes[a]["pinned"])
                c2.windows[a].send_to_back()
                self.assertFalse(c2.notes[a]["pinned"])
                # Pretend the system clock has crossed a scheduled hide/show window.
                now = time.time()
                c2.notes[a]["schedule"] = make_once_schedule(now + 10, now + 30)
                c2.notes[a]["schedule"]["phase"] = "before"
                c2.windows[a].last_edit_monotonic = float("-inf")
                c2.process_schedules(now + 11)
                # When a system tray exists the note must disappear.
                if c2.tray:
                    self.assertFalse(c2.notes[a]["visible"])
                    c2.process_schedules(now + 31)
                    self.assertTrue(c2.notes[a]["visible"])
                self.assertTrue(c2.save_now())
            finally:
                self.close_controller(c2)


if __name__ == "__main__":
    unittest.main()
