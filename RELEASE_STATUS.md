# VesperShell v0.3.5 beta — Release status (5 November 2026)

## User-verified Windows acceptance

The final Help-enabled v0.3.5 beta was built from the GitHub-ready source on Windows 10 using PY2EXE Builder 3.2.1, PyInstaller 6.22.3 and Inno Setup 7.1.1. The user reported that:

- The updated installer completed installation successfully and VesperShell launched.
- Existing application controls and functionality continued working.
- TurtleTick timers and TurtleHide hide/show schedules worked without reported issues.
- The offline Help document opened in the browser from the application interface.
- Uninstall and reinstall completed without reported errors.
- The standalone build worked as expected.

Historical Windows startup QA W01–W05 also passed in the earlier v0.3.5 checks. Four new Help-path unit tests and Python syntax checks passed during source preparation. This latest acceptance is **user-reported verification on one Windows 10 environment**, not an independently reproduced clean-PC test. The user did not separately report a controlled check of personal-note retention across uninstall; do not advertise that result as independently proven.

## Release decision

The v0.3.5 beta source is ready to publish. For binary downloads, attach only the **final Windows-tested Help-enabled installer** and clearly identify it as a beta prerelease. Earlier installers that lack the Help menu are superseded. Keep the release snapshot unchanged after publication, except for documented corrections.

## Known boundaries

- No independent clean Windows machine or second-user portability test, and no code signing.
- Notes are saved in plaintext JSON, not encrypted. No cloud synchronization is included.
- The HTML manual currently opens through the user's default browser. An embedded native help window is a future enhancement, not part of v0.3.5.
- Confirm applicable third-party redistribution and Inno Setup licence terms before any commercial distribution.

## Version and upgrade identity

Keep the application version at **0.3.5 beta**, preserve the existing `main.py2exe-appid` sidecar, and keep the installer AppId **`99C4F0A4-6D93-49A9-AE35-C8BD03C64886`** for upgrades. If using PY2EXE's *installer-from-existing-build* workflow, enter this AppId explicitly. Do not portray future roadmap items as already delivered.
