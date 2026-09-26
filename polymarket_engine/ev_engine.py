import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
CONF = Path("analytics/signal_confidence.json")
LIFE = Path("analytics/opportunity_lifecycle.json")
OUT = Path("analytics/expected_value.json")

ACTION_MULT = {
    "ENTRY": 1.00,
    "ADD": 0.90,
    "HOLD": 0.65,
    "REDUCE": 0.35,
    "MONITOR": 0.20,
    "AVOID": 0.00,
}

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
    conf = map_markets(load_json(CONF))
    life = map_markets(load_json(LIFE))

    rows = []
    all_markets = list(radar.get("deploy_now", [])) + list(radar.get("watchlist", []))

    for r in all_markets:
        name = r.get("market_name")
        edge_pct = float(r.get("expected_net_edge_pct", 0.0) or 0.0)
        radar_score = float(r.get("adaptive_radar_score", 0.0) or 0.0)
        fill_prob = float(r.get("expected_fill_probability", 0.90) or 0.90)

        c = conf.get(name, {})
        l = life.get(name, {})

        confidence = float(c.get("confidence_score", 0.0) or 0.0)
        action = l.get("recommended_action", "MONITOR")
        action_mult = ACTION_MULT.get(action, 0.20)

        expected_value = (edge_pct / 100.0) * fill_prob * max(confidence, 0.01) * action_mult
        risk_adjusted_score = radar_score * max(confidence, 0.01) * action_mult
        expected_sharpe = (expected_value / max(1.0 - confidence + 0.05, 0.05))

        rows.append({
            "market_name": name,
            "adaptive_radar_score": round(radar_score, 6),
            "confidence_score": round(confidence, 4),
            "expected_fill_probability": round(fill_prob, 4),
            "recommended_action": action,
            "expected_net_edge_pct": round(edge_pct, 4),
            "expected_value": round(expected_value, 6),
            "expected_sharpe": round(expected_sharpe, 6),
            "risk_adjusted_score": round(risk_adjusted_score, 6),
        })

    rows.sort(key=lambda x: (x["risk_adjusted_score"], x["expected_value"]), reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "markets": rows
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("EXPECTED VALUE ENGINE BUILT")
    print("markets:", len(rows))
    print("file: analytics/expected_value.json")

if __name__ == "__main__":
    main()
