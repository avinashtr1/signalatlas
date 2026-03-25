import json
from datetime import datetime, timezone
from pathlib import Path


class CycleLogger:
    def __init__(self, path="logs/cycle_audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, payload: dict):
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
