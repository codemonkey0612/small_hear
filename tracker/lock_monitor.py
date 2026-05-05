"""Detects workstation lock/unlock by polling OpenInputDesktop every second."""
import threading
import logging

try:
    import ctypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logging.warning("ctypes not available — lock detection disabled")


class LockMonitor:
    def __init__(self, state_machine):
        self._sm = state_machine
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._poll_loop, name="LockMonitor", daemon=True).start()

    def stop(self):
        self._stop.set()

    def _is_locked(self) -> bool:
        try:
            OpenDesktop  = ctypes.windll.user32.OpenDesktopW
            CloseDesktop = ctypes.windll.user32.CloseDesktop
            DESKTOP_READOBJECTS = 0x0001
            hdesk = OpenDesktop("Default", 0, False, DESKTOP_READOBJECTS)
            if hdesk:
                CloseDesktop(hdesk)
                return False
            return True
        except Exception:
            return False

    def _poll_loop(self):
        if not HAS_WIN32:
            return
        while not self._stop.wait(1.0):
            self._sm.set_locked(self._is_locked())
