import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
QUALITY_PATH = Path("analytics/alpha_quality_scores.json")
OUT_JSON = Path("analytics/cross_market_lag.json")
OUT_TXT = Path("analytics/cross_market_lag.txt")

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
        for r in rows:
            q = quality_map.get(r.get("market_name"), {})
            enriched.append({
                "market_name": r.get("market_name"),
                "side": r.get("side"),
                "edge": float(r.get("total_edge", 0.0) or 0.0),
                "net": float(r.get("expected_net_edge_pct", 0.0) or 0.0),
                "vacuum": float(r.get("vacuum_score", 0.0) or 0.0),
                "micro": float(r.get("microstructure_score", 0.0) or 0.0),
                "fill": float(r.get("expected_fill_probability", 1.0) or 1.0),
                "quality": float(q.get("quality_score", 0.0) or 0.0),
                "grade": q.get("grade"),
            })

        enriched.sort(key=lambda x: (x["edge"], x["quality"], x["vacuum"]), reverse=True)

        leader = enriched[0]
        trailer = enriched[-1]

        edge_gap = leader["edge"] - trailer["edge"]
        quality_gap = leader["quality"] - trailer["quality"]
        vacuum_gap = leader["vacuum"] - trailer["vacuum"]

        lag_score = round(
            0.45 * clamp(edge_gap / 0.08) +
            0.25 * clamp(quality_gap / 0.30) +
            0.20 * clamp(vacuum_gap / 0.20) +
            0.10 * clamp(leader["fill"]),
            6
        )

        if lag_score < 0.35:
            continue

        results.append({
            "bucket": bucket,
            "lag_score": lag_score,
            "leader_market": leader["market_name"],
            "leader_edge": round(leader["edge"], 6),
            "leader_quality": round(leader["quality"], 6),
            "leader_vacuum": round(leader["vacuum"], 6),
            "trailer_market": trailer["market_name"],
            "trailer_edge": round(trailer["edge"], 6),
            "trailer_quality": round(trailer["quality"], 6),
            "trailer_vacuum": round(trailer["vacuum"], 6),
            "edge_gap": round(edge_gap, 6),
            "quality_gap": round(quality_gap, 6),
            "vacuum_gap": round(vacuum_gap, 6),
            "markets_in_bucket": len(enriched),
        })

    results.sort(key=lambda x: x["lag_score"], reverse=True)
    return results

def to_text(results):
    lines = []
    lines.append("SIGNALATLAS CROSS-MARKET LAG")
    lines.append("")

    if not results:
        lines.append("No cross-market lag detected.")
        return "\n".join(lines)

    for i, r in enumerate(results[:10], start=1):
        lines.append(
            f"{i}. {r['bucket']} | "
            f"lag={r['lag_score']:.3f} | "
            f"leader={r['leader_market']} | "
            f"trailer={r['trailer_market']} | "
            f"edge_gap={r['edge_gap']*100:.2f}% | "
            f"quality_gap={r['quality_gap']:.3f}"
        )
    return "\n".join(lines)

def main():
    results = detect()

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "lags": results,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(to_text(results), encoding="utf-8")

    print(to_text(results))
    print("")
    print("files created:")
    print("analytics/cross_market_lag.json")
    print("analytics/cross_market_lag.txt")

if __name__ == "__main__":
    main()
