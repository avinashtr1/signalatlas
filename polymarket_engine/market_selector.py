import json
from pathlib import Path
from datetime import datetime, timezone

RAW = Path("analytics/market_raw.json")
OUT = Path("analytics/selected_markets.json")

TOP_N = 50

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
    raw = load_json(RAW)
    rows = raw.get("rows", [])

    ranked = []
    for r in rows:
        volume = to_float(r.get("volume"), 0.0)
        liquidity = to_float(r.get("liquidity"), 0.0)

        score = (0.6 * volume) + (0.4 * liquidity)

        ranked.append({
            "market_name": r.get("market_name"),
            "volume": volume,
            "liquidity": liquidity,
            "selection_score": round(score, 6)
        })

    ranked.sort(key=lambda x: x["selection_score"], reverse=True)
    selected = ranked[:TOP_N]

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(selected),
        "markets": selected
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("MARKET SELECTOR BUILT")
    print("count:", len(selected))
    print("file:", OUT)

if __name__ == "__main__":
    main()
