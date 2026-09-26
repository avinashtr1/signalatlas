import json
from pathlib import Path
from datetime import datetime, timezone

RANK = Path("analytics/opportunity_ranking.json")
STATE = Path("analytics/pro_alert_state.json")
OUT = Path("analytics/edge_decay.json")

DECAY_THRESHOLD = 0.08

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    rank = load_json(RANK)
    state = load_json(STATE).get("markets", {})

    decays = []

    for r in rank.get("top_opportunities", []):
        name = r.get("market_name")
        prev = state.get(name)
        if not prev:
            continue

        current = float(r.get("opportunity_score", 0.0) or 0.0)
        previous = float(prev.get("opportunity_score", 0.0) or 0.0)
        delta = current - previous

        if delta <= -DECAY_THRESHOLD:
            decays.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": name,
                "previous_opportunity_score": round(previous, 6),
                "current_opportunity_score": round(current, 6),
                "decay": round(delta, 6),
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(decays),
        "decays": decays,
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("EDGE DECAY ENGINE BUILT")
    print("count:", len(decays))
    print("file:", OUT)

if __name__ == "__main__":
    main()
