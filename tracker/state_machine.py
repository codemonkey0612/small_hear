import threading
import time
import logging
from datetime import date


def _today() -> str:
    return date.today().isoformat()


class StateMachine:
    """Tracks active seconds since midnight. Pause/resume; auto-resets at midnight."""

    def __init__(self):
        self._lock = threading.Lock()
        self._segment_start = time.monotonic()
        self._date = _today()
        self._active_seconds = 0.0
        self._paused = False

    def preload(self, seconds: float):
        with self._lock:
            self._active_seconds = seconds

    def pause(self):
        with self._lock:
            if not self._paused:
                self._active_seconds += time.monotonic() - self._segment_start
                self._paused = True
                logging.info("Tracking paused")

    def resume(self):
        with self._lock:
            if self._paused:
                self._paused = False
                self._segment_start = time.monotonic()
                logging.info("Tracking resumed")

    @property
    def paused(self) -> bool:
        return self._paused

    def tick(self):
        """Call periodically to detect midnight rollover."""
        with self._lock:
            today = _today()
            if today != self._date:
                if not self._paused:
                    now = time.monotonic()
                    self._active_seconds += now - self._segment_start
                    self._segment_start = now
                logging.info("Midnight reset. Yesterday: %.2fh",
                             self._active_seconds / 3600)
                self._active_seconds = 0.0
                self._date = today

    def snapshot(self) -> tuple[float, str, bool]:
        """Return (active_seconds_including_running_segment, date_str, paused)."""
        with self._lock:
            secs = self._active_seconds
            if not self._paused:
                secs += time.monotonic() - self._segment_start
            return secs, self._date, self._paused
