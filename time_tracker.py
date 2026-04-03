"""
time_tracker.py — Windows Time Tracker
Tracks ACTIVE / IDLE / LOCK time from midnight to midnight.
All output is via the system tray icon — no Telegram needed.

Usage:
  .\TimeTracker.exe time_tracker.py          # run silently (no console)
  python time_tracker.py                     # run with console (debugging)
  python time_tracker.py --register          # add to Windows startup
  python time_tracker.py --unregister        # remove from startup
  python time_tracker.py --status            # show startup status
"""

import sys
import os
import pathlib
import subprocess
import logging
import logging.handlers
import argparse
from datetime import date

# Resolve the directory where the exe (or script) lives — works both frozen and plain
if getattr(sys, 'frozen', False):
    _APP_DIR = pathlib.Path(sys.executable).parent
else:
    _APP_DIR = pathlib.Path(__file__).parent

_STATE_FILE = str(_APP_DIR / "state.json")
_LOG_FILE   = str(_APP_DIR / "TimeTracker.log")


def _setup_logging(log_file: str):
    handlers = [
        logging.handlers.RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
    ]
    try:
        if sys.stdout and sys.stdout.fileno() >= 0:
            handlers.append(logging.StreamHandler(sys.stdout))
    except Exception:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=handlers,
    )


def _relaunch_detached():
    """Relaunch this process fully detached from any console, then exit."""
    pythonw = pathlib.Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = pathlib.Path(sys.executable)
    subprocess.Popen(
        [str(pythonw), str(__file__), "--detached"],
        cwd=str(_APP_DIR),
        creationflags=0x00000008,  # DETACHED_PROCESS
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Windows Time Tracker")
    parser.add_argument("--register",   action="store_true")
    parser.add_argument("--unregister", action="store_true")
    parser.add_argument("--status",     action="store_true")
    parser.add_argument("--detached",   action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    # If launched from a terminal (not already detached), relaunch detached
    if not args.detached and not getattr(sys, 'frozen', False):
        _relaunch_detached()
        return  # never reached

    import config
    _setup_logging(_LOG_FILE)
    log = logging.getLogger("main")

    from tracker.startup import register, unregister, is_registered
    if args.register:
        register(); return
    if args.unregister:
        unregister(); return
    if args.status:
        print("Registered:", is_registered()); return

    log.info("Starting Time Tracker (idle threshold: %ds)", config.IDLE_THRESHOLD_SEC)

    from tracker.state_machine import StateMachine
    from tracker.idle_monitor  import IdleMonitor
    from tracker.lock_monitor  import LockMonitor
    from tracker.tray          import TrayIcon
    from tracker               import persistence

    sm = StateMachine()

    # Restore today's totals from a previous run if available
    saved = persistence.load(_STATE_FILE)
    if saved and saved.get("date") == date.today().isoformat():
        sm.preload_totals(persistence.decode_totals(saved["totals"]))
        log.info("Restored today's totals")

    idle = IdleMonitor(sm, config.IDLE_THRESHOLD_SEC)
    lock = LockMonitor(sm, idle)

    def _save():
        totals, date_str, _, _ = sm.snapshot()
        persistence.save(_STATE_FILE, date_str, totals)

    def _on_pause():
        sm.pause()
        idle.set_paused(True)
        _save()

    def _on_resume():
        idle.set_paused(False)
        sm.resume()

    def _on_quit():
        log.info("Quit via tray")
        _save()
        os._exit(0)

    tray = TrayIcon(
        state_machine=sm,
        on_pause=_on_pause,
        on_resume=_on_resume,
        on_quit=_on_quit,
    )

    lock.start()   # background thread

    log.info("All components started")
    try:
        tray.run()   # blocks main thread (pystray requirement)
    except KeyboardInterrupt:
        _save()


if __name__ == "__main__":
    main()
