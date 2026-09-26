import json
from pathlib import Path
from datetime import datetime, timezone

ALPHA = Path("analytics/alpha_fusion_signals.json")
OUT = Path("analytics/alpha_alerts.json")

ALERT_THRESHOLD = 0.25

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    alpha = load_json(ALPHA)
    signals = alpha.get("signals", [])

    alerts = []

    for s in signals:
        score = float(s.get("alpha_score",0))

        if score >= ALERT_THRESHOLD:
            alerts.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_name": s.get("market_name"),
                "alpha_score": score,
                "mispricing_edge": s.get("mispricing_edge"),
                "collapse_score": s.get("collapse_score"),
                "confidence_score": s.get("confidence_score"),
                "execution_urgency": s.get("execution_urgency")
            })

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(alerts),
        "alerts": alerts
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("ALPHA ALERT ENGINE BUILT")
    print("alerts:", len(alerts))
    print("file:", OUT)

if __name__ == "__main__":
    main()
