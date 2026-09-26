import json
from pathlib import Path
from datetime import datetime, timezone

LEADERBOARD_PATH = Path("analytics/alpha_leaderboard.json")
OUT_PATH = Path("logs/signals_detected.jsonl")

def load_rows():
    if not LEADERBOARD_PATH.exists():
        return []
    data = json.loads(LEADERBOARD_PATH.read_text())
    return data.get("leaderboard", [])

def append_log(row):

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_name": row.get("market_name"),
        "bucket": row.get("bucket_group_title"),
        "edge": float(row.get("total_edge", 0)),
        "expected_net_edge_pct": float(row.get("expected_net_edge_pct", 0)),
        "vacuum_score": float(row.get("vacuum_score", 0)),
        "microstructure_score": float(row.get("microstructure_score", 0)),
        "fill_probability": float(row.get("expected_fill_probability", 1)),
        "side": row.get("side"),
        "entry_price": float(row.get("entry_price", 0))
    }

    with OUT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")

def main():

    rows = load_rows()

    for r in rows:
        append_log(r)

    print(f"signals logged: {len(rows)}")
    print("file updated: logs/signals_detected.jsonl")

if __name__ == "__main__":
    main()
