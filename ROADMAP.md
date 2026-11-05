# VesperShell — future features (not included in v0.3.5 beta)

**Release priority:** Publish and verify the existing lightweight, offline VesperShell before building any features below. These are ideas, not promises or release dates. Each will be **opt-in** and individually controlled; nothing should silently enable the microphone, network, or background services. Core notes must remain usable offline without accounts or sync.

## 1. TurtlePeek: user-configurable default note size and hover expansion

- Allow users to enter preferred default dimensions numerically, selecting units (cm, inches or pixels where meaningful). Never force a 1×1 cm default on everyone.
- Optional compact/hover mode: e.g., a 1×1 cm parked note grows to approximately 3×3 inches on hover.
- Allow users to choose compact/expanded sizes and hover delay; no auto-collapse while typing or interacting with the note.
- Always provide keyboard, click and tray ways to expand or recover a note, including accessible alternatives for touch devices.
- Monitor DPI, physical size reporting and display scaling can vary; label physical measurements as approximate and keep windows on-screen.

## 2. TurtleLink: optional encrypted synchronization

- Prioritize local-network pairing and Bluetooth exploration. Evaluate encrypted email attachment exchange as a possible slower, asynchronous transport.
- Link devices with a **unique public ID for discovery** plus authenticated key exchange/verification (QR code or pairing code). An ID alone must never grant access to notes or serve as an encryption secret.
- End-to-end encrypt contents with established, audited crypto libraries; authenticate peers and prevent tampering and replay. If a relay or email transport is used, its operator must not hold plaintext or decryption keys.
- No account mandatory. Keys remain under user control. Document recovery, lost-device revocation, and the consequences of lost keys.
- Offline-first, explicit device linking, opt-in per device, conflict detection and non-destructive resolution with local backup/history before overwriting. Never auto-delete notes or backups.
- Assess the different capabilities and permission models of Windows, Android, Bluetooth and email before selecting the transport architecture.

## 3. TurtleVoice: optional voice commands

- User-enabled, visible microphone state and explicit permissions; prefer push-to-talk initially.
- A small command set (new note, show notes, hide note, start timer); confirm destructive operations.
- Offline speech recognition preferred where feasible; clearly disclose any network dependencies before users opt in.

## 4. TurtleSpeak: optional speech-to-text and text-to-speech

- Dictate into a note on request; allow reviewing/correcting transcription before saving.
- Read selected note text aloud, with optional voice and speed controls, and stop/pause actions where available.
- Local speech engines/models preferred; do not transmit note content or microphone audio without explicit permission.
- Test Unicode and languages (including Hindi) with installed voices and recognition models, without pretending every voice supports every language.

## Non-goals for these features

- No integrated code editor; that is a separate project.
- No default-on microphone, telemetry, cloud sync, or account registration.
- No forced automatic deletion or silently replacing divergent notes during synchronization.

**Guiding principle:** Quiet Awareness — inform without interrupting, remind without disturbing, and help without demanding attention.

## Additional ideas to investigate (not shipped)

- **Ghost Notes:** optional click-through windows with an explicit escape control so users cannot strand inaccessible notes.
- **FlipNotes and additional note types:** deliberate, accessible view changes with no hidden gestures.
- **Encrypted private notes:** security-reviewed design, key recovery and clear opt-in; never promise safety before independent testing.
- **Revision history and portable export:** user-controlled history, readable backups, reliable restore.
- **Auto-expiry and archive:** never silently destroy data; make expiry opt-in and reversible.
- **Workspace-aware notes:** user-defined groups, memory and positioning with offline operation.
