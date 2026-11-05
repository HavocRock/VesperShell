# VesperShell v0.3.5 startup repair — source candidate

v0.3.4 W01/W02 passed; W03 failed at Windows sign-in. Its reported HKCU Run command was 315 characters. W04/W05 were pending. This release replaces Run registration with an opt-in per-user VesperShell.lnk in the Windows Startup known folder, including redirected folders. It uses built-in Windows PowerShell and WScript.Shell; no administrator rights or added Python dependencies.

Fresh startup stays OFF. Opening the app or tray menu performs no migration. Only a deliberate enable/disable changes startup. QA mode disables the control and never reads or writes startup registration. Notes and settings are not changed by this repair.

The shortcut stores target, arguments and working directory separately, supports source pythonw.exe/main.py and packaged EXE launches, and preserves explicit --data-dir. Creation is staged and verified before replacement; the matching old Run value is removed afterward. If cleanup fails, the app reports a partial update: retry before signing in to avoid duplicate launches.

Safety: a Run value is removed only if it exactly matches this installation's legacy command, including data folder. A different installation's Run entry or shortcut is preserved and reported. Because v0.3.5 is extracted to a new folder, first disable startup using the original v0.3.4 copy, then opt in from v0.3.5. Alternatively, updating code in the same installation permits automatic migration when explicitly enabled. Do not delete or move the installed folder while startup is enabled. No Run key is created, and other Run values are never touched.

## Windows acceptance, still required

1. W01: Fresh normal launch: checkbox OFF, no shortcut or Run entry created.
2. W02: Enable from a deeply nested path with spaces: inspect VesperShell.lnk target, arguments, working directory; reopen menu: checked. Check source and packaged EXE independently. Same-location old Run entry migrates only after verified shortcut creation. Different-location entries produce a warning and are preserved.
3. W03: Sign out/in manually: exactly one app launches, tray works, hidden notes remain hidden. Test explicit data directory and a redirected Startup folder where available. Mark SKIP if not tested.
4. W04: Disable: owned shortcut and matching old Run value absent; next sign-in does not launch. Other startup values untouched.
5. W05: run_qa_windows.bat: isolated notes, disabled startup control, no startup reads/writes. Check normal startup configuration is unchanged.

Keep the working v0.3.3 copy and personal data backups. Automated tests use temporary folders and mocked registry/shortcut services; they do not prove actual Windows sign-in behavior. No live startup settings were changed during development. This source candidate is unpublished; no new EXE is bundled.

Microsoft references:
- https://learn.microsoft.com/windows/win32/setupapi/run-and-runonce-registry-keys (260-character Run command limit)
- https://support.microsoft.com/en-us/windows/experience/startup-boot/configure-startup-applications-in-windows (Startup folder shortcuts)
