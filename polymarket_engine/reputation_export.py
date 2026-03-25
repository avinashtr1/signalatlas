import json
import csv
from pathlib import Path
from datetime import datetime

OPEN_PATH = Path("logs/trades_open.jsonl")
CLOSED_PATH = Path("logs/trades_closed.jsonl")
ANALYTICS_DIR = Path("analytics")

def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open() as f:
        for line in f:
            line=line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def main():

    open_rows = load_jsonl(OPEN_PATH)
    closed_rows = load_jsonl(CLOSED_PATH)

    total_signals = len(open_rows) + len(closed_rows)

    wins = 0
    losses = 0
    pnl = 0

    for r in closed_rows:

        trade_pnl = float(r.get("realized_pnl",0) or 0)

        pnl += trade_pnl

        if trade_pnl > 0:
            wins += 1
        else:
            losses += 1

    resolved = len(closed_rows)

    win_rate = wins / resolved if resolved else 0

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "signals_generated": total_signals,
        "signals_resolved": resolved,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate,4),
        "realized_pnl": round(pnl,4)
    }

    ANALYTICS_DIR.mkdir(exist_ok=True)

    with open(ANALYTICS_DIR / "reputation_summary.json","w") as f:
        json.dump(summary,f,indent=2)

    with open(ANALYTICS_DIR / "signal_history.csv","w",newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "trade_id",
            "timestamp",
            "market",
            "edge",
            "entry_price",
            "pnl"
        ])

        for r in closed_rows:

            writer.writerow([
                r.get("trade_id"),
                r.get("ts"),
                r.get("market_name"),
                r.get("total_edge"),
                r.get("entry_price"),
                r.get("realized_pnl")
            ])

    print("reputation export complete")
    print("files created:")
    print("analytics/reputation_summary.json")
    print("analytics/signal_history.csv")

if __name__ == "__main__":
    main()
