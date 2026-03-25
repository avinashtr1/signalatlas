class MicrostructureAnalyzer:
    """
    Lightweight live microstructure scoring.

    Inputs come from:
    - market_state.liquidity_snapshot
    - MarketStateCache features:
        price_velocity
        liquidity_change
        staleness_seconds
    """

    def analyze(self, candidate, cache_features: dict):
        snap = candidate.market_state.liquidity_snapshot or {}

        volume_usd = float(snap.get("volume_usd", 0.0) or 0.0)
        depth_bps = float(snap.get("depth_bps", 0.0) or 0.0)

        price_velocity = float(cache_features.get("price_velocity", 0.0) or 0.0)
        liquidity_change = float(cache_features.get("liquidity_change", 0.0) or 0.0)
        staleness_seconds = float(cache_features.get("staleness_seconds", 0.0) or 0.0)

        score = 0.0
        reasons = []

        # 1) stale repricing
        if staleness_seconds > 20:
            score += 0.15
            reasons.append("stale_price")

        # 2) depth / liquidity weakness
        if volume_usd < 100000:
            score += 0.10
            reasons.append("thin_liquidity")
        elif volume_usd < 300000:
            score += 0.05
            reasons.append("medium_liquidity")

        # 3) fast move / repricing lag
        if abs(price_velocity) > 0.03:
            score += 0.12
            reasons.append("fast_price_move")
        elif abs(price_velocity) > 0.015:
            score += 0.06
            reasons.append("moderate_price_move")

        # 4) depth collapse / liquidity vacuum
        if liquidity_change < -50000:
            score += 0.20
            reasons.append("liquidity_vacuum")
        elif liquidity_change < -20000:
            score += 0.10
            reasons.append("liquidity_drop")

        # 5) wide / shallow book proxy
        if depth_bps >= 100:
            score += 0.08
            reasons.append("wide_book")

        # clip
        score = max(0.0, min(0.50, score))

        return {
            "microstructure_score": score,
            "microstructure_reasons": reasons,
            "price_velocity": price_velocity,
            "liquidity_change": liquidity_change,
            "staleness_seconds": staleness_seconds,
            "volume_usd": volume_usd,
            "depth_bps": depth_bps,
        }
