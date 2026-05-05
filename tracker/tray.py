"""
System tray icon — displays active hours as a number.
Right-click menu: Pause / Resume / Quit.
"""

import time
import threading
import logging

import pystray
from PIL import Image, ImageDraw, ImageFont


_COLOR_RUNNING = "#22c55e"
_COLOR_PAUSED  = "#64748b"


def _load_font(size: int):
    for name in ("seguibl.ttf", "arialbd.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


_FONT = _load_font(40)


def _make_icon(hours: float, paused: bool) -> Image.Image:
    color = _COLOR_PAUSED if paused else _COLOR_RUNNING
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
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
            "smile",
            icon=_make_icon(0.0, False),
            title="smile",
            menu=menu,
        )
        threading.Thread(target=self._refresh_loop, daemon=True).start()
        self._icon.run(setup=lambda i: setattr(i, "visible", True))

    def _refresh_loop(self):
        last_text = None
        last_paused = None
        while True:
            time.sleep(1)
            if not self._icon:
                continue
            self._sm.tick()
            secs, _, paused = self._sm.snapshot()
            hours = secs / 3600
            text = f"{hours:.1f}"
            if text == last_text and paused == last_paused:
                continue
            last_text, last_paused = text, paused
            try:
                self._icon.icon  = _make_icon(hours, paused)
                self._icon.title = (
                    f"smile — PAUSED: {hours:.1f}h" if paused
                    else f"smile — {hours:.1f}h"
                )
            except Exception:
                pass

    def _do_pause(self, icon=None, item=None):
        self._on_pause()

    def _do_resume(self, icon=None, item=None):
        self._on_resume()

    def _do_quit(self, icon=None, item=None):
        self._on_quit()
