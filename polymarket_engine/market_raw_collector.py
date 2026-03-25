import json
import requests
from pathlib import Path
from datetime import datetime, timezone

OUT = Path("analytics/market_raw.json")

MAX_MARKETS = 200
PAGE_SIZE = 50

URL = "https://gamma-api.polymarket.com/markets"

def fetch_page(offset):
    params = {
        "limit": PAGE_SIZE,
        "offset": offset,
        "active": "true"
    }
    r = requests.get(URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def main():

    markets = []
    offset = 0

    while len(markets) < MAX_MARKETS:

        data = fetch_page(offset)

        if not data:
            break

        markets.extend(data)
        offset += PAGE_SIZE

        if len(data) < PAGE_SIZE:
            break

    markets = markets[:MAX_MARKETS]

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(markets),
        "rows": markets
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("RAW MARKET COLLECTOR BUILT")
    print("markets:", len(markets))
    print("file:", OUT)

if __name__ == "__main__":
    main()
