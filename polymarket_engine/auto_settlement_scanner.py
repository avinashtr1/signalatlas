import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
OUTCOMES_PATH = Path("analytics/market_outcomes.json")
OUT_JSON = Path("analytics/auto_settlement_scan.json")
OUT_TXT = Path("analytics/auto_settlement_scan.txt")

GAMMA_BASE = "https://gamma-api.polymarket.com"

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def fetch_market(market_id: str):
    url = f"{GAMMA_BASE}/markets/{market_id}"
    req = Request(url, headers={"User-Agent": "SignalAtlas/1.0"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_outcome(m):
    """
    Conservative parser:
    - If explicit winner/outcome fields exist, use them.
    - Else if outcomePrices are effectively [1,0] or [0,1], infer YES/NO.
    - Otherwise return None.
    """
    candidates = [
        m.get("outcome"),
        m.get("winner"),
        m.get("resolution"),
        m.get("result"),
        m.get("resolvedOutcome"),
    ]
    for c in candidates:
        if isinstance(c, str):
            c2 = c.strip().upper()
            if c2 in {"YES", "NO"}:
                return c2

    prices = m.get("outcomePrices")
    outcomes = m.get("outcomes")

    try:
        if isinstance(prices, str):
            prices = json.loads(prices)
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
    except Exception:
        pass

    if isinstance(prices, list) and len(prices) >= 2:
        try:
            p0 = float(prices[0])
            p1 = float(prices[1])
            if p0 >= 0.999 and p1 <= 0.001:
                return "YES"
            if p1 >= 0.999 and p0 <= 0.001:
                return "NO"
        except Exception:
            pass

    return None

def main():
    leaderboard = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    outcomes_doc = load_json(OUTCOMES_PATH)
    outcomes = outcomes_doc.setdefault("outcomes", {})

    scanned = 0
    updated = 0
    detected = []

    for row in leaderboard:
        market_id = str(row.get("market_id") or "").strip()
        market_name = row.get("market_name")
        if not market_id or not market_name:
            continue

        scanned += 1
        try:
            market = fetch_market(market_id)
        except (URLError, HTTPError, TimeoutError, ValueError) as e:
            detected.append({
                "market_name": market_name,
                "market_id": market_id,
                "status": "fetch_error",
                "detail": str(e),
            })
            continue

        outcome = parse_outcome(market)
        if outcome in {"YES", "NO"}:
            prev = outcomes.get(market_name)
            outcomes[market_name] = outcome
            if prev != outcome:
                updated += 1
            detected.append({
                "market_name": market_name,
                "market_id": market_id,
                "status": "resolved",
                "outcome": outcome,
            })
        else:
            detected.append({
                "market_name": market_name,
                "market_id": market_id,
                "status": "unresolved_or_unknown",
            })

    save_json(OUTCOMES_PATH, outcomes_doc)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scanned": scanned,
        "updated_outcomes": updated,
        "results": detected,
    }
    save_json(OUT_JSON, payload)

    lines = [
        "SIGNALATLAS AUTO SETTLEMENT SCAN",
        "",
        f"Scanned: {scanned}",
        f"Updated outcomes: {updated}",
        "",
    ]
    for r in detected[:10]:
        if r["status"] == "resolved":
            lines.append(f"{r['market_name']} | {r['outcome']}")
        else:
            lines.append(f"{r['market_name']} | {r['status']}")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/auto_settlement_scan.json")
    print("analytics/auto_settlement_scan.txt")

if __name__ == "__main__":
    main()
