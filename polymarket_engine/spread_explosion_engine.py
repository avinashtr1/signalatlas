import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/spread_explosions.json")

MIN_ROWS = 2
SPREAD_MULTIPLIER = 2.0
MIN_ABS_SPREAD = 0.05

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def to_float(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default

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

        prev_spread = to_float(prev.get("spread"), None)
        curr_spread = to_float(curr.get("spread"), None)
        curr_vol = to_float(curr.get("volume"), None)

        if prev_spread is None or curr_spread is None:
            continue

        spread_ratio = None
        if prev_spread > 0:
            spread_ratio = curr_spread / prev_spread

        exploded = (
            curr_spread >= MIN_ABS_SPREAD and
            spread_ratio is not None and
            spread_ratio >= SPREAD_MULTIPLIER
        )

        if exploded:
            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": name,
                "prev_spread": round(prev_spread, 6),
                "curr_spread": round(curr_spread, 6),
                "spread_ratio": round(spread_ratio, 6),
                "volume": curr_vol,
                "state": "spread_explosion"
            })

    signals.sort(key=lambda x: x["spread_ratio"], reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("SPREAD EXPLOSION ENGINE BUILT")
    print("signals:", len(signals))
    print("file:", OUT)

if __name__ == "__main__":
    main()
