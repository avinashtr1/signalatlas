import json
from pathlib import Path
from datetime import datetime, timezone

MIS = Path("analytics/mispricing_signals.json")
COL = Path("analytics/liquidity_collapse_signals.json")
MIC = Path("analytics/microstructure_signals.json")
OPP = Path("analytics/opportunity_scores.json")
OUT = Path("analytics/alpha_fusion_signals.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def map_markets(doc, key="markets", name_key="market_name"):
    out = {}
    for r in doc.get(key, []):
        name = r.get(name_key)
        if name:
            out[name] = r
    return out

def alpha_tier(score):
    if score >= 0.75:
        return "A"
    if score >= 0.55:
        return "B"
    if score >= 0.35:
        return "C"
    return "D"

def main():
    mis = map_markets(load_json(MIS), key="signals", name_key="market")
    col = map_markets(load_json(COL), key="signals", name_key="market")
    mic = map_markets(load_json(MIC), key="signals", name_key="market_name")
    opp = map_markets(load_json(OPP), key="markets", name_key="market_name")

    signals = []

    for name, o in opp.items():
        edge = abs(float((mis.get(name) or {}).get("edge", 0.0) or 0.0))
        collapse = float((col.get(name) or {}).get("collapse_score", 0.0) or 0.0)
        micro = float((mic.get(name) or {}).get("microstructure_score", 0.0) or 0.0)

        radar = float(o.get("radar_score", 0.0) or 0.0)
        ev = float(o.get("expected_value", 0.0) or 0.0)
        conf = float(o.get("confidence_score", 0.0) or 0.0)
        urg = float(o.get("execution_urgency", 0.0) or 0.0)
        opp_score = float(o.get("opportunity_score", 0.0) or 0.0)

        alpha_score = (
            0.28 * min(edge, 1.0) +
            0.16 * min(collapse, 1.0) +
            0.12 * min(micro, 1.0) +
            0.16 * min(radar, 1.0) +
            0.12 * min(ev * 2.0, 1.0) +
            0.08 * min(conf, 1.0) +
            0.08 * min(urg, 1.0)
        )

        signals.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_name": name,
            "alpha_score": round(alpha_score, 6),
            "alpha_tier": alpha_tier(alpha_score),
            "mispricing_edge": round(edge, 6),
            "collapse_score": round(collapse, 6),
            "microstructure_score": round(micro, 6),
            "radar_score": round(radar, 6),
            "expected_value": round(ev, 6),
            "confidence_score": round(conf, 6),
            "execution_urgency": round(urg, 6),
            "opportunity_score": round(opp_score, 6),
            "freshness": o.get("freshness", "unknown"),
            "momentum": o.get("momentum", "unknown"),
        })

    signals.sort(key=lambda x: x["alpha_score"], reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(signals),
        "signals": signals
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("ALPHA FUSION ENGINE BUILT")
    print("signals:", len(signals))
    print("file:", OUT)

if __name__ == "__main__":
    main()
