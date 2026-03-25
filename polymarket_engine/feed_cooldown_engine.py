import json
from pathlib import Path
from datetime import datetime, timezone

CUR = Path("analytics/opportunity_ranking.json")
STATE = Path("analytics/feed_state.json")
DECISION = Path("analytics/feed_send_decision.json")

MIN_CHANGE = 0.02

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p, data):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def main():
    cur = load_json(CUR).get("top_opportunities", [])
    prev = load_json(STATE).get("markets", {})

    changed = False
    new_state = {}

    for r in cur:
        name = r.get("market_name")
        score = float(r.get("opportunity_score", 0.0) or 0.0)
        prev_score = prev.get(name)

        new_state[name] = score

        if prev_score is None:
            changed = True
        elif abs(score - prev_score) >= MIN_CHANGE:
            changed = True

    now = datetime.now(timezone.utc).isoformat()

    save_json(STATE, {
        "timestamp": now,
        "markets": new_state
    })

    save_json(DECISION, {
        "timestamp": now,
        "send_pro_feed_v2": changed
    })

    if changed:
        print("FEED CHANGE DETECTED")
    else:
        print("NO MATERIAL FEED CHANGE")

if __name__ == "__main__":
    main()
