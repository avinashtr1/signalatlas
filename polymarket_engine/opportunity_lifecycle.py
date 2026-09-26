import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
STATE = Path("analytics/signal_state_change.json")
MOM = Path("analytics/signal_momentum.json")
CONF = Path("analytics/signal_confidence.json")
OUT = Path("analytics/opportunity_lifecycle.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def map_markets(doc, key="markets"):
    out = {}
    for r in doc.get(key, []):
        name = r.get("market_name")
        if name:
            out[name] = r
    return out

def classify(score, freshness, momentum, conf):
    freshness = (freshness or "").lower()
    momentum = (momentum or "").lower()

    if score >= 0.45 and freshness in {"fresh", "emerging"} and momentum in {"rising", "accelerating"}:
        return "born"
    if score >= 0.35 and momentum in {"rising", "accelerating"}:
        return "strengthening"
    if score >= 0.25 and conf >= 0.75:
        return "mature"
    if momentum in {"fading", "breaking_down"}:
        return "fading"
    return "watch"

def action_for(stage):
    return {
        "born": "ENTRY",
        "strengthening": "ADD",
        "mature": "HOLD",
        "fading": "REDUCE",
        "watch": "MONITOR",
        "dead": "AVOID",
    }.get(stage, "MONITOR")

def main():
    radar = load_json(RADAR)
    state = map_markets(load_json(STATE))
    mom = map_markets(load_json(MOM))
    conf = map_markets(load_json(CONF))

    rows = []
    for bucket in ("deploy_now", "watchlist"):
        for r in radar.get(bucket, []):
            name = r.get("market_name")
            s = state.get(name, {})
            m = mom.get(name, {})
            c = conf.get(name, {})

            score = float(r.get("adaptive_radar_score", 0.0) or 0.0)
            freshness = s.get("freshness", "unknown")
            momentum = m.get("momentum_state", "flat")
            confidence = float(c.get("confidence_score", 0.0) or 0.0)

            stage = classify(score, freshness, momentum, confidence)

            rows.append({
                "market_name": name,
                "adaptive_radar_score": round(score, 6),
                "freshness": freshness,
                "momentum_state": momentum,
                "confidence_score": round(confidence, 4),
                "lifecycle_stage": stage,
                "recommended_action": action_for(stage),
            })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": rows
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("OPPORTUNITY LIFECYCLE BUILT")
    print("markets:", len(rows))
    print("file: analytics/opportunity_lifecycle.json")

if __name__ == "__main__":
    main()
