import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
CONF = Path("analytics/signal_confidence.json")
EV = Path("analytics/expected_value.json")
VAC = Path("analytics/liquidity_vacuum.json")
TIMING = Path("analytics/execution_timing.json")
MICRO = Path("analytics/microstructure_signals.json")
LIFE = Path("analytics/opportunity_lifecycle.json")

OUT = Path("analytics/opportunity_scores.json")

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

def compute_score(radar, confidence, momentum, urgency, ev, freshness, micro_bonus=0.0):
    score = 0.0

    score += radar * 0.35
    score += confidence * 0.20
    score += urgency * 0.15
    score += min(ev * 2.0, 1.0) * 0.20
    score += min(micro_bonus, 1.0) * 0.10

    if momentum == "rising":
        score += 0.10

    if freshness == "stale":
        score -= 0.08

    return max(0.0, min(score, 1.0))

def tier(score):
    if score >= 0.65:
        return "A"
    if score >= 0.50:
        return "B"
    if score >= 0.35:
        return "C"
    return "D"

def main():

    radar = load_json(RADAR)
    conf = map_markets(load_json(CONF))
    evmap = map_markets(load_json(EV))
    timing = map_markets(load_json(TIMING))
    micromap = map_markets(load_json(MICRO), key="signals")
    life = map_markets(load_json(LIFE))

    rows = []

    all_markets = list(radar.get("deploy_now", [])) + list(radar.get("watchlist", []))

    for r in all_markets:

        name = r.get("market_name")

        radar_score = float(r.get("adaptive_radar_score", 0.0) or 0.0)
        freshness = r.get("freshness", "unknown")
        momentum = r.get("momentum_state", "flat")

        c = conf.get(name, {})
        confidence = float(c.get("confidence_score", 0.0) or 0.0)

        e = evmap.get(name, {})
        ev = float(e.get("expected_value", 0.0) or 0.0)

        t = timing.get(name, {})
        urgency = float(t.get("execution_urgency", 0.0) or 0.0)

        ms = micromap.get(name, {})
        micro_bonus = float(ms.get("microstructure_score", 0.0) or 0.0)

        score = compute_score(
            radar_score,
            confidence,
            momentum,
            urgency,
            ev,
            freshness,
            micro_bonus
        )

        rows.append({
            "market_name": name,
            "radar_score": round(radar_score,6),
            "confidence_score": round(confidence,4),
            "expected_value": round(ev,6),
            "execution_urgency": round(urgency,4),
            "microstructure_bonus": round(micro_bonus,6),
            "freshness": freshness,
            "momentum": momentum,
            "opportunity_score": round(score,6),
            "opportunity_tier": tier(score)
        })

    rows.sort(key=lambda x: x["opportunity_score"], reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": rows
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("OPPORTUNITY SCORE ENGINE BUILT")
    print("markets:", len(rows))
    print("file: analytics/opportunity_scores.json")

if __name__ == "__main__":
    main()
