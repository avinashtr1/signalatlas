import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD = Path("analytics/alpha_leaderboard.json")
OUT = Path("analytics/signal_interactions.json")

def load_rows():
    if not LEADERBOARD.exists():
        return []
    data = json.loads(LEADERBOARD.read_text(encoding="utf-8"))
    return data.get("leaderboard", [])

def interaction_bonus(r):
    vacuum = float(r.get("vacuum_score", 0) or 0)
    micro = float(r.get("microstructure_score", 0) or 0)
    stale = float(r.get("stale_repricing_score", 0) or 0)
    resarb = float(r.get("resolution_arb_v2_score", 0) or 0)
    collapse = float(r.get("collapse_v2_score", 0) or 0)
    shock = float(r.get("shock_score", 0) or 0)

    bonus = 0.0
    tags = []

    if vacuum >= 0.15 and stale >= 0.60:
        bonus += 0.15
        tags.append("vacuum+stale")

    if vacuum >= 0.15 and micro >= 0.04:
        bonus += 0.10
        tags.append("vacuum+micro")

    if micro >= 0.04 and shock >= 0.10:
        bonus += 0.12
        tags.append("micro+shock")

    if collapse >= 0.20 and resarb >= 0.20:
        bonus += 0.18
        tags.append("collapse+arb")

    if stale >= 0.60 and resarb >= 0.20:
        bonus += 0.10
        tags.append("stale+arb")

    return round(min(bonus, 0.35), 4), tags

def main():
    rows = load_rows()
    out = []

    for r in rows:
        bonus, tags = interaction_bonus(r)
        out.append({
            "market_name": r.get("market_name"),
            "interaction_bonus": bonus,
            "interaction_tags": tags,
        })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": out
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("SIGNAL INTERACTIONS BUILT")
    print(f"rows: {len(out)}")
    print("file: analytics/signal_interactions.json")

if __name__ == "__main__":
    main()
