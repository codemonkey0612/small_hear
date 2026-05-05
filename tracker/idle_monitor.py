import threading
import logging

try:
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logging.warning("win32api not available — idle detection disabled")


IDLE_THRESHOLD_SEC = 60


class IdleMonitor:
    def __init__(self, state_machine):
        self._sm = state_machine
        self._stop = threading.Event()
        threading.Thread(target=self._poll_loop, name="IdleMonitor", daemon=True).start()

    def stop(self):
        self._stop.set()

    def _poll_loop(self):
        if not HAS_WIN32:
            return
        threshold_ms = IDLE_THRESHOLD_SEC * 1000
        while not self._stop.is_set():
            try:
                idle_ms = win32api.GetTickCount() - win32api.GetLastInputInfo()
                self._sm.set_idle(idle_ms >= threshold_ms)
            except Exception as e:
                logging.warning("IdleMonitor poll error: %s", e)
            self._stop.wait(1.0)
