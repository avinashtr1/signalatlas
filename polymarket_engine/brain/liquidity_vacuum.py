class LiquidityVacuumDetector:
    """
    Live vacuum detector.
    Returns (score, signal, reason)

    Score range:
    0.0 to 0.6
    """
    def detect(self, candidate, cache_features=None):
        cache_features = cache_features or {}

        snap = candidate.market_state.liquidity_snapshot or {}
        volume_usd = float(snap.get("volume_usd", 0.0) or 0.0)
        depth_bps = float(snap.get("depth_bps", 0.0) or 0.0)

        liquidity_change = float(cache_features.get("liquidity_change", 0.0) or 0.0)
        staleness_seconds = float(cache_features.get("staleness_seconds", 0.0) or 0.0)
        price_velocity = float(cache_features.get("price_velocity", 0.0) or 0.0)

        score = 0.0
        reason = None

        # strongest case: real drop in available liquidity
        if liquidity_change <= -100000:
            score = 0.60
            reason = "severe_liquidity_drop"
        elif liquidity_change <= -50000:
            score = 0.45
            reason = "major_liquidity_drop"
        elif liquidity_change <= -20000:
            score = 0.30
            reason = "moderate_liquidity_drop"

        # thin market + wide book
        elif volume_usd < 100000 and depth_bps >= 100:
            score = 0.30
            reason = "thin_and_wide"
        elif volume_usd < 150000 and depth_bps >= 75:
            score = 0.20
            reason = "medium_thin_and_wide"

        # stale + moving = likely repricing lag / air pocket
        elif staleness_seconds > 20 and abs(price_velocity) > 0.02:
            score = 0.20
            reason = "stale_fast_move"
        elif staleness_seconds > 30:
            score = 0.10
            reason = "stale_market"

        return score, bool(score > 0.0), reason
