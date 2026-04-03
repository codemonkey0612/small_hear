import json
import os
import logging
import pathlib
from tracker.state_machine import State


def save(state_file: str, date_str: str, totals: dict):
    path = pathlib.Path(state_file)
    data = {
        "date": date_str,
        "totals": {k.value: v for k, v in totals.items()}
    }
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception as e:
        logging.warning("Failed to save state: %s", e)


def load(state_file: str) -> dict | None:
    path = pathlib.Path(state_file)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Validate structure
        _ = data["date"]
        _ = data["totals"]
        return data
    except Exception as e:
        logging.warning("Failed to load state: %s", e)
        return None


def decode_totals(raw_totals: dict) -> dict:
    """Convert JSON {"ACTIVE": 123.4, ...} back to {State.ACTIVE: 123.4, ...}."""
    result = {State.ACTIVE: 0.0, State.IDLE: 0.0, State.LOCK: 0.0}
    for key, val in raw_totals.items():
        try:
            result[State(key)] = float(val)
        except (ValueError, KeyError):
            pass
    return result
