import json
from pathlib import Path
from collections import defaultdict
from polymarket_engine.data_adapters.polymarket_adapter import PolymarketAdapter
from polymarket_engine.execution.kill_switch import KillSwitch
from polymarket_engine.utils.channel_sender import send as send_channel

CLOSED_PATH = Path("logs/trades_closed.jsonl")
OPEN_PATH = Path("logs/trades_open.jsonl")

def load_jsonl(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

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

    closed = load_jsonl(CLOSED_PATH)
    open_rows = load_jsonl(OPEN_PATH)
    open_positions = latest_open_positions(open_rows, closed)

    pnls = [float(r.get("realized_pnl", 0.0) or 0.0) for r in closed]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    total_realized = sum(pnls)
    win_rate = (len(wins) / len(pnls) * 100.0) if pnls else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0

    total_open_capital = 0.0
    total_unreal = 0.0
    by_bucket = defaultdict(list)

    for pos in open_positions:
        market_id = pos.get("market_id")
        live_px = None
        try:
            live = adapter.get_market_by_id(str(market_id))
            live_px = float(live.get("current_price", 0.0) or 0.0)
        except Exception:
            pass

        alloc = float(pos.get("allocated_capital", 0.0) or 0.0)
        total_open_capital += alloc

        unreal = 0.0
        if live_px is not None:
            unreal = calc_unrealized(pos, live_px)
            total_unreal += unreal

        by_bucket[pos.get("bucket_group_title") or "NO_BUCKET"].append({
            "allocated_capital": alloc,
            "unrealized_pnl": unreal,
            "total_edge": float(pos.get("total_edge", 0.0) or 0.0),
        })

    equity = 100000.0 + total_realized + total_unreal

    kill_switch = KillSwitch()
    allowed, kill_reason = kill_switch.check({
        "capital_state": {
            "free_capital": 100000.0 + total_realized - total_open_capital,
            "locked_capital": total_open_capital
        },
        "pnl_state": {
            "realized_pnl": total_realized,
            "unrealized_pnl": total_unreal
        },
        "position_state": {
            "open_positions_count": len(open_positions),
            "closed_positions_count": len(closed)
        },
    })

    by_reason = defaultdict(int)
    for r in closed:
        by_reason[str(r.get("close_reason") or "UNKNOWN")] += 1

    best = max(closed, key=lambda r: float(r.get("realized_pnl", 0.0) or 0.0), default=None)
    worst = min(closed, key=lambda r: float(r.get("realized_pnl", 0.0) or 0.0), default=None)

    ranked_buckets = sorted(
        by_bucket.items(),
        key=lambda kv: -sum(x["allocated_capital"] for x in kv[1])
    )[:5]

    recent_closes = sorted(closed, key=lambda r: str(r.get("ts","")))[-5:]

    mode = "EXPANSION" if len(open_positions) > 0 else "HARVEST"

    lines = []
    lines.append("POLY ENGINE DAILY")
    lines.append(f"Equity: {equity:.2f}")
    lines.append(f"Realized PnL: {total_realized:.2f}")
    lines.append(f"Unrealized PnL: {total_unreal:.2f}")
    lines.append(f"Open trades: {len(open_positions)}")
    lines.append(f"Open capital: {total_open_capital:.2f}")
    lines.append(f"Mode: {mode}")
    lines.append(f"Risk status: {'OK' if allowed else 'HALTED'}")
    if not allowed:
        lines.append(f"Risk reason: {kill_reason}")

    lines.append("")
    lines.append(f"Closed trades: {len(closed)}")
    lines.append(f"Win rate: {win_rate:.1f}%")
    lines.append(f"Avg win: {avg_win:.2f}")
    lines.append(f"Avg loss: {avg_loss:.2f}")
    lines.append(f"Profit Take: {by_reason.get('PROFIT_TAKE', 0)}")
    lines.append(f"Edge Decay: {by_reason.get('EDGE_DECAY', 0)}")

    if best:
        lines.append("")
        lines.append(f"Best trade: {best.get('market_name','?')[:54]}")
        lines.append(f"Best PnL: {float(best.get('realized_pnl',0)):.2f}")

    if worst:
        lines.append("")
        lines.append(f"Worst trade: {worst.get('market_name','?')[:54]}")
        lines.append(f"Worst PnL: {float(worst.get('realized_pnl',0)):.2f}")

    if ranked_buckets:
        lines.append("")
        lines.append("Top Buckets:")
        for bucket, rows in ranked_buckets:
            cap = sum(x["allocated_capital"] for x in rows)
            upnl = sum(x["unrealized_pnl"] for x in rows)
            avg_edge = sum(x["total_edge"] for x in rows) / max(len(rows), 1)
            lines.append(f"- {bucket[:40]} | legs={len(rows)} | cap={cap:.2f} | uPnL={upnl:.2f} | edge={avg_edge:.3f}")

    if recent_closes:
        lines.append("")
        lines.append("Recent Closes:")
        for r in recent_closes:
            pnl = float(r.get("realized_pnl", 0.0) or 0.0)
            reason = r.get("close_reason") or "UNKNOWN"
            m = str(r.get("market_name","?"))[:42]
            lines.append(f"- {m} | pnl={pnl:.2f} | {reason}")

    ok = send_channel("operator", "\n".join(lines))
    print("\n".join(lines))
    print("\nsent:", ok)


if __name__ == "__main__":
    main()
