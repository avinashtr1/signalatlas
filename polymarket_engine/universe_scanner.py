import requests, json, time
from pathlib import Path
from datetime import datetime, timezone

OUT = Path("analytics/market_universe.json")
API = "https://gamma-api.polymarket.com/markets"

PAGE_SIZE = 100
MAX_PAGES = 200
SLEEP_MS = 150

def fetch_page(offset: int):
    params = {
        "limit": PAGE_SIZE,
        "offset": offset,
        "active": "true"
    }
    r = requests.get(API, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def safe_float(x, default=0.0):
    try:
        if x in (None, ""):
            return default
        return float(x)
    except Exception:
        return default

def main():
    markets = []
    seen_ids = set()

    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        data = fetch_page(offset)

        if not data:
            break

        added = 0
        for m in data:
            mid = str(m.get("id") or "")
            if not mid or mid in seen_ids:
                continue
            seen_ids.add(mid)

            markets.append({
                "id": mid,
                "question": m.get("question") or m.get("title") or "",
                "slug": m.get("slug"),
                "active": m.get("active"),
                "closed": m.get("closed"),
                "liquidity": safe_float(m.get("liquidity")),
                "volume": safe_float(m.get("volume")),
                "endDate": m.get("endDate"),
                "category": m.get("category"),
                "description": m.get("description"),
            })
            added += 1

        if added == 0:
            break

        time.sleep(SLEEP_MS / 1000.0)

    markets.sort(key=lambda x: (x["volume"], x["liquidity"]), reverse=True)

    OUT.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(markets),
        "markets": markets
    }, indent=2), encoding="utf-8")

    print("UNIVERSE SCANNER BUILT")
    print("markets discovered:", len(markets))
    if markets:
        print("top market:", markets[0]["question"])

if __name__ == "__main__":
    main()
