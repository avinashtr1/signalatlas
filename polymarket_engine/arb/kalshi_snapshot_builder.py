import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("analytics/kalshi_snapshot.json")
BASE = "https://trading-api.kalshi.com/v1/markets"

def fetch_page(limit=100, cursor=None):
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    url = BASE + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def f(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def main():
    rows = []
    cursor = None

    for i in range(5):
        data = fetch_page(limit=100, cursor=cursor)
        markets = data.get("markets", [])

        added = 0
        for m in markets:
            try:
                price = f(m.get("yes_price"))
                volume = f(m.get("volume"))
                liquidity = f(m.get("liquidity"))

                if price <= 0 or price >= 1:
                    continue
                if liquidity <= 0:
                    continue

                rows.append({
                    "market_id": m.get("ticker"),
                    "market_name": m.get("title"),
                    "yes_price": price,
                    "liquidity": liquidity,
                    "volume": volume
                })
                added += 1
            except:
                continue

        print(f"page {i+1}: added {added} | total {len(rows)}")

        cursor = data.get("cursor")
        if not cursor:
            break

        time.sleep(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))

    print("rows:", len(rows))
    if rows:
        print("sample:", rows[0])

if __name__ == "__main__":
    main()
