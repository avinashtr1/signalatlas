class ExecutionOptimizer:
    """
    Makes execution more realistic:
    - liquidity-aware sizing
    - partial fills
    - slippage penalty
    """

    def optimize(self, candidate, intended_trade_size):
        snapshot = candidate.market_state.liquidity_snapshot or {}
        volume = snapshot.get("volume_usd", 0.0)
        price = candidate.market_state.current_price

        # conservative maximum tradable notional as fraction of observed volume
        max_notional = max(25.0, volume * 0.0025)

        intended_notional = intended_trade_size * max(price, 0.01)

        fill_ratio = 1.0
        if intended_notional > max_notional:
            fill_ratio = max_notional / intended_notional

        executed_trade_size = intended_trade_size * fill_ratio

        # slippage model
        # thin liquidity + aggressive size => larger slippage
        liquidity_penalty = 0.0
        if volume < 80000:
            liquidity_penalty += 0.010
        elif volume < 150000:
            liquidity_penalty += 0.005

        size_penalty = 0.0
        if max_notional > 0:
            size_penalty = min(0.015, intended_notional / max_notional * 0.003)

        extra_slippage = liquidity_penalty + size_penalty

        return {
            "executed_trade_size": max(0.0, executed_trade_size),
            "fill_ratio": fill_ratio,
            "extra_slippage": extra_slippage,
            "max_notional": max_notional,
        }
