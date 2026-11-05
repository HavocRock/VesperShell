"""Actual main-loop, second-process recovery and lock-release regression."""
import os
import importlib.util
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HARNESS = r'''
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
import vespershell.ui as ui
root = Path(sys.argv[1])
base = ui.NotesController
class Controller(base):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notes[next(iter(self.notes))]['text'] = 'नमस्ते 🐢 lifecycle'
        self.windows[next(iter(self.windows))].editor.setPlainText('नमस्ते 🐢 lifecycle')
        self.save_now()
        self.poll = QTimer()
        self.poll.timeout.connect(self.check)
        self.poll.start(25)
        QTimer.singleShot(0, lambda: (root/'ready').write_text('ready'))
    def recover_controls(self):
        super().recover_controls()
        (root/'recovered').write_text('yes')
    def check(self):
        if (root/'stop').exists():
            self.poll.stop()
            self.quit_application()
ui.NotesController = Controller
sys.exit(ui.main(['--data-dir', str(root/'data')]))
'''

@unittest.skipUnless(importlib.util.find_spec("PySide6") is not None, "PySide6 not installed")
class ProcessLifecycleTests(unittest.TestCase):
    def wait_file(self, path, process):
        deadline = time.monotonic()+20
        while time.monotonic() < deadline:
            if path.exists():
                return
            if process.poll() is not None:
                self.fail('Primary exited early: '+str(process.returncode))
            time.sleep(.025)
        self.fail('Timed out waiting for '+path.name)

    def test_real_quit_relaunch_recovery_and_lock_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = dict(os.environ)
            env.setdefault('QT_QPA_PLATFORM','offscreen')
            for run in range(2):
                for name in ('ready','stop','recovered'):
                    (root/name).unlink(missing_ok=True)
                primary = subprocess.Popen([sys.executable,'-c',HARNESS,str(root)], env=env)
                try:
                    self.wait_file(root/'ready',primary)
                    self.assertTrue((root/'data'/'vespershell.lock').exists())
                    secondary = subprocess.run([sys.executable,'main.py','--data-dir',str(root/'data')],env=env,timeout=15)
                    self.assertEqual(secondary.returncode,0)
                    self.wait_file(root/'recovered',primary)
                    (root/'stop').write_text('quit')
                    self.assertEqual(primary.wait(timeout=15),0)
                    self.assertFalse((root/'data'/'vespershell.lock').exists())
                    from vespershell.model import NotesStore
                    self.assertEqual(NotesStore(root/'data'/'notes.json').load()[0]['text'],'नमस्ते 🐢 lifecycle')
                finally:
                    if primary.poll() is None:
                        primary.kill()
                        primary.wait(timeout=5)
