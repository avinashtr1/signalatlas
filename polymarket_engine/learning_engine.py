import json
from pathlib import Path
from statistics import mean
from datetime import datetime, timezone

MEM = Path("analytics/signal_memory.json")
OUT = Path("analytics/signal_learning_report.json")

def load_json(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    mem = load_json(MEM)
    rows = mem.get("rows", [])

    if not rows:
        print("No memory rows")
        return

    mis = []
    col = []
    mom = []

    alpha_scores = []

    for r in rows:
        alpha_scores.append(r.get("alpha_score",0))

        if r.get("mispricing_flag"):
            mis.append(r.get("alpha_score",0))

        if r.get("collapse_flag"):
            col.append(r.get("alpha_score",0))

        if r.get("momentum_break_flag"):
            mom.append(r.get("alpha_score",0))

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows_analyzed": len(rows),
        "avg_alpha_score": mean(alpha_scores) if alpha_scores else 0,
        "engine_strength": {
            "mispricing_engine": mean(mis) if mis else 0,
            "liquidity_collapse_engine": mean(col) if col else 0,
            "momentum_break_engine": mean(mom) if mom else 0
        }
    }

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("LEARNING ENGINE BUILT")
    print("file:", OUT)
    print("rows analyzed:", len(rows))

if __name__ == "__main__":
    main()
