import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/liquidity_vacuum_proxy.json")

MIN_ROWS = 2
VACUUM_THRESHOLD = 0.08

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

        prev_urg = float(prev.get("execution_urgency", 0.0) or 0.0)
        curr_urg = float(curr.get("execution_urgency", 0.0) or 0.0)

        prev_ev = float(prev.get("expected_value", 0.0) or 0.0)
        curr_ev = float(curr.get("expected_value", 0.0) or 0.0)

        prev_radar = float(prev.get("radar_score", 0.0) or 0.0)
        curr_radar = float(curr.get("radar_score", 0.0) or 0.0)

        urg_jump = curr_urg - prev_urg
        ev_jump = curr_ev - prev_ev
        radar_jump = curr_radar - prev_radar

        vacuum_score = (
            0.45 * max(urg_jump, 0.0) +
            0.35 * max(ev_jump, 0.0) +
            0.20 * max(abs(radar_jump), 0.0)
        )

        if vacuum_score >= VACUUM_THRESHOLD:
            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": name,
                "vacuum_score": round(vacuum_score, 6),
                "urgency_jump": round(urg_jump, 6),
                "ev_jump": round(ev_jump, 6),
                "radar_jump": round(radar_jump, 6),
                "state": "vacuum_proxy"
            })

    signals.sort(key=lambda x: x["vacuum_score"], reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("LIQUIDITY VACUUM PROXY ENGINE BUILT")
    print("signals:", len(signals))
    print("file:", OUT)

if __name__ == "__main__":
    main()
