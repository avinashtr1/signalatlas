import json
from pathlib import Path
from datetime import datetime, timezone

BOOK = Path("analytics/orderbooks.json")
OUT = Path("analytics/orderbook_imbalance.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def main():

    data = load_json(BOOK)

    signals = []

    for r in data.get("rows", []):

        bid = r.get("bid_depth",0)
        ask = r.get("ask_depth",0)

        total = bid + ask

        if total == 0:
            continue

        imbalance = (bid - ask) / total

        if abs(imbalance) > 0.4:

            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": r.get("market_name"),
                "imbalance": round(imbalance,4),
                "direction": "buy_pressure" if imbalance>0 else "sell_pressure"
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals
    }

    OUT.write_text(json.dumps(out,indent=2))

    print("ORDERBOOK IMBALANCE ENGINE BUILT")
    print("signals:",len(signals))
    print("file:",OUT)

if __name__ == "__main__":
    main()
