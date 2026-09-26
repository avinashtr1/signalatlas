import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
OUT = Path("analytics/liquidity_vacuum.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    radar = load_json(RADAR)
    markets = radar.get("markets", [])

    vacuums = []

    for m in markets:
        score = float(m.get("adaptive_radar_score", 0))
        freshness = m.get("freshness", "")
        momentum = m.get("momentum_state", "")

        # simple vacuum signal rule
        vacuum_score = 0.0

        if momentum == "up" and freshness == "stale":
            vacuum_score += 0.6

        if score > 0.3:
            vacuum_score += 0.3

        if vacuum_score >= 0.5:
            vacuums.append({
                "market_name": m.get("market_name"),
                "vacuum_score": round(vacuum_score,4),
                "radar_score": score,
                "momentum": momentum,
                "freshness": freshness
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vacuum_signals": vacuums,
        "count": len(vacuums)
    }

    OUT.write_text(json.dumps(out, indent=2))
    print("LIQUIDITY VACUUM ENGINE BUILT")
    print("signals:", len(vacuums))

if __name__ == "__main__":
    main()
