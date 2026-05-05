"""
System tray icon with a real-time popup window.
- Tray icon colour reflects current state, updates every second.
- Left-click or "Show" opens a small always-on-top window with live counters.
- Window updates every second while open.
"""

import time
import threading
import logging
import tkinter as tk

import pystray
from PIL import Image, ImageDraw
from tracker.state_machine import State


# ── colours ───────────────────────────────────────────────────────────────────

_STATE_COLOR = {
    "ACTIVE": "#22c55e",
    "IDLE":   "#f59e0b",
    "LOCK":   "#ef4444",
    "PAUSED": "#64748b",
}

_BG          = "#1e1e2e"   # dark background
_FG          = "#cdd6f4"   # light text
_FG_DIM      = "#6c7086"   # dimmed label


# ── tray icon image ───────────────────────────────────────────────────────────

def _make_icon(state: str) -> Image.Image:
    color = _STATE_COLOR.get(state, "#64748b")
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color)
    return img


# ── formatting ────────────────────────────────────────────────────────────────

def _fmt(secs: float) -> str:
    secs = max(0.0, secs)
    return f"{secs / 3600:.1f}"

def _pct(part: float, total: float) -> str:
    return f"{part / total * 100:.0f}%" if total > 0 else "0%"

def _bar(part: float, total: float, width: int = 12) -> str:
    ratio = min(part / total, 1.0) if total > 0 else 0.0
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


# ── popup window ──────────────────────────────────────────────────────────────

class _PopupWindow:
    def __init__(self, sm, on_pause, on_resume, on_quit, on_close):
        self._sm        = sm
        self._on_pause  = on_pause
        self._on_resume = on_resume
        self._on_quit   = on_quit
        self._on_close  = on_close
        self._root      = None
        self._labels    = {}
        self._running   = False

    def show(self):
        """Open the window (called from any thread via after_idle)."""
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return
        self._build()

    def destroy(self):
        if self._root:
            try:
                self._running = False
                self._root.destroy()
            except Exception:
                pass
            self._root = None

    def _build(self):
        self._root = tk.Tk()
        r = self._root
        r.title("Time Tracker")
        r.configure(bg=_BG)
        r.resizable(False, False)
        r.attributes("-topmost", True)
        r.protocol("WM_DELETE_WINDOW", self._close)

        # ── title row
        tk.Label(r, text="⏱  Time Tracker", bg=_BG, fg=_FG,
                 font=("Segoe UI", 13, "bold")).grid(
                 row=0, column=0, columnspan=3, pady=(14, 4), padx=20)

        self._date_lbl = tk.Label(r, text="", bg=_BG, fg=_FG_DIM,
                                  font=("Segoe UI", 9))
        self._date_lbl.grid(row=1, column=0, columnspan=3, pady=(0, 10))

        # ── state rows
        rows = [
            ("ACTIVE", "💚", _STATE_COLOR["ACTIVE"]),
            ("IDLE",   "💛", _STATE_COLOR["IDLE"]),
            ("LOCK",   "❤️",  _STATE_COLOR["LOCK"]),
        ]
        self._rows = {}
        for i, (key, icon, color) in enumerate(rows):
            base_row = 2 + i * 2

            # label
            tk.Label(r, text=f"{icon}  {key}", bg=_BG, fg=color,
                     font=("Segoe UI", 10, "bold"), width=10,
                     anchor="w").grid(row=base_row, column=0,
                                      padx=(20, 6), pady=(6, 0), sticky="w")

            # time
            time_lbl = tk.Label(r, text="00:00:00", bg=_BG, fg=_FG,
                                 font=("Courier New", 15, "bold"))
            time_lbl.grid(row=base_row, column=1, padx=6, pady=(6, 0))

            # pct
            pct_lbl = tk.Label(r, text="0%", bg=_BG, fg=_FG_DIM,
                                font=("Segoe UI", 9), width=5, anchor="e")
            pct_lbl.grid(row=base_row, column=2, padx=(0, 20), pady=(6, 0), sticky="e")

            # bar (canvas)
            bar_cv = tk.Canvas(r, bg=_BG, height=6, width=180,
                               highlightthickness=0)
            bar_cv.grid(row=base_row + 1, column=0, columnspan=3,
                        padx=20, pady=(2, 4), sticky="ew")

            self._rows[key] = (time_lbl, pct_lbl, bar_cv, color)

        # ── status label
        self._status_lbl = tk.Label(r, text="● ACTIVE", bg=_BG,
                                    fg=_STATE_COLOR["ACTIVE"],
                                    font=("Segoe UI", 9, "bold"))
        self._status_lbl.grid(row=8, column=0, columnspan=3, pady=(6, 2))

        # ── buttons
        btn_frame = tk.Frame(r, bg=_BG)
        btn_frame.grid(row=9, column=0, columnspan=3, pady=(4, 14))

        self._pause_btn = tk.Button(
            btn_frame, text="⏸  Pause", bg="#313244", fg=_FG,
            font=("Segoe UI", 9), relief="flat", padx=12, pady=5,
            cursor="hand2", command=self._toggle_pause,
            activebackground="#45475a", activeforeground=_FG,
        )
        self._pause_btn.pack(side="left", padx=6)

        tk.Button(
            btn_frame, text="✖  Quit", bg="#313244", fg="#f38ba8",
            font=("Segoe UI", 9), relief="flat", padx=12, pady=5,
            cursor="hand2", command=self._on_quit,
            activebackground="#45475a", activeforeground="#f38ba8",
        ).pack(side="left", padx=6)

        # ── position: bottom-right above taskbar
        r.update_idletasks()
        w = r.winfo_width()
        h = r.winfo_height()
        sw = r.winfo_screenwidth()
        sh = r.winfo_screenheight()
        r.geometry(f"+{sw - w - 16}+{sh - h - 56}")

        self._running = True
        self._tick()
        r.mainloop()
        self._on_close()

    def _tick(self):
        if not self._running or not self._root:
            return
        try:
            totals, date_str, state, paused = self._sm.snapshot()
            active = totals.get(State.ACTIVE, 0)
            idle   = totals.get(State.IDLE,   0)
            lock   = totals.get(State.LOCK,   0)
            total  = active + idle + lock or 1

            self._date_lbl.config(text=date_str)

            for key, val in [("ACTIVE", active), ("IDLE", idle), ("LOCK", lock)]:
                time_lbl, pct_lbl, bar_cv, color = self._rows[key]
                time_lbl.config(text=_fmt(val))
                pct_lbl.config(text=_pct(val, total))
                # redraw bar
                bar_cv.delete("all")
                bar_cv.update_idletasks()
                W = bar_cv.winfo_width() or 180
                filled_w = int(W * min(val / total, 1.0))
                bar_cv.create_rectangle(0, 0, W, 6, fill="#313244", outline="")
                if filled_w > 0:
                    bar_cv.create_rectangle(0, 0, filled_w, 6,
                                            fill=color, outline="")

            # status
            if paused:
                slabel, scolor = "⏸  PAUSED", _STATE_COLOR["PAUSED"]
            else:
                slabel = f"● {state.value}"
                scolor = _STATE_COLOR.get(state.value, _FG)
            self._status_lbl.config(text=slabel, fg=scolor)

            # pause button label
            self._pause_btn.config(
                text="▶  Resume" if paused else "⏸  Pause"
            )

        except Exception as e:
            logging.debug("Popup tick error: %s", e)

        self._root.after(1000, self._tick)

    def _toggle_pause(self):
        _, _, _, paused = self._sm.snapshot()
        if paused:
            self._on_resume()
        else:
            self._on_pause()

    def _close(self):
        self._running = False
        if self._root:
            self._root.destroy()
            self._root = None


