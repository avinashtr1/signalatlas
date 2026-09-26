import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

MEMORY_PATH = Path("analytics/signal_memory.jsonl")
OUT_JSON = Path("analytics/performance_analytics.json")
OUT_TXT = Path("analytics/performance_analytics.txt")

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

def pct(a, b):
    return (a / b) if b else 0.0

def main():
    rows = load_jsonl(MEMORY_PATH)

    resolved_rows = [r for r in rows if r.get("resolved") is True]
    unresolved_rows = [r for r in rows if r.get("resolved") is not True]

    wins = sum(1 for r in resolved_rows if r.get("signal_correct") is True)
    losses = sum(1 for r in resolved_rows if r.get("signal_correct") is False)

    module_stats = {
        "vacuum": {"hits": 0, "total": 0},
        "microstructure": {"hits": 0, "total": 0},
        "stale_repricing": {"hits": 0, "total": 0},
        "quality": {"hits": 0, "total": 0},
    }

    market_stats = defaultdict(lambda: {"hits": 0, "total": 0})
    bucket_stats = defaultdict(lambda: {"hits": 0, "total": 0})

    for r in resolved_rows:
        correct = r.get("signal_correct") is True
        market = r.get("market_name") or "UNKNOWN"
        bucket = r.get("bucket") or "UNKNOWN"

        market_stats[market]["total"] += 1
        bucket_stats[bucket]["total"] += 1

        if correct:
            market_stats[market]["hits"] += 1
            bucket_stats[bucket]["hits"] += 1

        if float(r.get("vacuum_rank", 0) or 0) > 0:
            module_stats["vacuum"]["total"] += 1
            if correct:
                module_stats["vacuum"]["hits"] += 1

        if float(r.get("micro_rank", 0) or 0) > 0:
            module_stats["microstructure"]["total"] += 1
            if correct:
                module_stats["microstructure"]["hits"] += 1

        if float(r.get("stale_repricing_score", 0) or 0) > 0:
            module_stats["stale_repricing"]["total"] += 1
            if correct:
                module_stats["stale_repricing"]["hits"] += 1

        if float(r.get("quality_score", 0) or 0) > 0:
            module_stats["quality"]["total"] += 1
            if correct:
                module_stats["quality"]["hits"] += 1

    module_summary = []
    for name, s in module_stats.items():
        module_summary.append({
            "module": name,
            "hits": s["hits"],
            "total": s["total"],
            "hit_rate": round(pct(s["hits"], s["total"]), 6),
        })

    market_summary = [
        {
            "market_name": k,
            "hits": v["hits"],
            "total": v["total"],
            "hit_rate": round(pct(v["hits"], v["total"]), 6),
        }
        for k, v in market_stats.items()
    ]
    bucket_summary = [
        {
            "bucket": k,
            "hits": v["hits"],
            "total": v["total"],
            "hit_rate": round(pct(v["hits"], v["total"]), 6),
        }
        for k, v in bucket_stats.items()
    ]

    module_summary.sort(key=lambda x: (x["hit_rate"], x["total"]), reverse=True)
    market_summary.sort(key=lambda x: (x["hit_rate"], x["total"]), reverse=True)
    bucket_summary.sort(key=lambda x: (x["hit_rate"], x["total"]), reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "resolved": len(resolved_rows),
        "unresolved": len(unresolved_rows),
        "wins": wins,
        "losses": losses,
        "win_rate": round(pct(wins, len(resolved_rows)), 6),
        "module_summary": module_summary,
        "market_summary": market_summary[:20],
        "bucket_summary": bucket_summary[:20],
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS PERFORMANCE ANALYTICS")
    lines.append("")
    lines.append(f"Rows: {len(rows)}")
    lines.append(f"Resolved: {len(resolved_rows)}")
    lines.append(f"Unresolved: {len(unresolved_rows)}")
    lines.append(f"Wins: {wins}")
    lines.append(f"Losses: {losses}")
    lines.append(f"Win Rate: {pct(wins, len(resolved_rows)):.2%}")
    lines.append("")
    lines.append("MODULE HIT RATES")
    for r in module_summary:
        lines.append(f"{r['module']}: {r['hit_rate']:.2%} ({r['hits']}/{r['total']})")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/performance_analytics.json")
    print("analytics/performance_analytics.txt")

if __name__ == "__main__":
    main()
