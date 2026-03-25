import json
from pathlib import Path
from polymarket_engine.data_adapters.polymarket_adapter import PolymarketAdapter

OUT = Path("analytics/polymarket_snapshot.json")

def is_valid_market(name):
    n = name.lower().strip()

    # senate control 2026
    if "senate" in n and "2026" in n and ("democratic party control" in n or "republican party control" in n):
        return True

    # bitcoin 100k-ish by 2026
    if "bitcoin" in n and "2026" in n and ("100k" in n or "100,000" in n or "$100k" in n or "$100,000" in n):
        return True

    # recession 2025
    if "recession" in n and "2025" in n:
        return True

    # fed cuts 2025
    if "fed" in n and "2025" in n and "cut" in n:
        return True

    # exact trump 2028 presidential election only
    if n == "will donald trump win the 2028 us presidential election?":
        return True

    return False

def safe_yes_price(m):
    try:
        raw = m.get("outcomePrices")
        if not raw:
            return None
        prices = json.loads(raw)
        if not prices:
            return None
        return float(prices[0])
    except Exception:
        return None

def main():
    adapter = PolymarketAdapter()
    markets = adapter._fetch_active_markets(limit=500)

    rows = []
    for m in markets:
        try:
            name = m.get("question")
            if not name or not is_valid_market(name):
                continue

            yes_price = safe_yes_price(m)
            if yes_price is None:
                continue

            rows.append({
                "market_id": str(m.get("id")),
                "market_name": str(name),
                "yes_price": float(yes_price),
            })
        except Exception:
            continue

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print("EXACT rows:", len(rows))
    for r in rows[:10]:
        print(r["market_name"], "|", r["yes_price"])

if __name__ == "__main__":
    main()
