import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY_PATH = Path("analytics/signal_memory.jsonl")
OUTCOMES_PATH = Path("analytics/market_outcomes.json")
OUT_JSON = Path("analytics/settlement_update_summary.json")
OUT_TXT = Path("analytics/settlement_update_summary.txt")

def load_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

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
    outcomes = load_json(OUTCOMES_PATH).get("outcomes", {})

    updated = []
    unresolved = 0
    resolved = 0

    for r in rows:
        market = r.get("market_name")
        outcome = outcomes.get(market)

        row = dict(r)

        if outcome is None:
            row["resolved"] = False
            row["outcome"] = None
            row["signal_correct"] = None
            unresolved += 1
        else:
            row["resolved"] = True
            row["outcome"] = outcome

            side = (row.get("side") or "").upper()
            if outcome == "YES":
                row["signal_correct"] = side in ("LONG", "YES", "BUY")
            elif outcome == "NO":
                row["signal_correct"] = side in ("SHORT", "NO", "SELL")
            else:
                row["signal_correct"] = None

            resolved += 1

        updated.append(row)

    with MEMORY_PATH.open("w", encoding="utf-8") as f:
        for row in updated:
            f.write(json.dumps(row) + "\n")

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": len(updated),
        "resolved": resolved,
        "unresolved": unresolved,
        "note": "market_outcomes.json can be filled manually for now; later this can be replaced by live settlement ingestion."
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_TXT.write_text(
        "\n".join([
            "SIGNALATLAS SETTLEMENT UPDATE",
            "",
            f"Rows: {len(updated)}",
            f"Resolved: {resolved}",
            f"Unresolved: {unresolved}",
        ]),
        encoding="utf-8"
    )

    print("SIGNALATLAS SETTLEMENT UPDATE")
    print("")
    print(f"Rows: {len(updated)}")
    print(f"Resolved: {resolved}")
    print(f"Unresolved: {unresolved}")
    print("")
    print("files created:")
    print("analytics/settlement_update_summary.json")
    print("analytics/settlement_update_summary.txt")

if __name__ == "__main__":
    main()
