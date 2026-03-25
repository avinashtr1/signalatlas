import json
from pathlib import Path

INP = Path("analytics/kalshi_snapshot.json")
OUT = Path("analytics/kalshi_snapshot_clean.json")

def is_valid(name: str, price: float) -> bool:
    n = name.lower()

    # remove obvious combo/parlay spam
    if n.count(",") >= 2:
        return False

    # remove very long junk titles
    if len(n) > 120:
        return False

    # remove dead extremes
    if price <= 0.01 or price >= 0.99:
        return False

    return True

def main():
    if not INP.exists():
        print("missing:", INP)
        return

    rows = json.loads(INP.read_text(encoding="utf-8"))
    clean = []

    for r in rows:
        try:
            name = str(r.get("market_name", ""))
            price = float(r.get("yes_price", 0))
            if is_valid(name, price):
                clean.append(r)
        except Exception:
            continue

    OUT.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    print("input_rows:", len(rows))
    print("clean_rows:", len(clean))
    if clean:
        print("sample:", clean[0])

if __name__ == "__main__":
    main()
