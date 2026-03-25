import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

MEMORY_PATH = Path("analytics/signal_memory.jsonl")
OUT_JSON = Path("analytics/signal_memory_analytics.json")
OUT_TXT = Path("analytics/signal_memory_analytics.txt")

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

def main():
    rows = load_jsonl(MEMORY_PATH)

    market_counter = Counter()
    bucket_counter = Counter()
    grade_counter = Counter()

    has_vacuum = 0
    has_micro = 0
    has_stale = 0

    for r in rows:
        market_counter[r.get("market_name")] += 1
        bucket_counter[r.get("bucket")] += 1
        grade_counter[r.get("quality_grade")] += 1

        flags = r.get("flags", {})
        has_vacuum += 1 if flags.get("has_vacuum") else 0
        has_micro += 1 if flags.get("has_micro") else 0
        has_stale += 1 if flags.get("has_stale") else 0

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "top_markets": market_counter.most_common(10),
        "top_buckets": bucket_counter.most_common(10),
        "grade_distribution": dict(grade_counter),
        "feature_counts": {
            "has_vacuum": has_vacuum,
            "has_micro": has_micro,
            "has_stale": has_stale,
        }
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS MEMORY ANALYTICS")
    lines.append("")
    lines.append(f"Rows: {len(rows)}")
    lines.append("")
    lines.append("GRADE DISTRIBUTION")
    for k, v in grade_counter.items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("FEATURE COUNTS")
    lines.append(f"has_vacuum: {has_vacuum}")
    lines.append(f"has_micro: {has_micro}")
    lines.append(f"has_stale: {has_stale}")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/signal_memory_analytics.json")
    print("analytics/signal_memory_analytics.txt")

if __name__ == "__main__":
    main()
