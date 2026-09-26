import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
VACUUM_PATH = Path("analytics/liquidity_vacuum_v2.json")
MICRO_PATH = Path("analytics/microstructure_intelligence.json")

OUT_JSON = Path("analytics/stale_repricing.json")
OUT_TXT = Path("analytics/stale_repricing.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def build_map(rows, key):
    out = {}
    for r in rows:
        k = r.get(key)
        if k:
            out[k] = r
    return out

def detect():
    leaderboard = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    quality_map = build_map(load_json(QUALITY_PATH).get("scores", []), "market_name")
    vacuum_map = build_map(load_json(VACUUM_PATH).get("vacuum_opportunities", []), "market_name")
    micro_map = build_map(load_json(MICRO_PATH).get("microstructure_signals", []), "market_name")

    results = []

    for r in leaderboard:
        market = r.get("market_name")
        edge = float(r.get("total_edge", 0.0) or 0.0)
        net = float(r.get("expected_net_edge_pct", 0.0) or 0.0)
        fill = float(r.get("expected_fill_probability", 1.0) or 1.0)
        entry_price = float(r.get("entry_price", 0.0) or 0.0)

        q = quality_map.get(market, {})
        v = vacuum_map.get(market, {})
        m = micro_map.get(market, {})

        quality_score = float(q.get("quality_score", 0.0) or 0.0)
        vacuum_rank = float(v.get("vacuum_rank", 0.0) or 0.0)
        micro_rank = float(m.get("micro_rank", 0.0) or 0.0)

        # lower entry price can imply more room for repricing in binary-style markets
        price_staleness = 1.0 - clamp(entry_price)

        stale_score = round(
            0.30 * clamp(edge / 0.15) +
            0.20 * clamp(net / 15.0) +
            0.20 * clamp(quality_score) +
            0.15 * clamp(vacuum_rank) +
            0.10 * clamp(micro_rank) +
            0.05 * price_staleness,
            6
        )

        if stale_score < 0.45:
            continue

        results.append({
            "market_name": market,
            "bucket": r.get("bucket_group_title"),
            "side": r.get("side"),
            "entry_price": round(entry_price, 6),
            "edge": round(edge, 6),
            "net_edge_pct": round(net, 6),
            "fill_probability": round(fill, 6),
            "quality_score": round(quality_score, 6),
            "vacuum_rank": round(vacuum_rank, 6),
            "micro_rank": round(micro_rank, 6),
            "stale_repricing_score": stale_score,
        })

    results.sort(key=lambda x: x["stale_repricing_score"], reverse=True)
    return results

def to_text(results):
    lines = []
    lines.append("SIGNALATLAS STALE REPRICING")
    lines.append("")

    if not results:
        lines.append("No stale repricing opportunities detected.")
        return "\n".join(lines)

    for i, r in enumerate(results[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"score={r['stale_repricing_score']:.3f} | "
            f"edge={r['edge']*100:.2f}% | "
            f"net={r['net_edge_pct']:.2f}% | "
            f"quality={r['quality_score']:.3f} | "
            f"vacuum={r['vacuum_rank']:.3f} | "
            f"micro={r['micro_rank']:.3f}"
        )

    return "\n".join(lines)

def main():
    results = detect()

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "stale_repricing_opportunities": results,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(results), encoding="utf-8")

    print(to_text(results))
    print("")
    print("files created:")
    print("analytics/stale_repricing.json")
    print("analytics/stale_repricing.txt")

if __name__ == "__main__":
    main()
