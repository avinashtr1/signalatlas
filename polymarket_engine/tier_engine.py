import json
from pathlib import Path
from datetime import datetime, timezone

SRC = Path("analytics/opportunity_ranking.json")
OUT = Path("analytics/tiers.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def get_tier(score: float) -> str:
    if score >= 0.30:
        return "A"
    if score >= 0.24:
        return "B"
    if score >= 0.18:
        return "C"
    return "D"

def get_quality(score: float) -> str:
    if score >= 0.30:
        return "institutional"
    if score >= 0.24:
        return "strong"
    if score >= 0.18:
        return "tradable"
    return "weak"

def main():
    data = load_json(SRC)
    rows = data.get("top_opportunities", [])

    tiers = []
    for r in rows:
        score = float(r.get("opportunity_score", 0.0) or 0.0)
        tiers.append({
            "market_name": r.get("market_name"),
            "opportunity_score": round(score, 6),
            "tier": get_tier(score),
            "quality": get_quality(score)
        })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(tiers),
        "tiers": tiers
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("TIER ENGINE BUILT")
    print("file:", OUT)
    print("count:", len(tiers))

if __name__ == "__main__":
    main()
