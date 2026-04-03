import threading
import time
import logging

try:
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logging.warning("win32api not available — idle detection disabled")


class IdleMonitor:
    def __init__(self, state_machine, idle_threshold_sec: int):
        from tracker.state_machine import State
        self._sm = state_machine
        self._threshold_ms = idle_threshold_sec * 1000
        self._locked = False
        self._paused = False
        self._stop = threading.Event()
        self._State = State

        t = threading.Thread(target=self._poll_loop, name="IdleMonitor", daemon=True)
        t.start()

    def set_locked(self, locked: bool):
        self._locked = locked

    def set_paused(self, paused: bool):
        self._paused = paused

    def stop(self):
        self._stop.set()

    def _poll_loop(self):
        if not HAS_WIN32:
            return
        while not self._stop.is_set():
            if not self._locked and not self._paused:
                try:
                    idle_ms = win32api.GetTickCount() - win32api.GetLastInputInfo()
                    if idle_ms >= self._threshold_ms:
                        self._sm.transition(self._State.IDLE)
                    else:
                        self._sm.transition(self._State.ACTIVE)
                except Exception as e:
                    logging.warning("IdleMonitor poll error: %s", e)
            self._stop.wait(1.0)
