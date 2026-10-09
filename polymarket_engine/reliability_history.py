"""Observed reliability transitions; no historical reconstruction."""

import json
from pathlib import Path


def record_transition(history_path, observed_at, state, reasons):
    """Append only when the observed state changes."""
    history_path = Path(history_path)
    valid = {"HEALTHY", "PENDING", "DEGRADED"}

    if state not in valid:
        raise ValueError(f"Invalid reliability state: {state}")

    previous = None

    if history_path.exists():
        with history_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    previous = json.loads(line)

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

    history_path.parent.mkdir(parents=True, exist_ok=True)

    with history_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, separators=(",", ":")) + "\n")

    return event
