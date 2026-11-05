"""Small offline Help-path checks, requiring no Qt or Windows installation."""
import tempfile
import unittest
from pathlib import Path
from vespershell.helpfile import locate_help_file


class HelpTests(unittest.TestCase):
    def test_installed_help_alongside_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / "Vesper Shell Beta.exe"
            docs = root / "docs"
            docs.mkdir()
            manual = docs / "VesperShell-Help.html"
            manual.write_text("OK", encoding="utf-8")
            # Compare file identity: Windows temporary paths may use 8.3 aliases.
            self.assertTrue(manual.samefile(locate_help_file(executable=str(exe), frozen=True)))

    def test_source_tree_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'vespershell').mkdir()
            docs = root / 'docs'
            docs.mkdir()
            manual = docs / 'VesperShell-Help.html'
            manual.write_text('OK', encoding='utf-8')
            self.assertTrue(manual.samefile(locate_help_file(executable=str(root/'python.exe'), frozen=False,
                module_file=str(root/'vespershell'/'helpfile.py'))))

    def test_missing_help_does_not_guess_remote_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(locate_help_file(executable=str(root/'VesperShell.exe'), frozen=True))

    def test_installed_help_takes_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'docs').mkdir()
            expected=root/'docs'/'VesperShell-Help.html'
            expected.write_text('installed', encoding='utf-8')
            (root/'VesperShell-Help.html').write_text('fallback', encoding='utf-8')
            self.assertTrue(expected.samefile(locate_help_file(executable=str(root/'app.exe'), frozen=True)))


if __name__ == '__main__':
    unittest.main()
