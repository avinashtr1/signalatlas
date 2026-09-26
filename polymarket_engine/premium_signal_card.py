import json
from pathlib import Path
from datetime import datetime, timezone

FEED = Path("analytics/intelligence_feed.json")
OUT = Path("analytics/intelligence_signal_card.txt")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def fmt(x, n=4):
    try:
        return f"{float(x):.{n}f}"
    except Exception:
        return "0.0000"

def main():
    feed = load_json(FEED)
    best = feed.get("best_market") or {}

    lines = [
        "🚨 SIGNALATLAS RADAR ALERT",
        "",
        f"Environment: {feed.get('market_environment', 'unknown')}",
        f"Ranking Mode: {feed.get('ranking_mode', 'unknown')}",
        "",
        "TOP MARKET",
        f"{best.get('market_name', 'N/A')}",
        "",
        f"Radar Score: {fmt(best.get('radar_score'), 6)}",
        f"Confidence: {fmt(best.get('confidence_score'), 4)}",
        f"Expected Value: {fmt(best.get('expected_value'), 6)}",
        f"Execution Urgency: {fmt(best.get('execution_urgency'), 4)}",
        f"Opportunity Score: {fmt(best.get('opportunity_score'), 6)}",
        f"Tier: {best.get('opportunity_tier', 'D')}",
        "",
        f"Freshness: {best.get('freshness', 'unknown')}",
        f"Momentum: {best.get('momentum', 'unknown')}",
        "",
        f"Emerging Signals: {feed.get('emerging_count', 0)}",
        f"Decaying Signals: {feed.get('decaying_count', 0)}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("PREMIUM SIGNAL CARD BUILT")
    print("file:", OUT)

if __name__ == "__main__":
    main()
