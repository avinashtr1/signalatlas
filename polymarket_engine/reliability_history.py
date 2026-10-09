"""Observed reliability transitions; no historical reconstruction."""

import json
import os
from pathlib import Path

VALID_STATES = {"HEALTHY", "PENDING", "DEGRADED"}
MAX_EVENTS = 5000


def read_events(history_path, limit=None):
    """Return valid observed events in chronological order."""
    path = Path(history_path)
    if not path.exists():
        return []

    events = []
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
                if (
                    isinstance(event, dict)
                    and event.get("state") in VALID_STATES
                    and isinstance(event.get("observed_at"), str)
                ):
                    events.append(event)
            except (ValueError, TypeError):
                continue

    return events[-limit:] if limit is not None else events


def record_transition(history_path, observed_at, state, reasons):
    """Append only on state changes; retain latest valid observations."""
    path = Path(history_path)

    if state not in VALID_STATES:
        raise ValueError(f"Invalid reliability state: {state}")

    events = read_events(path)
    previous = events[-1] if events else None

    if previous is not None and previous["state"] == state:
        return None

    event = {
        "observed_at": observed_at,
        "state": state,
        "previous_state": previous["state"] if previous else None,
        "event": (
            "BASELINE" if previous is None
            else "RECOVERED"
            if previous["state"] == "DEGRADED" and state == "HEALTHY"
            else "TRANSITION"
        ),
        "reasons": list(reasons),
    }

    events.append(event)
    path.parent.mkdir(parents=True, exist_ok=True)

    if len(events) <= MAX_EVENTS:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, separators=(",", ":")) + "\n")
    else:
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            with temp.open("w", encoding="utf-8") as stream:
                for item in events[-MAX_EVENTS:]:
                    stream.write(json.dumps(item, separators=(",", ":")) + "\n")
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    return event
