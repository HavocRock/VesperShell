"""Smoke a private packaged build using disposable data and owned processes only."""
import ctypes
from ctypes import wintypes
import json
import subprocess
import tempfile
import time
from pathlib import Path
from PySide6.QtCore import QCoreApplication
from vespershell.model import NotesStore, new_note
from vespershell.ui import recovery_server_name, request_recovery

app=QCoreApplication([])
exe=Path('dist/VesperShell/VesperShell.exe').resolve()
user32=ctypes.windll.user32
EnumProc=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextLengthW.argtypes=[wintypes.HWND]
user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user32.EnumWindows.argtypes=[EnumProc,wintypes.LPARAM]
user32.GetWindowLongW.argtypes=[wintypes.HWND,ctypes.c_int]
user32.GetWindowLongW.restype=ctypes.c_long
user32.IsWindowVisible.argtypes=[wintypes.HWND]
user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]

def windows(pid):
    found=[]
    @EnumProc
    def visit(hwnd,_):
        owner=wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        length=user32.GetWindowTextLengthW(hwnd)
        buf=ctypes.create_unicode_buffer(length+1)
        user32.GetWindowTextW(hwnd,buf,length+1)
        if owner.value == pid and buf.value.startswith('VesperShell · '):
            found.append(hwnd)
        return True
    user32.EnumWindows(visit,0)
    return found

with tempfile.TemporaryDirectory() as temp:
    data=Path(temp)/'data'
    note=new_note(100,100)
    note['text']='नमस्ते 🐢 packaged smoke'
    data.mkdir()
    store=NotesStore(data/'notes.json'); store.save([note])
    process=subprocess.Popen([str(exe),'--data-dir',str(data)])
    try:
        deadline=time.monotonic()+25
        handles=[]
        while time.monotonic()<deadline:
            assert process.poll() is None, 'Packaged app exited early'
            handles=windows(process.pid)
            if handles and request_recovery(recovery_server_name(data)):
                break
            time.sleep(.1)
        assert handles, 'No packaged note window'
        assert request_recovery(recovery_server_name(data)), 'No recovery acknowledgement'
        hwnd=handles[0]
        style=user32.GetWindowLongW(hwnd,-20)
        assert style & 0x80 and not style & 0x40000, hex(style)
        user32.PostMessageW(hwnd,0x0010,0,0)  # WM_CLOSE hides the note
        time.sleep(.3)
        assert process.poll() is None
        assert not user32.IsWindowVisible(hwnd), 'Close should hide'
        second=subprocess.run([str(exe),'--data-dir',str(data)],timeout=15)
        assert second.returncode==0
        time.sleep(.6)
        assert user32.IsWindowVisible(hwnd), 'Second launch should restore note'
        assert store.load()[0]['text']==note['text']
        print('PASS: packaged startup, current-user pipe acknowledgement, native tool style, close-to-hide, second-launch restore, Unicode persistence.')
        print('NOT VERIFIED: packaged Quit menu, visual tray/taskbar/Alt+Tab, Explorer restart, physical gestures, clean-PC installation.')
    finally:
        # Stop only the process started by this smoke check; no personal data.
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
