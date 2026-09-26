import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
OUT_PATH = Path("analytics/market_quality.json")

def load_leaderboard():
    if not LEADERBOARD_PATH.exists():
        return []
    data = json.loads(LEADERBOARD_PATH.read_text(encoding="utf-8"))
    return data.get("leaderboard", [])

def classify_market(row):

    edge = float(row.get("total_edge", 0.0) or 0.0)
    micro = float(row.get("microstructure_score", 0.0) or 0.0)
    vacuum = float(row.get("vacuum_score", 0.0) or 0.0)
    net = float(row.get("expected_net_edge_pct", 0.0) or 0.0)

    # High quality tradable markets
    if edge >= 0.10 and net >= 8 and micro >= 0.03:
        return "tradable"

    # Interesting but weaker signals
    if edge >= 0.06:
        return "watchlist"

    return "ignore"

def main():

    rows = load_leaderboard()

    tradable = []
    watchlist = []
    ignored = []

    for r in rows:
        category = classify_market(r)

        if category == "tradable":
            tradable.append(r)

        elif category == "watchlist":
            watchlist.append(r)

        else:
            ignored.append(r)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tradable": tradable[:20],
        "watchlist": watchlist[:20],
        "ignored": ignored[:50],
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("MARKET QUALITY REPORT")
    print("")
    print("tradable:", len(tradable))
    print("watchlist:", len(watchlist))
    print("ignored:", len(ignored))
    print("")
    print("file created:")
    print("analytics/market_quality.json")

if __name__ == "__main__":
    main()
