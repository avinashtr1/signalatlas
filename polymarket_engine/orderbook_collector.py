import requests
import json
from pathlib import Path
from datetime import datetime, timezone

RAW = Path("analytics/market_raw.json")
OUT = Path("analytics/orderbooks.json")

MAX_MARKETS = 20

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def main():

    raw = load_json(RAW)

    rows = []
    markets = raw.get("rows", [])[:MAX_MARKETS]

    for m in markets:

        question = m.get("market_name")
        bid = m.get("best_bid")
        ask = m.get("best_ask")

        # proxy depth values
        bid_depth = 0
        ask_depth = 0

        if bid is not None:
            bid_depth = abs(bid * 1000)

        if ask is not None:
            ask_depth = abs((1-ask) * 1000)

        rows.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_name": question,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth
        })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "rows": rows
    }

    OUT.write_text(json.dumps(out, indent=2))

    print("ORDERBOOK COLLECTOR BUILT")
    print("markets:", len(rows))
    print("file:", OUT)

if __name__ == "__main__":
    main()
