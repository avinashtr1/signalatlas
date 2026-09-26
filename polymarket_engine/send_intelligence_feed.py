import json
from pathlib import Path

from polymarket_engine.utils.channel_sender import send

FEED = Path("analytics/intelligence_feed.json")

def load_feed():
    if not FEED.exists():
        return {}
    return json.loads(FEED.read_text(encoding="utf-8"))

def build_text(feed):

    best = feed.get("best_market") or {}

    lines = [
        "🚨 SIGNALATLAS INTELLIGENCE FEED",
        "",
        f"Environment: {feed.get('market_environment','unknown')}",
        f"Top Opportunities: {feed.get('top_opportunities_count',0)}",
        f"Emerging: {feed.get('emerging_count',0)}",
        f"Decaying: {feed.get('decaying_count',0)}",
        f"Avg EV: {float(feed.get('avg_expected_value',0) or 0):.4f}",
        f"Avg Execution Urgency: {float(feed.get('avg_execution_urgency',0) or 0):.4f}",
        "",
        "BEST MARKET",
        f"Market: {best.get('market_name','N/A')}",
        f"Radar: {float(best.get('radar_score',0) or 0):.6f}",
        f"Confidence: {float(best.get('confidence_score',0) or 0):.4f}",
        f"EV: {float(best.get('expected_value',0) or 0):.6f}",
        f"Urgency: {float(best.get('execution_urgency',0) or 0):.4f}",
        f"Freshness: {best.get('freshness','unknown')}",
        f"Momentum: {best.get('momentum','unknown')}",
        f"Opportunity Score: {float(best.get('opportunity_score',0) or 0):.6f}",
        f"Tier: {best.get('opportunity_tier','D')}",
    ]

    return "\n".join(lines)


def main():

    feed = load_feed()
    text = build_text(feed)

    print(text)

    send("alpha_feed", text)

    print("\nINTELLIGENCE FEED SENT TO TELEGRAM CHANNEL")


if __name__ == "__main__":
    main()
