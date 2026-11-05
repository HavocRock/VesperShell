# VesperShell v0.3.5 — Windows source build instructions

**This download is SOURCE, not a Windows executable.** It includes the v0.3.5 beta Help-menu changes. The final updated installer and standalone build were successfully tested on the developer’s Windows 10 system. Keep a known-good release backup when building new versions.

1. Extract the entire source ZIP into a NEW Windows folder (do not extract onto an existing installation).
2. On Windows 10/11 with Python 3 installed, double-click `install_windows.bat`. It creates a local `.venv` and installs PySide6; it does NOT auto-launch the app. Developer dependency installation may need internet; normal app use doesn't.
3. For testing with isolated dummy notes, use `run_qa_windows.bat`. The startup menu item is intentionally **disabled** in QA mode.
4. To compile, run `build_windows.bat`. It installs build dependencies, runs the test suite, and creates `dist\VesperShell\VesperShell.exe`.
5. To test **Start VesperShell with Windows**, run the new executable normally from `dist\VesperShell` (not the QA launcher). This accesses standard VesperShell AppData and may migrate legacy data on first run, so back it up first. Use WINDOWS_QA.md and the 5-check HTML checklist. Never enable startup on a throwaway folder you intend to delete.
6. Distribute the **entire** `dist\VesperShell` folder including `_internal`, `Start-QA.bat`, docs and checklist; not the EXE by itself.

The included PyInstaller spec handles Windows-specific bundling. The v0.3.5 startup checks and final Help-enabled installation tests have passed on the developer’s Windows 10 system. An independent clean-PC compatibility test is still outstanding; the beta source can be published with that limitation clearly stated.


## Offline Help in v0.3.5 beta

The updated `build_windows.bat` copies `docs/VesperShell-Help.html` into `dist/VesperShell/docs`, along with LICENSE and THIRD_PARTY_NOTICES.md. The note ellipsis and tray Help actions locate the installed docs folder relative to the executable. The **final Help-enabled installer has already been rebuilt and user-tested**; older installers without the Help menu must not be published as the final v0.3.5 beta.
