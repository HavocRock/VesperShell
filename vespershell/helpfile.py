"""Locate VesperShell's local offline guide without reading remote URLs."""
from __future__ import annotations
from pathlib import Path
import sys


HELP_NAME = "VesperShell-Help.html"


def locate_help_file(*, executable: str | None = None, frozen: bool | None = None,
                     module_file: str | None = None) -> Path | None:
    """Return existing docs/VesperShell-Help.html in source or packaged form.

    In frozen builds, prefer the directory containing the *installed EXE*,
    NOT PyInstaller's private _internal directory or a temporary extraction path.
    """
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    main_exe = Path(executable or sys.executable).resolve()
    source_root = Path(module_file or __file__).resolve().parents[1]
    roots = [main_exe.parent] if is_frozen else [source_root, main_exe.parent]
    # Some developers bundle docs inside the PyInstaller resource directory.
    if is_frozen and hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        for candidate in (root / "docs" / HELP_NAME, root / HELP_NAME):
            if candidate.is_file():
                return candidate
    return None
