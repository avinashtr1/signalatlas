import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
OUT_JSON = Path("analytics/resolution_arbitrage.json")
OUT_TXT = Path("analytics/resolution_arbitrage.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def build_quality_map():
    data = load_json(QUALITY_PATH)
    out = {}
    for r in data.get("scores", []):
        name = r.get("market_name")
        if name:
            out[name] = r
    return out

def detect():
    leaderboard = load_json(LEADERBOARD_PATH).get("leaderboard", [])
    quality_map = build_quality_map()

    groups = defaultdict(list)
    for r in leaderboard:
        bucket = (r.get("bucket_group_title") or "").strip() or "UNKNOWN"
        groups[bucket].append(r)

    results = []

    for bucket, rows in groups.items():
        if len(rows) < 2:
            continue

        enriched = []
        prob_sum = 0.0

        for r in rows:
            price = float(r.get("entry_price", 0.0) or 0.0)
            name = r.get("market_name")
            q = quality_map.get(name, {})
            prob_sum += price
            enriched.append({
                "market_name": name,
                "side": r.get("side"),
                "entry_price": price,
                "edge": float(r.get("total_edge", 0.0) or 0.0),
                "net": float(r.get("expected_net_edge_pct", 0.0) or 0.0),
                "vacuum": float(r.get("vacuum_score", 0.0) or 0.0),
                "quality": float(q.get("quality_score", 0.0) or 0.0),
                "grade": q.get("grade"),
            })

        deviation = abs(prob_sum - 1.0)

        avg_edge = sum(r["edge"] for r in enriched) / len(enriched)
        avg_quality = sum(r["quality"] for r in enriched) / len(enriched)
        max_vacuum = max(r["vacuum"] for r in enriched)

        arb_score = round(
            0.45 * clamp(deviation / 0.15) +
            0.20 * clamp(avg_edge / 0.15) +
            0.20 * clamp(avg_quality) +
            0.15 * clamp(max_vacuum / 0.25),
            6
        )

        if arb_score < 0.30:
            continue

        enriched.sort(key=lambda x: (x["edge"], x["quality"]), reverse=True)

        results.append({
            "bucket": bucket,
            "arbitrage_score": arb_score,
            "probability_sum": round(prob_sum, 6),
            "deviation_from_one": round(deviation, 6),
            "avg_edge": round(avg_edge, 6),
            "avg_quality": round(avg_quality, 6),
            "max_vacuum": round(max_vacuum, 6),
            "markets_in_bucket": len(enriched),
            "top_markets": enriched[:5],
        })

    results.sort(key=lambda x: x["arbitrage_score"], reverse=True)
    return results

def to_text(results):
    lines = []
    lines.append("SIGNALATLAS RESOLUTION ARBITRAGE")
    lines.append("")

    if not results:
        lines.append("No resolution arbitrage detected.")
        return "\n".join(lines)

    for i, r in enumerate(results[:10], start=1):
        lines.append(
            f"{i}. {r['bucket']} | "
            f"arb={r['arbitrage_score']:.3f} | "
            f"prob_sum={r['probability_sum']:.3f} | "
            f"dev={r['deviation_from_one']:.3f} | "
            f"avg_edge={r['avg_edge']*100:.2f}%"
        )
    return "\n".join(lines)

def main():
    results = detect()

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "arbitrage_candidates": results,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(results), encoding="utf-8")

    print(to_text(results))
    print("")
    print("files created:")
    print("analytics/resolution_arbitrage.json")
    print("analytics/resolution_arbitrage.txt")

if __name__ == "__main__":
    main()
