"""Focused repair regressions. Offscreen tests do not certify Windows shell UI."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
try:
    import PySide6
except ImportError:
    raise unittest.SkipTest("PySide6 not installed")
from PySide6.QtCore import Qt, QPoint, QEvent, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from vespershell.ui import NotesController, DragBar, recovery_server_name, start_recovery_server, request_recovery
from vespershell.model import NotesStore, SettingsStore, make_once_schedule

class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['repair-tests'])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.c = NotesController(self.app, NotesStore(root/'notes.json'), SettingsStore(root/'settings.json'))
        self.win = next(iter(self.c.windows.values()))
        self.bar = self.win.findChild(DragBar)
        self.position = QPoint(18, 12)
        self.app.processEvents()

    def tearDown(self):
        self.c.clock_timer.stop()
        self.c.save_timer.stop()
        for win in self.c.windows.values():
            win._allow_close = True
            win.close()
            win.deleteLater()
        self.c.tray.hide()
        self.c.tray.deleteLater()
        self.c.tray_menu.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def click(self, double=False):
        if double:
            QTest.mouseDClick(self.bar, Qt.MouseButton.LeftButton, pos=self.position)
            QTest.mouseRelease(self.bar, Qt.MouseButton.LeftButton, pos=self.position)
        else:
            QTest.mouseClick(self.bar, Qt.MouseButton.LeftButton, pos=self.position)

    def test_header_clicks_do_not_toggle_pinning(self):
        self.click()
        self.click(double=True)
        self.click()
        self.assertFalse(self.win.data['pinned'])

    def test_footer_send_back_unpins_and_lowers(self):
        self.win.set_pin_state(True)
        self.assertTrue(self.win.data['pinned'])
        with patch.object(self.win, 'set_pin_state', wraps=self.win.set_pin_state) as change:
            self.win.send_back_button.click()
            change.assert_called_once_with(False, send_behind=True)
        self.assertFalse(self.win.data['pinned'])
        self.assertFalse(self.win.pin_button.isChecked())
        self.assertTrue(self.win.isVisible())

    def test_footer_send_back_when_already_unpinned(self):
        with patch.object(self.win, 'set_pin_state', wraps=self.win.set_pin_state) as change:
            self.win.send_back_button.click()
            change.assert_called_once_with(False, send_behind=True)
        self.assertTrue(self.win.isVisible())

    def test_header_drag_moves_note(self):
        original = self.win.pos()
        QTest.mousePress(self.bar, Qt.MouseButton.LeftButton, pos=self.position)
        destination = self.position + QPoint(40, 0)
        event = QMouseEvent(QEvent.Type.MouseMove, QPointF(destination),
            QPointF(self.bar.mapToGlobal(destination)), Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.bar, event)
        QTest.mouseRelease(self.bar, Qt.MouseButton.LeftButton, pos=destination)
        self.assertNotEqual(self.win.pos(), original)
        self.assertFalse(self.win.data['pinned'])

    def test_editor_double_click_selects_text_without_stack_changes(self):
        self.win.editor.setPlainText('hello world')
        QTest.mouseDClick(self.win.editor.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(12, 10))
        self.assertTrue(self.win.editor.textCursor().hasSelection())

    def test_tool_flags_survive_pin_and_geometry_and_keyboard(self):
        self.win.editor.setFocus()
        QTest.keyClicks(self.win.editor, 'editable')
        self.assertEqual(self.win.data['text'], 'editable')
        geometry = self.win.geometry()
        for pinned in (True, False):
            self.win.set_pin_state(pinned)
            self.assertEqual(self.win.windowType(), Qt.WindowType.Tool)
            self.assertEqual(bool(self.win.windowFlags() & Qt.WindowType.WindowStaysOnTopHint), pinned)
            self.assertEqual(self.win.geometry(), geometry)

    def test_quit_closes_windows_without_persisting_hidden_state(self):
        self.win.editor.setPlainText('नमस्ते 🐢')
        self.c.create_note()
        with patch.object(self.app, 'quit') as quit_app:
            self.c.quit_application()
            quit_app.assert_called_once()
        self.assertTrue(all(not w.isVisible() and w._allow_close for w in self.c.windows.values()))
        self.assertTrue(all(n['visible'] for n in self.c.store.load()))
        self.assertFalse(self.c.save_timer.isActive())
        self.assertFalse(self.c.clock_timer.isActive())

    def test_failed_save_decline_quit_keeps_controls_running(self):
        with patch.object(self.c, 'save_now', return_value=False), patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No), patch.object(self.app, 'quit') as quit_app:
            self.c.quit_application()
            quit_app.assert_not_called()
        self.assertFalse(self.c._quitting)
        self.assertFalse(self.win._allow_close)
        self.assertTrue(self.c.clock_timer.isActive())

    def test_close_hides_and_recovery_does_not_reveal_it(self):
        with patch.object(self.c, 'tray_available', return_value=True):
            self.win.close()
        self.assertFalse(self.win.isVisible())
        self.assertFalse(self.win._allow_close)
        self.c.recover_controls()
        self.assertFalse(self.win.isVisible())
        self.assertFalse(self.win.data['visible'])
        self.c.show_note(self.win.data['id'])
        self.assertTrue(self.win.isVisible())
        self.assertTrue(self.win.data['visible'])

    def test_hidden_notes_remain_hidden_during_recovery(self):
        self.c.create_note()
        second = list(self.c.windows.values())[-1]
        with patch.object(self.c, 'tray_available', return_value=True):
            self.c.hide_note(second.data['id'])
        self.c.recover_controls()
        self.assertFalse(second.isVisible())
        self.assertFalse(second.data['visible'])

    def test_recovery_socket_and_directory_isolation(self):
        name = recovery_server_name(Path(self.temp.name))
        self.assertNotEqual(name, recovery_server_name(Path(self.temp.name)/'other'))
        server = start_recovery_server(name, self.c)
        try:
            with patch.object(self.c, 'recover_controls') as recover:
                child = subprocess.Popen([sys.executable, "-c",
                    "from vespershell.ui import request_recovery; import sys; sys.exit(0 if request_recovery(sys.argv[1]) else 1)", name])
                self.addCleanup(lambda: child.kill() if child.poll() is None else None)
                for _ in range(1500):
                    self.app.processEvents()
                    if child.poll() is not None:
                        break
                    QTest.qWait(10)
                self.assertEqual(child.wait(timeout=3), 0)
                recover.assert_called_once()
        finally:
            server.close()

    def test_editing_defers_hide_until_idle_then_reappears(self):
        now = time.time()
        self.win.data['schedule'] = make_once_schedule(now+10, now+30)
        with patch.object(self.c, 'tray_available', return_value=True):
            self.win.last_edit_monotonic = time.monotonic()
            self.c.process_schedules(now+11)
            self.assertTrue(self.win.isVisible())
            self.assertEqual(self.win.data['schedule']['phase'], 'before')
            self.win.last_edit_monotonic -= 5
            self.c.process_schedules(now+12)
            self.assertFalse(self.win.isVisible())
            self.c.process_schedules(now+31)
            self.assertTrue(self.win.isVisible())

    def test_missing_tray_retains_last_visible_note(self):
        with patch.object(self.c, 'tray_available', return_value=False), patch.object(QMessageBox, 'information'):
            self.c.hide_note(self.win.data['id'])
        self.assertTrue(self.win.isVisible())
    @unittest.skipUnless(os.name == 'nt' and os.environ.get('QT_QPA_PLATFORM') == 'windows', 'requires native Windows Qt platform')
    def test_native_windows_tool_style_survives_pinning(self):
        import ctypes
        get_style = ctypes.windll.user32.GetWindowLongW
        get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
        get_style.restype = ctypes.c_long
        for pinned in (False, True, False):
            self.win.set_pin_state(pinned)
            self.app.processEvents()
            style = get_style(int(self.win.winId()), -20)
            self.assertTrue(style & 0x80, hex(style))  # WS_EX_TOOLWINDOW
            self.assertFalse(style & 0x40000, hex(style))  # WS_EX_APPWINDOW
