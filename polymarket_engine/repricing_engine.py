import json
from pathlib import Path
from datetime import datetime, timezone

MEM = Path("analytics/signal_memory.json")
SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/repricing_events.json")

REPRICE_THRESHOLD = 0.03

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    mem = load_json(MEM).get("rows", [])
    snap = load_json(SNAP).get("rows", [])

    events = []

    snap_map = {}

    for r in snap:
        snap_map[r["market_name"]] = r

    for r in mem:
        name = r["market_name"]
        base = r.get("radar_score",0)

        if name not in snap_map:
            continue

        now_prob = snap_map[name].get("radar_score",0)

        delta = now_prob - base

        if abs(delta) >= REPRICE_THRESHOLD:
            events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": name,
                "base_probability": base,
                "current_probability": now_prob,
                "repricing_delta": delta
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(events),
        "events": events
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("REPRICING ENGINE BUILT")
    print("file:", OUT)
    print("events:", len(events))

if __name__ == "__main__":
    main()
