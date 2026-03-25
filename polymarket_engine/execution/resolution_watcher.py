from datetime import datetime, timezone


class ResolutionWatcher:
    def __init__(self, paper_executor, inventory, polymarket_adapter):
        self.paper_executor = paper_executor
        self.inventory = inventory
        self.polymarket_adapter = polymarket_adapter

    def _extract_yes_outcome_price(self, market_payload: dict):
        prices = market_payload.get("outcomePrices") or []
        if not prices:
            return None

        try:
            yes_price = float(prices[0])
        except Exception:
            return None

        if yes_price > 1.0:
            yes_price = yes_price / 100.0

        return max(0.0, min(1.0, yes_price))

    def _is_resolved(self, market_payload: dict):
        # conservative rule:
        # only settle when market is closed/inactive and we have a clear outcome price
        closed = bool(market_payload.get("closed"))
        active = bool(market_payload.get("active"))
        yes_price = self._extract_yes_outcome_price(market_payload)

        if yes_price is None:
            return False

        # prefer final-like prices
        final_like = (yes_price <= 0.001) or (yes_price >= 0.999)

        return (closed or not active) and final_like

    def check_and_settle_positions(self):
        settled_trade_ids = []

        for pos in self.paper_executor.get_open_positions():
            market_id = pos["market_id"]

            try:
                live_market = self.polymarket_adapter.get_market_by_id(market_id)
            except Exception:
                continue

            if not self._is_resolved(live_market):
                continue

            outcome_price = self._extract_yes_outcome_price(live_market)
            if outcome_price is None:
                continue

            realized_pnl = self.paper_executor.close_position(pos["trade_id"], outcome_price)
            if realized_pnl is not None:
                self.inventory.release_and_realize_pnl(
                    pos["trade_id"],
                    realized_pnl,
                    pos["strategy_type"]
                )
                settled_trade_ids.append(pos["trade_id"])

        return settled_trade_ids
