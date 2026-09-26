import json
from pathlib import Path
from datetime import datetime, timezone

DETECTED_PATH = Path("logs/signals_detected.jsonl")
OPEN_PATH = Path("logs/trades_open.jsonl")
CLOSED_PATH = Path("logs/trades_closed.jsonl")

OUT_JSON = Path("analytics/signal_reputation_full.json")
OUT_TXT = Path("analytics/signal_reputation_full.txt")

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

def main():
    detected = load_jsonl(DETECTED_PATH)
    opened = load_jsonl(OPEN_PATH)
    closed = load_jsonl(CLOSED_PATH)

    detected_count = len(detected)
    executed_count = len(opened)
    resolved_count = len(closed)

    wins = 0
    losses = 0
    realized_pnl = 0.0
    total_edge_resolved = 0.0

    for r in closed:
        pnl = float(r.get("realized_pnl", 0.0) or 0.0)
        edge = float(r.get("total_edge", 0.0) or 0.0)

        realized_pnl += pnl
        total_edge_resolved += edge

        if pnl > 0:
            wins += 1
        else:
            losses += 1

    executed_rate = executed_count / detected_count if detected_count else 0.0
    resolution_rate = resolved_count / executed_count if executed_count else 0.0
    win_rate = wins / resolved_count if resolved_count else 0.0
    avg_resolved_edge = total_edge_resolved / resolved_count if resolved_count else 0.0

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals_detected": detected_count,
        "signals_executed": executed_count,
        "signals_resolved": resolved_count,
        "execution_rate": round(executed_rate, 6),
        "resolution_rate": round(resolution_rate, 6),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 6),
        "avg_resolved_edge": round(avg_resolved_edge, 6),
        "realized_pnl": round(realized_pnl, 6),
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = []
    lines.append("SIGNALATLAS FULL REPUTATION REPORT")
    lines.append("")
    lines.append(f"Signals Detected: {payload['signals_detected']}")
    lines.append(f"Signals Executed: {payload['signals_executed']}")
    lines.append(f"Signals Resolved: {payload['signals_resolved']}")
    lines.append(f"Execution Rate: {payload['execution_rate']*100:.2f}%")
    lines.append(f"Resolution Rate: {payload['resolution_rate']*100:.2f}%")
    lines.append(f"Wins: {payload['wins']}")
    lines.append(f"Losses: {payload['losses']}")
    lines.append(f"Win Rate: {payload['win_rate']*100:.2f}%")
    lines.append(f"Avg Resolved Edge: {payload['avg_resolved_edge']*100:.2f}%")
    lines.append(f"Realized PnL: {payload['realized_pnl']:.4f}")

    text = "\n".join(lines)
    OUT_TXT.write_text(text, encoding="utf-8")

    print(text)
    print("")
    print("files created:")
    print("analytics/signal_reputation_full.json")
    print("analytics/signal_reputation_full.txt")

if __name__ == "__main__":
    main()
