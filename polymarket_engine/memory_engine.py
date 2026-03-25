import json
from pathlib import Path
from datetime import datetime, timezone

ALPHA = Path("analytics/alpha_fusion_signals.json")
MIS = Path("analytics/mispricing_signals.json")
COL = Path("analytics/liquidity_collapse_signals.json")
MOM = Path("analytics/momentum_break_signals.json")
REGIME = Path("analytics/market_regime.json")

OUT = Path("analytics/signal_memory.json")
MAX_ROWS = 2000

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def map_markets(doc, key="signals", name_key="market_name"):
    out = {}
    for r in doc.get(key, []):
        name = r.get(name_key)
        if name:
            out[name] = r
    return out

def main():
    alpha = load_json(ALPHA)
    mis = map_markets(load_json(MIS), key="signals", name_key="market")
    col = map_markets(load_json(COL), key="signals", name_key="market")
    mom = map_markets(load_json(MOM), key="signals", name_key="market_name")
    regime = load_json(REGIME)

    rows = load_json(OUT).get("rows", [])
    now = datetime.now(timezone.utc).isoformat()
    env_ = regime.get("regime", "unknown")

    for s in alpha.get("signals", []):
        name = s.get("market_name")
        rows.append({
            "timestamp": now,
            "market_name": name,
            "market_environment": env_,
            "alpha_score": float(s.get("alpha_score", 0.0) or 0.0),
            "alpha_tier": s.get("alpha_tier", "D"),
            "mispricing_edge": float(s.get("mispricing_edge", 0.0) or 0.0),
            "collapse_score": float(s.get("collapse_score", 0.0) or 0.0),
            "microstructure_score": float(s.get("microstructure_score", 0.0) or 0.0),
            "radar_score": float(s.get("radar_score", 0.0) or 0.0),
            "expected_value": float(s.get("expected_value", 0.0) or 0.0),
            "confidence_score": float(s.get("confidence_score", 0.0) or 0.0),
            "execution_urgency": float(s.get("execution_urgency", 0.0) or 0.0),
            "opportunity_score": float(s.get("opportunity_score", 0.0) or 0.0),
            "freshness": s.get("freshness", "unknown"),
            "momentum": s.get("momentum", "unknown"),
            "mispricing_flag": name in mis,
            "collapse_flag": name in col,
            "momentum_break_flag": name in mom,
            "resolved": False,
            "outcome_pnl": None,
            "future_market_probability": None
        })

    rows = rows[-MAX_ROWS:]

    out = {
        "timestamp": now,
        "count": len(rows),
        "rows": rows
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("MEMORY ENGINE BUILT")
    print("file:", OUT)
    print("count:", len(rows))

if __name__ == "__main__":
    main()
