import json
from pathlib import Path
from datetime import datetime, timezone

SCORES = Path("analytics/opportunity_scores.json")
OUT = Path("analytics/top_opportunities.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():

    doc = load_json(SCORES)
    markets = doc.get("markets", [])

    top_now = []
    emerging = []
    decaying = []

    for m in markets:

        score = float(m.get("opportunity_score",0))
        freshness = m.get("freshness","")
        momentum = m.get("momentum","")

        if score >= 0.60:
            top_now.append(m)

        elif score >= 0.45 and momentum == "rising":
            emerging.append(m)

        elif freshness == "stale" and score < 0.40:
            decaying.append(m)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "top_opportunities_now": top_now[:10],
        "emerging_opportunities": emerging[:10],
        "decaying_opportunities": decaying[:10]
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("TOP OPPORTUNITIES ENGINE BUILT")
    print("top_now:", len(top_now))
    print("emerging:", len(emerging))
    print("decaying:", len(decaying))
    print("file: analytics/top_opportunities.json")

if __name__ == "__main__":
    main()
