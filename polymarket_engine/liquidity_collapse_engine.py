import json
from pathlib import Path
from datetime import datetime, timezone

SNAP = Path("analytics/market_snapshots.json")
OUT = Path("analytics/liquidity_collapse_signals.json")

THRESHOLD = 0.15

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():

    snap = load_json(SNAP)
    rows = snap.get("rows", [])

    signals = []

    for r in rows[-20:]:

        urgency = float(r.get("execution_urgency",0))
        ev = float(r.get("expected_value",0))
        radar = float(r.get("radar_score",0))

        collapse_score = urgency + ev - radar

        if collapse_score > THRESHOLD:

            signals.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market": r.get("market_name"),
                "collapse_score": round(collapse_score,4),
                "execution_urgency": urgency,
                "expected_value": ev
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("LIQUIDITY COLLAPSE ENGINE BUILT")
    print("signals:",len(signals))
    print("file:",OUT)

if __name__ == "__main__":
    main()
