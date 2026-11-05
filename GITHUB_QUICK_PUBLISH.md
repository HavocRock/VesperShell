# GitHub quick publication — VesperShell v0.3.5 beta

## Fast route: GitHub Desktop

1. Extract the GitHub-ready source ZIP to a normal local folder. The repository root is the inner **VesperShell** folder (where `README.md`, `main.py`, `.gitignore` and `LICENSE` live).
2. Open GitHub Desktop. Select **File → Add local repository**. If it says the folder is not yet a repository, select **Create a repository here** and use name **VesperShell**. Do not generate a second licence or README.
3. Review **Changes**. There should be **no `notes.json`, `settings.json`, `note-backups`, personal files, `.venv`, `__pycache__`, `dist`, `build`, or secrets**. The tracked `VesperShell.spec` and `main.py2exe-appid` are intentional.
4. Commit: `VesperShell v0.3.5 beta — Windows-verified Help and release docs`.
5. Choose **Publish repository**, choose **Public** only if desired, and confirm. Your username and authorization stay in GitHub Desktop; never post a password or token in chat.
6. Visit your GitHub repository and confirm README, `docs/VesperShell-Help.html`, source, `LICENSE`, and tests are present.

## Command-line route (if GitHub Desktop is unavailable)

Create an **empty** repository named `VesperShell` at https://github.com/new without generating an extra README, `.gitignore`, or licence. Then in PowerShell, from the extracted **VesperShell** folder:

```powershell
git init -b main
git add .
git status --short
git commit -m "VesperShell v0.3.5 beta: tested Help and release docs"
git remote add origin https://github.com/YOUR-USERNAME/VesperShell.git
git push -u origin main
```

Replace `YOUR-USERNAME` with the actual GitHub username and sign in using the normal GitHub authentication flow. Review `git status --short` **before** committing; if any private files appear, stop and remove them from staging.

## Release download

On GitHub, select **Releases → Draft a new release**; tag `v0.3.5-beta` and mark it **Pre-release**. The final Help-enabled installer has now been tested by the user on Windows 10, including installation and reinstall. Upload **that exact tested installer**, not an older installer with the same filename. If the binary is not available during publication, publish the source repository first and add the binary later.

Release description can be brief: "Offline, privacy-first Windows sticky notes with quiet countdowns, local-time visibility scheduling, signature themes, optional Windows startup, and a printable offline Help guide. Beta release; user data is stored as plaintext JSON."

Never upload untested binaries or private test-note data. Preserve the existing installer AppId for upgrades. Windows executables may trigger Microsoft SmartScreen warnings until a signing/reputation process is established; don't encourage users to ignore security warnings blindly.

**Installer upgrade identity:** Keep `main.py2exe-appid` in the repository. If packaging a previously built executable, explicitly set the existing AppId (`99C4F0A4-6D93-49A9-AE35-C8BD03C64886`) in PY2EXE so Windows upgrades the same installation rather than creating a second app entry.
