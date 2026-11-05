# v0.3.5 beta

- Add **Help · Offline guide** to tray and note menus; open a local HTML manual using the default browser.
- Bundle printable offline HTML Help and retain clear error messages if it is missing.
- Correct public README to document the proven **↓ Send back** control and Windows startup behavior.
- Application notes storage, timers, schedules and preferences are unchanged by Help addition.
- Final Help-enabled Windows 10 beta was installed and user-tested successfully; countdowns, schedules, uninstall/reinstall and standalone launch were reported working. Independent clean-PC compatibility remains to be tested.

- Replace opt-in Windows Run registration with a verified per-user Startup shortcut.
- Preserve QA isolation, default off, custom data paths, source and EXE launching.
- Remove only matching legacy registration after shortcut verification; preserve foreign entries.
- Add isolated startup tests and focused Windows acceptance instructions.

# v0.3.4 beta — Windows start-at-sign-in (reconstructed source)

- New **Start VesperShell with Windows** checkable option in system tray, OFF by default.
- Uses current-user HKCU Run registry entry; no admin rights, Windows service, cloud calls or telemetry. Unchecking removes entry.
- Supports packaged EXE and source Python launcher, and optional custom data folder. Startup happens only after Windows user signs in.
- `--qa-mode` disables startup changes; test batch files use isolated notes storage under `%TEMP%`.
- Carries forward the v0.3.3 footer `↓ Send back`, header drag only, and second-launch recovery that leaves intentionally hidden notes hidden.
- No saved-notes or preferences schema changes. Legacy gesture setting remains readable but is not used.

**Provenance:** Reconstructed on 2026-11-04 from the v0.3.2 source plus the documented v0.3.3 and v0.3.4 changes. This ZIP is not byte-identical to the original missing v0.3.4 ZIP; native Windows acceptance remains required.

# v0.3.2 beta — 3 November 2026

Private repair candidate; Windows visual acceptance pending.

- A06: Quit saves once, permits note windows to close, stops timers and exits; failed-save cancellation keeps the app running. Removed the second unconditional save during intentional Quit.
- A06: A second launch asks the existing instance to restore notes and re-register its tray icon through a per-data-directory, current-user local pipe. It waits for acknowledgement; data locks remain authoritative. No TCP listener or internet service.
- A06: Create a tray object even when the shell tray is temporarily unavailable, allowing Qt to register it when the tray appears; final-note hiding checks actual tray availability.
- C06: Use frameless tool windows for notes, retaining the type through pin changes. Native Windows extended-style checks pass; actual taskbar/Alt+Tab/focus acceptance is still required.
- F01/F03: Count completed header clicks, handle Qt's double-click event as the second press, and cancel sequences after dragging, excessive delay, distance, or a disabled/changed preference. Flip after release to avoid recreating the native window during the pressed gesture.
- Added repair and real-process regressions; clarified migration, PDF-source diagnosis, package audit and build instructions.
- Windows packaging: checked-in spec excludes a conflicting PATH-installed ICU 78 library that caused QtCore startup failure; the final packaged smoke check passes.
- No data schema, Unicode transformation, timer, schedule, theme, migration or backup implementation changes.

# Changelog

## v0.3.1 beta — VesperShell rename

- Rebranded the app, module, dialogs, source assets, launch scripts and Windows build output from TurtleNotes to **VesperShell**, with Vesper as the turtle mascot.
- Preserved all existing note IDs, themes, timer fields and the version-1 JSON format.
- On first ordinary launch, non-destructively copy existing TurtleNotes AppData (including settings and backups) if the VesperShell folder does not already exist.
- Added regression tests for upgrade migration, conflict safety and corrupted data handling.
- The TurtleHide, TurtleFlip and TurtleTick functionality is unchanged.

## v0.3.0 beta — TurtleHide + TurtleFlip
- One-time and daily local-time windows to hide a note and bring it back automatically.
- Daily schedules support midnight crossing; all schedules save to the existing notes database.
- Scheduled hiding pauses briefly while the user is actively typing.
- Double-click or triple-click note header to toggle stacking; optional disable via tray settings.
- Tray restore brings a note forward and pins it; keeping the escape route explicit.
- New per-note `Scheduled` label, independent of TurtleTick countdowns.
- One-time, non-destructive pre-v0.3 notes backup on existing installations.
- Backward-compatible existing notes and theme preferences. No code editor added.
- Added offline regression tests for scheduling, storage, migration and settings.


## 0.2.2 beta — visual polish and GitHub packaging

- Add a quiet static glow to the active note, preserving performance and readable text.
- Retain rounded cards and independent Moon Violet, Amber Ember, and Turtle Grove themes.
- Integrate the original turtle artwork and embedded Windows `.ico` into the build.
- Fix pinned-note toolbar tooltip on launch.
- Include public-repo documentation, publication instructions, asset checks, and privacy-safe `.gitignore` patterns.
- Keep existing note schema (`version: 1`) and classic color IDs compatible.

## 0.2.1 — contrast and backup fixes

- Improve contrast in Classic Sky and Classic Lavender themes.
- Improve the visibility of selected toolbar controls.
- Correct the one-time upgrade-backup behavior for new installations.

## 0.2.0 — themed edition

- Add three per-note mood themes and a default theme for newly created notes.
- Preserve classic note colors and prior data.

## 0.1.x — initial prototype

- Multiple notes, local autosave, colored notes, pinning, tray menu, TurtleTick.
