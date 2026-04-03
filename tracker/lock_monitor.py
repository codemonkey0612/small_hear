"""
Detects screen lock/unlock by polling OpenInputDesktop every second.
No Win32 message window needed — no conflict with pystray.
"""
import time
import threading
import logging

try:
    import ctypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logging.warning("ctypes not available — lock detection disabled")


class LockMonitor:
    def __init__(self, state_machine, idle_monitor):
        from tracker.state_machine import State
        self._sm    = state_machine
        self._idle  = idle_monitor
        self._State = State
        self._stop  = threading.Event()

    def start(self):
        t = threading.Thread(target=self._poll_loop, name="LockMonitor", daemon=True)
        t.start()

    def stop(self):
        self._stop.set()

    def _is_locked(self) -> bool:
        """Returns True when the workstation is locked."""
        # GetForegroundWindow returns NULL when the desktop is locked
        # and the lock screen is the only thing visible.
        # More reliable: check if the current session is locked via LockWorkStation flag.
        # We use OpenDesktop("Default") — succeeds when unlocked, fails when locked.
        try:
            OpenDesktop   = ctypes.windll.user32.OpenDesktopW
            CloseDesktop  = ctypes.windll.user32.CloseDesktop
            DESKTOP_READOBJECTS = 0x0001
            hdesk = OpenDesktop("Default", 0, False, DESKTOP_READOBJECTS)
            if hdesk:
                CloseDesktop(hdesk)
                return False  # unlocked
            return True       # locked
        except Exception:
            return False

    def _poll_loop(self):
        if not HAS_WIN32:
            logging.info("LockMonitor: no win32 — lock detection disabled")
            return

        locked = False
        logging.info("LockMonitor: polling started")

        while not self._stop.wait(1.0):
            now_locked = self._is_locked()
            if now_locked and not locked:
                locked = True
                logging.info("Session LOCKED")
                self._idle.set_locked(True)
                self._sm.transition(self._State.LOCK)
            elif not now_locked and locked:
                locked = False
                logging.info("Session UNLOCKED")
                self._idle.set_locked(False)
                self._sm.transition(self._State.ACTIVE)
