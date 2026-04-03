"""
System tray icon — the sole UI for the time tracker.
Must run on the main thread (pystray requirement on Windows).

Menu shows live time totals, updated every second.
Right-click → see times, pause/resume, quit.
"""

import time
import threading
import logging

import pystray
from PIL import Image, ImageDraw
from tracker.state_machine import State


# ── icon drawing ──────────────────────────────────────────────────────────────

_STATE_COLORS = {
    "ACTIVE": "#22c55e",
    "IDLE":   "#f59e0b",
    "LOCK":   "#ef4444",
    "PAUSED": "#64748b",
}

def _make_icon(state: str) -> Image.Image:
    color = _STATE_COLORS.get(state, "#64748b")
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outer glow ring
    draw.ellipse([2, 2, 62, 62], fill=color + "55" if len(color) == 7 else color)
    # Solid inner circle
    draw.ellipse([10, 10, 54, 54], fill=color)
    return img


# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt(secs: float) -> str:
    secs = max(0.0, secs)
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def _bar(secs: float, total: float, width: int = 10) -> str:
    ratio = min(secs / total, 1.0) if total > 0 else 0.0
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


# ── TrayIcon ──────────────────────────────────────────────────────────────────

class TrayIcon:
    def __init__(self, state_machine, on_pause, on_resume, on_quit):
        self._sm        = state_machine
        self._on_pause  = on_pause
        self._on_resume = on_resume
        self._on_quit   = on_quit
        self._paused    = False
        self._icon      = None

    def run(self):
        """Block the calling thread — must be the main thread on Windows."""
        self._icon = pystray.Icon(
            "TimeTracker",
            icon=_make_icon("ACTIVE"),
            title="Time Tracker",
            menu=pystray.Menu(self._build_menu_items),
        )
        # Background thread refreshes icon + menu every second
        t = threading.Thread(target=self._refresh_loop, daemon=True)
        t.start()

        # setup= ensures the icon is visible before the loop starts
        self._icon.run(setup=self._on_setup)

    def update_state(self, state_name: str):
        if self._icon:
            try:
                self._icon.icon = _make_icon(state_name)
            except Exception:
                pass

    # ── menu factory (called by pystray on every menu open) ──────────────────

    def _build_menu_items(self):
        totals, date_str, state, paused = self._sm.snapshot()
        active = totals.get(State.ACTIVE, 0)
        idle   = totals.get(State.IDLE,   0)
        lock   = totals.get(State.LOCK,   0)
        total  = active + idle + lock or 1

        status_label = f"{'⏸ PAUSED' if paused else ('🟢 ACTIVE' if state.value == 'ACTIVE' else ('🟡 IDLE' if state.value == 'IDLE' else '🔴 LOCKED'))}"

        items = [
            pystray.MenuItem(f"📅  {date_str}", None, enabled=False),
            pystray.MenuItem(status_label,      None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"💚 Active   {_fmt(active)}  {_bar(active, total)}  {active/total*100:.0f}%", None, enabled=False),
            pystray.MenuItem(f"💛 Idle     {_fmt(idle)}   {_bar(idle,   total)}  {idle/total*100:.0f}%",   None, enabled=False),
            pystray.MenuItem(f"❤️  Locked   {_fmt(lock)}   {_bar(lock,   total)}  {lock/total*100:.0f}%",   None, enabled=False),
            pystray.Menu.SEPARATOR,
        ]

        if paused:
            items.append(pystray.MenuItem("▶  Resume", self._do_resume))
        else:
            items.append(pystray.MenuItem("⏸  Pause",  self._do_pause))

        items.append(pystray.MenuItem("✖  Quit", self._do_quit))
        return items

    def _on_setup(self, icon):
        icon.visible = True
        logging.info("Tray icon visible")

    # ── background refresh ────────────────────────────────────────────────────

    def _refresh_loop(self):
        while True:
            time.sleep(1)
            if not self._icon:
                continue
            _, _, state, paused = self._sm.snapshot()
            label = "PAUSED" if paused else state.value
            try:
                self._icon.icon  = _make_icon(label)
                self._icon.title = f"Time Tracker — {label}"
            except Exception:
                pass

    # ── actions ───────────────────────────────────────────────────────────────

    def _do_pause(self, icon=None, item=None):
        self._paused = True
        logging.info("Paused via tray")
        self._on_pause()

    def _do_resume(self, icon=None, item=None):
        self._paused = False
        logging.info("Resumed via tray")
        self._on_resume()

    def _do_quit(self, icon=None, item=None):
        logging.info("Quit via tray")
        self._on_quit()   # calls os._exit(0)
