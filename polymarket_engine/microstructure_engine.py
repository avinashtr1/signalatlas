import json
from pathlib import Path
from datetime import datetime, timezone

RADAR = Path("analytics/radar_live.json")
OUT = Path("analytics/microstructure_signals.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    radar = load_json(RADAR)
    markets = radar.get("markets", []) or []

    signals = []

    for m in markets:
        name = m.get("market_name")
        radar_score = float(m.get("adaptive_radar_score", 0.0) or 0.0)
        freshness = (m.get("freshness") or "").lower()
        momentum = (m.get("momentum_state") or "").lower()

        stale_repricing = float(m.get("stale_repricing_score", 0.0) or 0.0)
        vacuum_v2 = float(m.get("vacuum_v2_score", 0.0) or 0.0)
        collapse_v2 = float(m.get("collapse_v2_score", 0.0) or 0.0)
        shock = float(m.get("shock_score", 0.0) or 0.0)

        spread_widening_score = min(1.0, stale_repricing * 0.6 + shock * 0.4)
        liquidity_stress_score = min(1.0, vacuum_v2 * 0.55 + collapse_v2 * 0.45)

        imbalance_score = 0.0
        if freshness == "stale" and momentum in {"up", "rising", "accelerating"}:
            imbalance_score += 0.45
        if radar_score >= 0.30:
            imbalance_score += 0.20
        if stale_repricing >= 0.50:
            imbalance_score += 0.20
        imbalance_score = min(1.0, imbalance_score)

        micro_score = round(
            0.35 * spread_widening_score +
            0.40 * liquidity_stress_score +
            0.25 * imbalance_score,
            6
        )

        if micro_score >= 0.20:
            signals.append({
                "market_name": name,
                "microstructure_score": micro_score,
                "spread_widening_score": round(spread_widening_score, 6),
                "liquidity_stress_score": round(liquidity_stress_score, 6),
                "imbalance_score": round(imbalance_score, 6),
                "freshness": freshness,
                "momentum_state": momentum,
                "radar_score": round(radar_score, 6),
            })

    signals.sort(key=lambda x: x["microstructure_score"], reverse=True)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "count": len(signals),
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("MICROSTRUCTURE ENGINE BUILT")
    print("signals:", len(signals))
    print("file: analytics/microstructure_signals.json")

if __name__ == "__main__":
    main()
