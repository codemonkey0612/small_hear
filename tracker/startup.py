import winreg
import sys
import pathlib
import logging

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "WindowsTimeTracker"


def register():
    """Add this app to Windows startup (HKCU, no admin required)."""
    # When frozen by PyInstaller, sys.executable IS the built TimeTracker.exe
    if getattr(sys, 'frozen', False):
        cmd = f'"{sys.executable}"'
    else:
        root = pathlib.Path(__file__).resolve().parent.parent
        named_exe = root / "TimeTracker.exe"
        if named_exe.exists():
            launcher = named_exe
        else:
            exe = pathlib.Path(sys.executable)
            launcher = exe.parent / "pythonw.exe"
            if not launcher.exists():
                launcher = exe
        script = str(root / "time_tracker.py")
        cmd = f'"{launcher}" "{script}"'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        logging.info("Registered startup: %s", cmd)
        print(f"Startup registered:\n  {cmd}")
    except Exception as e:
        logging.error("Failed to register startup: %s", e)
        print(f"Failed: {e}")


def unregister():
    """Remove from Windows startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        logging.info("Unregistered startup")
        print("Startup entry removed.")
    except FileNotFoundError:
        print("No startup entry found.")
    except Exception as e:
        logging.error("Failed to unregister startup: %s", e)
        print(f"Failed: {e}")


def is_registered() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
