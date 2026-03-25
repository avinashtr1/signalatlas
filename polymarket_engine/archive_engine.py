import json
from pathlib import Path
from datetime import datetime, timezone

FEED = Path("analytics/intelligence_feed.json")
ARCHIVE = Path("analytics/feed_archive.json")

MAX_ROWS = 200

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    feed = load_json(FEED)
    best = feed.get("best_market") or {}

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_environment": feed.get("market_environment", "unknown"),
        "ranking_mode": feed.get("ranking_mode", "unknown"),
        "top_opportunities_count": int(feed.get("top_opportunities_count", 0) or 0),
        "emerging_count": int(feed.get("emerging_count", 0) or 0),
        "decaying_count": int(feed.get("decaying_count", 0) or 0),
        "avg_expected_value": float(feed.get("avg_expected_value", 0.0) or 0.0),
        "avg_execution_urgency": float(feed.get("avg_execution_urgency", 0.0) or 0.0),
        "best_market_name": best.get("market_name"),
        "radar_score": float(best.get("radar_score", 0.0) or 0.0),
        "confidence_score": float(best.get("confidence_score", 0.0) or 0.0),
        "expected_value": float(best.get("expected_value", 0.0) or 0.0),
        "execution_urgency": float(best.get("execution_urgency", 0.0) or 0.0),
        "opportunity_score": float(best.get("opportunity_score", 0.0) or 0.0),
        "opportunity_tier": best.get("opportunity_tier", "D"),
        "freshness": best.get("freshness", "unknown"),
        "momentum": best.get("momentum", "unknown"),
    }

    doc = load_json(ARCHIVE)
    rows = doc.get("rows", [])
    rows.append(row)
    rows = rows[-MAX_ROWS:]

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "rows": rows,
    }

    ARCHIVE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("ARCHIVE ENGINE BUILT")
    print("file:", ARCHIVE)
    print("count:", len(rows))

if __name__ == "__main__":
    main()
