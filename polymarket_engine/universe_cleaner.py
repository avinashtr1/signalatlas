import json
from pathlib import Path
from datetime import datetime, timezone

SRC = Path("analytics/market_universe.json")
OUT = Path("analytics/market_universe_clean.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def parse_dt(x):
    if not x:
        return None
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None

def keep_market(m, now_utc):
    q = (m.get("question") or "").strip()
    if not q:
        return False

    end_dt = parse_dt(m.get("endDate"))
    if end_dt is not None and end_dt <= now_utc:
        return False

    return True

def main():
    doc = load_json(SRC)
    markets = doc.get("markets", [])
    now_utc = datetime.now(timezone.utc)

    clean = [m for m in markets if keep_market(m, now_utc)]

    OUT.write_text(json.dumps({
        "timestamp": now_utc.isoformat(),
        "count": len(clean),
        "markets": clean,
    }, indent=2), encoding="utf-8")

    print("UNIVERSE CLEANER BUILT")
    print("raw:", len(markets))
    print("clean:", len(clean))
    if clean:
        print("top clean:", clean[0].get("question"))
        print("top endDate:", clean[0].get("endDate"))

if __name__ == "__main__":
    main()
