import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
SCORES = Path("analytics/opportunity_scores.json")
EV = Path("analytics/expected_value.json")
TIMING = Path("analytics/execution_timing.json")

OUT = Path("analytics/performance_metrics.json")

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

def main():

    radar = load_json(RADAR)
    scores = map_markets(load_json(SCORES))
    evmap = map_markets(load_json(EV))
    timing = map_markets(load_json(TIMING))

    markets = list(radar.get("deploy_now", [])) + list(radar.get("watchlist", []))

    total = len(markets)

    tier_counts = {"A":0,"B":0,"C":0,"D":0}
    ev_values = []
    urgency_values = []

    for r in markets:

        name = r.get("market_name")

        s = scores.get(name,{})
        tier = s.get("opportunity_tier","D")

        if tier in tier_counts:
            tier_counts[tier] += 1

        e = evmap.get(name,{})
        ev = float(e.get("expected_value",0) or 0)
        ev_values.append(ev)

        t = timing.get(name,{})
        urgency = float(t.get("execution_urgency",0) or 0)
        urgency_values.append(urgency)

    avg_ev = sum(ev_values)/len(ev_values) if ev_values else 0
    avg_urgency = sum(urgency_values)/len(urgency_values) if urgency_values else 0

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals_detected": total,
        "tier_distribution": tier_counts,
        "avg_expected_value": round(avg_ev,6),
        "avg_execution_urgency": round(avg_urgency,6)
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("PERFORMANCE ENGINE BUILT")
    print("signals:", total)
    print("file: analytics/performance_metrics.json")

if __name__ == "__main__":
    main()
