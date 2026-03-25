import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

MEMORY_PATH = Path("analytics/signal_memory.jsonl")
OUT_JSON = Path("analytics/resolution_tracking.json")
OUT_TXT = Path("analytics/resolution_tracking.txt")

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

    by_market = defaultdict(list)
    by_bucket = defaultdict(list)

    for r in rows:
        market = r.get("market_name") or "UNKNOWN"
        bucket = r.get("bucket") or "UNKNOWN"
        by_market[market].append(r)
        by_bucket[bucket].append(r)

    market_summary = []
    for market, items in by_market.items():
        market_summary.append({
            "market_name": market,
            "count": len(items),
            "avg_edge": round(avg([float(x.get("edge", 0.0) or 0.0) for x in items]), 6),
            "avg_quality": round(avg([float(x.get("quality_score", 0.0) or 0.0) for x in items]), 6),
            "avg_vacuum": round(avg([float(x.get("vacuum_rank", 0.0) or 0.0) for x in items]), 6),
            "avg_micro": round(avg([float(x.get("micro_rank", 0.0) or 0.0) for x in items]), 6),
            "avg_stale": round(avg([float(x.get("stale_repricing_score", 0.0) or 0.0) for x in items]), 6),
        })

    bucket_summary = []
    for bucket, items in by_bucket.items():
        bucket_summary.append({
            "bucket": bucket,
            "count": len(items),
            "avg_edge": round(avg([float(x.get("edge", 0.0) or 0.0) for x in items]), 6),
            "avg_quality": round(avg([float(x.get("quality_score", 0.0) or 0.0) for x in items]), 6),
            "avg_vacuum": round(avg([float(x.get("vacuum_rank", 0.0) or 0.0) for x in items]), 6),
            "avg_micro": round(avg([float(x.get("micro_rank", 0.0) or 0.0) for x in items]), 6),
            "avg_stale": round(avg([float(x.get("stale_repricing_score", 0.0) or 0.0) for x in items]), 6),
        })

    market_summary.sort(key=lambda x: (x["avg_edge"], x["count"]), reverse=True)
    bucket_summary.sort(key=lambda x: (x["avg_edge"], x["count"]), reverse=True)

    resolved_rows = [r for r in rows if r.get("resolved") is True]
    unresolved_rows = [r for r in rows if r.get("resolved") is not True]

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "resolved_signals": len(resolved_rows),
        "unresolved_signals": len(unresolved_rows),
        "market_summary": market_summary[:20],
        "bucket_summary": bucket_summary[:20],
        "note": "Tracking structure is live. Real resolution/outcome fields can be added once market settlement data is available."
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS RESOLUTION TRACKING")
    lines.append("")
    lines.append(f"Rows: {len(rows)}")
    lines.append(f"Resolved Signals: {len(resolved_rows)}")
    lines.append(f"Unresolved Signals: {len(unresolved_rows)}")
    lines.append("")
    lines.append("TOP MARKETS")
    for i, r in enumerate(market_summary[:10], start=1):
        lines.append(
            f"{i}. {r['market_name']} | "
            f"count={r['count']} | "
            f"edge={r['avg_edge']*100:.2f}% | "
            f"quality={r['avg_quality']:.3f}"
        )
    lines.append("")
    lines.append("TOP BUCKETS")
    for i, r in enumerate(bucket_summary[:10], start=1):
        lines.append(
            f"{i}. {r['bucket']} | "
            f"count={r['count']} | "
            f"edge={r['avg_edge']*100:.2f}% | "
            f"quality={r['avg_quality']:.3f}"
        )

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/resolution_tracking.json")
    print("analytics/resolution_tracking.txt")

if __name__ == "__main__":
    main()
