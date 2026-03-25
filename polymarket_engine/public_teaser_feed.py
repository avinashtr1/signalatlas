import json
from pathlib import Path
from datetime import datetime, timezone

ALPHA_FEED_PATH = Path("analytics/alpha_feed.json")
OUT_JSON = Path("analytics/public_teaser_feed.json")
OUT_TXT = Path("analytics/public_teaser_feed.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    feed = load_json(ALPHA_FEED_PATH)

    deploy = feed.get("deploy_now", [])[:2]
    quality = feed.get("top_quality", [])[:2]

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deploy_now": deploy,
        "top_quality": quality,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS MARKET INTELLIGENCE")
    lines.append("")

    if deploy:
        lines.append("WATCHLIST")
        for i, r in enumerate(deploy, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"side={r.get('side')} | "
                f"edge={float(r.get('total_edge', 0))*100:.2f}%"
            )
        lines.append("")

    if quality:
        lines.append("HIGH-CONVICTION NAMES")
        for i, r in enumerate(quality, start=1):
            lines.append(
                f"{i}. {r.get('market_name')} | "
                f"grade={r.get('grade')}"
            )
        lines.append("")

    lines.append("More detailed live signals available in premium feed.")

    text = "\n".join(lines).strip()
    OUT_TXT.write_text(text, encoding="utf-8")

    print(text)
    print("")
    print("files created:")
    print("analytics/public_teaser_feed.json")
    print("analytics/public_teaser_feed.txt")

if __name__ == "__main__":
    main()
