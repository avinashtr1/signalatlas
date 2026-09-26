import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY_PATH = Path("analytics/signal_memory.jsonl")
OUT_JSON = Path("analytics/module_scoring.json")
OUT_TXT = Path("analytics/module_scoring.txt")

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

    quality_vals = []
    vacuum_vals = []
    micro_vals = []
    stale_vals = []

    for r in rows:
        quality_vals.append(float(r.get("quality_score", 0.0) or 0.0))
        vacuum_vals.append(float(r.get("vacuum_rank", 0.0) or 0.0))
        micro_vals.append(float(r.get("micro_rank", 0.0) or 0.0))
        stale_vals.append(float(r.get("stale_repricing_score", 0.0) or 0.0))

    modules = [
        {"module": "quality", "avg_score": round(avg(quality_vals), 6), "count": len([x for x in quality_vals if x > 0])},
        {"module": "vacuum", "avg_score": round(avg(vacuum_vals), 6), "count": len([x for x in vacuum_vals if x > 0])},
        {"module": "microstructure", "avg_score": round(avg(micro_vals), 6), "count": len([x for x in micro_vals if x > 0])},
        {"module": "stale_repricing", "avg_score": round(avg(stale_vals), 6), "count": len([x for x in stale_vals if x > 0])},
    ]

    modules.sort(key=lambda x: x["avg_score"], reverse=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "modules": modules,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS MODULE SCORING")
    lines.append("")
    lines.append(f"Rows: {len(rows)}")
    lines.append("")
    for i, m in enumerate(modules, start=1):
        lines.append(f"{i}. {m['module']} | avg={m['avg_score']:.3f} | count={m['count']}")

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print("")
    print("files created:")
    print("analytics/module_scoring.json")
    print("analytics/module_scoring.txt")

if __name__ == "__main__":
    main()
