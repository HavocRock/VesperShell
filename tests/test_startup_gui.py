"""Optional Qt tray checks; UI interaction still needs native Windows acceptance."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication
    from vespershell.ui import NotesController
    from vespershell.model import NotesStore, SettingsStore
    HAS_QT=True
except ImportError:
    HAS_QT=False

@unittest.skipUnless(HAS_QT,'PySide6 not installed')
class StartupUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication(['startup-tests'])
        cls.app.setQuitOnLastWindowClosed(False)
    def launch(self,qa):
        self.temp=tempfile.TemporaryDirectory();d=Path(self.temp.name)
        self.ctrl=NotesController(self.app, NotesStore(d/'notes.json'),SettingsStore(d/'settings.json'),qa_mode=qa)
        self.ctrl._build_tray_menu()
        actions=[a for a in self.ctrl.tray_menu.actions() if a.text()=='Start VesperShell with Windows']
        self.assertEqual(len(actions),1)
        return actions[0]
    def tearDown(self):
        if hasattr(self,'ctrl'):
            self.ctrl.clock_timer.stop();self.ctrl.save_timer.stop()
            for w in self.ctrl.windows.values():w._allow_close=True;w.close()
            self.ctrl.tray.hide();self.ctrl.tray.deleteLater();self.ctrl.tray_menu.deleteLater()
            self.app.processEvents();self.temp.cleanup()
    def test_startup_off_by_default_then_enable(self):
        with patch('vespershell.ui.startup.windows_supported',return_value=True),patch('vespershell.ui.startup.registered_command',return_value=None),patch('vespershell.ui.startup.is_enabled_for_this_install',return_value=False),patch('vespershell.ui.startup.set_enabled') as writer:
            action=self.launch(False)
            self.assertFalse(action.isChecked());writer.assert_not_called()
            action.trigger();writer.assert_called_once_with(True,None)
    def test_qa_mode_disables_startup(self):
        with patch('vespershell.ui.startup.windows_supported',return_value=True),patch('vespershell.ui.startup.registered_command') as reader,patch('vespershell.ui.startup.set_enabled') as writer:
            action=self.launch(True)
            self.assertFalse(action.isEnabled());action.trigger()
            reader.assert_not_called();writer.assert_not_called()
