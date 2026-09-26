import json
from pathlib import Path
from datetime import datetime, timezone

FEED = Path("analytics/intelligence_feed.json")
PRIVATE_OUT = Path("analytics/intelligence_feed_private.txt")
PUBLIC_OUT = Path("analytics/intelligence_feed_public.txt")

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

    env_ = feed.get("market_environment", "unknown")
    ranking = feed.get("ranking_mode", "unknown")
    top_n = int(feed.get("top_opportunities_count", 0) or 0)
    emerging = int(feed.get("emerging_count", 0) or 0)
    decaying = int(feed.get("decaying_count", 0) or 0)

    private_lines = [
        "🚨 SIGNALATLAS PRO INTELLIGENCE",
        "",
        f"Environment: {env_}",
        f"Ranking Mode: {ranking}",
        f"Top Opportunities: {top_n}",
        f"Emerging: {emerging}",
        f"Decaying: {decaying}",
        f"Avg EV: {fmt(feed.get('avg_expected_value'), 4)}",
        f"Avg Execution Urgency: {fmt(feed.get('avg_execution_urgency'), 4)}",
        "",
        "BEST MARKET",
        f"Market: {best.get('market_name', 'N/A')}",
        f"Radar: {fmt(best.get('radar_score'), 6)}",
        f"Confidence: {fmt(best.get('confidence_score'), 4)}",
        f"EV: {fmt(best.get('expected_value'), 6)}",
        f"Urgency: {fmt(best.get('execution_urgency'), 4)}",
        f"Freshness: {best.get('freshness', 'unknown')}",
        f"Momentum: {best.get('momentum', 'unknown')}",
        f"Opportunity Score: {fmt(best.get('opportunity_score'), 6)}",
        f"Tier: {best.get('opportunity_tier', 'D')}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
    ]

    public_lines = [
        "📡 SIGNALATLAS MARKET RADAR",
        "",
        f"Environment: {env_}",
        f"Emerging Signals: {emerging}",
        f"Decaying Signals: {decaying}",
        "",
        "Top market on radar:",
        f"{best.get('market_name', 'N/A')}",
        "",
        "Upgrade for full EV, urgency, confidence, and execution view.",
    ]

    PRIVATE_OUT.write_text("\n".join(private_lines), encoding="utf-8")
    PUBLIC_OUT.write_text("\n".join(public_lines), encoding="utf-8")

    print("PREMIUM FEED FORMATTER BUILT")
    print("private:", PRIVATE_OUT)
    print("public:", PUBLIC_OUT)

if __name__ == "__main__":
    main()
