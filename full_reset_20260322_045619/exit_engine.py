import json
from pathlib import Path
from datetime import datetime, timezone

from polymarket_engine.edge_decay_monitor import detect_edge_decay
from polymarket_engine.data_adapters.polymarket_adapter import PolymarketAdapter

OPEN_LOG = Path("logs/trades_open.jsonl")
CLOSED_LOG = Path("logs/trades_closed.jsonl")

adapter = PolymarketAdapter()


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path, row):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")



def _extract_bucket_sum(market_payload):
    prices = market_payload.get("bucket_group_prices") or []
    try:
        vals = [float(x) for x in prices]
    except Exception:
        return None
    if not vals:
        return None
    return sum(vals)


def calc_realized(position, live_price):
    entry = float(position.get("entry_price", 0))
    size = float(position.get("filled_size_usd", 0))
    side = position.get("side", "LONG")

    if side == "SHORT":
        return size * (entry - live_price)

    return size * (live_price - entry)


def run_exit_engine():

    open_trades = load_jsonl(OPEN_LOG)
    closed_trades = load_jsonl(CLOSED_LOG)
    already_closed_ids = {str(x.get("trade_id")) for x in closed_trades if x.get("trade_id")}
    decay_trades = detect_edge_decay()

    if not decay_trades:
        return []

    decay_ids = {t["trade_id"] for t in decay_trades}
    closed = []

    for t in open_trades:

        trade_id = str(t.get("trade_id"))
        if trade_id in already_closed_ids:
            continue

        try:
            live = adapter.get_market_by_id(str(t["market_id"]))
            live_price = float(live.get("current_price", 0))
        except Exception:
            continue

        bucket_sum = _extract_bucket_sum(live)
        bucket_rebalanced = False
        if str(t.get("side", "LONG")).upper() == "SHORT" and bucket_sum is not None:
            if bucket_sum <= 1.02:
                bucket_rebalanced = True

        if trade_id not in decay_ids and not bucket_rebalanced:
            continue

        realized = calc_realized(t, live_price)

        close_reason = "BUCKET_REBALANCE" if bucket_rebalanced and trade_id not in decay_ids else "EDGE_DECAY"

        close_record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "CLOSE",
            "trade_id": t["trade_id"],
            "market_id": t["market_id"],
            "market_name": t.get("market_name"),
            "side": t.get("side"),
            "entry_price": t.get("entry_price"),
            "exit_price": live_price,
            "allocated_capital": t.get("allocated_capital"),
            "realized_pnl": realized,
            "close_reason": close_reason,
            "bucket_sum": bucket_sum
        }

        append_jsonl(CLOSED_LOG, close_record)

        closed.append(close_record)

    return closed


if __name__ == "__main__":
    print(run_exit_engine())
