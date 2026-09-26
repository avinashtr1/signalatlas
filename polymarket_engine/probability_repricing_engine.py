import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/probability_repricing.json")

MIN_ROWS = 2
REPRICE_THRESHOLD = 0.04

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    snap = load_json(SNAP)
    rows = snap.get("rows", [])

    by_market = defaultdict(list)
    for r in rows:
        name = r.get("market_name")
        if name:
            by_market[name].append(r)

    signals = []

    for name, items in by_market.items():
        items = sorted(items, key=lambda x: x.get("timestamp", ""))
        if len(items) < MIN_ROWS:
            continue

        prev = items[-2]
        curr = items[-1]

        prev_prob = float(prev.get("radar_score", 0.0) or 0.0)
        curr_prob = float(curr.get("radar_score", 0.0) or 0.0)

        delta = curr_prob - prev_prob

        if abs(delta) >= REPRICE_THRESHOLD:
            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": name,
                "prev_probability": round(prev_prob, 6),
                "curr_probability": round(curr_prob, 6),
                "repricing_delta": round(delta, 6),
                "direction": "up" if delta > 0 else "down"
            })

    signals.sort(key=lambda x: abs(x["repricing_delta"]), reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("PROBABILITY REPRICING ENGINE BUILT")
    print("signals:", len(signals))
    print("file:", OUT)

if __name__ == "__main__":
    main()
