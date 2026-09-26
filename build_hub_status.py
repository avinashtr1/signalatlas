import json
from pathlib import Path
from datetime import datetime, timezone

def read_json(path):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except:
        return {}

perf = read_json("analytics/performance_metrics.json")
truth = read_json("analytics/execution_truth.json")
timing = read_json("analytics/execution_timing.json")

out = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "signals_detected": perf.get("signals_detected"),
    "avg_execution_urgency": perf.get("avg_execution_urgency"),
    "closed_positions": (truth.get("summary") or {}).get("total_trades"),
    "realized_pnl": (truth.get("summary") or {}).get("total_realized_pnl"),
    "timing_markets": len((timing.get("markets") or [])),
}

Path("analytics/hub_status.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
Path("signalatlas_dashboard/hub_status.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("hub_status refreshed:", out["generated_at"])
