import json
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/market_regime_live.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    rows = load_json(SNAP).get("rows", [])

    if not rows:
        out = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": "unknown",
            "metrics": {}
        }
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("MARKET REGIME ENGINE BUILT")
        print("regime: unknown")
        print("file:", OUT)
        return

    recent = rows[-30:]

    radar_vals = [float(r.get("radar_score", 0.0) or 0.0) for r in recent]
    urg_vals = [float(r.get("execution_urgency", 0.0) or 0.0) for r in recent]
    ev_vals = [float(r.get("expected_value", 0.0) or 0.0) for r in recent]

    avg_radar = mean(radar_vals) if radar_vals else 0.0
    avg_urg = mean(urg_vals) if urg_vals else 0.0
    avg_ev = mean(ev_vals) if ev_vals else 0.0

    radar_range = (max(radar_vals) - min(radar_vals)) if len(radar_vals) >= 2 else 0.0

    regime = "calm"

    if avg_urg >= 0.55 and radar_range >= 0.08:
        regime = "volatile"
    elif avg_urg >= 0.45 and avg_ev >= 0.06:
        regime = "trending"
    elif avg_radar <= 0.18 and avg_ev <= 0.03:
        regime = "illiquid"
    else:
        regime = "calm"

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "metrics": {
            "avg_radar_score": round(avg_radar, 6),
            "avg_execution_urgency": round(avg_urg, 6),
            "avg_expected_value": round(avg_ev, 6),
            "radar_range": round(radar_range, 6)
        }
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("MARKET REGIME ENGINE BUILT")
    print("regime:", regime)
    print("file:", OUT)

if __name__ == "__main__":
    main()
