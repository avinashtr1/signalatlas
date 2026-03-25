import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

OPEN_PATH = Path("logs/trades_open.jsonl")
OUT_JSON = Path("analytics/probability_shocks.json")
OUT_TXT = Path("analytics/probability_shocks.txt")


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


def detect_shocks(rows):
    by_market = defaultdict(list)

    for r in rows:
        market = r.get("market_name") or "UNKNOWN"
        try:
            entry_price = float(r.get("entry_price", 0.0) or 0.0)
            ts = r.get("ts")
        except Exception:
            continue

        by_market[market].append({
            "ts": ts,
            "entry_price": entry_price,
            "trade_id": r.get("trade_id"),
            "total_edge": float(r.get("total_edge", 0.0) or 0.0),
            "vacuum_score": float(r.get("vacuum_score", 0.0) or 0.0),
            "microstructure_score": float(r.get("microstructure_score", 0.0) or 0.0),
        })

    shocks = []

    for market, entries in by_market.items():
        if len(entries) < 2:
            continue

        entries.sort(key=lambda x: x["ts"])

        first = entries[0]
        last = entries[-1]

        move = last["entry_price"] - first["entry_price"]
        abs_move = abs(move)

        # simple first version: shock if >= 1.5 percentage points
        if abs_move >= 0.015:
            shocks.append({
                "market_name": market,
                "first_ts": first["ts"],
                "last_ts": last["ts"],
                "first_price": round(first["entry_price"], 6),
                "last_price": round(last["entry_price"], 6),
                "move": round(move, 6),
                "abs_move": round(abs_move, 6),
                "latest_edge": round(last["total_edge"], 6),
                "latest_vacuum": round(last["vacuum_score"], 6),
                "latest_micro": round(last["microstructure_score"], 6),
                "samples": len(entries),
            })

    shocks.sort(key=lambda x: x["abs_move"], reverse=True)
    return shocks


def to_text(shocks):
    lines = []
    lines.append("SIGNALATLAS PROBABILITY SHOCK REPORT")
    lines.append("")

    if not shocks:
        lines.append("No probability shocks detected.")
        return "\n".join(lines)

    for i, s in enumerate(shocks, start=1):
        lines.append(
            f"{i}. {s['market_name']} | move={s['move']:.4f} | "
            f"first={s['first_price']:.4f} | last={s['last_price']:.4f} | "
            f"edge={s['latest_edge']:.4f} | vacuum={s['latest_vacuum']:.2f} | "
            f"micro={s['latest_micro']:.2f} | samples={s['samples']}"
        )

    return "\n".join(lines)


def main():
    rows = load_jsonl(OPEN_PATH)
    shocks = detect_shocks(rows)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "shock_count": len(shocks),
        "shocks": shocks,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    text = to_text(shocks)
    OUT_TXT.write_text(text, encoding="utf-8")

    print(text)
    print("")
    print("files created:")
    print("analytics/probability_shocks.json")
    print("analytics/probability_shocks.txt")


if __name__ == "__main__":
    main()
