import threading
import time
import logging
from datetime import date


def _today() -> str:
    return date.today().isoformat()


class StateMachine:
    """Active-time counter with three independent pause gates.

    The counter accumulates only when none of the gates are set:
      - user_paused (manual)
      - idle (no input for IDLE_THRESHOLD_SEC)
      - locked (workstation locked)

    Auto-resets at midnight on tick().
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._segment_start = time.monotonic()
        self._date = _today()
        self._active_seconds = 0.0
        self._user_paused = False
        self._idle = False
        self._locked = False

    def _is_counting(self) -> bool:
        return not (self._user_paused or self._idle or self._locked)

    def _flip(self, was_counting: bool, now: float):
        is_counting = self._is_counting()
        if was_counting and not is_counting:
            self._active_seconds += now - self._segment_start
        elif not was_counting and is_counting:
            self._segment_start = now

    def preload(self, seconds: float):
        with self._lock:
            self._active_seconds = seconds

    def pause(self):
        with self._lock:
            if self._user_paused:
                return
            was = self._is_counting()
            self._user_paused = True
            self._flip(was, time.monotonic())
            logging.info("User paused")

    def resume(self):
        with self._lock:
            if not self._user_paused:
                return
            was = self._is_counting()
            self._user_paused = False
            self._flip(was, time.monotonic())
            logging.info("User resumed")

    def set_idle(self, idle: bool):
        with self._lock:
            if self._idle == idle:
                return
            was = self._is_counting()
            self._idle = idle
            self._flip(was, time.monotonic())

    def set_locked(self, locked: bool):
        with self._lock:
            if self._locked == locked:
                return
            was = self._is_counting()
            self._locked = locked
            self._flip(was, time.monotonic())
            logging.info("Session %s", "LOCKED" if locked else "UNLOCKED")

    @property
    def paused(self) -> bool:
        """True when counter is gated for any reason."""
        with self._lock:
            return not self._is_counting()

    def tick(self):
        """Call periodically to detect midnight rollover."""
        with self._lock:
            today = _today()
            if today != self._date:
                if self._is_counting():
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
            if self._is_counting():
                secs += time.monotonic() - self._segment_start
            return secs, self._date, not self._is_counting()
