"""Mock Windows registry: these tests never alter the user's startup settings."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from vespershell import startup

class FakeKey:
    def __enter__(self): return self
    def __exit__(self, *_): return False

class FakeRegistry(types.ModuleType):
    HKEY_CURRENT_USER=object(); KEY_QUERY_VALUE=1; KEY_SET_VALUE=2; REG_SZ=3
    def __init__(self):
        super().__init__('winreg');self.d={};self.writes=[]
    def OpenKey(self,root,path,reserved=0,access=None):
        assert root is self.HKEY_CURRENT_USER and path==startup.RUN_KEY
        if startup.VALUE_NAME not in self.d:raise FileNotFoundError()
        return FakeKey()
    def CreateKeyEx(self,root,path,reserved=0,access=None):
        assert root is self.HKEY_CURRENT_USER and path==startup.RUN_KEY
        self.writes.append('create');return FakeKey()
    def QueryValueEx(self,key,name):return self.d[name]
    def SetValueEx(self,key,name,reserved,kind,cmd):
        self.d[name]=(cmd,kind);self.writes.append('set')
    def DeleteValue(self,key,name):
        del self.d[name];self.writes.append('delete')

class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'VesperShell.lnk'
        self.registry=FakeRegistry()
        self.links={}
        self.patches=[patch.object(startup,'windows_supported',return_value=True),
            patch.dict(sys.modules, {'winreg':self.registry}),
            patch.object(startup,'shortcut_path',return_value=self.path),
            patch.object(startup,'shell_link',side_effect=self.link)]
        for p in self.patches:p.start()
    def link(self,path,spec=None):
        if spec is not None:
            path.write_text(__import__('json').dumps(spec))
        return __import__('json').loads(path.read_text())
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def test_off_by_default_read_only(self):
        self.assertFalse(startup.is_enabled_for_this_install())
        self.assertFalse(self.path.exists());self.assertFalse(self.registry.writes)
    def test_enable_disable_idempotent(self):
        for _ in range(2):startup.set_enabled(True)
        self.assertTrue(startup.is_enabled_for_this_install())
        for _ in range(2):startup.set_enabled(False)
        self.assertFalse(self.path.exists());self.assertFalse(self.registry.writes)
    def test_migration_removes_only_owned_value(self):
        self.registry.d[startup.VALUE_NAME]=(startup.startup_command(),self.registry.REG_SZ)
        startup.set_enabled(True)
        self.assertTrue(self.path.exists());self.assertFalse(self.registry.d)
        self.assertEqual(self.registry.writes,['delete'])
    def test_foreign_registry_preserved(self):
        self.registry.d[startup.VALUE_NAME]=('another install',self.registry.REG_SZ)
        for enabled in (True,False):
            with self.assertRaises(OSError):startup.set_enabled(enabled)
        self.assertFalse(self.path.exists());self.assertFalse(self.registry.writes)
    def test_foreign_shortcut_preserved(self):
        self.path.write_text('{"target":"other"}')
        with self.assertRaises(OSError):startup.set_enabled(True)
        self.assertEqual(self.path.read_text(),'{"target":"other"}')
    def test_failed_creation_preserves_legacy(self):
        self.registry.d[startup.VALUE_NAME]=(startup.startup_command(),self.registry.REG_SZ)
        with patch.object(startup,'shell_link',side_effect=OSError('failed')):
            with self.assertRaises(OSError):startup.set_enabled(True)
        self.assertFalse(self.path.exists());self.assertFalse(self.registry.writes)
    def test_qa_never_accesses_windows(self):
        with patch.object(startup,'shortcut_path',side_effect=AssertionError):
            startup.set_enabled(True,qa_mode=True)
            startup.set_enabled(False,qa_mode=True)
        self.assertFalse(self.registry.writes)
    def test_long_frozen_target_and_custom_data(self):
        target=str(Path(self.temp.name)/('deep folder/'*20)/'VesperShell.exe')
        with patch.object(startup.sys,'executable',target),patch.object(startup.sys,'frozen',True,create=True):
            spec=startup.launch_spec(Path(self.temp.name)/'notes & spaces')
        self.assertGreater(len(spec['target'])+len(spec['arguments']),315)
        self.assertEqual(spec['target'],str(Path(target).resolve()))
        self.assertIn('--data-dir',spec['arguments']);self.assertNotIn('--qa-mode',spec['arguments'])
    def test_source_prefers_pythonw(self):
        exe=Path(self.temp.name)/'python.exe';pyw=exe.with_name('pythonw.exe');pyw.touch()
        with patch.object(startup.sys,'executable',str(exe)),patch.object(startup.sys,'frozen',False,create=True):
            spec=startup.launch_spec()
        self.assertEqual(spec['target'],str(pyw));self.assertIn('main.py',spec['arguments'])
    def test_non_windows(self):
        with patch.object(startup,'windows_supported',return_value=False):
            self.assertFalse(startup.is_enabled_for_this_install())
            with self.assertRaises(OSError):startup.set_enabled(True)
    def test_failed_legacy_cleanup_reports_partial_state(self):
        self.registry.d[startup.VALUE_NAME]=(startup.startup_command(),self.registry.REG_SZ)
        with patch.object(self.registry,'DeleteValue',side_effect=PermissionError):
            with self.assertRaisesRegex(OSError,'old Run entry'):startup.set_enabled(True)
        self.assertTrue(self.path.exists());self.assertTrue(self.registry.d)
