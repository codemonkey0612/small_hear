import threading
import time
import logging
from datetime import date
from enum import Enum


class State(Enum):
    ACTIVE = "ACTIVE"
    IDLE   = "IDLE"
    LOCK   = "LOCK"


def _today() -> str:
    return date.today().isoformat()


class StateMachine:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = State.ACTIVE
        self._segment_start = time.monotonic()
        self._date = _today()
        self.totals: dict[State, float] = {State.ACTIVE: 0.0, State.IDLE: 0.0, State.LOCK: 0.0}
        self._day_summary_callback = None   # set by reporter to send EOD summary
        self._paused = False

    def set_day_summary_callback(self, cb):
        self._day_summary_callback = cb

    def preload_totals(self, totals: dict[State, float]):
        """Restore persisted totals from a previous run on the same day."""
        with self._lock:
            self.totals = totals

    def pause(self):
        with self._lock:
            if not self._paused:
                self._flush_segment(time.monotonic())
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

    def transition(self, new_state: State):
        with self._lock:
            if self._paused:
                return
            now = time.monotonic()
            today = _today()

            # Midnight crossed — flush, emit summary, reset
            if today != self._date:
                self._flush_segment(now)
                logging.info("Midnight reset. Day summary: %s", self._format_totals())
                if self._day_summary_callback:
                    try:
                        self._day_summary_callback(dict(self.totals), self._date)
                    except Exception:
                        pass
                self.totals = {s: 0.0 for s in State}
                self._date = today

            if new_state != self._state:
                self._flush_segment(now)
                logging.debug("State %s → %s", self._state.value, new_state.value)
                self._state = new_state
                self._segment_start = now

    def snapshot(self) -> tuple[dict[State, float], str, State, bool]:
        """Return (totals_including_running_segment, date_str, current_state, paused)."""
        with self._lock:
            copy = dict(self.totals)
            if not self._paused:
                now = time.monotonic()
                copy[self._state] = copy.get(self._state, 0.0) + (now - self._segment_start)
            return copy, self._date, self._state, self._paused

    # ------------------------------------------------------------------ helpers

    def _flush_segment(self, now: float):
        elapsed = now - self._segment_start
        self.totals[self._state] = self.totals.get(self._state, 0.0) + elapsed
        self._segment_start = now

    def _format_totals(self) -> str:
        def fmt(s):
            secs = self.totals.get(s, 0.0)
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            return f"{h}h{m:02d}m"
        return f"Active={fmt(State.ACTIVE)} Idle={fmt(State.IDLE)} Lock={fmt(State.LOCK)}"
