import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/momentum_break_signals.json")

MIN_ROWS = 2
DELTA_THRESHOLD = 0.03
SCORE_THRESHOLD = 0.08

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    snap = load_json(SNAP)
    rows = snap.get("rows", [])

    by_market = defaultdict(list)
    for r in rows:
        name = r.get("market_name")
        if name:
            by_market[name].append(r)

    signals = []

    for name, items in by_market.items():
        items = sorted(items, key=lambda x: x.get("timestamp", ""))
        if len(items) < MIN_ROWS:
            continue

        prev = items[-2]
        curr = items[-1]

        prev_radar = float(prev.get("radar_score", 0.0) or 0.0)
        curr_radar = float(curr.get("radar_score", 0.0) or 0.0)

        prev_opp = float(prev.get("opportunity_score", 0.0) or 0.0)
        curr_opp = float(curr.get("opportunity_score", 0.0) or 0.0)

        prev_urg = float(prev.get("execution_urgency", 0.0) or 0.0)
        curr_urg = float(curr.get("execution_urgency", 0.0) or 0.0)

        radar_delta = curr_radar - prev_radar
        opp_delta = curr_opp - prev_opp
        urg_delta = curr_urg - prev_urg

        break_score = (
            0.45 * max(radar_delta, 0.0) +
            0.35 * max(opp_delta, 0.0) +
            0.20 * max(urg_delta, 0.0)
        )

        state = "flat"
        if break_score >= SCORE_THRESHOLD and radar_delta >= DELTA_THRESHOLD:
            state = "breakout"
        elif break_score >= SCORE_THRESHOLD:
            state = "acceleration"

        if state != "flat":
            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": name,
                "momentum_break_score": round(break_score, 6),
                "state": state,
                "radar_delta": round(radar_delta, 6),
                "opportunity_delta": round(opp_delta, 6),
                "urgency_delta": round(urg_delta, 6),
                "current_radar_score": round(curr_radar, 6),
                "current_opportunity_score": round(curr_opp, 6),
                "current_execution_urgency": round(curr_urg, 6),
            })

    signals.sort(key=lambda x: x["momentum_break_score"], reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals,
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("MOMENTUM BREAK ENGINE BUILT")
    print("signals:", len(signals))
    print("file:", OUT)

if __name__ == "__main__":
    main()
