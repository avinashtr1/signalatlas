import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
VACUUM_PATH = Path("analytics/liquidity_vacuum_v2.json")
MICRO_PATH = Path("analytics/microstructure_intelligence.json")
STALE_PATH = Path("analytics/stale_repricing.json")
WEIGHTS_PATH = Path("analytics/adaptive_weights.json")

OUT_JSON = Path("analytics/adaptive_composite_score.json")
OUT_TXT = Path("analytics/adaptive_composite_score.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def build_map(rows, key):
    out = {}
    for r in rows:
        k = r.get(key)
        if k:
            out[k] = r
    return out

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def main():
    leaderboard = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    quality_map = build_map(load_json(QUALITY_PATH).get("scores", []), "market_name")
    vacuum_map = build_map(load_json(VACUUM_PATH).get("vacuum_opportunities", []), "market_name")
    micro_map = build_map(load_json(MICRO_PATH).get("microstructure_signals", []), "market_name")
    stale_map = build_map(load_json(STALE_PATH).get("stale_repricing_opportunities", []), "market_name")
    weights = load_json(WEIGHTS_PATH).get("adaptive_weights", {})

    w_quality = float(weights.get("quality", 0.30))
    w_vacuum = float(weights.get("vacuum", 0.25))
    w_micro = float(weights.get("microstructure", 0.20))
    w_stale = float(weights.get("stale_repricing", 0.25))

    rows = []

    for r in leaderboard:
        market = r.get("market_name")
        q = quality_map.get(market, {})
        v = vacuum_map.get(market, {})
        m = micro_map.get(market, {})
        s = stale_map.get(market, {})

        quality_score = float(q.get("quality_score", 0.0) or 0.0)
        vacuum_rank = float(v.get("vacuum_rank", 0.0) or 0.0)
        micro_rank = float(m.get("micro_rank", 0.0) or 0.0)
        stale_score = float(s.get("stale_repricing_score", 0.0) or 0.0)
        edge = float(r.get("total_edge", 0.0) or 0.0)
        net = float(r.get("expected_net_edge_pct", 0.0) or 0.0)

        composite = round(
            w_quality * clamp(quality_score) +
            w_vacuum * clamp(vacuum_rank) +
            w_micro * clamp(micro_rank) +
            w_stale * clamp(stale_score),
            6
        )

        rows.append({
            "market_name": market,
            "bucket": r.get("bucket_group_title"),
            "side": r.get("side"),
            "edge": round(edge, 6),
            "net_edge_pct": round(net, 6),
            "quality_score": round(quality_score, 6),
            "vacuum_rank": round(vacuum_rank, 6),
            "micro_rank": round(micro_rank, 6),
            "stale_repricing_score": round(stale_score, 6),
            "adaptive_composite_score": composite,
        })

    rows.sort(key=lambda x: (x["adaptive_composite_score"], x["edge"]), reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "weights_used": {
            "quality": w_quality,
            "vacuum": w_vacuum,
            "microstructure": w_micro,
            "stale_repricing": w_stale,
        },
        "ranked_markets": rows,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS ADAPTIVE COMPOSITE SCORE")
    lines.append("")
    for i, r in enumerate(rows[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"score={r['adaptive_composite_score']:.3f} | "
            f"edge={r['edge']*100:.2f}% | "
            f"quality={r['quality_score']:.3f} | "
            f"vacuum={r['vacuum_rank']:.3f} | "
            f"micro={r['micro_rank']:.3f} | "
            f"stale={r['stale_repricing_score']:.3f}"
        )

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/adaptive_composite_score.json")
    print("analytics/adaptive_composite_score.txt")

if __name__ == "__main__":
    main()
