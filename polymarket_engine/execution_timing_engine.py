import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
LIFE = Path("analytics/opportunity_lifecycle.json")
CONF = Path("analytics/signal_confidence.json")
OUT = Path("analytics/execution_timing.json")

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

def decide(radar_score, confidence, freshness, momentum, vacuum, action):
    freshness = (freshness or "").lower()
    momentum = (momentum or "").lower()
    action = (action or "").upper()

    if action in {"AVOID"}:
        return "AVOID"

    if radar_score >= 0.35 and confidence >= 0.80 and freshness in {"fresh", "emerging"} and momentum in {"rising", "accelerating"}:
        return "ENTER_NOW"

    if radar_score >= 0.25 and confidence >= 0.75 and vacuum >= 0.60 and action in {"ENTRY", "ADD"}:
        return "SCALE_IN"

    if freshness == "stale" and momentum in {"flat", "fading"}:
        return "WAIT_LIQUIDITY"

    if radar_score < 0.18 or confidence < 0.55:
        return "AVOID"

    return "MONITOR"

def urgency(decision, radar_score):
    base = {
        "ENTER_NOW": 0.95,
        "SCALE_IN": 0.75,
        "WAIT_LIQUIDITY": 0.40,
        "MONITOR": 0.25,
        "AVOID": 0.05,
    }.get(decision, 0.10)
    return round(min(1.0, max(0.0, base * (0.75 + radar_score))), 4)

def main():
    radar = load_json(RADAR)
    life = map_markets(load_json(LIFE))
    conf = map_markets(load_json(CONF))

    rows = []
    all_markets = list(radar.get("deploy_now", [])) + list(radar.get("watchlist", []))

    for r in all_markets:
        name = r.get("market_name")
        l = life.get(name, {})
        c = conf.get(name, {})

        radar_score = float(r.get("adaptive_radar_score", 0.0) or 0.0)
        confidence = float(c.get("confidence_score", 0.0) or 0.0)
        freshness = r.get("freshness", "unknown")
        momentum = r.get("momentum_state", "flat")
        vacuum = float(r.get("vacuum_v2_score", 0.0) or 0.0)
        action = l.get("recommended_action", "MONITOR")

        decision = decide(radar_score, confidence, freshness, momentum, vacuum, action)

        rows.append({
            "market_name": name,
            "adaptive_radar_score": round(radar_score, 6),
            "confidence_score": round(confidence, 4),
            "freshness": freshness,
            "momentum_state": momentum,
            "vacuum_v2_score": round(vacuum, 4),
            "lifecycle_action": action,
            "execution_decision": decision,
            "execution_urgency": urgency(decision, radar_score),
        })

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": rows
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("EXECUTION TIMING ENGINE BUILT")
    print("markets:", len(rows))
    print("file: analytics/execution_timing.json")

if __name__ == "__main__":
    main()
