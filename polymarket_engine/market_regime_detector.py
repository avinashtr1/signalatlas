import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD = Path("analytics/alpha_leaderboard.json")
VACUUM_V2 = Path("analytics/liquidity_vacuum_v2_plus.json")
COLLAPSE_V2 = Path("analytics/liquidity_collapse_v2.json")
ARB_V2 = Path("analytics/resolution_arbitrage_v2.json")
SHOCKS = Path("analytics/probability_shocks.json")
DRIFT = Path("analytics/probability_drift_report.json")

OUT_JSON = Path("analytics/market_regime.json")
OUT_TXT = Path("analytics/market_regime.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def avg(xs):
    return sum(xs) / len(xs) if xs else 0.0

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def main():
    board = load_json(LEADERBOARD).get("leaderboard", [])
    vac = load_json(VACUUM_V2).get("vacuum_v2_signals", [])
    col = load_json(COLLAPSE_V2).get("collapse_v2_signals", [])
    arb = load_json(ARB_V2).get("resolution_arb_v2_signals", [])
    shocks = load_json(SHOCKS).get("shocks", [])
    drift = load_json(DRIFT).get("drift_markets", [])

    fills = [float(r.get("expected_fill_probability", 0.0) or 0.0) for r in board]
    net_edges = [float(r.get("expected_net_edge_pct", 0.0) or 0.0) for r in board]
    vac_scores = [float(r.get("vacuum_v2_score", 0.0) or 0.0) for r in vac]
    col_scores = [float(r.get("collapse_v2_score", 0.0) or 0.0) for r in col]
    arb_scores = [float(r.get("resolution_arb_v2_score", 0.0) or 0.0) for r in arb]

    avg_fill = avg(fills)
    avg_edge = avg(net_edges)
    avg_vac = avg(vac_scores)
    avg_col = avg(col_scores)
    avg_arb = avg(arb_scores)

    event_spike_score = clamp(
        0.50 * clamp(len(shocks) / 5.0) +
        0.30 * clamp(len(drift) / 5.0) +
        0.20 * clamp(avg_edge / 15.0)
    )

    thin_liquidity_score = clamp(
        0.45 * avg_col +
        0.30 * avg_vac +
        0.25 * clamp(1.0 - avg_fill)
    )

    resolution_phase_score = clamp(
        0.65 * avg_arb +
        0.20 * clamp(avg_edge / 15.0) +
        0.15 * avg_vac
    )

    volatile_score = clamp(
        0.35 * event_spike_score +
        0.35 * avg_col +
        0.30 * clamp(avg_edge / 15.0)
    )

    calm_score = clamp(
        0.45 * avg_fill +
        0.25 * (1.0 - avg_col) +
        0.15 * (1.0 - event_spike_score) +
        0.15 * (1.0 - thin_liquidity_score)
    )

    regime_scores = {
        "calm": round(calm_score, 6),
        "volatile": round(volatile_score, 6),
        "thin_liquidity": round(thin_liquidity_score, 6),
        "resolution_phase": round(resolution_phase_score, 6),
        "event_spike": round(event_spike_score, 6),
    }

    active_regime = max(regime_scores, key=regime_scores.get)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_regime": active_regime,
        "regime_scores": regime_scores,
        "inputs": {
            "avg_fill_probability": round(avg_fill, 6),
            "avg_net_edge_pct": round(avg_edge, 6),
            "avg_vacuum_v2_score": round(avg_vac, 6),
            "avg_collapse_v2_score": round(avg_col, 6),
            "avg_resolution_arb_v2_score": round(avg_arb, 6),
            "shock_count": len(shocks),
            "drift_count": len(drift),
            "leaderboard_rows": len(board),
        }
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "SIGNALATLAS MARKET REGIME",
        "",
        f"Active Regime: {active_regime}",
        f"Calm: {regime_scores['calm']:.3f}",
        f"Volatile: {regime_scores['volatile']:.3f}",
        f"Thin Liquidity: {regime_scores['thin_liquidity']:.3f}",
        f"Resolution Phase: {regime_scores['resolution_phase']:.3f}",
        f"Event Spike: {regime_scores['event_spike']:.3f}",
    ]
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/market_regime.json")
    print("analytics/market_regime.txt")

if __name__ == "__main__":
    main()
