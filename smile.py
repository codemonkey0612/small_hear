"""
smile.py — Windows active-time tracker
Tracks accumulated active time from midnight to midnight via the system tray.
Pause manually when stepping away.

Usage:
  smile.exe                       # run silently (no console)
  python smile.py                 # run with console (debugging)
  python smile.py --register      # add to Windows startup
  python smile.py --unregister    # remove from startup
  python smile.py --status        # show startup status
"""

import sys
import os
import pathlib
import subprocess
import logging
import logging.handlers
import argparse
from datetime import date

if getattr(sys, 'frozen', False):
    _APP_DIR = pathlib.Path(sys.executable).parent
else:
    _APP_DIR = pathlib.Path(__file__).parent

_STATE_FILE = str(_APP_DIR / "state.json")
_LOG_FILE   = str(_APP_DIR / "smile.log")


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
    parser = argparse.ArgumentParser(description="smile — Windows active-time tracker")
    parser.add_argument("--register",   action="store_true")
    parser.add_argument("--unregister", action="store_true")
    parser.add_argument("--status",     action="store_true")
    parser.add_argument("--detached",   action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if not args.detached and not getattr(sys, 'frozen', False):
        _relaunch_detached()
        return

    _setup_logging(_LOG_FILE)
    log = logging.getLogger("main")

    from tracker.startup import register, unregister, is_registered
    if args.register:   register();   return
    if args.unregister: unregister(); return
    if args.status:     print("Registered:", is_registered()); return

    log.info("Starting smile")

    from tracker.state_machine import StateMachine
    from tracker.tray          import TrayIcon
    from tracker               import persistence

    sm = StateMachine()

    saved = persistence.load(_STATE_FILE)
    if saved and saved.get("date") == date.today().isoformat():
        sm.preload(float(saved.get("active_seconds", 0)))
        log.info("Restored today's active time")

    def _save():
        secs, date_str, _ = sm.snapshot()
        persistence.save(_STATE_FILE, date_str, secs)

    def _on_pause():
        sm.pause()
        _save()

    def _on_resume():
        sm.resume()

    def _on_quit():
        log.info("Quit via tray")
        try:
            _save()
        except Exception as e:
            log.warning("Save on quit failed: %s", e)
        os._exit(0)

    tray = TrayIcon(
        state_machine=sm,
        on_pause=_on_pause,
        on_resume=_on_resume,
        on_quit=_on_quit,
    )

    log.info("Started")
    try:
        tray.run()
    except KeyboardInterrupt:
        _save()


if __name__ == "__main__":
    main()
