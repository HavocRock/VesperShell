"""Windows current-user opt-in startup. No admin rights, services or network."""
from __future__ import annotations
import subprocess
import os
import json
import base64
import uuid
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "VesperShell"


def windows_supported() -> bool:
    return sys.platform == "win32"


def startup_command(data_dir: Path | None = None) -> str:
    """Form safe Windows command-line arguments for this installation."""
    if getattr(sys, 'frozen', False):
        parts = [str(Path(sys.executable).resolve())]
    else:
        exe = Path(sys.executable).resolve()
        pyw = exe.with_name('pythonw.exe')
        parts = [str(pyw if pyw.is_file() else exe),
                 str(Path(__file__).resolve().parents[1] / 'main.py')]
    if data_dir is not None:
        parts.extend(['--data-dir', str(Path(data_dir).expanduser().resolve())])
    return subprocess.list2cmdline(parts)


def registered_command() -> str | None:
    if not windows_supported():
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_QUERY_VALUE) as key:
            value, kind = winreg.QueryValueEx(key, VALUE_NAME)
    except FileNotFoundError:
        return None
    if kind != winreg.REG_SZ or not isinstance(value, str):
        raise OSError('VesperShell startup entry has an unexpected format')
    return value


def startup_folder() -> Path:
    # CSIDL_STARTUP resolves the current user's redirected Startup known folder.
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    result = ctypes.windll.shell32.SHGetFolderPathW(None, 7, None, 0, buffer)
    if result != 0 or not buffer.value:
        raise OSError('Could not locate the per-user Startup folder')
    return Path(buffer.value)


def shortcut_path() -> Path:
    return startup_folder() / 'VesperShell.lnk'


def launch_spec(data_dir=None):
    if getattr(sys, 'frozen', False):
        target = Path(sys.executable).resolve()
        args = []
        working = target.parent
    else:
        target = Path(sys.executable).resolve()
        pyw = target.with_name('pythonw.exe')
        if pyw.is_file():
            target = pyw
        working = Path(__file__).resolve().parents[1]
        args = [str(working / 'main.py')]
    if data_dir is not None:
        args.extend(['--data-dir', str(Path(data_dir).expanduser().resolve())])
    return dict(target=str(target), arguments=subprocess.list2cmdline(args), working=str(working))


def shell_link(path, spec=None):
    # Values are JSON encoded, never interpolated into PowerShell source.
    payload = base64.b64encode(json.dumps(dict(path=str(path), spec=spec)).encode()).decode()
    script = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=New-Object Text.UTF8Encoding; $p=ConvertFrom-Json ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + payload + "'))); "
    script += "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($p.path); "
    if spec is not None:
        script += "$s.TargetPath=$p.spec.target; $s.Arguments=$p.spec.arguments; $s.WorkingDirectory=$p.spec.working; $s.Description='VesperShell optional startup'; $s.Save(); "
    script += "@{target=$s.TargetPath; arguments=$s.Arguments; working=$s.WorkingDirectory}|ConvertTo-Json -Compress"
    encoded = base64.b64encode(script.encode('utf-16-le')).decode()
    exe = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        result = subprocess.run([str(exe), '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            capture_output=True, timeout=30, creationflags=0x08000000)
        if result.returncode:
            raise OSError('Windows could not read or save the startup shortcut')
        return json.loads(result.stdout.decode('utf-8-sig'))
    except (subprocess.SubprocessError, ValueError) as exc:
        raise OSError('Windows startup shortcut operation failed') from exc


def is_enabled_for_this_install(data_dir=None):
    if not windows_supported():
        return False
    path = shortcut_path()
    return path.is_file() and shell_link(path) == launch_spec(data_dir)


def set_enabled(enabled, data_dir=None, *, qa_mode=False):
    if qa_mode:
        return
    if not windows_supported():
        raise OSError('Start with Windows is available only on Windows')
    path = shortcut_path()
    spec = launch_spec(data_dir)
    legacy = registered_command()
    # Never delete another installation's registration or overwrite its shortcut.
    if legacy is not None and legacy != startup_command(data_dir):
        raise OSError('An older or different VesperShell installation owns the Run entry. Disable startup in that copy first, then enable it here.')
    if path.exists() and shell_link(path) != spec:
        raise OSError('A different installation owns VesperShell.lnk. Disable startup in that copy first.')
    if enabled:
        temporary = path.with_name('VesperShell-' + uuid.uuid4().hex + '.lnk')
        try:
            shell_link(temporary, spec)
            if shell_link(temporary) != spec:
                raise OSError('Startup shortcut verification failed')
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        path.unlink(missing_ok=True)
    if legacy is not None:
        import winreg
        # Recheck under the same handle immediately before deletion.
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
            if winreg.QueryValueEx(key, VALUE_NAME) != (legacy, winreg.REG_SZ):
                raise OSError('Run entry changed; it was preserved. Startup may be partially updated.')
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except OSError as exc:
                raise OSError('Shortcut updated, but the old Run entry could not be removed. Retry this option before sign-in.') from exc
