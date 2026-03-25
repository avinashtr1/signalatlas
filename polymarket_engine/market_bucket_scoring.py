import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

MEMORY_PATH = Path("analytics/signal_memory.jsonl")
OUT_JSON = Path("analytics/market_bucket_scoring.json")
OUT_TXT = Path("analytics/market_bucket_scoring.txt")

def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def avg(vals):
    return sum(vals) / len(vals) if vals else 0.0

def main():
    rows = load_jsonl(MEMORY_PATH)

    market_stats = defaultdict(lambda: {"count": 0, "edge": [], "quality": [], "vacuum": [], "micro": [], "stale": []})
    bucket_stats = defaultdict(lambda: {"count": 0, "edge": [], "quality": [], "vacuum": [], "micro": [], "stale": []})

    for r in rows:
        market = r.get("market_name") or "UNKNOWN"
        bucket = r.get("bucket") or "UNKNOWN"

        for target in (market_stats[market], bucket_stats[bucket]):
            target["count"] += 1
            target["edge"].append(float(r.get("edge", 0.0) or 0.0))
            target["quality"].append(float(r.get("quality_score", 0.0) or 0.0))
            target["vacuum"].append(float(r.get("vacuum_rank", 0.0) or 0.0))
            target["micro"].append(float(r.get("micro_rank", 0.0) or 0.0))
            target["stale"].append(float(r.get("stale_repricing_score", 0.0) or 0.0))

    def score_item(name, stats):
        score = (
            0.25 * avg(stats["edge"]) / 0.15 +
            0.25 * avg(stats["quality"]) +
            0.20 * avg(stats["vacuum"]) +
            0.15 * avg(stats["micro"]) +
            0.15 * avg(stats["stale"])
        )
        return {
            "name": name,
            "count": stats["count"],
            "avg_edge": round(avg(stats["edge"]), 6),
            "avg_quality": round(avg(stats["quality"]), 6),
            "avg_vacuum": round(avg(stats["vacuum"]), 6),
            "avg_micro": round(avg(stats["micro"]), 6),
            "avg_stale": round(avg(stats["stale"]), 6),
            "score": round(score, 6),
        }

    market_rank = [score_item(name, stats) for name, stats in market_stats.items()]
    bucket_rank = [score_item(name, stats) for name, stats in bucket_stats.items()]

    market_rank.sort(key=lambda x: (x["score"], x["count"]), reverse=True)
    bucket_rank.sort(key=lambda x: (x["score"], x["count"]), reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "top_markets": market_rank[:15],
        "top_buckets": bucket_rank[:15],
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS MARKET / BUCKET SCORING")
    lines.append("")
    lines.append(f"Rows: {len(rows)}")
    lines.append("")
    lines.append("TOP MARKETS")
    for i, x in enumerate(market_rank[:10], start=1):
        lines.append(f"{i}. {x['name']} | score={x['score']:.3f} | count={x['count']}")
    lines.append("")
    lines.append("TOP BUCKETS")
    for i, x in enumerate(bucket_rank[:10], start=1):
        lines.append(f"{i}. {x['name']} | score={x['score']:.3f} | count={x['count']}")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/market_bucket_scoring.json")
    print("analytics/market_bucket_scoring.txt")

if __name__ == "__main__":
    main()
