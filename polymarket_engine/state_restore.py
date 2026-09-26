import json
from pathlib import Path

OPEN_LOG = Path("logs/trades_open.jsonl")
CLOSED_LOG = Path("logs/trades_closed.jsonl")


def _load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def restore_state(paper_executor, inventory):
    open_rows = _load_jsonl(OPEN_LOG)
    closed_rows = _load_jsonl(CLOSED_LOG)

    closed_ids = {r.get("trade_id") for r in closed_rows if r.get("trade_id")}
    restored_open = 0

    for row in open_rows:
        trade_id = row.get("trade_id")
        if not trade_id or trade_id in closed_ids:
            continue

        position = {
            "trade_id": trade_id,
            "market_id": row.get("market_id"),
            "strategy_type": row.get("strategy_type", "TEST_STRATEGY"),
            "status": "OPEN",
            "side": row.get("side", "LONG"),
            "entry_timestamp": row.get("entry_timestamp") or row.get("ts"),
            "entry_price": float(row.get("entry_price", 0.0) or 0.0),
            "filled_size_usd": float(row.get("filled_size_usd", 0.0) or 0.0),
            "allocated_capital": float(row.get("allocated_capital", 0.0) or 0.0),
            "fill_ratio": float(row.get("fill_ratio", 1.0) or 1.0),
            "extra_slippage": float(row.get("extra_slippage", 0.0) or 0.0),
            "bucket_group_id": row.get("bucket_group_id"),
            "bucket_group_title": row.get("bucket_group_title"),
            "rank_score": row.get("rank_score"),
            "structural_edge": row.get("structural_edge"),
            "total_edge": row.get("total_edge"),
            "vacuum_score": row.get("vacuum_score"),
            "vacuum_reason": row.get("vacuum_reason"),
            "microstructure_score": row.get("microstructure_score"),
            "microstructure_reasons": row.get("microstructure_reasons"),
            "resolution_score": row.get("resolution_score"),
            "resolution_reason": row.get("resolution_reason"),
            "unrealized_pnl": float(row.get("unrealized_pnl", 0.0) or 0.0),
            "realized_pnl": 0.0,
            "market_name": row.get("market_name"),
            "event_group": row.get("event_group"),
        }

        paper_executor.positions[trade_id] = position
        inventory._locked_capital[trade_id] = position["allocated_capital"]
        inventory.exposure_by_strategy[position["strategy_type"]] += position["allocated_capital"]
        restored_open += 1

    realized = 0.0
    for row in closed_rows:
        realized += float(row.get("realized_pnl", 0.0) or 0.0)
    inventory.realized_pnl = realized

    return {
        "restored_open_positions": restored_open,
        "restored_closed_trades": len(closed_ids),
        "restored_realized_pnl": realized,
    }
