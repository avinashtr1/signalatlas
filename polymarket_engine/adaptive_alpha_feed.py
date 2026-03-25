import json
from pathlib import Path
from datetime import datetime, timezone

COMPOSITE_PATH = Path("analytics/adaptive_composite_score.json")

OUT_TXT = Path("analytics/adaptive_alpha_feed.txt")
OUT_JSON = Path("analytics/adaptive_alpha_feed.json")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def main():

    data = load_json(COMPOSITE_PATH)
    rows = data.get("ranked_markets", [])

    rows.sort(
        key=lambda r: (
            r.get("adaptive_composite_score",0),
            r.get("edge",0)
        ),
        reverse=True
    )

    top = rows[:10]

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(top),
        "markets": top
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS ADAPTIVE ALPHA FEED")
    lines.append("")
    lines.append("TOP ADAPTIVE SIGNALS")
    lines.append("")

    for i,r in enumerate(top,start=1):

        edge = r.get("edge",0)*100
        score = r.get("adaptive_composite_score",0)

        lines.append(
            f"{i}. {r['market_name']} | "
            f"score={score:.3f} | "
            f"edge={edge:.2f}% | "
            f"side={r.get('side')}"
        )

    OUT_TXT.write_text("\n".join(lines),encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/adaptive_alpha_feed.json")
    print("analytics/adaptive_alpha_feed.txt")

if __name__ == "__main__":
    main()
