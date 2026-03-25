from datetime import datetime, timezone
from polymarket_engine.utils.trade_logger import TradeLogger
from polymarket_engine.utils.telegram_notifier import TelegramNotifier

class PaperExecutor:
    def __init__(self):
        self.positions = {}
        self.failed_fills = []
        self.trade_logger = TradeLogger()
        self.tg = TelegramNotifier()

    def execute_trade(self, decision_result, intended_trade_size):
        candidate = decision_result["candidate"]
        analysis = decision_result["analysis"]
        trade_id = candidate.candidate_id

        entry_price = candidate.market_state.current_price
        side = analysis.get("trade_side", "LONG")

        executed_trade_size = analysis.get("executed_trade_size", intended_trade_size)
        extra_slippage = analysis.get("extra_slippage", 0.0)

        if side == "SHORT":
            effective_entry_price = max(0.01, min(0.99, entry_price - extra_slippage))
            allocated_capital = executed_trade_size * (1.0 - effective_entry_price)
        else:
            effective_entry_price = max(0.01, min(0.99, entry_price + extra_slippage))
            allocated_capital = executed_trade_size * effective_entry_price

        details = candidate.signal_details or {}

        days_left = float(getattr(candidate, "days_to_resolution", 0.0) or 0.0)
        total_minutes = max(0, int(days_left * 24 * 60))
        d = total_minutes // (24 * 60)
        h = (total_minutes % (24 * 60)) // 60
        m = total_minutes % 60
        resolution_eta = f"{d}d {h}h {m}m"

        position = {
            "trade_id": trade_id,
            "market_id": candidate.market_state.market_id,
            "strategy_type": candidate.strategy_type,
            "execution_mode": analysis.get("execution_mode", "PASSIVE"),
            "status": "OPEN",
            "side": side,
            "entry_timestamp": datetime.now(timezone.utc).isoformat(),
            "entry_price": effective_entry_price,
            "filled_size_usd": executed_trade_size,
            "allocated_capital": allocated_capital,
            "fill_ratio": analysis.get("fill_ratio", 1.0),
            "extra_slippage": extra_slippage,
            "bucket_group_id": details.get("bucket_group_id"),
            "bucket_group_title": details.get("bucket_group_title"),
            "rank_score": analysis.get("rank_score"),
            "structural_edge": analysis.get("structural_edge"),
            "total_edge": analysis.get("total_edge"),
            "vacuum_score": analysis.get("vacuum_score"),
            "vacuum_reason": analysis.get("vacuum_reason"),
            "microstructure_score": analysis.get("microstructure_score"),
            "microstructure_reasons": analysis.get("microstructure_reasons"),
            "resolution_score": analysis.get("resolution_score"),
            "resolution_reason": analysis.get("resolution_reason"),
            "unrealized_pnl": executed_trade_size * analysis.get("expected_net_edge_pct", 0.0) / 100.0,
            "realized_pnl": 0.0,
        }

        
        # ensure execution_mode is persisted
        position["execution_mode"] = analysis.get("execution_mode", "PASSIVE")

        self.positions[trade_id] = position
        self.trade_logger.log_open(position, candidate=candidate, analysis=analysis)

        self.tg.send(
            "POLY OPEN\n"
            f"Mode: {position.get('execution_mode')}\n"
            f"Bucket: {position.get('bucket_group_title')}\n"
            f"Market: {candidate.market_state.name}\n"
            f"Side: {side}\n"
            f"Resolution ETA: {resolution_eta}\n"
            f"Entry: {round(effective_entry_price, 6)}\n"
            f"Capital: {round(allocated_capital, 2)}\n"
            f"Rank: {round(float(analysis.get('rank_score', 0.0) or 0.0), 4)}\n"
            f"Structural: {round(float(analysis.get('structural_edge', 0.0) or 0.0), 4)}\n"
            f"Vacuum: {round(float(analysis.get('vacuum_score', 0.0) or 0.0), 4)} ({analysis.get('vacuum_reason')})\n"
            f"Micro: {round(float(analysis.get('microstructure_score', 0.0) or 0.0), 4)} {analysis.get('microstructure_reasons')}\n"
            f"Resolution: {round(float(analysis.get('resolution_score', 0.0) or 0.0), 4)} ({analysis.get('resolution_reason')})\n"
            f"Total edge: {round(float(analysis.get('total_edge', 0.0) or 0.0), 4)}"
        )

        return position



    def update_unrealized_pnl(self, market_id, live_price):
        for pos in self.positions.values():
            if pos.get("status") != "OPEN":
                continue
            if str(pos.get("market_id")) != str(market_id):
                continue

            qty = float(pos.get("filled_size_usd", 0.0) or 0.0)
            entry = float(pos.get("entry_price", 0.0) or 0.0)
            side = str(pos.get("side", "LONG")).upper()

            if side == "SHORT":
                pnl = qty * (entry - float(live_price))
            else:
                pnl = qty * (float(live_price) - entry)

            pos["unrealized_pnl"] = float(pnl)

    def refresh_all_unrealized_pnl(self, adapter):
        for pos in self.get_open_positions():
            try:
                market = adapter.get_market_by_id(pos["market_id"])
            except Exception:
                continue

            live_price = None
            if market.get("current_price") is not None:
                try:
                    live_price = float(market.get("current_price"))
                except Exception:
                    live_price = None

            if live_price is None:
                continue

            self.update_unrealized_pnl(pos["market_id"], live_price)

    def close_position(self, trade_id, outcome_price):
        pos = self.positions.get(trade_id)
        if pos and pos.get("status") == "CLOSED":
            return None
        if not pos or pos["status"] != "OPEN":
            return None

        qty = pos["filled_size_usd"]
        entry = pos["entry_price"]
        side = pos.get("side", "LONG")

        if side == "SHORT":
            realized_pnl = qty * (entry - outcome_price)
        else:
            realized_pnl = qty * (outcome_price - entry)

        pos["status"] = "CLOSED"
        pos["realized_pnl"] = realized_pnl
        pos["unrealized_pnl"] = 0.0

        self.trade_logger.log_close(pos)

        self.tg.send(
            "POLY CLOSE\n"
            f"Bucket: {pos.get('bucket_group_title')}\n"
            f"Market ID: {pos.get('market_id')}\n"
            f"Side: {pos.get('side')}\n"
            f"Exit px: {round(float(outcome_price), 6)}\n"
            f"Realized PnL: {round(float(realized_pnl), 4)}"
        )

        return realized_pnl

    def get_open_positions(self):
        return [p for p in self.positions.values() if p.get("status") == "OPEN"]

    def get_summary(self):
        open_positions = [p for p in self.positions.values() if p.get("status") == "OPEN"]
        closed_positions = [p for p in self.positions.values() if p.get("status") == "CLOSED"]
        return {
            "total_unrealized_pnl": sum(p.get("unrealized_pnl", 0.0) for p in open_positions),
            "open_positions_count": len(open_positions),
            "closed_positions_count": len(closed_positions),
        }


    def execute_ranked(self, ranked):

        funded = 0

        for candidate, result in ranked:

            try:
                self.execute_trade(result, 300)
                funded += 1
            except Exception:
                pass

        return funded
