"""
System tray icon — displays current ACTIVE hours as a number.
Right-click menu: Pause / Resume / Quit.
"""

import time
import threading
import logging

import pystray
from PIL import Image, ImageDraw, ImageFont
from tracker.state_machine import State


_STATE_COLOR = {
    "ACTIVE": "#22c55e",
    "IDLE":   "#f59e0b",
    "LOCK":   "#ef4444",
    "PAUSED": "#64748b",
}


def _load_font(size: int):
    for name in ("seguibl.ttf", "arialbd.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


_FONT = _load_font(40)


def _make_icon(hours: float, label: str) -> Image.Image:
    color = _STATE_COLOR.get(label, "#cdd6f4")
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    text = f"{hours:.1f}"
    bbox = draw.textbbox((0, 0), text, font=_FONT)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (64 - w) // 2 - bbox[0]
    y = (64 - h) // 2 - bbox[1]
    draw.text((x, y), text, fill=color, font=_FONT)
    return img


class TrayIcon:
    def __init__(self, state_machine, on_pause, on_resume, on_quit):
        self._sm        = state_machine
        self._on_pause  = on_pause
        self._on_resume = on_resume
        self._on_quit   = on_quit
        self._icon      = None

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Pause",  self._do_pause),
            pystray.MenuItem("Resume", self._do_resume),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",   self._do_quit),
        )
        self._icon = pystray.Icon(
            "TimeTracker",
            icon=_make_icon(0.0, "ACTIVE"),
            title="Time Tracker",
            menu=menu,
        )
        threading.Thread(target=self._refresh_loop, daemon=True).start()
        self._icon.run(setup=lambda i: setattr(i, "visible", True))

    def _refresh_loop(self):
        last_text = None
        last_label = None
        while True:
            time.sleep(1)
            if not self._icon:
                continue
            totals, _, state, paused = self._sm.snapshot()
            hours = totals.get(State.ACTIVE, 0) / 3600
            label = "PAUSED" if paused else state.value
            text = f"{hours:.1f}"
            if text == last_text and label == last_label:
                continue
            last_text, last_label = text, label
            try:
                self._icon.icon  = _make_icon(hours, label)
                self._icon.title = f"Time Tracker — {label}: {hours:.1f}h"
            except Exception:
                pass

    def _do_pause(self, icon=None, item=None):
        logging.info("Paused")
        self._on_pause()

    def _do_resume(self, icon=None, item=None):
        logging.info("Resumed")
        self._on_resume()

    def _do_quit(self, icon=None, item=None):
        logging.info("Quit")
        self._on_quit()