# ── TrayIcon ──────────────────────────────────────────────────────────────────

class TrayIcon:
    def __init__(self, state_machine, on_pause, on_resume, on_quit):
        self._sm        = state_machine
        self._on_pause  = on_pause
        self._on_resume = on_resume
        self._on_quit   = on_quit
        self._icon      = None
        self._popup     = None
        self._popup_open = False

    def run(self):
        """Block the calling thread — must be the main thread on Windows."""
        menu = pystray.Menu(
            pystray.MenuItem("Show",   self._show_popup, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Pause",  self._do_pause),
            pystray.MenuItem("Resume", self._do_resume),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",   self._do_quit),
        )
        self._icon = pystray.Icon(
            "TimeTracker",
            icon=_make_icon("ACTIVE"),
            title="Time Tracker — ACTIVE",
            menu=menu,
        )
        threading.Thread(target=self._refresh_loop, daemon=True).start()
        self._icon.run(setup=lambda i: setattr(i, 'visible', True))

    # ── internal ─────────────────────────────────────────────────────────────

    def _show_popup(self, icon=None, item=None):
        if self._popup_open:
            return
        self._popup_open = True
        t = threading.Thread(target=self._run_popup, daemon=True)
        t.start()

    def _run_popup(self):
        def _closed():
            self._popup_open = False

        popup = _PopupWindow(
            sm=self._sm,
            on_pause=self._do_pause,
            on_resume=self._do_resume,
            on_quit=self._do_quit,
            on_close=_closed,
        )
        popup.show()

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

    def _do_pause(self, icon=None, item=None):
        logging.info("Paused")
        self._on_pause()

    def _do_resume(self, icon=None, item=None):
        logging.info("Resumed")
        self._on_resume()

    def _do_quit(self, icon=None, item=None):
        logging.info("Quit")
        self._on_quit()
