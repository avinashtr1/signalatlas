import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SNAP = Path("analytics/market_snapshots.json")
SEL = Path("analytics/selected_markets.json")
OUT = Path("analytics/cross_market_lead_lag.json")

MIN_MOVE = 0.03
MAX_SELECTED = 50

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def to_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

def main():
    snap = load_json(SNAP).get("rows", [])
    selected = load_json(SEL).get("markets", [])[:MAX_SELECTED]

    selected_names = {m.get("market_name") for m in selected if m.get("market_name")}

    by_market = defaultdict(list)
    for r in snap:
        name = r.get("market_name")
        if name in selected_names:
            by_market[name].append(r)

    deltas = []
    for name, items in by_market.items():
        items = sorted(items, key=lambda x: x.get("timestamp", ""))
        if len(items) < 2:
            continue

        prev = items[-2]
        curr = items[-1]

        prev_prob = to_float(prev.get("radar_score"), 0.0)
        curr_prob = to_float(curr.get("radar_score"), 0.0)
        delta = curr_prob - prev_prob

        if abs(delta) >= MIN_MOVE:
            deltas.append({
                "market_name": name,
                "prev_probability": round(prev_prob, 6),
                "curr_probability": round(curr_prob, 6),
                "delta": round(delta, 6),
                "direction": "up" if delta > 0 else "down"
            })

    deltas.sort(key=lambda x: abs(x["delta"]), reverse=True)

    leader = deltas[0] if deltas else None
    laggers = deltas[1:6] if len(deltas) > 1 else []

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(deltas),
        "leader": leader,
        "laggers": laggers,
        "signals": deltas
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("CROSS MARKET LEAD LAG ENGINE BUILT")
    print("count:", len(deltas))
    print("file:", OUT)

if __name__ == "__main__":
    main()
