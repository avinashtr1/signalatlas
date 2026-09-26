import json
from collections import defaultdict
from pathlib import Path

from polymarket_engine.mark_to_market import compute_unrealized_pnl

OPEN_PATH = Path("logs/trades_open.jsonl")
CLOSED_PATH = Path("logs/trades_closed.jsonl")
START_EQUITY = 100000.0


def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main():
    open_rows = load_jsonl(OPEN_PATH)
    closed_rows = load_jsonl(CLOSED_PATH)

    total_open_capital = sum(float(r.get("allocated_capital", 0.0) or 0.0) for r in open_rows)
    total_closed_pnl = sum(float(r.get("realized_pnl", 0.0) or 0.0) for r in closed_rows)
    total_unrealized_pnl = float(compute_unrealized_pnl() or 0.0)
    equity_estimate = START_EQUITY + total_closed_pnl + total_unrealized_pnl

    print("\n===== DASHBOARD =====")
    print("open_trades:", len(open_rows))
    print("closed_trades:", len(closed_rows))
    print("total_open_capital:", round(total_open_capital, 2))
    print("total_closed_realized_pnl:", round(total_closed_pnl, 4))
    print("total_unrealized_pnl:", round(total_unrealized_pnl, 4))
    print("equity_estimate:", round(equity_estimate, 4))

    by_bucket = defaultdict(list)
    for r in open_rows:
        key = r.get("bucket_group_title") or "NO_BUCKET"
        by_bucket[key].append(r)

    print("\nOPEN BUCKETS:")
    for bucket, rows in sorted(
        by_bucket.items(),
        key=lambda kv: -sum(float(x.get("allocated_capital", 0.0) or 0.0) for x in kv[1])
    ):
        cap = sum(float(x.get("allocated_capital", 0.0) or 0.0) for x in rows)
        avg_edge = sum(float(x.get("total_edge", 0.0) or 0.0) for x in rows) / max(len(rows), 1)
        avg_micro = sum(float(x.get("microstructure_score", 0.0) or 0.0) for x in rows) / max(len(rows), 1)
        print({
            "bucket": bucket,
            "legs": len(rows),
            "capital": round(cap, 2),
            "avg_total_edge": round(avg_edge, 4),
            "avg_micro_score": round(avg_micro, 4),
        })

    if closed_rows:
        by_closed_bucket = defaultdict(list)
        for r in closed_rows:
            key = r.get("bucket_group_title") or "NO_BUCKET"
            by_closed_bucket[key].append(r)

        print("\nCLOSED BUCKETS:")
        for bucket, rows in sorted(
            by_closed_bucket.items(),
            key=lambda kv: -sum(float(x.get("realized_pnl", 0.0) or 0.0) for x in kv[1])
        ):
            pnl = sum(float(x.get("realized_pnl", 0.0) or 0.0) for x in rows)
            print({
                "bucket": bucket,
                "closed_trades": len(rows),
                "realized_pnl": round(pnl, 4),
            })

    print("===== END =====\n")


if __name__ == "__main__":
    main()
