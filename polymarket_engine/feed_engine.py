import json
from pathlib import Path
from datetime import datetime, timezone

TOP = Path("analytics/top_opportunities.json")
PERF = Path("analytics/performance_metrics.json")
LEARN = Path("analytics/learning_engine.json")
REGIME = Path("analytics/market_regime.json")

OUT = Path("analytics/intelligence_feed.json")


def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    top = load_json(TOP)
    perf = load_json(PERF)
    learn = load_json(LEARN)
    regime = load_json(REGIME)

    top_now = top.get("top_opportunities_now", [])
    emerging = top.get("emerging_opportunities", [])
    decaying = top.get("decaying_opportunities", [])

    avg_ev = perf.get("avg_expected_value", 0)
    avg_urg = perf.get("avg_execution_urgency", 0)

    best_market = None
    if top_now:
        best_market = top_now[0]
    elif emerging:
        best_market = emerging[0]
    elif decaying:
        best_market = decaying[0]

    feed = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_environment": regime.get("regime", "unknown"),
        "ranking_mode": (learn.get("tuning_profile") or {}).get("ranking_mode", "unknown"),
        "top_opportunities_count": len(top_now),
        "emerging_count": len(emerging),
        "decaying_count": len(decaying),
        "avg_expected_value": round(avg_ev, 6),
        "avg_execution_urgency": round(avg_urg, 6),
        "best_market": best_market,
    }

    OUT.write_text(json.dumps(feed, indent=2), encoding="utf-8")

    print("FEED ENGINE REWRITTEN OK")
    print("file: analytics/intelligence_feed.json")


if __name__ == "__main__":
    main()
