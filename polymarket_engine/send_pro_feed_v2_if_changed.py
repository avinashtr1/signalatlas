import json
from pathlib import Path
import subprocess
import sys

DECISION = Path("analytics/feed_send_decision.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    d = load_json(DECISION)
    should_send = bool(d.get("send_pro_feed_v2", False))

    if not should_send:
        print("PRO FEED V2 SKIPPED: NO MATERIAL CHANGE")
        return

    r = subprocess.run(
        [sys.executable, "-m", "polymarket_engine.send_pro_feed_v2"],
        check=False
    )
    raise SystemExit(r.returncode)

if __name__ == "__main__":
    main()
