import json
import csv
from pathlib import Path
from datetime import datetime, timezone

OPEN_PATH = Path("logs/trades_open.jsonl")
ANALYTICS_DIR = Path("analytics")

def load_jsonl(path):
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

def latest_open_positions(open_rows):
    latest = {}
    for r in open_rows:
        trade_id = r.get("trade_id")
        if trade_id:
            latest[trade_id] = r
    return list(latest.values())

def build_leaderboard():
    open_rows = load_jsonl(OPEN_PATH)
    positions = latest_open_positions(open_rows)

    leaderboard = []
    for r in positions:
        leaderboard.append({
            "trade_id": r.get("trade_id"),
            "timestamp": r.get("ts"),
            "market_id": r.get("market_id"),
            "market_name": r.get("market_name"),
            "bucket_group_title": r.get("bucket_group_title"),
            "side": r.get("side"),
            "entry_price": float(r.get("entry_price", 0.0) or 0.0),
            "structural_edge": float(r.get("structural_edge", 0.0) or 0.0),
            "total_edge": float(r.get("total_edge", 0.0) or 0.0),
            "expected_net_edge_pct": float(r.get("expected_net_edge_pct", 0.0) or 0.0),
            "microstructure_score": float(r.get("microstructure_score", 0.0) or 0.0),
            "vacuum_score": float(r.get("vacuum_score", 0.0) or 0.0),
            "expected_fill_probability": float(r.get("expected_fill_probability", 0.0) or 0.0),
            "allocated_capital": float(r.get("allocated_capital", 0.0) or 0.0),
        })

    leaderboard.sort(
        key=lambda x: (
            x["total_edge"],
            x["expected_net_edge_pct"],
            x["vacuum_score"],
            x["microstructure_score"]
        ),
        reverse=True
    )

    for i, row in enumerate(leaderboard, start=1):
        row["rank"] = i

    return leaderboard

def export_leaderboard(leaderboard):
    ANALYTICS_DIR.mkdir(exist_ok=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(leaderboard),
        "leaderboard": leaderboard,
    }

    with (ANALYTICS_DIR / "alpha_leaderboard.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with (ANALYTICS_DIR / "alpha_leaderboard.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rank",
            "market_name",
            "bucket_group_title",
            "side",
            "entry_price",
            "structural_edge",
            "total_edge",
            "expected_net_edge_pct",
            "microstructure_score",
            "vacuum_score",
            "expected_fill_probability",
            "allocated_capital",
            "trade_id",
            "timestamp",
            "market_id",
        ])
        for row in leaderboard:
            writer.writerow([
                row["rank"],
                row["market_name"],
                row["bucket_group_title"],
                row["side"],
                row["entry_price"],
                row["structural_edge"],
                row["total_edge"],
                row["expected_net_edge_pct"],
                row["microstructure_score"],
                row["vacuum_score"],
                row["expected_fill_probability"],
                row["allocated_capital"],
                row["trade_id"],
                row["timestamp"],
                row["market_id"],
            ])

def main():
    leaderboard = build_leaderboard()
    export_leaderboard(leaderboard)

    print("alpha leaderboard export complete")
    print("files created:")
    print("analytics/alpha_leaderboard.json")
    print("analytics/alpha_leaderboard.csv")
    print()
    print("TOP SIGNALS")
    for row in leaderboard[:10]:
        print(
            f"#{row['rank']} | {row['market_name']} | "
            f"edge={row['total_edge']:.4f} | "
            f"net={row['expected_net_edge_pct']:.4f}% | "
            f"vacuum={row['vacuum_score']:.4f} | "
            f"micro={row['microstructure_score']:.4f}"
        )

if __name__ == "__main__":
    main()
