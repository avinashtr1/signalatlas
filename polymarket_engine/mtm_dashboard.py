import json
from collections import defaultdict
from pathlib import Path

from polymarket_engine.data_adapters.polymarket_adapter import PolymarketAdapter

OPEN_PATH = Path("logs/trades_open.jsonl")
CLOSED_PATH = Path("logs/trades_closed.jsonl")


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


def latest_open_positions(open_rows, closed_rows):
    closed_ids = {r.get("trade_id") for r in closed_rows}
    latest = {}
    for r in open_rows:
        tid = r.get("trade_id")
        if tid and tid not in closed_ids:
            latest[tid] = r
    return list(latest.values())


def calc_unrealized(position, live_yes_price):
    side = position.get("side", "LONG")
    qty = float(position.get("filled_size_usd", 0.0) or 0.0)
    entry = float(position.get("entry_price", 0.0) or 0.0)

    if side == "SHORT":
        return qty * (entry - live_yes_price)
    return qty * (live_yes_price - entry)


def main():
    adapter = PolymarketAdapter()

    open_rows = load_jsonl(OPEN_PATH)
    closed_rows = load_jsonl(CLOSED_PATH)
    open_positions = latest_open_positions(open_rows, closed_rows)

    print("\n===== MTM DASHBOARD =====")
    print("open_positions:", len(open_positions))
    print("closed_trades:", len(closed_rows))

    total_alloc = 0.0
    total_unreal = 0.0
    bucket_rows = defaultdict(list)

    detailed = []

    for pos in open_positions:
        market_id = pos.get("market_id")
        try:
            live = adapter.get_market_by_id(str(market_id))
            live_px = float(live.get("current_price", 0.0) or 0.0)
        except Exception:
            live_px = None

        alloc = float(pos.get("allocated_capital", 0.0) or 0.0)
        total_alloc += alloc

        unreal = None
        if live_px is not None:
            unreal = calc_unrealized(pos, live_px)
            total_unreal += unreal

        row = {
            "trade_id": pos.get("trade_id"),
            "bucket": pos.get("bucket_group_title"),
            "market_name": pos.get("market_name"),
            "side": pos.get("side"),
            "entry_price": round(float(pos.get("entry_price", 0.0) or 0.0), 6),
            "live_price": round(live_px, 6) if live_px is not None else None,
            "allocated_capital": round(alloc, 2),
            "unrealized_pnl": round(unreal, 4) if unreal is not None else None,
            "total_edge": round(float(pos.get("total_edge", 0.0) or 0.0), 4),
            "microstructure_score": round(float(pos.get("microstructure_score", 0.0) or 0.0), 4),
        }
        detailed.append(row)
        bucket_rows[pos.get("bucket_group_title") or "NO_BUCKET"].append(row)

    print("total_open_capital:", round(total_alloc, 2))
    print("total_unrealized_pnl:", round(total_unreal, 4))
    print("mtm_equity_estimate:", round(100000 + total_unreal, 4))

    print("\nBUCKET SUMMARY:")
    for bucket, rows in sorted(bucket_rows.items(), key=lambda kv: -sum((x["allocated_capital"] or 0.0) for x in kv[1])):
        cap = sum((x["allocated_capital"] or 0.0) for x in rows)
        upnl = sum((x["unrealized_pnl"] or 0.0) for x in rows)
        print({
            "bucket": bucket,
            "legs": len(rows),
            "capital": round(cap, 2),
            "unrealized_pnl": round(upnl, 4),
        })

    print("\nOPEN POSITIONS:")
    for row in detailed:
        print(row)

    print("===== END =====\n")


if __name__ == "__main__":
    main()
