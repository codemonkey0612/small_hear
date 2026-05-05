import json
import os
import logging
import pathlib


def save(state_file: str, date_str: str, active_seconds: float):
    path = pathlib.Path(state_file)
    data = {"date": date_str, "active_seconds": active_seconds}
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
        _ = data["date"]
        return data
    except Exception as e:
        logging.warning("Failed to load state: %s", e)
        return None
