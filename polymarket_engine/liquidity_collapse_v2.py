import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
VACUUM_V2P_PATH = Path("analytics/liquidity_vacuum_v2_plus.json")

OUT_JSON = Path("analytics/liquidity_collapse_v2.json")
OUT_TXT = Path("analytics/liquidity_collapse_v2.txt")

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

        gross_edge = float(r.get("total_edge", 0.0) or 0.0)
        net_edge = float(r.get("expected_net_edge_pct", 0.0) or 0.0)
        vacuum = float(r.get("vacuum_score", 0.0) or 0.0)
        micro = float(r.get("microstructure_score", 0.0) or 0.0)
        fill = float(r.get("expected_fill_probability", 0.0) or 0.0)
        quality = float(q.get("quality_score", 0.0) or 0.0)
        vacuum_v2 = float(v.get("vacuum_v2_score", 0.0) or 0.0)

        # proxies until real depth snapshots are added
        spread_stress = (
            0.45 * clamp(vacuum / 0.20) +
            0.25 * clamp(micro / 0.05) +
            0.30 * clamp(gross_edge / 0.15)
        )

        book_thinning = (
            0.40 * clamp(1.0 - fill) +
            0.30 * clamp(vacuum_v2) +
            0.30 * clamp(net_edge / 15.0)
        )

        fake_liquidity_risk = (
            0.35 * clamp(vacuum / 0.20) +
            0.20 * clamp(micro / 0.05) +
            0.25 * clamp(vacuum_v2) +
            0.20 * clamp(quality)
        )

        collapse_score = round(
            0.35 * spread_stress +
            0.35 * book_thinning +
            0.30 * fake_liquidity_risk,
            6
        )

        rows.append({
            "market_name": market,
            "bucket": r.get("bucket_group_title"),
            "side": r.get("side"),
            "gross_edge": round(gross_edge, 6),
            "net_edge_pct": round(net_edge, 6),
            "quality_score": round(quality, 6),
            "vacuum_score": round(vacuum, 6),
            "micro_score": round(micro, 6),
            "fill_probability": round(fill, 6),
            "vacuum_v2_score": round(vacuum_v2, 6),
            "spread_stress_score": round(spread_stress, 6),
            "book_thinning_score": round(book_thinning, 6),
            "fake_liquidity_risk": round(fake_liquidity_risk, 6),
            "collapse_v2_score": collapse_score,
            "confidence_tier": tier(collapse_score),
        })

    rows.sort(key=lambda x: (x["collapse_v2_score"], x["net_edge_pct"]), reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "collapse_v2_signals": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["SIGNALATLAS LIQUIDITY COLLAPSE V2", ""]
    for i, r in enumerate(rows[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"score={r['collapse_v2_score']:.3f} | "
            f"tier={r['confidence_tier']} | "
            f"spread={r['spread_stress_score']:.3f} | "
            f"thin={r['book_thinning_score']:.3f} | "
            f"net={r['net_edge_pct']:.2f}%"
        )

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/liquidity_collapse_v2.json")
    print("analytics/liquidity_collapse_v2.txt")

if __name__ == "__main__":
    main()
