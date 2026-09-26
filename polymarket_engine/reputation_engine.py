import json
from pathlib import Path

OPEN_PATH = Path("logs/trades_open.jsonl")
CLOSED_PATH = Path("logs/trades_closed.jsonl")

def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def compute_reputation():

    open_rows = load_jsonl(OPEN_PATH)
    closed_rows = load_jsonl(CLOSED_PATH)

    total_signals = len(open_rows) + len(closed_rows)
    resolved_signals = len(closed_rows)

    wins = 0
    losses = 0
    total_pnl = 0.0
    total_edge = 0.0

    for r in closed_rows:
        pnl = float(r.get("realized_pnl",0.0) or 0.0)
        edge = float(r.get("total_edge",0.0) or 0.0)

        total_pnl += pnl
        total_edge += edge

        if pnl > 0:
            wins += 1
        else:
            losses += 1

    win_rate = wins / resolved_signals if resolved_signals else 0
    avg_edge = total_edge / resolved_signals if resolved_signals else 0

    report = {
        "signals_generated": total_signals,
        "signals_resolved": resolved_signals,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate,4),
        "avg_edge": round(avg_edge,4),
        "total_realized_pnl": round(total_pnl,4)
    }

    return report


if __name__ == "__main__":
    r = compute_reputation()

    print("\n===== SIGNALATLAS REPUTATION =====")
    for k,v in r.items():
        print(k,":",v)
    print("==================================\n")
