import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
VACUUM_V2P_PATH = Path("analytics/liquidity_vacuum_v2_plus.json")

OUT_JSON = Path("analytics/resolution_arbitrage_v2.json")
OUT_TXT = Path("analytics/resolution_arbitrage_v2.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def quality_map():
    out = {}
    for r in load_json(QUALITY_PATH).get("scores", []):
        k = r.get("market_name")
        if k:
            out[k] = r
    return out

def vacuum_map():
    out = {}
    for r in load_json(VACUUM_V2P_PATH).get("vacuum_v2_signals", []):
        k = r.get("market_name")
        if k:
            out[k] = r
    return out

def tier(score):
    if score >= 0.80:
        return "A"
    if score >= 0.65:
        return "B"
    if score >= 0.50:
        return "C"
    return "D"

def main():
    board = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    qmap = quality_map()
    vmap = vacuum_map()

    rows = []
    for r in board:
        market = r.get("market_name")
        q = qmap.get(market, {})
        v = vmap.get(market, {})

        entry_price = float(r.get("entry_price", 0.0) or 0.0)
        gross_edge = float(r.get("total_edge", 0.0) or 0.0)
        net_edge = float(r.get("expected_net_edge_pct", 0.0) or 0.0)
        vacuum = float(r.get("vacuum_score", 0.0) or 0.0)
        micro = float(r.get("microstructure_score", 0.0) or 0.0)
        fill = float(r.get("expected_fill_probability", 0.0) or 0.0)
        quality = float(q.get("quality_score", 0.0) or 0.0)
        vacuum_v2 = float(v.get("vacuum_v2_score", 0.0) or 0.0)

        # proxy: near-resolution opportunities tend to have stronger edge + cleaner fills + clearer pricing dislocation
        near_resolution_score = (
            0.30 * clamp(gross_edge / 0.15) +
            0.25 * clamp(net_edge / 15.0) +
            0.20 * clamp(fill) +
            0.15 * clamp(quality) +
            0.10 * clamp(vacuum_v2)
        )

        payoff_asymmetry_score = (
            0.35 * clamp(abs(0.50 - entry_price) / 0.50) +
            0.30 * clamp(gross_edge / 0.15) +
            0.20 * clamp(fill) +
            0.15 * clamp(quality)
        )

        execution_safety_score = (
            0.45 * clamp(fill) +
            0.25 * clamp(quality) +
            0.15 * clamp(vacuum / 0.20) +
            0.15 * clamp(micro / 0.05)
        )

        arb_v2_score = round(
            0.40 * near_resolution_score +
            0.35 * payoff_asymmetry_score +
            0.25 * execution_safety_score,
            6
        )

        rows.append({
            "market_name": market,
            "bucket": r.get("bucket_group_title"),
            "side": r.get("side"),
            "entry_price": round(entry_price, 6),
            "gross_edge": round(gross_edge, 6),
            "net_edge_pct": round(net_edge, 6),
            "quality_score": round(quality, 6),
            "fill_probability": round(fill, 6),
            "vacuum_score": round(vacuum, 6),
            "micro_score": round(micro, 6),
            "vacuum_v2_score": round(vacuum_v2, 6),
            "near_resolution_score": round(near_resolution_score, 6),
            "payoff_asymmetry_score": round(payoff_asymmetry_score, 6),
            "execution_safety_score": round(execution_safety_score, 6),
            "resolution_arb_v2_score": arb_v2_score,
            "confidence_tier": tier(arb_v2_score),
        })

    rows.sort(key=lambda x: (x["resolution_arb_v2_score"], x["net_edge_pct"]), reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "resolution_arb_v2_signals": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["SIGNALATLAS RESOLUTION ARBITRAGE V2", ""]
    for i, r in enumerate(rows[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"score={r['resolution_arb_v2_score']:.3f} | "
            f"tier={r['confidence_tier']} | "
            f"near={r['near_resolution_score']:.3f} | "
            f"safety={r['execution_safety_score']:.3f} | "
            f"net={r['net_edge_pct']:.2f}%"
        )

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/resolution_arbitrage_v2.json")
    print("analytics/resolution_arbitrage_v2.txt")

if __name__ == "__main__":
    main()
